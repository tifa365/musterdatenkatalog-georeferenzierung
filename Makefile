.PHONY: help sync data download-catalog download-geodata build map all test clean

help:
	@printf "Targets:\n"
	@printf "  make sync              Install project and dev dependencies with uv\n"
	@printf "  make data              Download the raw CSV and municipality geodata\n"
	@printf "  make download-catalog  Download the Musterdatenkatalog CSV\n"
	@printf "  make download-geodata  Download the BKG VG250 municipality shapefile\n"
	@printf "  make build             Generate match report, enriched CSV, and GeoJSON\n"
	@printf "  make map               Generate the HTML map from merged_gemeinden.geojson\n"
	@printf "  make all               Run data, build, and map in sequence\n"
	@printf "  make test              Run the offline test suite\n"
	@printf "  make clean             Remove ignored raw inputs and transient outputs\n"

sync:
	uv sync --group dev

data: download-catalog download-geodata

download-catalog:
	uv run python scripts/download_musterdatenkatalog.py

download-geodata:
	uv run python scripts/download_gemeinden_geodaten.py

build:
	uv run georeferenzierung.py

map:
	uv run map.py

all: data build map

test:
	uv run --group dev python -m py_compile georeferenzierung.py map.py scripts/download_musterdatenkatalog.py scripts/download_gemeinden_geodaten.py
	uv run --group dev pytest

clean:
	rm -rf __pycache__ scripts/__pycache__ tests/__pycache__ gemeinden_geodaten musterdatenkatalog.csv musterdatenkatalog_georeferenziert.csv gemeinden_match_report.csv
