from __future__ import annotations

import re
from difflib import get_close_matches
from pathlib import Path

import geopandas as gpd
import pandas as pd

CATALOG_PATH = Path("musterdatenkatalog.csv")
BOUNDARIES_PATH = Path("gemeinden_geodaten/VG250_GEM.shp")
MATCHED_ROWS_PATH = Path("musterdatenkatalog_georeferenziert.csv")
SUMMARY_GEOJSON_PATH = Path("merged_gemeinden.geojson")
MATCH_REPORT_PATH = Path("gemeinden_match_report.csv")

CSV_REQUIRED_COLUMNS = {"ORG"}
BOUNDARY_COLUMNS = ["GEN", "AGS", "BEZ", "geometry"]
SAFE_PREFIXES = (
    "gemeinde ",
    "stadt ",
    "markt ",
    "flecken ",
    "gemeindeverwaltung ",
    "amtsverwaltung ",
    "amt ",
    "verbandsgemeinde ",
    "samtgemeinde ",
    "ortsgemeinde ",
    "verwaltungsgemeinschaft ",
    "landgemeinde ",
    "landkreis ",
    "kreis ",
)
SAFE_SUFFIXES = (
    " und der beauftragenden gemeinden",
    " und der beauftragenden staedte und gemeinden",
    " und den zu erfuellenden gemeinden",
    " und den zu erfüllenden gemeinden",
)
NORMALIZED_ALIASES = {
    "freiburg i br": "freiburg im breisgau",
    "bad lobendsten": "bad lobenstein",
    "erfstadt": "erftstadt",
    "fuerstenwald spree": "fuerstenwalde spree",
    "hennef": "hennef sieg",
    "kreisstadt dietzenbach": "dietzenbach",
    "kreisstadt hofheim am taunus": "hofheim am taunus",
    "oldenburg": "oldenburg oldb",
    "tambach dietharz": "tambach dietharz thuer wald",
}
SUGGESTION_CUTOFF = 0.85
WEB_SIMPLIFY_TOLERANCE_METERS = 100


def validate_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")


def normalize_name(value: object) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("ß", "ss")
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    text = text.replace("&", " und ")
    text = re.sub(r"[-/]", " ", text)
    text = re.sub(r"[.,()]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    for prefix in SAFE_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()

    for suffix in SAFE_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()

    return NORMALIZED_ALIASES.get(text, text)


def build_match_report(catalog: pd.DataFrame, boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    municipality_names = boundaries["GEN"].dropna().astype(str).unique().tolist()
    exact_lookup: dict[str, list[str]] = {}
    municipality_lookup: dict[str, list[str]] = {}

    for name in municipality_names:
        exact_lookup.setdefault(name, []).append(name)
        municipality_lookup.setdefault(normalize_name(name), []).append(name)

    rows: list[dict[str, object]] = []
    normalized_keys = list(municipality_lookup)

    for org in sorted(catalog["ORG"].dropna().astype(str).unique()):
        normalized_org = normalize_name(org)
        exact_matches = exact_lookup.get(org, [])
        matched_gen = exact_matches[0] if len(exact_matches) == 1 else None
        match_status = "exact" if matched_gen else "unmatched"
        suggestions: list[str] = []

        if len(exact_matches) > 1:
            match_status = "ambiguous"
            suggestions = exact_matches[:3]
        elif matched_gen is None:
            normalized_matches = municipality_lookup.get(normalized_org, [])
            if len(normalized_matches) == 1:
                matched_gen = normalized_matches[0]
                match_status = "normalized"
            elif len(normalized_matches) > 1:
                match_status = "ambiguous"
                suggestions = normalized_matches[:3]
            else:
                suggestion_keys = get_close_matches(
                    normalized_org,
                    normalized_keys,
                    n=3,
                    cutoff=SUGGESTION_CUTOFF,
                )
                suggestions = [municipality_lookup[key][0] for key in suggestion_keys]

        rows.append(
            {
                "ORG": org,
                "normalized_org": normalized_org,
                "match_status": match_status,
                "matched_gen": matched_gen,
                "suggestion_1": suggestions[0] if len(suggestions) > 0 else "",
                "suggestion_2": suggestions[1] if len(suggestions) > 1 else "",
                "suggestion_3": suggestions[2] if len(suggestions) > 2 else "",
            }
        )

    report = pd.DataFrame(rows)
    report.to_csv(MATCH_REPORT_PATH, index=False)
    return report


def build_matched_rows(
    catalog: pd.DataFrame, boundaries: gpd.GeoDataFrame, match_report: pd.DataFrame
) -> pd.DataFrame:
    boundary_subset = boundaries[BOUNDARY_COLUMNS].drop_duplicates(subset=["GEN"]).copy()
    matched_rows = catalog.merge(
        match_report[["ORG", "match_status", "matched_gen"]],
        on="ORG",
        how="left",
        validate="many_to_one",
    )
    matched_rows = matched_rows.merge(
        boundary_subset.drop(columns="geometry"),
        left_on="matched_gen",
        right_on="GEN",
        how="left",
        validate="many_to_one",
    )
    matched_rows.to_csv(MATCHED_ROWS_PATH, index=False)
    return matched_rows


def build_summary_geojson(
    matched_rows: pd.DataFrame, boundaries: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    matched_only = matched_rows[matched_rows["matched_gen"].notna()].copy()

    if matched_only.empty:
        raise ValueError("No municipalities matched. Check gemeinden_match_report.csv.")

    summary = (
        matched_only.groupby("matched_gen", as_index=False)
        .agg(
            catalog_rows=("ORG", "size"),
            org_variants=("ORG", "nunique"),
            org_examples=("ORG", lambda values: "; ".join(sorted(pd.unique(values))[:5])),
        )
        .rename(columns={"matched_gen": "GEN"})
    )

    boundary_subset = boundaries[BOUNDARY_COLUMNS].drop_duplicates(subset=["GEN"]).copy()
    summary_gdf = boundary_subset.merge(summary, on="GEN", how="inner", validate="one_to_one")
    summary_gdf = gpd.GeoDataFrame(summary_gdf, geometry="geometry", crs=boundaries.crs)
    summary_gdf = summary_gdf.to_crs(3857)
    summary_gdf["geometry"] = summary_gdf.geometry.simplify(
        WEB_SIMPLIFY_TOLERANCE_METERS,
        preserve_topology=True,
    )
    summary_gdf = summary_gdf.to_crs(4326)
    summary_gdf.to_file(SUMMARY_GEOJSON_PATH, driver="GeoJSON", index=False)
    return summary_gdf


def main() -> None:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(
            "musterdatenkatalog.csv is missing. Run `uv run python scripts/download_musterdatenkatalog.py` first."
        )
    if not BOUNDARIES_PATH.exists():
        raise FileNotFoundError(
            "gemeinden_geodaten/VG250_GEM.shp is missing. "
            "Run `uv run python scripts/download_gemeinden_geodaten.py` first."
        )

    catalog = pd.read_csv(CATALOG_PATH)
    validate_columns(catalog, CSV_REQUIRED_COLUMNS, "musterdatenkatalog.csv")

    boundaries = gpd.read_file(BOUNDARIES_PATH)
    validate_columns(boundaries, {"GEN"}, str(BOUNDARIES_PATH))

    match_report = build_match_report(catalog, boundaries)
    matched_rows = build_matched_rows(catalog, boundaries, match_report)
    summary_gdf = build_summary_geojson(matched_rows, boundaries)

    status_counts = match_report["match_status"].value_counts().to_dict()
    print(f"Wrote {MATCH_REPORT_PATH}")
    print(f"Wrote {MATCHED_ROWS_PATH}")
    print(f"Wrote {SUMMARY_GEOJSON_PATH} with {len(summary_gdf)} municipalities")
    print(f"Match status counts: {status_counts}")


if __name__ == "__main__":
    main()
