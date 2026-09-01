"""CanopyLab field trial MCP server.

An MCP server that answers questions about the trial results, published to Posit
Connect and used from Posit Assistant inside Positron. Connect hosts it like any
other content: same permissions model, same logs, same audit trail — so an
assistant that can read internal trial data is governed the same way a Shiny app is.

Run locally:
    uv run fastmcp run mcp/server.py:mcp --transport http --port 8000

Publish to Connect (see MCP-SETUP.md for the whole story):
    cp python/trials.py data/synthetic-agronomy.duckdb ./mcp/
    rsconnect deploy fastapi -n <server-nickname> --entrypoint server:app ./mcp

The data in here is synthetic and exists for demonstration purposes only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl
from fastmcp import FastMCP

# `trials` is the shared module the Streamlit app uses too. In the repository it
# lives in python/; in a Connect bundle the deploy step copies it in beside this
# file, because a bundle has no parent project to reach up into. Both locations go
# on the path, nearest first, so the same file runs in both places.
_here = Path(__file__).resolve().parent
for _candidate in (_here.parent / "python", _here):  # inserted at 0, so _here wins
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

import trials  # noqa: E402  (the path insert has to come first)

DISCLAIMER = "CanopyLab Agronomics is a fictional company. " + trials.DISCLAIMER


def query(sql: str, params: list | None = None) -> list[dict]:
    """Read-only query, as plain dictionaries for the MCP wire format.

    `trials.query` does the connection handling -- one read-only connection per
    call -- and this only reshapes the result.
    """
    return trials.query(sql, params).to_dicts()


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
    programme with genetics would overstate it. The calculation itself is
    `trials.yield_response()`, the same function the Streamlit dashboard calls, so
    an assistant and a dashboard cannot report different numbers.

    Args:
        hybrid: Optional hybrid name, e.g. "CL-Ember 33". Omit for all hybrids.
    """
    plots = trials.read_plots()
    if hybrid is not None:
        plots = plots.filter(pl.col("variety") == hybrid)
        if plots.is_empty():
            raise ValueError(f"No plots for hybrid {hybrid!r}.")

    return (
        trials.yield_response(plots)
        .select(
            hybrid=pl.col("variety"),
            programme=pl.col("treatment"),
            plots=pl.col("plots"),
            mean_yield_t_ha=pl.col("mean_yield_t_ha").round(2),
            gain_vs_check_t_ha=pl.col("gain_vs_check_t_ha").round(2),
            mean_disease_index=pl.col("mean_disease_index").round(1),
        )
        .to_dicts()
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
