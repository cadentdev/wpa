#!/usr/bin/env bash
# Stop hook: lint, format check, and the full test suite with the coverage
# floor must pass before a Claude Code session ends. Exit 2 sends the failure
# back to Claude to fix; exit 1 would let the session finish anyway.
#
# stop_hook_active is true when Claude is already continuing because of this
# hook. Blocking again every time could loop for hours in an unattended cloud
# session, so a second consecutive failure is reported but allowed through.
# CI is the backstop.

input=$(cat)
active=$(printf '%s' "$input" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("stop_hook_active", False))' 2>/dev/null)

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# Run the tools as modules of the interpreter the project is installed into.
# A bare `pytest`/`ruff` can resolve to an unrelated install on PATH (e.g. a
# uv tool shim) that lacks pytest-cov or the project's dependencies.
if out=$( { python3 -m ruff check . && python3 -m ruff format --check . && python3 -m pytest -q --cov=wpa --cov-fail-under=98; } 2>&1 ); then
  exit 0
fi

printf '%s\n' "$out" | tail -40 >&2
if [ "$active" = "True" ]; then
  echo "check-before-stop: checks still failing after a retry; stopping anyway. CI will catch it." >&2
  exit 0
fi
echo "check-before-stop: lint, format, tests, or coverage failed. Fix before finishing." >&2
exit 2
