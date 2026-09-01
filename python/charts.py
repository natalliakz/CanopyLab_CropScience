"""Altair chart builders for the Python side of the project.

Separate from `streamlit_app.py` on purpose: a chart that lives in a function can
be rendered from a script, checked in a notebook, and saved to PNG in CI. A chart
built inline in an app can only be looked at by starting the app.

Colour comes from `_brand.yml` through `trials.treatment_scale()`, and it follows
the treatment rather than the row order, so filtering to two programmes does not
repaint them.

This project contains synthetic data and analysis created for demonstration
purposes only.
"""

from __future__ import annotations

import altair as alt
import polars as pl

from trials import CHECK, palette, treatment_scale

COLORS = palette()
DOMAIN, RANGE = treatment_scale()

# Font *stacks*, not bare family names. The brand fonts are Google fonts, so a
# browser fetches them, but a static PNG export happens wherever the code runs --
# a CI runner or a Connect host with neither font installed. vl-convert given a
# font it cannot find silently drops every label, so name the fallbacks.
BODY_FONT = "Open Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
HEADING_FONT = "Source Serif 4, Georgia, serif"


def register_theme() -> None:
    """Point Altair's defaults at the brand palette and fonts.

    Called once by the app. Charts stay free of styling so that a re-brand is an
    edit to `_brand.yml` and nothing else.
    """

    @alt.theme.register("canopylab", enable=True)
    def _canopylab() -> alt.theme.ThemeConfig:
        return {
            "config": {
                "font": BODY_FONT,
                "title": {
                    "font": HEADING_FONT,
                    "color": COLORS["canopy"],
                    "fontSize": 15,
                    "anchor": "start",
                },
                "axis": {
                    "labelColor": COLORS["stone"],
                    "titleColor": COLORS["stone"],
                    "titleFontWeight": "normal",
                    "domainColor": COLORS["hairline"],
                    "tickColor": COLORS["hairline"],
                    "gridColor": COLORS["hairline"],
                    "gridWidth": 0.6,
                },
                "legend": {
                    "labelColor": COLORS["black"],
                    "titleColor": COLORS["stone"],
                },
                "view": {"stroke": None},
                "range": {"category": RANGE},
            }
        }


def _treatment_color() -> alt.Color:
    return alt.Color(
        "treatment:N",
        title=None,
        scale=alt.Scale(domain=DOMAIN, range=RANGE),
        legend=alt.Legend(orient="top", direction="horizontal"),
    )


def response_chart(response: pl.DataFrame, height: int = 360) -> alt.LayerChart:
    """Cleveland dot plot: three dots per hybrid, joined by the gain they span.

    A grouped bar chart would put the interesting quantity -- the distance between
    check and programme -- in the gap between bars, where it cannot be read. The
    rule puts it on the page.
    """
    spans = response.group_by("variety").agg(
        low=pl.col("mean_yield_t_ha").min(),
        high=pl.col("mean_yield_t_ha").max(),
    )

    # Sort by untreated yield, so the axis reads as genetic potential and the
    # programme dots read as what was added to it.
    order = (
        response.filter(pl.col("treatment") == CHECK)
        .sort("mean_yield_t_ha", descending=True)
        .get_column("variety")
        .to_list()
    )

    hybrid = alt.Y("variety:N", sort=order, title=None)

    rules = (
        alt.Chart(spans)
        .mark_rule(color=COLORS["hairline"], strokeWidth=2)
        .encode(y=hybrid, x=alt.X("low:Q"), x2="high:Q")
    )

    dots = (
        alt.Chart(response)
        .mark_point(size=140, filled=True, opacity=1, stroke="white", strokeWidth=1.5)
        .encode(
            y=hybrid,
            x=alt.X(
                "mean_yield_t_ha:Q",
                title="Mean yield (t/ha)",
                scale=alt.Scale(zero=False, padding=28),
            ),
            color=_treatment_color(),
            tooltip=[
                alt.Tooltip("variety:N", title="Hybrid"),
                alt.Tooltip("treatment:N", title="Programme"),
                alt.Tooltip("mean_yield_t_ha:Q", title="Mean yield (t/ha)", format=".2f"),
                alt.Tooltip("gain_vs_check_t_ha:Q", title="Gain (t/ha)", format="+.2f"),
                alt.Tooltip("mean_disease_index:Q", title="Disease index", format=".1f"),
                alt.Tooltip("plots:Q", title="Plots"),
            ],
        )
    )

    return (rules + dots).properties(height=height)


def season_chart(trend: pl.DataFrame, height: int = 360) -> alt.Chart:
    """Mean yield by season and programme, with an optional dashed hybrid overlay.

    `trend` carries a `scope` column: "All hybrids" plus, when one is highlighted,
    a second set of lines for that hybrid alone. Dash carries scope so colour is
    left to say which programme it is.
    """
    return (
        alt.Chart(trend)
        .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=60, filled=True))
        .encode(
            # Five seasons fit horizontally; without this Vega rotates them to
            # vertical the moment the card narrows.
            x=alt.X("season:O", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y(
                "mean_yield_t_ha:Q",
                title="Mean yield (t/ha)",
                scale=alt.Scale(zero=False, nice=True),
            ),
            color=_treatment_color(),
            strokeDash=alt.StrokeDash("scope:N", title=None, legend=None),
            detail="scope:N",
            tooltip=[
                alt.Tooltip("season:O", title="Season"),
                alt.Tooltip("treatment:N", title="Programme"),
                alt.Tooltip("scope:N", title="Scope"),
                alt.Tooltip("mean_yield_t_ha:Q", title="Mean yield (t/ha)", format=".2f"),
            ],
        )
        .properties(height=height)
    )
