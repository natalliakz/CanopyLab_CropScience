"""Shared field trial logic for the Python side of the project.

The Python counterpart to the `canopytrials` R package, and it exists for the same
reason: the Streamlit app and the MCP server both need to answer "what did the
protection programme gain us", and they must not answer it differently. The
definition lives here once, with tests in `tests/test_trials.py`.

The one rule worth stating out loud: **yield response is measured against the same
hybrid's own untreated plots**, never against the trial-wide average. Hybrids
differ in genetic potential, and comparing a treated plot to the overall mean would
credit the protection programme with genetics it had nothing to do with.

This project contains synthetic data and analysis created for demonstration
purposes only.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import polars as pl
import yaml

CHECK = "Untreated Check"

DISCLAIMER = (
    "This project contains synthetic data and analysis created for demonstration "
    "purposes only."
)

#: Fixed programme -> palette-name mapping. Colour follows the entity, so the
#: control stays grey no matter which programmes a filter leaves on screen.
TREATMENT_COLORS = {
    CHECK: "stone",
    "Programme Alpha": "sky",
    "Programme Bravo": "leaf",
}


def project_root() -> Path:
    """The project directory, wherever this module has been copied to.

    `CANOPYLAB_ROOT` wins, so a Connect bundle or a container can say where the
    project lives instead of relying on the layout of the repository.
    """
    override = os.environ.get("CANOPYLAB_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent


MISSING_DATA = (
    "No trial data found: expected either data/synthetic-agronomy.duckdb or the\n"
    "two synthetic-*.csv files. Generate them first:\n"
    "  uv run python data/generate_data.py"
)


def database_path() -> Path:
    """Locate the DuckDB file, and say how to make it if it is missing."""
    override = os.environ.get("CANOPYLAB_DB")
    candidates = [Path(override)] if override else []
    here = Path(__file__).resolve().parent
    candidates += [
        here / "synthetic-agronomy.duckdb",  # copied beside us in a bundle
        project_root() / "data" / "synthetic-agronomy.duckdb",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(MISSING_DATA)


def csv_paths() -> tuple[Path, Path]:
    """Locate the two committed CSVs: trial plots and stations.

    The CSVs are the fallback data source, and they are the reason a git-backed
    Connect deployment works at all: git-backed content has no build step, so
    nothing can run `generate_data.py` before the app starts. The CSVs are small
    and text, so they live in the repository; the DuckDB file does not.
    """
    for directory in (Path(__file__).resolve().parent, project_root() / "data"):
        trials = directory / "synthetic-field-trials.csv"
        sites = directory / "synthetic-sites.csv"
        if trials.exists() and sites.exists():
            return trials, sites

    raise FileNotFoundError(MISSING_DATA)


def _connect() -> duckdb.DuckDBPyConnection:
    """Open the trial data, preferring the database and falling back to the CSVs.

    Either way the caller sees the same three relations -- `field_trials`, `sites`
    and `variety_season_summary` -- so a query written against the DuckDB file in
    Positron's Connections pane also runs inside a CSV-only Connect bundle.
    """
    try:
        return duckdb.connect(str(database_path()), read_only=True)
    except FileNotFoundError:
        pass

    trials, sites = csv_paths()
    connection = duckdb.connect()
    for relation, path in (("field_trials", trials), ("sites", sites)):
        # Inlined rather than bound: DuckDB does not accept prepared parameters in
        # DDL. The paths come from this module, not from a caller.
        literal = str(path).replace("'", "''")
        connection.execute(
            f"CREATE VIEW {relation} AS SELECT * FROM read_csv_auto('{literal}')"
        )
    connection.execute(
        """
        CREATE VIEW variety_season_summary AS
        SELECT
            season,
            variety,
            treatment,
            count(*)                              AS plots,
            round(avg(yield_t_ha), 2)             AS mean_yield_t_ha,
            round(avg(disease_pressure_index), 1) AS mean_disease_index
        FROM field_trials
        GROUP BY season, variety, treatment
        """
    )
    return connection


def query(sql: str, params: list | None = None) -> pl.DataFrame:
    """Run one read-only query and close the connection.

    A new connection per call, deliberately: Connect may run several processes of
    the same content, and a shared long-lived handle to a file-backed database is
    the wrong shape for that.
    """
    connection = _connect()
    try:
        return connection.execute(sql, params or []).pl()
    finally:
        connection.close()


def read_plots() -> pl.DataFrame:
    """Every harvested plot, joined to its station's soil type."""
    return query(
        """
        SELECT t.*, s.soil_type, s.elevation_m, s.normal_rainfall_mm
        FROM field_trials t
        JOIN sites s USING (site_id, site_name, region)
        ORDER BY t.season, t.site_name, t.variety, t.treatment, t.replicate
        """
    )


def read_sites() -> pl.DataFrame:
    """One row per research station."""
    return query("SELECT * FROM sites ORDER BY site_name")


def yield_response(plots: pl.DataFrame, check: str = CHECK) -> pl.DataFrame:
    """Mean yield per hybrid and programme, with the gain over its own check.

    Raises if the control is absent: a gain with nothing to be a gain over is a
    number people would quote, so refuse to produce it.
    """
    if check not in plots.get_column("treatment").unique().to_list():
        raise ValueError(
            f"No {check!r} plots in this data, so there is nothing to measure a "
            "gain against."
        )

    means = plots.group_by("variety", "treatment").agg(
        plots=pl.len(),
        mean_yield_t_ha=pl.col("yield_t_ha").mean(),
        sd_yield_t_ha=pl.col("yield_t_ha").std(),
        mean_disease_index=pl.col("disease_pressure_index").mean(),
    )

    checks = means.filter(pl.col("treatment") == check).select(
        "variety", check_yield=pl.col("mean_yield_t_ha")
    )

    return (
        means.join(checks, on="variety", how="inner")
        .with_columns(
            gain_vs_check_t_ha=pl.col("mean_yield_t_ha") - pl.col("check_yield")
        )
        .drop("check_yield")
        .sort("variety", "gain_vs_check_t_ha")
    )


def site_summary(plots: pl.DataFrame) -> pl.DataFrame:
    """One row per station, best yield first."""
    return (
        plots.group_by("site_name", "region")
        .agg(
            plots=pl.len(),
            mean_yield_t_ha=pl.col("yield_t_ha").mean(),
            mean_disease_index=pl.col("disease_pressure_index").mean(),
            mean_rainfall_mm=pl.col("rainfall_mm").mean(),
        )
        .sort("mean_yield_t_ha", descending=True)
    )


def season_trend(plots: pl.DataFrame, by: str = "treatment") -> pl.DataFrame:
    """Mean yield per season, grouped by treatment (or by variety)."""
    if by not in {"treatment", "variety"}:
        raise ValueError("`by` must be 'treatment' or 'variety'.")

    return (
        plots.group_by("season", by)
        .agg(
            plots=pl.len(),
            mean_yield_t_ha=pl.col("yield_t_ha").mean(),
            mean_disease_index=pl.col("disease_pressure_index").mean(),
        )
        .sort("season", by)
    )


def palette() -> dict[str, str]:
    """The brand palette, read from `_brand.yml` rather than hard-coded.

    Same file the Quarto report, the Shiny app and the ggplot theme read. Editing
    it re-brands the Streamlit app too, which is the whole point of the file.
    """
    brand_file = project_root() / "_brand.yml"
    if not brand_file.exists():  # a bundle that ships without the brand file
        return {
            "leaf": "#3E7B52", "canopy": "#2A5638", "sprout": "#8FBF7A",
            "loam": "#8A6A4A", "grain": "#D8A93B", "sky": "#3D7CA8",
            "clay": "#B4472E", "stone": "#6E7671", "mist": "#EFF3EE",
            "hairline": "#D6DED7", "black": "#1A1F1B", "white": "#FFFFFF",
        }
    return yaml.safe_load(brand_file.read_text())["color"]["palette"]


def treatment_scale() -> tuple[list[str], list[str]]:
    """Domain and range for colouring treatments, in a fixed order."""
    colors = palette()
    domain = list(TREATMENT_COLORS)
    return domain, [colors[TREATMENT_COLORS[name]] for name in domain]
