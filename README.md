# CanopyLab Agronomics — field trial analytics on Posit Team

CanopyLab Agronomics is a fictional crop science company. Its trialling team runs
protection programmes against five hybrids at six research stations, and has to
answer the same question every autumn: **which hybrid, at which station, under
which programme?**

This project is what that answer looks like when it is built on Posit Team — one
project, two languages, four pieces of published content, and one Git history
that decides what is running in production.

> **This project contains synthetic data and analysis created for demonstration
> purposes only.** Every station, hybrid, programme and yield figure was generated
> by an algorithm.

---

## What is in here

| | File | What it demonstrates |
|---|---|---|
| **Data** | `data/generate_data.py` | 1,800 synthetic harvested plots → two CSVs and a DuckDB database |
| **Package** | `canopytrials/` | The shared R package: data access, the definition of *yield response*, the brand theme. Tested with testthat. |
| **Report** | `trial-report.qmd` | Quarto report in R — `gt` tables, ggplot2 charts, inline numbers that update on re-render |
| **Dashboard** | `app.R` | Shiny app with `bslib`, filters, value boxes, and the same package underneath |
| **Notebook** | `notebooks/field-trial-tour.ipynb` | Python: polars, DuckDB, great_tables, scikit-learn, ggsql — written in Positron's notebook editor |
| **SQL** | `sql/*.sql`, `sql/*.ggsql` | Plain SQL for the Connections pane, plus ggsql queries that draw charts straight from the database |
| **Charts** | `python/run_ggsql.py` | Runs any `.ggsql` file to an interactive HTML chart and a PNG |
| **Assistant tools** | `mcp/server.py` | An MCP server published to Connect, callable from Posit Assistant |
| **CI/CD** | `.github/workflows/` | Publish to Connect on merge to `main`; check the R package on every PR |
| **Branding** | `_brand.yml` | One palette and typography, used by the report, the app, the ggplot theme and the Python charts |

## Getting started

```bash
# 1. Python side
uv sync

# 2. Generate the synthetic data (not committed — it is regenerable)
uv run python data/generate_data.py

# 3. R side
Rscript -e 'renv::restore()'
R CMD INSTALL canopytrials
```

Then pick a door:

```bash
quarto render trial-report.qmd                 # the report
Rscript -e 'shiny::runApp("app.R")'            # the dashboard
uv run python python/run_ggsql.py              # every .ggsql file → outputs/
uv run uvicorn server:app --app-dir mcp --port 8123   # the MCP server
```

Open `notebooks/field-trial-tour.ipynb` in Positron to walk the Python path
interactively.

## The data

Six research stations across three regions, five seasons (2021–2025, with 2023
running about 30% below normal rainfall), five hybrids differing in yield
potential, disease tolerance and drought tolerance, and three treatments —
*Untreated Check*, *Programme Alpha*, *Programme Bravo* — with four replicate
plots each. 1,800 plots in total.

`field_trials` is one row per harvested plot: hybrid, station, season, treatment,
replicate, rainfall, disease pressure index and yield in t/ha. `sites` is one row
per station. The DuckDB file also carries a `variety_season_summary` view.

The signal is deliberate and consistent: protection programmes lift yield by about
0.7 t/ha on average, they lift it *most* where disease pressure is highest and for
the hybrids with the least of their own tolerance, and the dry season compresses
the differences between hybrids. Every headline in the report and the dashboard is
computed from the data, not written by hand.

## Re-branding it for your own organisation

`_brand.yml` is the only file to edit. Change the palette and the fonts there, and
the Quarto report (`theme: brand`), the Shiny app (`bs_theme(brand = "_brand.yml")`),
the ggplot theme (`canopytrials::theme_canopylab()`) and the notebook's matplotlib
charts all follow. Drop a logo into the commented block at the bottom of the file
to add it to the report and the app headers.

## Publishing to Posit Connect

Set two environment variables and run one script:

```bash
export CONNECT_SERVER="https://connect.example.com"
export CONNECT_API_KEY="..."
Rscript deploy.R
```

That publishes the report and the dashboard; the script prints the two
`rsconnect` commands for the notebook and the MCP server. Once
`CONNECT_SERVER`/`CONNECT_API_KEY` exist as repository secrets, every merge to
`main` does the same thing without anybody clicking Publish — see
`.github/workflows/deploy-connect.yml`.

For the MCP server specifically — the three Connect settings it needs and the
Posit Assistant configuration that consumes it — see **[MCP-SETUP.md](MCP-SETUP.md)**.

## Notes and known limits

- The synthetic data is regenerated, not committed. `uv run python
  data/generate_data.py` is deterministic (fixed seed), so everyone gets the same
  1,800 plots.
- `ggsql` for R needs R ≥ 4.5; the R install fails on 4.4.x with an error about
  `tools::sha256sum`. The `.ggsql` files here are run through the Python API
  (`python/run_ggsql.py`), which works on any supported Python. The queries
  themselves are identical either way.
- Nothing in this repository has been deployed to a live Connect server — the
  deployment commands and CI workflow are written against Connect's documented
  interfaces but were not executed here.
- Three `.ggsql` parser constraints worth knowing before you edit the queries: no
  trailing semicolon, `LABEL` accepts `title`/`subtitle`/`x`/`y`, and a `--`
  inside a quoted label string breaks execution.

---

## Important Disclaimer

**This project contains synthetic data and analysis created for demonstration
purposes only.**

All data, insights, business scenarios, and analytics presented in this
demonstration project have been artificially generated using AI. The data does
not represent actual business information, performance metrics, customer data,
or operational statistics.

### Key Points:

- **Synthetic Data**: All datasets are computer-generated and designed to
  illustrate analytical capabilities
- **Illustrative Analysis**: Insights and recommendations are examples of the
  types of analysis possible with Posit tools
- **No Actual Business Data**: No real business information or data was used or
  accessed in creating this demonstration
- **Educational Purpose**: This project serves as a technical demonstration of
  data science workflows and reporting capabilities
- **AI-Generated Content**: Analysis, commentary, and business scenarios were
  created by AI for illustration purposes
- **No Real-World Implications**: The scenarios and insights presented should
  not be interpreted as actual business advice or strategies

This demonstration showcases how Posit's commercial and open-source tools can be
applied to the Crop Science industry. The synthetic data and analysis provide a
foundation for understanding the potential value of implementing similar
analytical workflows with actual business data.

For questions about adapting these techniques to your real business scenarios,
please contact your Posit representative.
---

*This demonstration was created using Posit's commercial data science tools and
open-source packages. All synthetic data and analysis are provided for
evaluation purposes only.*
