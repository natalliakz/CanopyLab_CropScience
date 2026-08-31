"""Run a `.ggsql` file against the project database and save the chart.

This project contains synthetic data and analysis created for demonstration
purposes only.

ggsql queries are plain text, which means they live in version control, get code
reviewed, and can be run by anything -- a notebook cell, this script, or the ggsql
CLI. Keeping the query in a `.ggsql` file rather than buried in a notebook is the
habit that gets an analysis out of one person's laptop.

Usage:
    uv run python python/run_ggsql.py sql/02-treatment-response.ggsql
    uv run python python/run_ggsql.py            # runs every .ggsql file

Outputs land in `outputs/` as interactive HTML plus a PNG for slides.
"""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import ggsql

ROOT = Path(__file__).resolve().parent.parent
DUCKDB_PATH = ROOT / "data" / "synthetic-agronomy.duckdb"
SQL_DIR = ROOT / "sql"
OUTPUT_DIR = ROOT / "outputs"


def reader() -> ggsql.DuckDBReader:
    """A ggsql reader pointed at the project's DuckDB file.

    The URL is relative to nothing -- it is resolved here so the script works from
    any working directory, which matters once a scheduled job on Connect is the
    thing running it.
    """
    if not DUCKDB_PATH.exists():
        raise SystemExit(
            f"No database at {DUCKDB_PATH}.\n"
            "Run `uv run python data/generate_data.py` first."
        )
    return ggsql.DuckDBReader(f"duckdb://{DUCKDB_PATH}")


def run(path: Path) -> Path:
    """Execute one `.ggsql` file, returning the path of the saved HTML chart."""
    query = path.read_text()

    # `validate()` checks the ggsql grammar without touching the database, so a
    # typo in a VISUALISE clause fails fast with a useful message.
    ggsql.validate(query)

    # ggsql compiles the query to a Vega-Lite specification. Altair reads that
    # spec directly, which is how the same query can end up in a notebook, an
    # HTML report or a PNG for a slide without being rewritten.
    spec = reader().execute(query)
    chart = alt.Chart.from_json(ggsql.VegaLiteWriter().render(spec))

    # A single-panel chart has no intrinsic size, so give it one; a faceted chart
    # sizes its own panels and rejects a width at the top level.
    if not isinstance(chart, alt.FacetChart):
        chart = chart.properties(width=700, height=400)

    OUTPUT_DIR.mkdir(exist_ok=True)
    html_path = OUTPUT_DIR / f"{path.stem}.html"
    chart.save(str(html_path))

    # vl-convert renders the same spec to a static image for slide decks.
    try:
        chart.save(str(OUTPUT_DIR / f"{path.stem}.png"), ppi=144)
    except Exception as error:  # pragma: no cover - image export is optional
        print(f"  (PNG export skipped: {error})")

    return html_path


def main() -> None:
    if len(sys.argv) > 1:
        paths = [Path(argument) for argument in sys.argv[1:]]
    else:
        paths = sorted(SQL_DIR.glob("*.ggsql"))

    for path in paths:
        print(f"{path} ->")
        print(f"  {run(path).relative_to(ROOT)}")

    print(
        "\nThis project contains synthetic data and analysis created for "
        "demonstration purposes only."
    )


if __name__ == "__main__":
    main()
