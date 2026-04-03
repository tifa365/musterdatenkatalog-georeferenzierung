from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

SOURCE_URL = (
    "https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/aktuell/"
    "vg250_01-01.utm32s.shape.ebenen.zip"
)
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "gemeinden_geodaten"
TARGET_PREFIX = "VG250_GEM"
TARGET_SUFFIXES = {".shp", ".shx", ".dbf", ".prj", ".cpg"}


def download_archive(source_url: str, output_path: Path) -> None:
    with urlopen(source_url) as response, output_path.open("wb") as destination:
        shutil.copyfileobj(response, destination)


def extract_gemeinden(zip_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as archive:
        members = [
            member
            for member in archive.namelist()
            if Path(member).name.startswith(TARGET_PREFIX)
            and Path(member).suffix.lower() in TARGET_SUFFIXES
        ]

        if not members:
            raise SystemExit(
                "The downloaded BKG archive does not contain the expected VG250_GEM files."
            )

        for member in members:
            target_path = output_dir / Path(member).name
            with archive.open(member) as source, target_path.open("wb") as destination:
                shutil.copyfileobj(source, destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and extract the official BKG VG250 municipality shapefile."
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=DEFAULT_OUTPUT_DIR,
        type=Path,
        help=f"Directory for the extracted VG250_GEM files (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        delete=False,
        dir=output_dir.parent,
        prefix="gemeinden_geodaten.tmp.",
        suffix=".zip",
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)

    try:
        try:
            download_archive(SOURCE_URL, tmp_path)
        except HTTPError as exc:
            raise SystemExit(
                "Could not download municipality geodata from the official BKG source "
                f"({exc.code} {exc.reason})."
            ) from exc
        except URLError as exc:
            raise SystemExit(
                "Could not reach the official BKG source for municipality geodata: "
                f"{exc.reason}"
            ) from exc

        extract_gemeinden(tmp_path, output_dir)
    except OSError as exc:
        raise SystemExit(f"Could not prepare municipality geodata: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    print(f"Wrote {output_dir / 'VG250_GEM.shp'}")


if __name__ == "__main__":
    sys.exit(main())
