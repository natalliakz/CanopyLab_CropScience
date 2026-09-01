# Git-backed Connect content: the Streamlit app

**Do not edit the files in this directory.** Almost all of them are copies, written
by `scripts/build_connect_bundle.py`. Edit the originals in the project root and
rebuild:

```bash
uv run python scripts/build_connect_bundle.py
```

CI runs the same script with `--check` on every pull request, so a copy that falls
behind its original fails the build rather than reaching Connect.

## Why this directory exists

Connect deploys git-backed content by reading a repository, a branch and a
subdirectory. There is no build step in that path — no CI runner, no
`generate_data.py`, no `R CMD INSTALL`. Connect installs `requirements.txt` and
runs the entrypoint against the files as committed.

So the directory is self-contained, and it is deliberately a *mirror* of the part
of the project root the app uses:

| In here | Copied from | Why the app needs it |
|---|---|---|
| `streamlit_app.py` | `../../streamlit_app.py` | the entrypoint |
| `python/trials.py` | `../../python/trials.py` | the shared definition of *yield response* |
| `python/charts.py` | `../../python/charts.py` | the Altair chart builders |
| `_brand.yml` | `../../_brand.yml` | the palette the charts read |
| `.streamlit/config.toml` | `../../.streamlit/config.toml` | Streamlit's own chrome colours |
| `data/*.csv` | `../../data/` | the synthetic trial data |
| `requirements.txt` | — | hand-maintained; five packages |
| `manifest.json` | — | generated; Connect's file list and Python constraint |

Because the layout matches, `streamlit_app.py` runs unchanged: `python/` is beside
it here exactly as it is in the repository.

The data is the two CSVs rather than the DuckDB file — text, so it diffs and
reviews like code. `trials.py` opens the database when it can find one and builds
the same three relations over the CSVs when it cannot, so the app, the queries and
the numbers are identical either way.

There is no `canopytrials` here and no R at all. This bundle installs five
packages from Package Manager and nothing else, which is the point: nothing in it
has to be built before it will start.

## Pointing Connect at it

In Connect: **New Content → Import from Git**, then

- repository: this repository's URL
- branch: `main`
- subdirectory: `connect/streamlit`

Connect finds `manifest.json`, installs `requirements.txt` and re-deploys whenever
`main` moves. `manifest.json` requests Python 3.12 or newer — if the server has no
matching interpreter, change `PYTHON_REQUIRES` in
`scripts/build_connect_bundle.py` and rebuild.

To publish the same directory directly instead, from a shell with `CONNECT_SERVER`
and `CONNECT_API_KEY` exported:

```bash
uv run rsconnect deploy manifest connect/streamlit/manifest.json \
  --title "CanopyLab field trial explorer (Python)"
```

---

*This project contains synthetic data and analysis created for demonstration
purposes only. All data, insights and business scenarios were artificially
generated using AI.*
