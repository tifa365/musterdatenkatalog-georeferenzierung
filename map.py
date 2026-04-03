from __future__ import annotations

from pathlib import Path

import folium
import geopandas as gpd

SUMMARY_GEOJSON_PATH = Path("merged_gemeinden.geojson")
OUTPUT_MAP_PATH = Path("gemeinden_map.html")


def main() -> None:
    if not SUMMARY_GEOJSON_PATH.exists():
        raise FileNotFoundError(
            "merged_gemeinden.geojson is missing. Run `uv run georeferenzierung.py` first."
        )

    gdf = gpd.read_file(SUMMARY_GEOJSON_PATH)
    if gdf.empty:
        raise ValueError("merged_gemeinden.geojson is empty.")

    minx, miny, maxx, maxy = gdf.total_bounds
    center = [(miny + maxy) / 2, (minx + maxx) / 2]
    municipality_map = folium.Map(location=center, zoom_start=6, tiles="CartoDB positron")

    tooltip = folium.GeoJsonTooltip(
        fields=["GEN", "AGS", "BEZ", "catalog_rows", "org_variants", "org_examples"],
        aliases=[
            "Municipality",
            "AGS",
            "Type",
            "Catalog rows",
            "ORG variants",
            "ORG examples",
        ],
        sticky=False,
    )

    folium.GeoJson(
        gdf,
        tooltip=tooltip,
        style_function=lambda _: {
            "fillColor": "#2f6db3",
            "color": "#0b1f33",
            "weight": 1.2,
            "fillOpacity": 0.55,
        },
        highlight_function=lambda _: {
            "fillOpacity": 0.8,
            "weight": 2,
        },
    ).add_to(municipality_map)

    municipality_map.fit_bounds([[miny, minx], [maxy, maxx]])
    municipality_map.save(OUTPUT_MAP_PATH)
    print(f"Wrote {OUTPUT_MAP_PATH}")


if __name__ == "__main__":
    main()
