# Robot Canvas

Visual, config-driven authoring and execution for Robot Framework. Built for hardware-in-the-loop (HIL) operators who prefer drag-and-drop over raw syntax.

## Features

- **Blockly-based editor** — Visual blocks for test cases, keywords, control flow (IF, FOR, WHILE, TRY)
- **Model-first architecture** — Canonical Pydantic model; Blockly is a view
- **Generic keyword palette** — Curated default with Expert toggle; loaded from Robot libdoc
- **Round-trip editing** — Import `.robot` → edit visually → export `.robot`
- **Run from UI** — Dry-run validation, hardware-free execution, full Robot output
- **Workspace storage** — JSON sidecar (`.canvas.json`) + generated `.robot` suites
- **Export & integration** — JUnit XML, CSV, JSON, Robot output.xml; CI/SonarQube ready
- **Docker Compose MVP** — One command, no-friction setup
- **Native path** — `pip install robot-canvas` / `pipx run robot-canvas`

## Quick Start

### Docker Compose (recommended)

```bash
docker compose up --build
# Open http://localhost:8000
```

### Native (pipx)

```bash
pipx install robot-canvas
robot-canvas init --workspace my_workspace
robot-canvas serve --workspace my_workspace
# Open http://localhost:8000
```

### From source

```bash
git clone https://github.com/your-org/robot-canvas
cd robot-canvas
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
robot-canvas init --workspace my_workspace
robot-canvas serve --workspace my_workspace
```

## CLI Reference

```bash
robot-canvas --version
robot-canvas init [--workspace DIR] [--force]
robot-canvas serve [--workspace DIR] [--host HOST] [--port PORT] [--reload]
robot-canvas generate DOCUMENT.json [--out FILE.robot]
robot-canvas validate DOCUMENT.json [--dry-run]
robot-canvas catalog [--library NAME] [--curated]
```

## Project Structure

```
robot-canvas/
├── src/robot_canvas/
│   ├── api/           # FastAPI application + schemas
│   ├── generator/     # Robot source writer + validation
│   ├── keywords/      # libdoc catalog + palette
│   ├── model/         # Pydantic canvas document model
│   ├── workspace/     # File storage + demo suite
│   ├── cli.py         # Command line interface
│   └── __main__.py
├── web/               # React + TypeScript + Blockly frontend (to be built)
├── tests/             # Unit tests (30 passing)
├── demo/              # Example workspace
└── pyproject.toml
```

## Development

```bash
# Install dev dependencies
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Run tests
.\.venv\Scripts\python.exe -m pytest tests -v

# Lint & format
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m ruff format src tests

# Type check
.\.venv\Scripts\python.exe -m mypy src
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Canvas Document                   │
│  (Pydantic model: suite, tests, keywords, settings) │
└──────────────┬──────────────────────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│   Blockly   │ │   Writer    │
│   (Editor)  │ │ (.robot out)│
└─────────────┘ └──────┬──────┘
                       ▼
              ┌─────────────────┐
              │  Robot Runner   │
              │  (dry-run, run) │
              └─────────────────┘
```

## Roadmap

| Phase | Deliverable |
|-------|-------------|
| 0 ✓   | Scaffold, model, writer, validation, catalog, CLI, workspace |
| 1     | Blockly editor MVP (suite/test/setup/teardown, keyword blocks) |
| 2     | Control flow, user keywords, argument validation, import `.robot` |
| 3     | Run history (SQLite), results dashboard, JUnit/CSV/JSON export |
| 4     | pywebview desktop, docs, CI, release packaging |

## License

MIT