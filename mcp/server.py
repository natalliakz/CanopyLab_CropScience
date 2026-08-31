"""CanopyLab field trial MCP server.

An MCP server that answers questions about the trial results, published to Posit
Connect and used from Posit Assistant inside Positron. Connect hosts it like any
other content: same permissions model, same logs, same audit trail — so an
assistant that can read internal trial data is governed the same way a Shiny app is.

Run locally:
    uv run fastmcp run mcp/server.py:mcp --transport http --port 8000

Publish to Connect (see MCP-SETUP.md for the whole story):
    rsconnect deploy fastapi -n <server-nickname> --entrypoint server:app ./mcp

The data in here is synthetic and exists for demonstration purposes only.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
from fastmcp import FastMCP

DISCLAIMER = (
    "CanopyLab Agronomics is a fictional company. This project contains synthetic "
    "data and analysis created for demonstration purposes only."
)


def database_path() -> Path:
    """Find the DuckDB file locally, in CI, and in a Connect content bundle.

    Connect unpacks the bundle into its own directory, so nothing may assume the
    repository layout. `CANOPYLAB_DB` wins, then a copy next to this file (which
    is what the deploy step ships), then the project's data directory.
    """
    override = os.environ.get("CANOPYLAB_DB")
    if override:
        return Path(override)

    here = Path(__file__).parent
    candidates = [
        here / "synthetic-agronomy.duckdb",
        here.parent / "data" / "synthetic-agronomy.duckdb",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "No synthetic-agronomy.duckdb found. Generate it first:\n"
        "  uv run python data/generate_data.py"
    )


def query(sql: str, params: list | None = None) -> list[dict]:
    """One read-only connection per call, closed straight after.

    Connect may run several processes of this server, so a shared long-lived
    handle to a file-backed database is the wrong shape.
    """
    connection = duckdb.connect(str(database_path()), read_only=True)
    try:
        result = connection.execute(sql, params or [])
        columns = [description[0] for description in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]
    finally:
        connection.close()


mcp = FastMCP(
    name="canopylab-trials",
    instructions=(
        "Answers questions about CanopyLab's synthetic field trial programme: "
        "yield by hybrid and protection programme, station detail, season trends, "
        "and disease pressure. Yield response is always measured against the same "
        "hybrid's own untreated check plots. " + DISCLAIMER
    ),
)


@mcp.tool
def list_hybrids() -> list[dict]:
    """List the hybrids under trial with their plot counts and mean yield."""
    return query(
        """
        SELECT variety                            AS hybrid,
               count(*)                           AS plots,
               round(avg(yield_t_ha), 2)          AS mean_yield_t_ha,
               round(avg(disease_pressure_index), 1) AS mean_disease_index
        FROM field_trials
        GROUP BY variety
        ORDER BY mean_yield_t_ha DESC
        """
    )


@mcp.tool
def yield_response(hybrid: str | None = None) -> list[dict]:
    """Yield gain of each protection programme over the untreated check.

    The gain is measured against the same hybrid's own untreated plots, never the
    trial-wide average — hybrids differ in genetic potential, and crediting the
    programme with genetics would overstate it.

    Args:
        hybrid: Optional hybrid name, e.g. "CL-Ember 33". Omit for all hybrids.
    """
    return query(
        """
        WITH means AS (
            SELECT variety, treatment,
                   avg(yield_t_ha) AS mean_yield,
                   count(*)        AS plots
            FROM field_trials
            WHERE ? IS NULL OR variety = ?
            GROUP BY variety, treatment
        ),
        checks AS (
            SELECT variety, mean_yield AS check_yield
            FROM means
            WHERE treatment = 'Untreated Check'
        )
        SELECT m.variety                                       AS hybrid,
               m.treatment                                     AS programme,
               m.plots,
               round(m.mean_yield, 2)                          AS mean_yield_t_ha,
               round(m.mean_yield - c.check_yield, 2)          AS gain_vs_check_t_ha
        FROM means m
        JOIN checks c USING (variety)
        ORDER BY m.variety, gain_vs_check_t_ha
        """,
        [hybrid, hybrid],
    )


@mcp.tool
def station_summary() -> list[dict]:
    """Mean yield, disease pressure and rainfall for each trial station."""
    return query(
        """
        SELECT t.site_name                             AS station,
               t.region,
               s.soil_type,
               count(*)                                AS plots,
               round(avg(t.yield_t_ha), 2)             AS mean_yield_t_ha,
               round(avg(t.disease_pressure_index), 1) AS mean_disease_index,
               round(avg(t.rainfall_mm), 0)            AS mean_rainfall_mm
        FROM field_trials t
        JOIN sites s ON s.site_name = t.site_name
        GROUP BY t.site_name, t.region, s.soil_type
        ORDER BY mean_yield_t_ha DESC
        """
    )


@mcp.tool
def season_trend(programme: str = "Programme Bravo") -> list[dict]:
    """Mean yield per hybrid per season under one protection programme.

    Args:
        programme: "Untreated Check", "Programme Alpha" or "Programme Bravo".
    """
    return query(
        """
        SELECT season,
               variety                     AS hybrid,
               round(avg(yield_t_ha), 2)   AS mean_yield_t_ha,
               round(avg(rainfall_mm), 0)  AS mean_rainfall_mm
        FROM field_trials
        WHERE treatment = ?
        GROUP BY season, variety
        ORDER BY season, hybrid
        """,
        [programme],
    )


@mcp.tool
def run_sql(sql: str) -> list[dict]:
    """Run a read-only SELECT against the trial database.

    Tables: field_trials (one row per harvested plot), sites (one row per
    station), and the view variety_season_summary. The connection is read-only,
    so writes fail at the database rather than being filtered here.

    Args:
        sql: A single SELECT or WITH statement.
    """
    statement = sql.strip().rstrip(";")
    if not statement.lower().startswith(("select", "with")):
        raise ValueError("Only SELECT and WITH statements are allowed.")
    rows = query(statement)
    return rows[:200]


@mcp.tool
def data_notice() -> str:
    """Explain where this data comes from before anyone quotes it."""
    return DISCLAIMER


# Connect deploys this as a FastAPI/ASGI app, and serves the MCP endpoint at
# /mcp under the content's URL. Locally, `fastmcp run` uses `mcp` directly.
app = mcp.http_app(path="/mcp")

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000)
