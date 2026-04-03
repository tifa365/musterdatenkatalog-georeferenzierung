from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

import georeferenzierung


def test_normalize_name_handles_prefixes_and_safe_aliases() -> None:
    assert georeferenzierung.normalize_name("Gemeinde Bad Zwischenahn") == "bad zwischenahn"
    assert georeferenzierung.normalize_name("Fürstenwald/Spree") == "fuerstenwalde spree"
    assert georeferenzierung.normalize_name("Kreisstadt Dietzenbach") == "dietzenbach"


def test_build_match_report_distinguishes_exact_normalized_and_unmatched(tmp_path: Path) -> None:
    catalog = pd.DataFrame(
        {
            "ORG": [
                "Dietzenbach",
                "Kreisstadt Hofheim am Taunus",
                "Landau",
            ]
        }
    )
    boundaries = gpd.GeoDataFrame(
        {
            "GEN": ["Dietzenbach", "Hofheim am Taunus"],
            "AGS": ["1", "2"],
            "BEZ": ["Stadt", "Stadt"],
            "geometry": [Point(0, 0), Point(1, 1)],
        },
        geometry="geometry",
        crs=4326,
    )

    original_report_path = georeferenzierung.MATCH_REPORT_PATH
    georeferenzierung.MATCH_REPORT_PATH = tmp_path / "gemeinden_match_report.csv"
    try:
        report = georeferenzierung.build_match_report(catalog, boundaries)
    finally:
        georeferenzierung.MATCH_REPORT_PATH = original_report_path

    rows = report.set_index("ORG")
    assert rows.loc["Dietzenbach", "match_status"] == "exact"
    assert rows.loc["Kreisstadt Hofheim am Taunus", "match_status"] == "normalized"
    assert rows.loc["Kreisstadt Hofheim am Taunus", "matched_gen"] == "Hofheim am Taunus"
    assert rows.loc["Landau", "match_status"] == "unmatched"


def test_main_shows_explicit_message_when_csv_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(georeferenzierung, "CATALOG_PATH", tmp_path / "missing.csv")
    monkeypatch.setattr(georeferenzierung, "BOUNDARIES_PATH", tmp_path / "VG250_GEM.shp")

    with pytest.raises(FileNotFoundError, match="download_musterdatenkatalog.py"):
        georeferenzierung.main()


def test_main_shows_explicit_message_when_geodata_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv_path = tmp_path / "musterdatenkatalog.csv"
    csv_path.write_text("ORG\nDietzenbach\n", encoding="utf-8")
    monkeypatch.setattr(georeferenzierung, "CATALOG_PATH", csv_path)
    monkeypatch.setattr(georeferenzierung, "BOUNDARIES_PATH", tmp_path / "VG250_GEM.shp")

    with pytest.raises(FileNotFoundError, match="download_gemeinden_geodaten.py"):
        georeferenzierung.main()
