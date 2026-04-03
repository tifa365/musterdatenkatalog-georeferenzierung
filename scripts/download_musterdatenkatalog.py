from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

SOURCE_URL = (
    "https://www.bertelsmann-stiftung.de/fileadmin/files/"
    "musterdatenkatalog/2025-06-13_musterdatenkatalog.csv"
)


def download_file(source_url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        delete=False,
        dir=output_path.parent,
        prefix=f"{output_path.name}.tmp.",
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)

    try:
        with urlopen(source_url) as response, tmp_path.open("wb") as destination:
            shutil.copyfileobj(response, destination)
        tmp_path.replace(output_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    default_output = Path(__file__).resolve().parent.parent / "musterdatenkatalog.csv"
    parser = argparse.ArgumentParser(
        description="Download the Musterdatenkatalog CSV from the official Bertelsmann Stiftung URL."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default=default_output,
        type=Path,
        help=f"Output path for the downloaded CSV (default: {default_output})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        download_file(SOURCE_URL, args.output)
    except HTTPError as exc:
        raise SystemExit(
            "Could not download musterdatenkatalog.csv from the official Bertelsmann "
            f"Stiftung source ({exc.code} {exc.reason})."
        ) from exc
    except URLError as exc:
        raise SystemExit(
            "Could not reach the official Bertelsmann Stiftung source for "
            f"musterdatenkatalog.csv: {exc.reason}"
        ) from exc
    except OSError as exc:
        raise SystemExit(f"Could not write musterdatenkatalog.csv: {exc}") from exc

    print(f"Wrote {args.output}")


if __name__ == "__main__":
    sys.exit(main())
