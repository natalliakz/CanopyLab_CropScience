# Publishing the MCP server to Connect and using it from Posit Assistant

The end state: an assistant inside Positron that can answer "which hybrid gains
least from Programme Bravo, and why" by querying CanopyLab's trial database —
where the tool it calls is Connect content, governed by Connect's permissions,
visible in Connect's logs, and deployed by the same CI pipeline as the Shiny app.

Everything below has been run except the Connect steps themselves, which need a
Connect server and an API key. The server has been verified locally: it starts,
serves `/mcp`, and a client lists all six tools.

---

## 1. Check it works locally first

```bash
# From the project root
uv run python data/generate_data.py          # if you have not already
uv run uvicorn server:app --app-dir mcp --port 8123
```

In another terminal:

```bash
uv run python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8123/mcp") as client:
        print([tool.name for tool in await client.list_tools()])
        result = await client.call_tool("yield_response", {"hybrid": "CL-Cinder 07"})
        print(result.content[0].text)

asyncio.run(main())
PY
```

Expected: `['list_hybrids', 'yield_response', 'station_summary', 'season_trend',
'run_sql', 'data_notice']`.

## 2. Ship the database with the bundle

The server reads a DuckDB file. Connect unpacks the content bundle into its own
directory, so the file has to travel with it:

```bash
cp data/synthetic-agronomy.duckdb mcp/synthetic-agronomy.duckdb
```

`mcp/server.py` looks for `$CANOPYLAB_DB`, then the copy beside itself, then
`../data/`. In a real deployment you would point `CANOPYLAB_DB` at a mounted path,
or swap the DuckDB connection for your warehouse and let Connect hold the
credential as an environment variable.

## 3. Deploy

```bash
# One-time: teach rsconnect about your server
rsconnect add --server https://connect.example.com --api-key "$CONNECT_API_KEY" --name canopylab

rsconnect deploy fastapi \
  --name canopylab \
  --entrypoint server:app \
  --title "CanopyLab trials MCP" \
  ./mcp
```

`rsconnect deploy fastapi` is correct here — an MCP server over HTTP *is* an ASGI
app. `--entrypoint server:app` points at the `app` object at the bottom of
`server.py`.

## 4. Three settings in Connect, then it is done

In the content's settings panel:

1. **Access** — who may call it. An MCP server inherits Connect's whole
   permissions model, which is the reason to host it here rather than on a laptop.
2. **Runtime → minimum processes: 1.** MCP clients hold a session open; a content
   item that has scaled to zero will make the first call time out.
3. **Category** — Connect auto-detects `mcp` from `fastmcp` in
   `requirements.txt`. If it does not, set the category to *MCP Server* manually
   (or via the Update Content API). The category is what makes Connect show the
   MCP connection details on the content page.

Then set a vanity URL, e.g. `https://connect.example.com/canopylab-trials-mcp/`.
The MCP endpoint is that URL plus `mcp`.

## 5. Point Posit Assistant at it

Posit Assistant reads MCP configuration from either of:

| File | Scope |
|---|---|
| `~/.posit/assistant/settings.json` | you, every project |
| `.posit/assistant/settings.json` | this project, everyone who clones it |

They are merged by server name, so a project can add servers without touching
your global config. This repository ships the project-scoped version at
[`.posit/assistant/settings.json`](.posit/assistant/settings.json) — edit the URL
and go:

```json
{
  "mcpServers": {
    "canopylab-trials": {
      "type": "remote",
      "url": "https://connect.example.com/canopylab-trials-mcp/mcp",
      "headers": {
        "Authorization": "Key {env:CONNECT_API_KEY}"
      }
    }
  }
}
```

Two details that matter:

- `{env:CONNECT_API_KEY}` is expanded at runtime, so **no key is ever written into
  a file that gets committed**. Export it in your shell profile, or on Workbench
  set it once in the session environment.
- `Key <token>` — not `Bearer` — is Connect's API-key scheme. If your Connect has
  OAuth integrations configured, drop the `headers` block entirely and let
  Assistant discover the OAuth endpoints instead.

Then, in Positron:

1. Reload the window (or restart Assistant) so it re-reads the settings file.
2. Run `/mcp` in the Assistant chat. The server should appear as connected, with
   its six tools listed.
3. Ask it something real:
   > *Using the canopylab-trials tools, which hybrid gains least from Programme
   > Bravo, and what does its disease index look like compared with the others?*

If `/mcp` shows the server as failed, the usual causes in order: the content has
scaled to zero (fix minimum processes), the URL is missing the trailing `/mcp`,
or `CONNECT_API_KEY` is not exported in the environment Positron was launched
from.

## 6. Let CI redeploy it

`.github/workflows/deploy-connect.yml` redeploys the MCP server on every merge to
`main`, alongside the Quarto report and the Shiny app. The same `CONNECT_SERVER`
and `CONNECT_API_KEY` secrets serve all three. This is the point Luis was making
about developing where you deploy: the assistant's tools are versioned in Git, and
nobody has an MCP server running on their laptop that only they can reach.

---

*This project contains synthetic data and analysis created for demonstration
purposes only. All data, insights and business scenarios were artificially
generated using AI.*
