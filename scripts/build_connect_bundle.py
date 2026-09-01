#!/usr/bin/env python3
"""Assemble the git-backed Connect bundle for the Streamlit app.

Connect can deploy content straight from a Git repository: you point it at a
repository, a branch and a *subdirectory*, and it re-deploys whatever that
directory contains whenever the branch moves. There is no build step and no CI
runner in that path -- Connect reads the committed files and nothing else. So the
directory has to be self-contained: the app, the shared modules it imports, the
brand file, the data, a `requirements.txt` and a `manifest.json`.

`connect/streamlit/` is that directory, and this script builds it. It is a mirror
of the subset of the project root the app needs, which is why the app itself needs
no path juggling: `python/`, `_brand.yml` and `data/` sit in the same places
relative to `streamlit_app.py` as they do in the repository.

    uv run python scripts/build_connect_bundle.py            # rebuild and commit
    uv run python scripts/build_connect_bundle.py --check    # fail if it drifted

Everything this script writes is committed, and CI runs `--check` on every pull
request, so the bundle cannot quietly fall behind the source it was copied from.
Edit the originals, never the copies.

Standard library only, deliberately: `--check` should run on a bare CI runner.

This project contains synthetic data and analysis created for demonstration
purposes only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "connect" / "streamlit"

ENTRYPOINT = "streamlit_app.py"

#: Copied from the project root into the bundle, source -> destination. The paths
#: match on both sides on purpose.
COPIES = {
    "streamlit_app.py": "streamlit_app.py",
    ".streamlit/config.toml": ".streamlit/config.toml",
    "_brand.yml": "_brand.yml",
    "python/trials.py": "python/trials.py",
    "python/charts.py": "python/charts.py",
    # The CSVs rather than the DuckDB file: they are text, they diff, and
    # `trials.py` reads them when the database is absent -- which it is here,
    # because a git-backed deployment cannot run `data/generate_data.py`.
    "data/synthetic-field-trials.csv": "data/synthetic-field-trials.csv",
    "data/synthetic-sites.csv": "data/synthetic-sites.csv",
}

#: Lives in the bundle and is maintained by hand, so it is listed in the manifest
#: but never copied over.
BUNDLE_OWNED = ("requirements.txt",)

#: Advisory. Connect honours `environment.python.requires` when it is present, so
#: the range below is the constraint that actually matters -- any 3.12 or newer
#: interpreter on the server will do. Both are safe to bump; they are pinned to
#: constants rather than read from the local interpreter so that the manifest this
#: script writes is byte-identical on a laptop and on a CI runner.
PYTHON_VERSION = "3.13.2"
PYTHON_REQUIRES = ">=3.12"


def checksum(path: Path) -> str:
    """The md5 Connect expects in `manifest.json`, matching rsconnect's format."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def manifest(bundle: Path) -> dict:
    """The manifest for the bundle as it currently sits on disk."""
    files = sorted([*COPIES.values(), *BUNDLE_OWNED])
    return {
        "version": 1,
        "locale": "en_US.UTF-8",
        "metadata": {"appmode": "python-streamlit", "entrypoint": ENTRYPOINT},
        "python": {
            "version": PYTHON_VERSION,
            "package_manager": {"name": "pip", "package_file": "requirements.txt"},
        },
        "environment": {"python": {"requires": PYTHON_REQUIRES}},
        "files": {name: {"checksum": checksum(bundle / name)} for name in files},
    }


def rendered(data: dict) -> str:
    return json.dumps(data, indent=2) + "\n"


def build() -> list[str]:
    """Copy the sources in and write the manifest. Returns what changed."""
    changed = []

    for source, destination in COPIES.items():
        origin, target = ROOT / source, BUNDLE / destination
        if not origin.exists():
            sys.exit(
                f"Missing {source}.\n"
                "Generate the data first:  uv run python data/generate_data.py"
            )
        if not target.exists() or target.read_bytes() != origin.read_bytes():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, target)
            changed.append(destination)

    for name in BUNDLE_OWNED:
        if not (BUNDLE / name).exists():
            sys.exit(f"Missing connect/streamlit/{name}, which is not generated.")

    written = rendered(manifest(BUNDLE))
    target = BUNDLE / "manifest.json"
    if not target.exists() or target.read_text() != written:
        target.write_text(written)
        changed.append("manifest.json")

    return changed


def check() -> int:
    """Report drift without writing anything."""
    stale = [
        destination
        for source, destination in COPIES.items()
        if not (BUNDLE / destination).exists()
        or (BUNDLE / destination).read_bytes() != (ROOT / source).read_bytes()
    ]

    current = BUNDLE / "manifest.json"
    if not current.exists() or current.read_text() != rendered(manifest(BUNDLE)):
        stale.append("manifest.json")

    if stale:
        print("connect/streamlit/ is out of date:")
        for name in stale:
            print(f"  {name}")
        print("\nRebuild it:  uv run python scripts/build_connect_bundle.py")
        return 1

    print("connect/streamlit/ matches its sources.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the bundle differs from its sources",
    )
    arguments = parser.parse_args()

    if arguments.check:
        return check()

    changed = build()
    if changed:
        print("Updated connect/streamlit/:")
        for name in changed:
            print(f"  {name}")
        print("\nCommit the result -- Connect deploys the committed files.")
    else:
        print("connect/streamlit/ was already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
