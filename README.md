# Musterdatenkatalog Georeferenzierung

This project georeferences municipality names from the Musterdatenkatalog CSV using official German municipality boundaries and turns the result into a map.

## What It Does

The workflow combines two data sources:

- `musterdatenkatalog.csv`: the source table, using the `ORG` column for municipality names
- `gemeinden_geodaten/VG250_GEM.shp`: the municipality boundary shapefile

The result is a normalized match report, a row-level CSV with matched municipality metadata, a compact municipality GeoJSON, and an HTML map.

## Workflow

1. `georeferenzierung.py` reads the CSV and normalizes municipality names from `ORG`.
2. It matches those names against `GEN` in the shapefile, including a few safe aliases.
3. It writes `gemeinden_match_report.csv` for exact, normalized, and unmatched names.
4. It writes `musterdatenkatalog_georeferenziert.csv` with row-level match metadata.
5. It writes `merged_gemeinden.geojson` with one feature per matched municipality.
6. `map.py` reads that GeoJSON and creates `gemeinden_map.html` with Folium.

## Files

- `georeferenzierung.py`: CSV-to-geometry matching step
- `map.py`: map rendering step
- `pyproject.toml`: project metadata and Python dependencies managed by `uv`
- `uv.lock`: locked dependency versions for reproducible environments
- `gemeinden_match_report.csv`: unique `ORG` values with match status and suggestions
- `musterdatenkatalog_georeferenziert.csv`: row-level catalog data plus matched municipality fields
- `merged_gemeinden.geojson`: compact municipality-level geospatial output
- `gemeinden_map.html`: generated interactive map

## Run Locally

Use `make` as the main entry point. Run `make all` for the main workflow:

```bash
make all
```

`make all` downloads the raw inputs, builds the matched outputs, and generates the HTML map. For setup and validation around that workflow, run:

```bash
make sync
make all
make test
```

This sequence installs dependencies, runs the full pipeline, and executes the offline test suite.

Individual `make` targets:

- `make sync`: install project and dev dependencies
- `make data`: download the raw catalog CSV and municipality geodata
- `make build`: generate the match report, enriched CSV, and merged GeoJSON
- `make map`: generate `gemeinden_map.html`
- `make all`: run the full download/build/map workflow
- `make test`: run the offline compile check and `pytest` suite

Raw inputs are downloaded from official sources:

- Musterdatenkatalog CSV: `https://www.bertelsmann-stiftung.de/fileadmin/files/musterdatenkatalog/2025-06-13_musterdatenkatalog.csv`
- Municipality geodata: BKG VG250 Gemeinden (`VG250_GEM`) via the official BKG direct download

## Related Project

This repository is a downstream georeferencing and mapping workflow for the Musterdatenkatalog. The main Musterdatenkatalog repository and issue tracker are here:

- Main repository: `https://github.com/bertelsmannstift/Musterdatenkatalog-V4`

## Important Note

Matching is no longer exact-name only. The script removes safe administrative prefixes such as `Gemeinde` and `Verbandsgemeinde`, applies a small alias list for known shorthand and typo cases, and writes unmatched names with suggestions to `gemeinden_match_report.csv`. The current alias list already fixes `Fürstenwald/Spree`, `Kreisstadt Dietzenbach`, and `Kreisstadt Hofheim am Taunus`.

If a required input file is missing, the scripts fail with an explicit download instruction instead of silently generating partial results.

## Current Unmatched Cases

In the current data snapshot, `gemeinden_match_report.csv` still contains `78` unmatched `ORG` values. Most of them are not single municipalities, so leaving them unmatched is correct with the current municipality shapefile:

- `39` are districts or counties, for example `Ennepe-Ruhr-Kreis`, `Rhein-Kreis Neuss`, and `Wetteraukreis`
- `35` are supra-municipal administrative units, for example `Amt Schlei-Ostsee`, `Verbandsgemeinde Südeifel`, and `Verwaltungsgemeinschaft Nesseaue`
- `4` look like municipality naming issues, typos, or ambiguous short forms, for example `Landau`, `Gronau`, `Harburg`, and `Wetter`

Examples of likely fixable name issues:

- `Verbandsgemeinde Traben-Trabach` likely refers to `Traben-Trarbach`
- `Landkreis Neustadt an der Waldnaab` aligns with `Neustadt a.d.Waldnaab`
- `Stolberg` may need `Stolberg (Rhld.)`
- `Harburg` may need `Harburg (Schwaben)`, but the short form is risky

Examples that remain intentionally unmatched because they are not municipalities:

- `Amt Schlei-Ostsee`
- `Ennepe-Ruhr-Kreis`
- `Kyffhäuserkreis`
