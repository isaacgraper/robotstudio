# Robotstudio

Visual, model-driven authoring, execution and export for
[Robot Framework](https://robotframework.org). Drag blocks, keep real `.robot`
files, run suites, and let an LLM drive the whole thing over MCP.

Robotstudio is deliberately generic: it works with plain Robot Framework
libraries and discovers keywords through libdoc. Nothing vendor-specific is
built in.

## What you get

- **Blockly editor** for suites, tests, keywords, setups/teardowns and control
  flow (IF, FOR, WHILE, TRY).
- **Model-first design** — a canonical Pydantic document; the editor is one
  view over it. The same document renders deterministic `.robot` source.
- **Keyword palette from libdoc** — a curated default set plus an Expert mode
  that exposes every keyword in the configured libraries.
- **Round-trip editing** — import an existing `.robot` file, edit it visually,
  and regenerate source.
- **Run suites** from the CLI, the web UI, or MCP. One run at a time, hard
  timeout, output confined to the workspace.
- **Exports** — JUnit XML, results CSV, authored-cases CSV, results JSON, and a
  redacted bundle ZIP with the sources and raw Robot artifacts.
- **MCP server** — 16 tools, resources and prompts so Claude Code, Claude
  Desktop and other MCP clients can search keywords, author suites, validate,
  run and export.
- **No external services** — a local workspace directory and a single process.

## Install

```bash
pip install robotstudio
# or, with the MCP server:
pip install "robotstudio[mcp]"
# or, isolated:
pipx install "robotstudio[mcp]"
```

Requires Python 3.11+.

### Docker

```bash
docker compose up --build
# http://localhost:8000
```

The image builds the frontend, bundles it into the wheel, and serves the whole
app from one container. Mount a host directory at `/workspace` to keep suites.

## Quick start

```bash
robotstudio init --workspace my_workspace   # writes a demo suite
robotstudio serve --workspace my_workspace  # http://127.0.0.1:8000
```

Then open the UI, pick the demo suite, edit it, hit **Run**, and download the
JUnit XML or bundle from the results pane.

Headless:

```bash
robotstudio validate my_workspace/robotstudio-demo.canvas.json --dry-run
robotstudio run robotstudio-demo --workspace my_workspace
robotstudio runs --workspace my_workspace
robotstudio export <run-id> junit --workspace my_workspace --out junit.xml
```

## CLI

```text
robotstudio --version
robotstudio init    [--workspace DIR] [--force]
robotstudio serve   [--workspace DIR] [--host HOST] [--port PORT] [--reload]
robotstudio generate DOCUMENT.json [--out FILE.robot]
robotstudio validate DOCUMENT.json [--dry-run]
robotstudio catalog [--library NAME] [--curated]
robotstudio run     STEM [--workspace DIR] [--timeout SECONDS]
robotstudio runs    [--workspace DIR]
robotstudio export  RUN_ID FORMAT [--workspace DIR] [--out FILE] [--redact REGEX]
robotstudio mcp     [--workspace DIR]
```

`FORMAT` is one of `junit`, `results-csv`, `cases-csv`, `results-json`,
`bundle`.

Environment variables:

| Variable | Meaning |
| --- | --- |
| `ROBOTSTUDIO_WORKSPACE` | Workspace directory (default `workspace`) |
| `ROBOTSTUDIO_LIBRARIES` | Comma-separated extra libraries for the catalog |

## MCP server

The MCP layer is optional:

```bash
pip install "robotstudio[mcp]"
```

### Claude Code

```bash
claude mcp add robotstudio -- robotstudio mcp --workspace /absolute/path/to/workspace
```

On Windows, point at the console script explicitly:

```powershell
claude mcp add robotstudio -- "$env:USERPROFILE\.local\bin\robotstudio.exe" mcp --workspace C:\path\to\workspace
```

### Claude Desktop

Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "robotstudio": {
      "command": "robotstudio",
      "args": ["mcp", "--workspace", "C:/path/to/workspace"]
    }
  }
}
```

The server speaks stdio, writes logs to stderr only, and never prints to
stdout outside the protocol.

### Tools

| Tool | Purpose |
| --- | --- |
| `studio_list_suites` | List workspace suites |
| `studio_get_suite` | Load a suite as a canvas document |
| `studio_save_suite` | Create or overwrite a suite |
| `studio_delete_suite` | Delete a suite |
| `studio_read_robot` | Read generated `.robot` source |
| `studio_import_robot` | Import a `.robot` file |
| `studio_preview` | Render a document without saving |
| `studio_validate` | Parse, or dry-run with `dry_run_check` |
| `studio_search_keywords` | Search the libdoc catalog |
| `studio_describe_keyword` | Full keyword documentation |
| `studio_list_libraries` | Inspected libraries and failures |
| `studio_refresh_catalog` | Clear the libdoc cache |
| `studio_run_suite` | Execute a suite |
| `studio_list_runs` | Recent runs |
| `studio_get_run` | One run summary |
| `studio_export_run` | Export a run |

Resources: `robotstudio://suites`, `robotstudio://suites/{stem}`,
`robotstudio://suites/{stem}/robot`, `robotstudio://runs/{run_id}`.

Prompts: `author_suite`, `debug_failed_run`.

Any MCP-capable client works. For clients that only speak OpenAPI, the FastAPI
app publishes `/openapi.json` and interactive docs at `/docs`.

## Workspace layout

```text
my_workspace/
├── my-suite.canvas.json   # authored document (source of truth)
├── my-suite.robot         # generated Robot Framework suite
└── .runs/
    └── 20260101-120000-ab12cd34/
        ├── summary.json
        ├── console.log
        └── robot/
            ├── output.xml
            ├── log.html
            └── report.html
```

Runs are single-flight per process. `run_suite` is always available; there is
no opt-in flag. Use `--timeout` to bound execution.

## Development

Poetry manages the project:

```bash
poetry install --all-extras
poetry run pytest tests -q
poetry run ruff check src tests
poetry run ruff format src tests
poetry run mypy src
```

Editable installs still work with pip:

```bash
python -m pip install -e ".[mcp]"
```

Build the frontend into the package (needed for `serve` to host the SPA):

```bash
cd web
npm ci
npm run build
# copy web/dist into src/robotstudio/web_dist for a local wheel build
```

`poetry build` includes `src/robotstudio/web_dist`, so the published wheel is
self-contained.

## Project structure

```text
robotstudio/
├── src/robotstudio/
│   ├── api/           # FastAPI application and schemas
│   ├── exports/       # JUnit, CSV, JSON and bundle exporters
│   ├── generator/     # Robot writer and validation
│   ├── keywords/      # libdoc catalog
│   ├── mcp/           # MCP server (tools, resources, prompts)
│   ├── model/         # Canvas document and result models
│   ├── runner/        # Suite execution and run history
│   ├── workspace/     # Storage, demo suite and .robot importer
│   ├── cli.py
│   └── __main__.py
├── web/               # React + TypeScript + Blockly frontend
├── tests/
└── pyproject.toml
```

## License

MIT
