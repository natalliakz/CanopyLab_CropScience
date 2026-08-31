"""Generate the synthetic CanopyLab field trial dataset.

This project contains synthetic data and analysis created for demonstration
purposes only.

CanopyLab Agronomics is a fictional crop science company. Every site, hybrid and
treatment programme below was invented for this demo; none of it corresponds to a
real product, location or trial result.

The script writes three files into this directory:

    synthetic-field-trials.csv    one row per harvested plot
    synthetic-sites.csv           one row per trial station
    synthetic-agronomy.duckdb     both tables, for the SQL and ggsql parts

The DuckDB file is what makes the SQL half of the demo work: Positron's
Connections pane can browse it, a `.sql` file can query it, and ggsql can chart
the result without anything leaving the laptop.

Run:
    uv run python data/generate_data.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent

TRIALS_CSV = HERE / "synthetic-field-trials.csv"
SITES_CSV = HERE / "synthetic-sites.csv"
DUCKDB_PATH = HERE / "synthetic-agronomy.duckdb"

SEED = 20260831

# --- The fictional trial network --------------------------------------------
# Six stations across three regions. Soil and rainfall differ by station, which
# is what gives the data something for an agronomist to actually look at.

SITES = [
    # name, region, soil, elevation_m, normal_rainfall_mm
    ("North Ridge Station", "Northern Plains", "Silt loam", 415, 520),
    ("Clay Flats Station", "Northern Plains", "Heavy clay", 380, 470),
    ("River Bend Station", "Central Valley", "Sandy loam", 210, 610),
    ("Lakeview Station", "Central Valley", "Silt loam", 245, 655),
    ("Sandhill Station", "Eastern Belt", "Loamy sand", 160, 700),
    ("High Plains Station", "Eastern Belt", "Clay loam", 520, 430),
]

SEASONS = [2021, 2022, 2023, 2024, 2025]

#: Five fictional hybrids. The "CL-" prefix marks them as CanopyLab's own coding
#: and keeps them obviously invented.
VARIETIES = {
    # name: (yield potential t/ha, disease tolerance 0-1, drought tolerance 0-1)
    "CL-Aurora 21": (10.4, 0.35, 0.55),
    "CL-Beacon 44": (11.2, 0.70, 0.30),
    "CL-Cinder 07": (9.6, 0.55, 0.80),
    "CL-Delta 12": (10.8, 0.50, 0.45),
    "CL-Ember 33": (11.6, 0.25, 0.35),
}

#: Three crop protection programmes. "Untreated Check" is the agronomic control
#: -- the plot that receives nothing, so the others have something to beat.
TREATMENTS = {
    "Untreated Check": 0.00,
    "Programme Alpha": 0.55,  # proportion of disease pressure suppressed
    "Programme Bravo": 0.80,
}

REPLICATES = 4

#: Season weather, as a multiplier on normal rainfall and an index of how much
#: disease came with it. Wet seasons carry more disease; 2023 is the dry one.
SEASON_WEATHER = {
    2021: (1.00, 45),
    2022: (1.15, 62),
    2023: (0.72, 28),
    2024: (1.05, 51),
    2025: (0.93, 38),
}


def build_sites() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "site_id": [f"S{index:02d}" for index in range(1, len(SITES) + 1)],
            "site_name": [site[0] for site in SITES],
            "region": [site[1] for site in SITES],
            "soil_type": [site[2] for site in SITES],
            "elevation_m": [site[3] for site in SITES],
            "normal_rainfall_mm": [site[4] for site in SITES],
        }
    )


def build_trials(sites: pl.DataFrame, rng: np.random.Generator) -> pl.DataFrame:
    """One row per harvested plot: a full factorial, replicated four times.

    The yield of a plot is built up from named, separable effects so that the
    analysis downstream has something true to recover:

      * a genetic potential per hybrid,
      * a site effect (soil and elevation),
      * a season effect (rainfall relative to normal),
      * a disease penalty, which the treatment programme suppresses and the
        hybrid's own tolerance blunts,
      * plot-to-plot noise, which is why field trials use replicates at all.
    """
    rows: list[dict[str, object]] = []
    site_records = sites.to_dicts()

    # A fixed, mild site effect. Heavy clay and the high, dry station give up a
    # little yield; the valley silt loams give a little back.
    site_effect = {
        "North Ridge Station": 0.3,
        "Clay Flats Station": -0.6,
        "River Bend Station": 0.5,
        "Lakeview Station": 0.8,
        "Sandhill Station": -0.2,
        "High Plains Station": -0.9,
    }

    plot_counter = 0
    for season in SEASONS:
        rain_factor, season_disease = SEASON_WEATHER[season]
        for site in site_records:
            rainfall = float(
                site["normal_rainfall_mm"] * rain_factor * rng.normal(1.0, 0.06)
            )
            # Growing degree days track elevation (cooler higher up) with a
            # season-to-season wobble.
            gdd = float(2650 - 0.45 * site["elevation_m"] + rng.normal(0, 70))

            # Disease pressure is a wet-season phenomenon, amplified on heavy
            # soils that hold water.
            soil_wetness = {"Heavy clay": 12, "Clay loam": 6, "Silt loam": 2}.get(
                str(site["soil_type"]), -6
            )
            site_disease = float(
                np.clip(season_disease + soil_wetness + rng.normal(0, 5), 2, 98)
            )

            for variety, (potential, disease_tol, drought_tol) in VARIETIES.items():
                for treatment, suppression in TREATMENTS.items():
                    for replicate in range(1, REPLICATES + 1):
                        plot_counter += 1

                        # Disease actually experienced by this plot.
                        plot_disease = float(
                            np.clip(
                                site_disease * (1 - suppression) * rng.normal(1.0, 0.10),
                                0,
                                100,
                            )
                        )
                        disease_penalty = (
                            (plot_disease / 100) * 3.4 * (1 - disease_tol)
                        )

                        # Moisture stress: how far below normal rainfall the
                        # season ran, softened by the hybrid's drought tolerance.
                        moisture_shortfall = max(
                            0.0, 1 - rainfall / float(site["normal_rainfall_mm"])
                        )
                        drought_penalty = moisture_shortfall * 4.2 * (1 - drought_tol)

                        yield_t_ha = (
                            potential
                            + site_effect[str(site["site_name"])]
                            + 0.9 * (rain_factor - 1)
                            - disease_penalty
                            - drought_penalty
                            + rng.normal(0, 0.45)  # plot noise
                        )

                        stand_count = float(rng.normal(7.8, 0.35))
                        lodging = float(
                            np.clip(
                                rng.gamma(1.6, 1.8) + 0.05 * plot_disease,
                                0,
                                60,
                            )
                        )

                        rows.append(
                            {
                                "plot_id": f"P{plot_counter:05d}",
                                "season": season,
                                "site_id": site["site_id"],
                                "site_name": site["site_name"],
                                "region": site["region"],
                                "variety": variety,
                                "treatment": treatment,
                                "replicate": replicate,
                                "rainfall_mm": round(rainfall, 1),
                                "growing_degree_days": round(gdd, 0),
                                "disease_pressure_index": round(plot_disease, 1),
                                "stand_count_per_m2": round(stand_count, 2),
                                "lodging_pct": round(lodging, 1),
                                "yield_t_ha": round(max(yield_t_ha, 0.5), 2),
                            }
                        )

    return pl.DataFrame(rows)


def write_duckdb(trials: pl.DataFrame, sites: pl.DataFrame) -> None:
    """Load both tables into a DuckDB file.

    This is the database Positron's Connections pane opens, the `.sql` files
    query, and ggsql charts. A single file keeps the demo self-contained -- no
    warehouse credentials to arrange before a customer meeting.
    """
    DUCKDB_PATH.unlink(missing_ok=True)
    connection = duckdb.connect(str(DUCKDB_PATH))
    try:
        # DuckDB reads the polars frames straight out of the Python scope.
        connection.register("trials_df", trials)
        connection.register("sites_df", sites)
        connection.execute("CREATE TABLE field_trials AS SELECT * FROM trials_df")
        connection.execute("CREATE TABLE sites AS SELECT * FROM sites_df")
        connection.execute(
            """
            CREATE VIEW variety_season_summary AS
            SELECT
                season,
                variety,
                treatment,
                count(*)              AS plots,
                round(avg(yield_t_ha), 2)             AS mean_yield_t_ha,
                round(avg(disease_pressure_index), 1) AS mean_disease_index
            FROM field_trials
            GROUP BY season, variety, treatment
            """
        )
    finally:
        connection.close()


def main() -> None:
    rng = np.random.default_rng(SEED)

    sites = build_sites()
    trials = build_trials(sites, rng)

    sites.write_csv(SITES_CSV)
    trials.write_csv(TRIALS_CSV)
    write_duckdb(trials, sites)

    print(
        f"Wrote {trials.height:,} plots from {trials.get_column('site_id').n_unique()} "
        f"stations across {trials.get_column('season').n_unique()} seasons"
    )
    print(f"  {TRIALS_CSV.name}")
    print(f"  {SITES_CSV.name}")
    print(f"  {DUCKDB_PATH.name}  (tables: field_trials, sites; view: variety_season_summary)")
    print(
        "\nThis project contains synthetic data and analysis created for "
        "demonstration purposes only."
    )


if __name__ == "__main__":
    main()
