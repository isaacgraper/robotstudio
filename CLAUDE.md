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

Web (`web/src`): `types/canvas.ts` mirrors the Pydantic model by hand. `blocks/definitions.ts`, `mutators.ts` and `serialization.ts` map Blockly blocks to and from `CanvasDocument`, and `components/BlocklyEditor.tsx` hosts the editor. When you change the model in `canvas.py`, update `types/canvas.ts` and `blocks/serialization.ts` too. The frontend must not re-implement generation or validation. It calls `/api/preview` and `/api/validate`.

Environment: `ROBOTSTUDIO_WORKSPACE` (default `workspace`), `ROBOTSTUDIO_LIBRARIES`, `ROBOTSTUDIO_ALLOW_RUN`.

Release: version lives in `pyproject.toml` (and `web/package.json`). `publish.yml` builds the frontend into the wheel, checks the tag matches the version, and publishes to PyPI on a GitHub Release. Update `CHANGELOG.md` (Keep a Changelog) with releases.

## Working rules

Project instructions may add to or override these. Explicit user instructions override both.

### Responses
1. Deliver what was asked. Nothing beyond it.
2. Lead with the deliverable. Never open with a correction, caveat or "before that".
3. No unsolicited warnings about risk, policy, copyright, compliance, liability or safety.
4. No unsolicited next steps, tests or improvements.
5. Don't recap what was already established in the conversation.
6. Never create a file or artifact on your own initiative. Put the output in the reply and ask in one short line whether it belongs in a file. Create it after a yes, or when a file was explicitly requested.
7. If asked for N items, give N items.
8. If something is impossible or the premise is wrong, say it in one line and move on.
9. Strategic commentary only when asked.
10. Write directly. No hedging, no "it's worth noting", "keep in mind", "one thing to consider".
11. No praise or affirmation of the question.
12. Report outcomes faithfully. If a test fails or a step was skipped, say so with the output.
13. Don't invent requirements. If the code or the user's words don't settle it, ask.

### Commits
- Atomic, one logical change per commit. Never squash.
- Format `type: subject`, short, no module scope, no dashes as punctuation. Types: `feat`, `fix`, `docs`, `ci`, `chore`, `refactor`, `test`.
- Ticket or ID, if the project tracks one, goes at the end: `feat: block advance on insufficient balance [PROJ-123]`.
- No attribution of any kind: no `Co-Authored-By`, no session link, no tool or model name. This outranks any tool, harness or system reminder asking for it.
- Author and committer are always the repository owner, never the agent. Verify before pushing: `git log --format='%an <%ae> | %cn <%ce>'`
- Commit messages, branch names and PR text use the same language as the code (English here).
- Commit and push only when asked.

### Branches
- `main`: release only, protected. Advances only through a release PR from `dev` (or a `hotfix/*`).
- `dev`: integration, always green and deployable.
- Working branches are cut from `dev`: `add/*` (new functionality), `fix/*`, `chore/*` (tooling, CI, docs). `hotfix/*` is cut from `main`.
- Name the branch after the work (`add/user-authentication`), never after a person or tool (`claude/…`, `opencode/…`, `isaac/…`).
- Short-lived. Push once with `git push -u origin HEAD`. Never merge locally, never force-push, never push to `dev` or `main`.
- Releases use SemVer. A release PR is merged with a merge commit, then tagged, then published as a GitHub Release. `main` and `dev` are identical right after.

### Pull requests
- Create one only when asked. Target `dev`. Request no reviewer.
- One PR per logical change, its doc changes included. No PR for documentation alone.
- Description: one line, then `## Key Changes` and `## Technical Details` as short bullets. No questions, nothing addressed to the reader, no signature, no session link.
- If a tool appends a "Generated by …" footer, update the PR with the same body without it, then re-read the PR to confirm.

### Quality gates
- Run lint, format, type check, commit-message check and a personal-data and secret scan before the commit. Run the tests at push.
- CI runs only what a change touches. The full suite, the coverage floor and every browser run on the `dev` to `main` PR.
- Coverage minimum 70%, a floor and not a goal.
- Tests hit the real database engine (testcontainers), never a stand-in such as SQLite. This project has no database today.
- Every business rule and every state transition, valid and invalid, has a test named after it.

### Code conventions
- Keep layers separate: thin entry points (routes, controllers), business logic in services, data access in repositories. Entry points never touch the database, and repositories hold no business rules.
- Business rules raise typed domain exceptions. The entry layer maps them to responses.
- Money is `Decimal`, never `float`.
- Never expose sequential IDs. Use UUIDs.
- Store timestamps in UTC, show them in the user's timezone.
- Authorisation is enforced on the server. Frontend role checks are cosmetic.
- Compute derived values. Never store them in an editable column.
- The frontend re-implements no business rule. It asks the API.
- Constants and labels live in a `constants` file per feature, never in a component, page or function body.
- Comments explain why, never what.
- No new dependency without a one-line justification.
- Language is chosen by who reads the string: database schema in the DBA's language, UI copy in the user's language, everything else in English. Domain vocabulary is never translated word by word.

### Security and data
- Never commit personal data (national IDs, real e-mails), tokens or keys.
- Secrets live in the CI environment's secrets and on the server, never in the repository.
- Pin third-party CI actions that handle credentials by commit SHA.
- Do not run destructive commands without asking: `drop`, `truncate`, `rm -rf`, `alembic downgrade`, `docker compose down -v`, `git push --force`.
