# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Web editor**: selecting a suite no longer crashes the page. Blocks load and save
  in Blockly's own workspace format, edits round-trip to identical Robot source, and
  suite settings the canvas does not edit are kept on save.
- **Web editor**: keyword names are free text, so user keywords can be called, and
  documentation and raw lines are no longer dropped (Blockly core has no multi-line field).
- **Web editor**: IF/ELSE IF/ELSE and TRY/EXCEPT/ELSE/FINALLY are sibling blocks instead of
  mutators; call arguments are stacked argument blocks.
- **Web UI**: switching suites shows the selected suite, and Validate and Dry Run show their
  result after a Preview.

## [0.1.0] - 2026-11-24

### Added

- **Packaging & rename**: `robotstudio` distribution, import package, CLI command,
  and `ROBOTSTUDIO_*` environment prefix with PEP 621 metadata, poetry-core build,
  lockfile, and SPDX MIT license.
- **Workspace storage**: Atomic JSON sidecar plus generated `.robot` storage,
  a starter suite, and a `.robot` importer; the storage package is now trackable.
- **Execution engine**: Single-flight suite runner with hard timeout, console capture,
  `output.xml` parsing, and `.runs/` history.
- **Export formats**: JUnit XML, results CSV, authored-cases CSV, results JSON,
  and a redacted bundle ZIP.
- **API endpoints**: Run, run history and export endpoints, plus `/llms.txt` for agent clients.
- **Web interface**: Run action with per-test results and export links.
- **MCP server**: 16 `studio_*` tools, `robotstudio://` resources, and author/debug
  prompts over stdio for Claude Code and Desktop.
- **CLI commands**: `run`, `runs`, `export`, and `mcp` subcommands.
- **CI/CD pipeline**: Lint, type checking, tests on Python 3.11–3.13, web build,
  wheel smoke test, Docker build, and Trusted Publishing to TestPyPI and PyPI.
- **Docker image**: Multi-stage poetry-core build that bundles the SPA into the wheel.
- **Documentation**: Install paths, CLI, MCP setup, and workspace layout.
- **Escape hatch**: `--no-run` flag and `ROBOTSTUDIO_ALLOW_RUN` environment variable
  to disable suite execution for locked-down deployments.

### Changed

- Migrated from setuptools to Poetry with PEP 621 metadata while keeping
  editable installs working through PEP 660.
- Rewrote the Dockerfile as a multi-stage poetry-core build (Node → wheel → slim runtime).
- Fixed the unanchored `workspace/` gitignore pattern that was hiding the storage package.
- Buffered Robot's console during dry runs so validation never leaks into the MCP protocol stream.

### Removed

- Deprecated test scripts (`test_import.py`, `test_parse.py`, `test_write*.txt`)
  and the committed `rigor.log` file that are no longer in use.

### Breaking Changes

- The package is now imported as `robotstudio` (was `robot_canvas`).
- The console script is `robotstudio` (was `robot-canvas`).
- Environment variables use the `ROBOTSTUDIO_` prefix (was `ROBOT_CANVAS_`).
- Internal import paths for all modules have moved. Any consumers importing from
  `robot_canvas.*` will need to update to `robotstudio.*`.

[0.1.0]: https://github.com/isaacgraper/robotstudio/releases/tag/v0.1.0