"""Runtime switches shared by the CLI, HTTP API and MCP server."""

from __future__ import annotations

import os

ENV_ALLOW_RUN = "ROBOTSTUDIO_ALLOW_RUN"
_DISABLED = {"0", "false", "no", "off"}


def allow_run_from_env() -> bool:
    """Return whether suite execution is enabled.

    Execution is allowed unless ``ROBOTSTUDIO_ALLOW_RUN`` is set to a falsey
    value, so the default deployment keeps the full feature set.
    """
    value = os.environ.get(ENV_ALLOW_RUN, "true")
    return value.strip().lower() not in _DISABLED
