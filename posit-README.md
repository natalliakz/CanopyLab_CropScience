# CanopyLab Agronomics — Posit internal demo guide

## Demo context

**Customer:** Syngenta
**Focus:** Posit Team, weighted heavily toward **Positron**
**Audience:** R users who build packages and publish Shiny/Quarto to Connect, and
Python users currently living in VS Code and Jupyter
**Requested by:** Luis and Linc, from the discovery call

### What they asked for, in their words

- *"Start with almost just an overview of here is who we are and broadly what each
  of our three products do before getting into the actual product interface demo."*
- *"Then we dive into it mostly focusing on Positron and then also the Connect
  deployment piece."*
- *"We put Git as part of this process… where you can basically do CI/CD… it helps
  you make the transformation between Workbench and Connect."*
- Connect *"simplifies things like user management, log management, deployment. We
  can do it directly. We can do it via Git as well."*
- *"Maybe show even a little bit of what a Connect deployed application just kind
  of looks like."*
- *"We can do Jupyter notebooks, we can do JupyterLab, we can do Positron, we can
  do RStudio Workbench… the main goal was basically to talk about Positron as the
  new feature that we're bringing in, especially for the folks in Python."*
- Luis, on why deployment lands: *"As a developer… the deployment piece of it is
  just this gorgeous."* And on server-side images: *"You're developing in the same
  platform where your application will live… we also wanted people out of the local
  mindset, to get them to Git."*

### So the demo has four acts

| Act | Minutes | What you are doing |
|---|---|---|
| 1. Who we are, three products | 5 | Whiteboard the picture. No IDE yet. |
| 2. Positron, deep | 20 | The Python developer's day, in one editor |
| 3. R users: package → report → app | 10 | Why R teams package things, and Quarto/Shiny publishing |
| 4. Git, CI/CD, Connect, and Assistant tools | 15 | The deployment story, which is the sale |

Total ≈ 50 minutes with questions. Cut Act 3's package internals first if you are
short; cut nothing from Act 4.

---

## Act 1 — Who we are and what the three products do (5 min, no screen share)

Draw it, left to right, and say it in one breath:

```
   DEVELOP                    VERSION                 DEPLOY
┌──────────────┐           ┌──────────┐          ┌──────────────┐
│  Workbench   │  ──push──▶│   Git    │──CI/CD──▶│   Connect    │
│              │           │          │          │              │
│ Positron     │           │ PRs,     │          │ Shiny, Quarto│
│ RStudio      │           │ reviews, │          │ APIs, MCP,   │
│ JupyterLab   │           │ history  │          │ notebooks    │
│ VS Code      │           └──────────┘          │              │
└──────────────┘                                 │ users, logs, │
       ▲                                         │ schedules,   │
       │                                         │ audit        │
       └──────── Package Manager ────────────────▶└──────────────┘
              (R and Python, same service)
```

Three sentences, one per product:

- **Workbench** puts the IDEs on a server: Positron, RStudio, JupyterLab, VS Code,
  on the same images as production, with the compute your models actually need.
- **Package Manager** is the R *and* Python package supply: a curated, approved,
  reproducible source, so `renv.lock` and `uv.lock` mean the same thing on a laptop,
  a CI runner and the Connect host.
- **Connect** is where the work goes to live and be found — Shiny, Quarto, APIs,
  notebooks, MCP servers — with one place for permissions, logs, schedules and
  history.

Then the line Luis gave you, said as your own: **you develop on the same images you
deploy to, so "works fine on my laptop" stops being a category of bug.** Git in the
middle is what turns publishing from an act of memory into a property of the repo.

Do not open an IDE until you have said all of that.

## Act 2 — Positron, for the Python folks (20 min)

Open the project folder in Positron. `CanopyLab_CropScience/` is a single project
holding R and Python side by side — which is itself the first point.

**2.1 The notebook editor** — open `notebooks/field-trial-tour.ipynb`.
This is a Jupyter notebook, `.ipynb`, no conversion, opening in Positron's own
notebook editor. Run the first cells. Say: *this is the file your team already has;
nothing about it changes.*

**2.2 The Variables pane** — after loading the data, point at it. Every object in
the session, sizes and types, without printing anything. VS Code does not have
this; it is the thing R users have had for fifteen years and Python users have been
doing `df.head()` for.

**2.3 The Data Explorer** — click `trials` in the Variables pane. 1,800 rows, sort
by yield, filter to `Untreated Check`, look at the column summaries. Then say the
uncomfortable part: *this is what people leave the IDE and open Excel for.*

**2.4 The Plots pane with history** — run the chart cells. Step back through the
plot history. Point out that comparing this run's chart to the last one is a click,
not a re-run.

**2.5 The Connections pane** — connect to `data/synthetic-agronomy.duckdb`. Browse
`field_trials` and `sites`, expand columns, preview a table. No credentials, no
warehouse, works on a plane. Say: *in your world this is Snowflake or Postgres, and
the pane is the same.*

**2.6 SQL and ggsql — charts straight from the query.**
Open `sql/01-trial-summary.sql` and run it against the DuckDB connection. Then open
`sql/02-treatment-response.ggsql` and show the grammar-of-graphics clauses bolted
onto the end of ordinary SQL:

```sql
SELECT variety, treatment, avg(yield_t_ha) AS mean_yield
FROM field_trials GROUP BY variety, treatment
VISUALISE mean_yield AS x, variety AS y, treatment AS color
DRAW point
LABEL title => 'Every hybrid gains from a protection programme, by different amounts'
```

```bash
uv run python python/run_ggsql.py sql/02-treatment-response.ggsql
```

Run all four (`03` is a season trend, `04` facets disease vs yield by treatment).
The point for a data engineer: **the chart is a property of the query**, so the
analyst who owns the SQL owns the chart, and it lives in Git as text.

**2.7 Posit Assistant** — in the notebook, ask it to add a cell that ranks stations
by response to Programme Bravo. Show `/plan` for something larger, and mention
`AGENTS.md` for project memory. Keep this short here; the payoff lands in Act 4
when the Assistant is calling Connect-hosted tools.

**2.8 A Python app, from the same project.**
`uv run streamlit run streamlit_app.py`. Filter the regions, narrow to 2023,
highlight a hybrid, and hover a dot — the Altair tooltips give the gain per hybrid.

Two things to say while it is on screen:

- It reads `python/trials.py`, and `trials.yield_response()` is the same definition
  the R package pins — measured against the hybrid's own untreated check. The
  Python team did not re-derive it from the Shiny app's SQL, and `uv run pytest`
  holds them to it (`tests/test_trials.py`, eight tests including "refuses to guess
  without a control").
- Its charts read `_brand.yml`, the same file the Quarto report and the Shiny app
  read. Same palette, no design review.

If the room is Python-first, run this *before* the Shiny app in Act 3 and let
`app.R` be the "and R too" moment rather than the other way around.

**Where VS Code users land:** same keybindings available, same extensions story,
plus the panes above and a real R session when they need one. This is the migration
argument, and it is not "give up your editor" — it is "the same editor with the
data-science furniture."

## Act 3 — The R users: package, report, app (10 min)

**3.1 The package.** `canopytrials/` is the internal package: `read_trials()`,
`yield_response()`, `site_summary()`, `theme_canopylab()`. Show
`R/summaries.R` and then `tests/testthat/test-summaries.R`.

The line to say: *"yield response" is defined exactly once per language, in a
function, with a test that pins the definition — gain is always measured against
the same hybrid's own untreated plots. The report, both dashboards and the
Assistant's tools all call it. They cannot disagree about the number.* That is why
R teams package things, and it is exactly the argument for a private Package
Manager repository.

If someone asks why there are two implementations at all: because the two teams
work in two languages, and the alternative is not one implementation — it is five
copies of the same SQL in five files. `tests/test_trials.py` asserts the Python
result has the same shape and columns as the R one, so a rename on either side
fails CI rather than surfacing as two different numbers on two dashboards.

**3.2 The Quarto report.** Render `trial-report.qmd`. Point out:
- `theme: brand` — the palette comes from `_brand.yml`, which the Shiny app and
  the ggplot theme also read.
- the inline numbers in the prose (`r best$variety`) — the sentences update with
  the data, so nobody re-types a figure after harvest.
- the DuckDB section: the aggregation runs in the database.

**3.3 The Shiny app.** `Rscript -e 'shiny::runApp("app.R")'`. Filter regions,
narrow the seasons to 2023, highlight a hybrid. Note that the value boxes and the
table come from the same package functions as the report.

Put it beside the Streamlit app from 2.8 if you have the screen space: same
filters, same numbers, same palette, two languages. Nobody had to pick a winner.

Then say: *all three of these are published the same way, and none of them knows
where it is running.*

## Act 4 — Git, CI/CD, Connect, and MCP in the Assistant (15 min)

**4.1 Publish directly, once.** `Rscript deploy.R`, or the Publish button in
Positron. Show it landing in Connect. This is the "we can do it directly" half.

**4.2 Then show the Connect content page.** This is the part Luis asked for
explicitly — what a deployed application actually looks like:
- **Access** — who can see it, groups, and the sharing link
- **Logs** — the app's stdout, per process, without SSH
- **Schedule** — the Quarto report re-rendering after each harvest and emailing
  the trialling team
- **Versions** — the previous bundle still there, one click to roll back
- **Runtime** — process counts and timeouts

Say: *this is the user management, log management and deployment surface, once, for
everything — an R Shiny app, a Python notebook, an API, an MCP server.*

**4.3 Now show the Git half.** Open
`.github/workflows/deploy-connect.yml`. Walk the five publish steps: Quarto report,
Shiny app, Streamlit app, notebook, MCP server. Then
`.github/workflows/check-package.yml`: every PR runs two jobs — `R CMD check` on
`canopytrials`, and `uv sync --locked` plus `pytest` on the Python module — before
it can merge. One pipeline, both languages, no separate release process.

The transformation Luis described, stated plainly: **`main` is the definition of
what is running.** No one publishes from a laptop; no one wonders which version is
live; the deployment record is the commit history. And because the CI runner
restores from `renv.lock` and `uv.lock` through Package Manager, it installs the
same versions the Workbench session had.

**4.4 The MCP server — Assistant with your data, governed.**
`mcp/server.py` is a FastMCP server exposing six tools over the trial database.
Deployed to Connect:

```bash
rsconnect deploy fastapi --entrypoint server:app --title "CanopyLab trials MCP" ./mcp
```

Connect auto-detects the `mcp` content category from `fastmcp` in
`requirements.txt`. Then `.posit/assistant/settings.json` points Positron's
Assistant at it:

```json
{
  "mcpServers": {
    "canopylab-trials": {
      "type": "remote",
      "url": "https://connect.example.com/canopylab-trials-mcp/mcp",
      "headers": { "Authorization": "Key {env:CONNECT_API_KEY}" }
    }
  }
}
```

Run `/mcp` in the Assistant panel to show it connected, then ask in the chat:

> *Using the canopylab-trials tools, which hybrid gains least from Programme
> Bravo, and how does its disease index compare with the others?*

The closing point, and it is the strongest one in the demo: **the assistant's
access to internal data is Connect content.** Same permissions, same logs, same
audit trail, deployed by the same pipeline. Not an API key in someone's dotfile,
not a server on a laptop. Full instructions live in `MCP-SETUP.md`.

---

## Data context (so you can answer questions confidently)

Six fictional research stations in three regions, five seasons (2021–2025; 2023
runs ~30% below normal rainfall), five hybrids differing in yield potential,
disease tolerance and drought tolerance, three treatments (*Untreated Check*,
*Programme Alpha* at moderate suppression, *Programme Bravo* at strong
suppression), four replicate plots each — 1,800 harvested plots.

Numbers you will be asked about:

| Fact | Value |
|---|---|
| Mean gain, Programme Bravo vs untreated | **+0.69 t/ha** |
| Disease pressure index, untreated → Bravo | **47.5 → 9.5** |
| Biggest responder | CL-Ember 33, +1.00 t/ha |
| Smallest responder | CL-Beacon 44, +0.37 t/ha (it has its own disease tolerance) |
| Dry-season effect | every hybrid drops; the spread between hybrids narrows |
| Held-out R² of the notebook's linear model | 0.775, MAE 0.414 t/ha |

Why crop science and not something generic: this is Syngenta's actual shape of
problem — replicated trials, site-year effects, treatment response, a dry year
that changes the ranking. Nothing here is Syngenta's data, and nothing here uses a
real hybrid or product name.

## Setup before the meeting

```bash
uv sync
uv run python data/generate_data.py
Rscript -e 'renv::restore()'
R CMD INSTALL canopytrials
quarto render trial-report.qmd
uv run pytest                                # 8 tests, ~1s
uv run python python/run_ggsql.py            # warms outputs/
```

Then:

1. Publish the five content items to your Connect demo server (`Rscript deploy.R`
   plus the three printed commands), so Act 4 shows real content pages.
2. Deploy the MCP server and configure `.posit/assistant/settings.json` with your
   Connect URL. Export `CONNECT_API_KEY` in the shell you launch Positron from,
   and confirm `/mcp` shows it connected. **Do this the day before** — it is the
   only step with a moving part.
3. Have the Connect content page for the Shiny app open in a tab already.
4. Open the notebook once and run it through, so the kernel is warm.

## Pre-demo checklist

- [ ] Positron open on `CanopyLab_CropScience/`, other projects closed
- [ ] DuckDB connection already added in the Connections pane
- [ ] Notebook run once, outputs visible, kernel alive
- [ ] `trial-report.html` rendered and openable
- [ ] Shiny app running locally in a spare terminal
- [ ] Streamlit app running locally in another (`uv run streamlit run streamlit_app.py`)
- [ ] Connect tab open on the deployed app's content page
- [ ] `/mcp` confirmed connected in the Assistant panel
- [ ] `CONNECT_SERVER` / `CONNECT_API_KEY` exported; **no keys visible on screen**
- [ ] Terminal font size up; Assistant panel wide enough to read

## Talking points by objection

**"We already have VS Code and Jupyter."** Good — keep them, they run on Workbench
too. Positron is the option for the people who keep leaving the editor to look at
data. Show 2.3 and 2.5 again and stop talking.

**"Our R and Python teams are separate."** They are separate until deployment. One
Connect, one Package Manager, one CI pipeline, one `_brand.yml`. This project is
one folder with both languages in it.

**"We have Git already."** Then you are most of the way there. What is missing is
the last hop: a merge to `main` that puts the thing in front of users. That is the
workflow file, and it is 60 lines.

**"How do we govern AI access to internal data?"** Act 4.4. The tools are Connect
content with Connect permissions and Connect logs. That is the answer, and it is a
short one.

**"Can we do this on our own infrastructure?"** Yes — Workbench, Connect and
Package Manager all run in your VPC or on-prem, on your images.

## Known gaps, so nothing surprises you

- Nothing here has been deployed to a live Connect server. The commands and the CI
  workflow follow Connect's documented interfaces but were not executed. Publish
  once yourself before the meeting.
- `ggsql` for R requires R ≥ 4.5 (on 4.4.x its install fails with a
  `tools::sha256sum` error). The `.ggsql` files here run through the Python API,
  which is the right story for this audience anyway. Do not promise the R binding
  live unless you have tested it on your R version.
- `canopytrials` is installed from source here. Before Connect can restore it, it
  needs a home: a local source repository in Package Manager, or a Git remote that
  `renv` can install from. Worth saying out loud — it is a natural Package Manager
  segue.
- Altair's PNG export needs font *stacks*, not `"Open Sans"` on its own: given a
  font it cannot find, `vl-convert` renders the chart and silently drops every
  label. `python/charts.py` names fallbacks. If you add a chart and the labels
  vanish from a saved PNG, that is why — the browser is unaffected.
- The `.ggsql` parser has three edges: no trailing semicolon, `LABEL` accepts
  `title`/`subtitle`/`x`/`y` only, and a `--` inside a quoted label string breaks
  execution. Do not improvise new labels on stage.

## Follow-ups to offer

- A Workbench trial on their images, with Positron enabled for the Python team
- A private Package Manager repository holding their internal packages
- One of their existing Shiny apps or notebooks put behind this exact CI pipeline
- The MCP pattern applied to one of their real internal data services

---

*This project contains synthetic data and analysis created for demonstration
purposes only. All data, insights and business scenarios were artificially
generated using AI.*
