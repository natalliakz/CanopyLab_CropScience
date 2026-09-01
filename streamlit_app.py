# CanopyLab field trial explorer, the Python edition.
#
# The same dashboard as app.R, built by the Python half of the team. It reads the
# same DuckDB file, wears the same `_brand.yml` palette, and -- the part that
# matters -- takes its definition of "yield response" from `python/trials.py`
# instead of re-deriving it. R users have the canopytrials package; Python users
# have that module. Neither team copies SQL out of the other's dashboard.
#
# Run it locally (in Positron: open this file and use the Run button, or):
#   uv run streamlit run streamlit_app.py
#
# Publish it:
#   uv run rsconnect deploy streamlit --entrypoint streamlit_app.py .
# Or let .github/workflows/deploy-connect.yml do it on merge to main.
#
# This project contains synthetic data and analysis created for demonstration
# purposes only.

import sys
from pathlib import Path

import polars as pl
import streamlit as st

# The shared modules live in python/ so the R package and the Python package sit
# side by side rather than one of them owning the project root.
sys.path.insert(0, str(Path(__file__).parent / "python"))

from charts import register_theme, response_chart, season_chart  # noqa: E402
from trials import (  # noqa: E402
    CHECK,
    DISCLAIMER,
    read_plots,
    season_trend,
    site_summary,
    yield_response,
)

ALL = "All hybrids"

st.set_page_config(
    page_title="CanopyLab field trial explorer",
    page_icon="🌱",
    layout="wide",
)
register_theme()


@st.cache_data
def load_plots() -> pl.DataFrame:
    """One read of the database per session, not one per widget interaction."""
    return read_plots()


try:
    plots = load_plots()
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

seasons = sorted(plots.get_column("season").unique().to_list())
regions = sorted(plots.get_column("region").unique().to_list())
varieties = sorted(plots.get_column("variety").unique().to_list())

with st.sidebar:
    st.caption("Synthetic data for demonstration purposes only.")

    chosen_regions = st.multiselect("Regions", regions, default=regions)
    first_season, last_season = st.select_slider(
        "Seasons", options=seasons, value=(seasons[0], seasons[-1])
    )
    highlight = st.selectbox("Highlight a hybrid", [ALL, *varieties])

    st.divider()
    st.caption(
        "Yield response is always measured against the same hybrid's own "
        "untreated plots — the definition lives in `trials.yield_response()`, so "
        "this dashboard, the MCP server and the trial report cannot disagree."
    )

if not chosen_regions:
    st.info("Select at least one region.")
    st.stop()

filtered = plots.filter(
    pl.col("region").is_in(chosen_regions),
    pl.col("season") >= first_season,
    pl.col("season") <= last_season,
)

if filtered.is_empty():
    st.info("No plots match these filters.")
    st.stop()

st.title("CanopyLab field trial explorer")

response = yield_response(filtered)
protected = filtered.filter(pl.col("treatment") != CHECK)
bravo_gain = (
    response.filter(pl.col("treatment") == "Programme Bravo")
    .get_column("gain_vs_check_t_ha")
    .mean()
)

plots_seen, mean_protected, gain = st.columns(3)
plots_seen.metric("Plots in view", f"{filtered.height:,}")
mean_protected.metric(
    "Mean yield, protected plots",
    f"{protected.get_column('yield_t_ha').mean():.2f} t/ha",
)
gain.metric("Programme Bravo vs check", f"+{bravo_gain:.2f} t/ha")

response_column, season_column = st.columns([7, 5])

with response_column:
    st.subheader("Yield response by hybrid")
    st.caption("Grey is the untreated check; the rule spans the gain. Hover for detail.")
    st.altair_chart(response_chart(response), width="stretch")

with season_column:
    st.subheader("Season by season")
    st.caption(
        f"Solid: all hybrids. Dashed: {highlight}."
        if highlight != ALL
        else "All hybrids in the selected regions."
    )

    trend = season_trend(filtered).with_columns(scope=pl.lit(ALL))
    if highlight != ALL:
        one_hybrid = season_trend(filtered.filter(pl.col("variety") == highlight))
        trend = pl.concat([trend, one_hybrid.with_columns(scope=pl.lit(highlight))])

    st.altair_chart(season_chart(trend), width="stretch")

st.subheader("Station detail")

# Rounded here rather than only in `column_config`, so the numbers are right in the
# CSV a viewer downloads from the table's toolbar as well as on screen.
stations = site_summary(filtered).with_columns(
    pl.col("mean_yield_t_ha").round(2),
    pl.col("mean_disease_index").round(1),
    pl.col("mean_rainfall_mm").round(0),
)

st.dataframe(
    stations,
    width="stretch",
    hide_index=True,
    column_config={
        "site_name": "Station",
        "region": "Region",
        "plots": st.column_config.NumberColumn("Plots"),
        "mean_yield_t_ha": st.column_config.ProgressColumn(
            "Mean yield (t/ha)",
            format="%.2f",
            min_value=0,
            max_value=float(filtered.get_column("yield_t_ha").max()),
        ),
        "mean_disease_index": st.column_config.NumberColumn(
            "Disease index", format="%.1f"
        ),
        "mean_rainfall_mm": st.column_config.NumberColumn("Rainfall (mm)", format="%.0f"),
    },
)

st.caption(
    f"{DISCLAIMER} All data, insights and business scenarios were artificially "
    "generated using AI."
)
