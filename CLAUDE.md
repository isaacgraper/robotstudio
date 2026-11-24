# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Python 3.11+, managed with Poetry (`poetry.toml`, `poetry.lock`). CI runs the same gates on 3.11, 3.12 and 3.13.

```bash
poetry install --all-extras                 # --all-extras pulls in the `mcp` extra
poetry run pytest tests -q
poetry run pytest tests/test_writer.py::test_name -q   # single test
poetry run ruff check src tests
poetry run ruff format src tests            # CI uses `ruff format --check`
poetry run mypy src
```

Ruff enforces Google-style docstrings (`D`) in `src/` (tests are exempt). Line length 88.

Frontend (`web/`, Node 22, Vite + React 18 + Blockly):

```bash
cd web && npm ci && npm run dev     # dev server on :5173, proxies /api
cd web && npm run build             # tsc && vite build; this is the only frontend check, there are no JS tests or linter
```

Running the app: `robotstudio init|serve|run|runs|export|validate|generate|catalog|mcp` (see `cli.py`). The server serves the SPA only if `src/robotstudio/web_dist/` exists; it is gitignored. For a local wheel, copy `web/dist` there (CI and the Dockerfile do this).

Gotchas:
- `web/vite.config.ts` proxies `/api` to `http://backend:8000`, but the compose service is named `robotstudio`. Outside compose, the dev proxy needs a different target.
- `.gitignore` ignores `*.robot` and `*.canvas.json` everywhere except `tests/golden/*.robot`. Workspace data never gets committed.
- The `workspace/` ignore rule is anchored (`/workspace/`) on purpose. An unanchored rule hides `src/robotstudio/workspace/`.

## Architecture

One canonical document, three front ends. `model/canvas.py` defines `CanvasDocument` (Pydantic): suites, tests, keywords and a recursive `Step` union (`call`, `if`, `for`, `while`, `try`, `var`, `return`, `break`, `continue`, `comment`, `raw`). Everything else is a view over it:

- **Generation:** `generator/writer.py` renders a document to `.robot` source deterministically. `tests/golden/demo.robot` pins the output, so writer changes show up there. `generator/validation.py` parses source with Robot's own parser, or does a dry run.
- **Import:** `workspace/import_robot.py` (the largest module) is the reverse path, `.robot` to document. It is a round-trip with the writer, so change them together.
- **Storage:** `workspace/store.py` keeps `<stem>.canvas.json` (source of truth) plus the generated `<stem>.robot` in a workspace directory. Writes are atomic. Stems must match `^[a-z0-9][a-z0-9-]*$`, which is the path-safety check. Run output goes under `<workspace>/.runs/<run_id>/`.
- **Execution:** `runner/execution.py` saves, then launches `python -m robot` in a subprocess with a hard timeout. A process-wide lock allows one run at a time (`RunBusyError`). It parses `output.xml` into `RunSummary` (`model/results.py`) and writes `summary.json`. Exports (`exports/`: JUnit, CSV, JSON, redacted bundle ZIP) are built from the summary.
- **Keywords:** `keywords/catalog.py` discovers keywords through libdoc over `DEFAULT_LIBRARIES` plus `ROBOTSTUDIO_LIBRARIES`, cached with `lru_cache`. `CURATED` is the default palette set. Expert mode exposes everything.

Front ends, each a thin layer over the modules above:
- `api/app.py` is a FastAPI app (`create_app`). Routes live under `/api/*` and `/llms.txt`, and it serves the built SPA at `/`. CORS allows only localhost origins on 5173 and 8000.
- `mcp/server.py` is a FastMCP stdio server (`create_server`) with 16 `studio_*` tools, `robotstudio://` resources and two prompts. `studio_run_suite` is not registered at all when running is disabled. It must never write to stdout outside the protocol.
- `cli.py` wires both and exposes the headless commands.

Run gating: `ROBOTSTUDIO_ALLOW_RUN` (default true) and `--no-run` are read through `settings.allow_run_from_env`, and the API, MCP and CLI all honour them. The README's statement that there is no opt-in flag is outdated.

Web (`web/src`): `types/canvas.ts` mirrors the Pydantic model by hand. `blocks/definitions.ts` defines the Blockly blocks and `blocks/serialization.ts` maps `CanvasDocument` to and from Blockly workspace JSON (`{ blocks: { languageVersion, blocks: [...] } }`). `components/BlocklyEditor.tsx` hosts the editor. Every value is a text field. IF/ELSE IF/ELSE and TRY/EXCEPT/ELSE/FINALLY are sibling blocks in a statement chain, restricted by connection checks, not mutators. `workspaceToModel` takes the open document as a base and only replaces tests, keywords and libraries, so settings the canvas does not edit survive a save. When you change the model in `canvas.py`, update `types/canvas.ts` and `blocks/serialization.ts` too. The frontend must not re-implement generation or validation. It calls `/api/preview` and `/api/validate`.

Environment: `ROBOTSTUDIO_WORKSPACE` (default `workspace`), `ROBOTSTUDIO_LIBRARIES`, `ROBOTSTUDIO_ALLOW_RUN`.

Release: version lives in `pyproject.toml` (and `web/package.json`). `publish.yml` builds the frontend into the wheel, checks the tag matches the version, and publishes to PyPI on a GitHub Release. Update `CHANGELOG.md` (Keep a Changelog) with releases.

## Token and workflow rules

### Task sizing
- Small tasks (1-2 files, quick bug fixes, minor UI tweaks): no plan. Read only the target files, apply the minimal fix directly, and explain in under 3 sentences.
- Multi-file features, refactors or complex updates (3+ files or architectural changes): before writing code, write a concise plan of at most 40 lines with Goal, Target Files, Key Constraints and a Checklist. Stop and wait for approval before executing, and report progress against the checklist as each step finishes. Put the plan in a `PLAN.md` file only when asked, and ask before deleting it.

### Context and output hygiene
- Never scan or read the entire codebase unless explicitly asked. Inspect only the files tied to the task.
- Output targeted edits or specific functions instead of rewriting unchanged files.
- Keep responses concise: no filler intros, no unsolicited refactoring.
