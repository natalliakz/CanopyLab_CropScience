"""Tests for the shared Python trial logic.

The Python mirror of canopytrials/tests/testthat/test-summaries.R, and for the
same reason: the definition of "yield response" is the number the customer will
quote, so it gets a test rather than a code review.

Like the R tests, these run against a small fixture instead of the generated
DuckDB file, so `pytest` passes on a fresh clone where the synthetic data has not
been built yet.

Run them:
    uv run pytest

This project contains synthetic data and analysis created for demonstration
purposes only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

import trials  # noqa: E402


def fixture() -> pl.DataFrame:
    """Two hybrids of different potential, each with the same 2.5 t/ha response."""
    return pl.DataFrame(
        {
            "variety": ["CL-Test 01"] * 4 + ["CL-Test 02"] * 4,
            "treatment": [
                "Untreated Check",
                "Untreated Check",
                "Programme Bravo",
                "Programme Bravo",
            ]
            * 2,
            "yield_t_ha": [8.0, 9.0, 10.0, 11.0, 6.0, 7.0, 9.0, 10.0],
            "disease_pressure_index": [60.0, 50.0, 10.0, 12.0, 70.0, 66.0, 14.0, 10.0],
            "season": [2025] * 8,
            "region": ["Test Region"] * 8,
            "site_name": ["Test Station"] * 8,
            "rainfall_mm": [500.0] * 8,
        }
    )


def gain_for(response: pl.DataFrame, variety: str, treatment: str) -> float:
    return (
        response.filter(
            pl.col("variety") == variety, pl.col("treatment") == treatment
        )
        .get_column("gain_vs_check_t_ha")
        .item()
    )


def test_yield_response_measures_against_the_hybrids_own_check():
    response = trials.yield_response(fixture())

    assert set(response.columns) == {
        "variety",
        "treatment",
        "plots",
        "mean_yield_t_ha",
        "sd_yield_t_ha",
        "mean_disease_index",
        "gain_vs_check_t_ha",
    }

    # CL-Test 01: check mean 8.5, treated mean 10.5 -> gain 2.0
    assert gain_for(response, "CL-Test 01", "Programme Bravo") == pytest.approx(2.0)

    # CL-Test 02 has lower potential and a larger response. Measured against the
    # trial-wide average these two would come out looking the same.
    assert gain_for(response, "CL-Test 02", "Programme Bravo") == pytest.approx(3.0)

    # The control's gain over itself is zero, by construction.
    checks = response.filter(pl.col("treatment") == trials.CHECK)
    assert checks.get_column("gain_vs_check_t_ha").to_list() == [0.0, 0.0]


def test_yield_response_refuses_to_guess_without_a_control():
    no_check = fixture().filter(pl.col("treatment") != trials.CHECK)
    with pytest.raises(ValueError, match="Untreated Check"):
        trials.yield_response(no_check)


def test_yield_response_matches_the_r_package_column_names():
    """The two implementations answer the same question, so they share a shape.

    If someone renames a column on one side, this test fails rather than the
    dashboard and the report quietly disagreeing about which column to read.
    """
    r_columns = {
        "variety",
        "treatment",
        "plots",
        "mean_yield_t_ha",
        "sd_yield_t_ha",
        "mean_disease_index",
        "gain_vs_check_t_ha",
    }
    assert set(trials.yield_response(fixture()).columns) == r_columns


def test_site_summary_returns_one_row_per_station_best_first():
    summary = trials.site_summary(fixture())
    assert summary.height == 1
    assert summary.get_column("plots").item() == 8
    assert summary.get_column("mean_yield_t_ha").item() == pytest.approx(8.75)


def test_season_trend_groups_by_treatment_and_season():
    trend = trials.season_trend(fixture())
    assert trend.height == 2  # one season, two treatments
    assert sorted(trend.get_column("mean_yield_t_ha").to_list()) == pytest.approx(
        [7.5, 10.0]
    )


def test_season_trend_can_group_by_variety_and_rejects_anything_else():
    by_variety = trials.season_trend(fixture(), by="variety")
    assert by_variety.height == 2
    assert "variety" in by_variety.columns

    with pytest.raises(ValueError, match="treatment"):
        trials.season_trend(fixture(), by="site_name")


def test_the_brand_palette_is_complete_and_fixed():
    domain, colors = trials.treatment_scale()
    assert domain == ["Untreated Check", "Programme Alpha", "Programme Bravo"]
    assert all(color.startswith("#") and len(color) == 7 for color in colors)
    # Distinct colours, or the legend is decoration rather than information.
    assert len(set(colors)) == 3


def test_database_path_says_how_to_fix_a_missing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("CANOPYLAB_ROOT", str(tmp_path))
    monkeypatch.delenv("CANOPYLAB_DB", raising=False)
    monkeypatch.setattr(trials, "__file__", str(tmp_path / "trials.py"))

    with pytest.raises(FileNotFoundError, match="generate_data.py"):
        trials.database_path()


def test_csv_paths_says_how_to_fix_missing_data(monkeypatch, tmp_path):
    monkeypatch.setenv("CANOPYLAB_ROOT", str(tmp_path))
    monkeypatch.setattr(trials, "__file__", str(tmp_path / "trials.py"))

    with pytest.raises(FileNotFoundError, match="generate_data.py"):
        trials.csv_paths()


def csv_only_project(root: Path) -> None:
    """A project directory holding the two CSVs and no database.

    Which is exactly the shape of `connect/streamlit/`: a git-backed Connect
    deployment has no build step, so the data it starts with is the data that was
    committed.
    """
    data = root / "data"
    data.mkdir()
    (data / "synthetic-field-trials.csv").write_text(
        "site_id,site_name,region,season,variety,treatment,replicate,"
        "rainfall_mm,disease_pressure_index,yield_t_ha\n"
        "1,Test Station,Test Region,2025,CL-Test 01,Untreated Check,1,500,55.0,8.0\n"
        "1,Test Station,Test Region,2025,CL-Test 01,Programme Bravo,1,500,11.0,10.0\n"
    )
    (data / "synthetic-sites.csv").write_text(
        "site_id,site_name,region,soil_type,elevation_m,normal_rainfall_mm\n"
        "1,Test Station,Test Region,Loam,120,520\n"
    )


def test_the_csvs_stand_in_for_the_database(monkeypatch, tmp_path):
    """No DuckDB file, same three relations, same answers."""
    csv_only_project(tmp_path)
    monkeypatch.setenv("CANOPYLAB_ROOT", str(tmp_path))
    monkeypatch.delenv("CANOPYLAB_DB", raising=False)
    monkeypatch.setattr(trials, "__file__", str(tmp_path / "python" / "trials.py"))

    with pytest.raises(FileNotFoundError):
        trials.database_path()

    plots = trials.read_plots()
    assert plots.height == 2
    assert {"soil_type", "elevation_m", "normal_rainfall_mm"} <= set(plots.columns)

    assert trials.read_sites().height == 1

    # The view the DuckDB file carries is rebuilt over the CSVs, so a query
    # written against the database in the Connections pane still runs here.
    summary = trials.query("SELECT * FROM variety_season_summary ORDER BY treatment")
    assert summary.height == 2

    assert gain_for(
        trials.yield_response(plots), "CL-Test 01", "Programme Bravo"
    ) == pytest.approx(2.0)
