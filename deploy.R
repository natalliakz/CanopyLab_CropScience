# Manual publishing, for the first time and for the demo.
#
# The same four deployments the CI workflow does, in one script you can step
# through from Positron. Useful when showing "publish directly" before showing
# "publish via Git" — the point being that they put the same bundle on the same
# server, and the second one just remembers to do it every time.
#
# Requires two environment variables (never hard-code these):
#   CONNECT_SERVER   https://connect.example.com
#   CONNECT_API_KEY  a Connect API key
#
# Set them in ~/.Renviron, or on Workbench in the session environment.

server_url <- Sys.getenv("CONNECT_SERVER")
api_key <- Sys.getenv("CONNECT_API_KEY")

if (!nzchar(server_url) || !nzchar(api_key)) {
  stop(
    "Set CONNECT_SERVER and CONNECT_API_KEY before running this script.\n",
    "Nothing here is deployable without them, and neither belongs in Git."
  )
}

# 1. Register the server and the publishing account -------------------------

rsconnect::addServer(url = server_url, name = "connect")
rsconnect::connectApiUser(
  account = Sys.getenv("USER", "publisher"),
  server = "connect",
  apiKey = api_key
)

# 2. The Quarto report ------------------------------------------------------
#
# Deployed as a document, so Connect can re-render it on a schedule and email
# the result. The rendered HTML is not what gets uploaded — the source is.

rsconnect::deployDoc(
  "trial-report.qmd",
  appName = "canopylab-trial-report",
  server = "connect",
  forceUpdate = TRUE
)

# 3. The Shiny app ----------------------------------------------------------
#
# appFiles is explicit on purpose: the DuckDB file, the outputs directory and
# the notebook do not belong in the app bundle, and a smaller bundle restarts
# faster.

rsconnect::deployApp(
  appDir = ".",
  appFiles = c(
    "app.R",
    "_brand.yml",
    "data/synthetic-field-trials.csv",
    "data/synthetic-sites.csv"
  ),
  appName = "canopylab-trial-explorer",
  server = "connect",
  forceUpdate = TRUE
)

# 4. The Python content -----------------------------------------------------
#
# rsconnect-python handles the Streamlit app, the notebook and the MCP server.
# Run these from the terminal — they are shown here so the whole deployment story
# lives in one file.

cat(
  "\nFrom the terminal, for the Python side:\n\n",
  "  uv run rsconnect deploy streamlit \\\n",
  "    --server $CONNECT_SERVER --api-key $CONNECT_API_KEY \\\n",
  "    --entrypoint streamlit_app.py \\\n",
  "    --title 'CanopyLab field trial explorer (Python)' \\\n",
  "    --exclude .venv --exclude canopytrials --exclude renv .\n\n",
  "  uv run rsconnect deploy notebook \\\n",
  "    --server $CONNECT_SERVER --api-key $CONNECT_API_KEY \\\n",
  "    notebooks/field-trial-tour.ipynb\n\n",
  "  cp data/synthetic-agronomy.duckdb mcp/synthetic-agronomy.duckdb\n",
  "  cp python/trials.py mcp/trials.py\n",
  "  uv run rsconnect deploy fastapi \\\n",
  "    --server $CONNECT_SERVER --api-key $CONNECT_API_KEY \\\n",
  "    --entrypoint server:app --title 'CanopyLab trials MCP' ./mcp\n\n",
  "See MCP-SETUP.md for the three Connect settings the MCP server needs.\n",
  sep = ""
)
