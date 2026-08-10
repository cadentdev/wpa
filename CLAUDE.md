# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

WPA is a Python CLI tool for WordPress automation via the REST API. It manages posts, pages, users, and media. Distributed on PyPI as `wpa`.

WPA is a client-side automation tool (not a wp-cli replacement). It covers the subset of WordPress management exposed by the REST API — primarily content and user management. Command names follow wp-cli conventions where possible (`wp post list` → `wpa post list`).

## Commands

```bash
# Install for development
pip install -e '.[dev]'

# Run all tests with coverage
pytest --cov=wpa --cov-report=term-missing

# Run a single test file
pytest tests/test_user.py

# Run a single test
pytest tests/test_user.py::TestUserList::test_user_list_success

# Lint
ruff check .
ruff format --check .
```

CI runs on ubuntu/macos/windows across Python 3.10, 3.11, 3.12, 3.13, plus a weekly scheduled run on `main` to catch dependency drift. The required status check is `test (ubuntu-latest, 3.12)`, which also runs the bandit/pip-audit security step.

## Architecture

**Entry point**: `wpa/cli.py` — argparse-based CLI with subcommands (`publish`, `post list/get/create/update/delete`, `page list/get/create/update/delete`, `site add/list`, `user list/get/create/update/delete/set-role`, `media list/get/import/delete`, `comment list/get/create/update/delete/approve/unapprove/spam/unspam/trash/count`, `term list/get/create/update/delete`, plus `category` and `tag` aliases).

**Modules**:
- `cli.py` — Command parsing, dispatches to other modules
- `api.py` — Shared REST client (`WPApiClient`). All HTTP requests go through this module — only module that imports `requests`
- `config.py` — Site credential management using XDG_CONFIG_HOME (`~/.config/wpa/<site>/.env`). Enforces HTTPS for public IPs, allows HTTP for private networks and local TLDs (`.lan`, `.local`, `.test`, `.internal`)
- `exceptions.py` — Custom exceptions (`WPApiError`, `WPConnectionError`, `WPTimeoutError`) replacing `sys.exit(1)` pattern
- `post.py` — Post CRUD operations against `/wp-json/wp/v2/posts`. Supports filtering by status, author, category, tag, search
- `page.py` — Page CRUD operations against `/wp-json/wp/v2/pages`. Supports filtering by status, search, parent
- `publish.py` — Parses YAML frontmatter from markdown files, converts to HTML, creates pages via `WPApiClient`. Default status is `draft`
- `user.py` — User CRUD operations against `/wp-json/wp/v2/users`. Uses `WPApiClient` for all requests. Supports `list`, `get`, `create`, `update`, `delete`, and `set-role` (shortcut for changing a user's role)
- `media.py` — Media CRUD operations against `/wp-json/wp/v2/media`. Uses `WPApiClient` for all requests. Supports `list` (with `--media-type`/`--mime-type` filters), `get`, `import` (multipart upload from a local file with optional title/alt-text/caption/description/post), and `delete` (trash-aware, `--force` to permanently delete)
- `comment.py` — Comment CRUD and moderation against `/wp-json/wp/v2/comments`. Supports `list` (filter by post, status, parent, author email, search), `get`, `create`, `update`, `delete` (trash-aware, `--force` to permanently delete), plus moderation shortcuts `approve`, `unapprove`, `spam`, `unspam`, `trash`, and `count` (per-status totals via the `X-WP-Total` header)
- `term.py` — Taxonomy term CRUD against `/wp-json/wp/v2/{categories,tags,<custom>}`. One module handles built-in taxonomies (`category` → `categories`, `post_tag` → `tags`) and custom taxonomies (passed through by slug). The CLI exposes `wpa term --taxonomy <slug>` plus thin `wpa category` / `wpa tag` aliases that pre-set the taxonomy. Term `delete` is always permanent (the REST API does not support trashing terms).
- `formatter.py` — Shared output formatting (table, json, csv, tsv) with column selection via `--fields`, plus `--ids`, `--count`, `--field` output modifiers

**Global flags**: `--debug` (HTTP request/response details) available on all commands. `--site` selects a named site config.

**Tests**: All in `tests/` (520 tests), use `unittest.mock` to mock HTTP requests. No live WordPress connection needed.

## Key Conventions

- Python 3.10 minimum — ruff targets `py310`
- Version string lives in `wpa/__init__.py` only — `pyproject.toml` reads it via `dynamic = ["version"]`
- Lint/audit tools (ruff, bandit, pip-audit) are pinned exactly in the `dev` extra; bump deliberately and fix new findings in the same PR. Runtime deps stay unpinned (upper-bound only known-broken releases)
- Branch protection on `main` — use feature branches + PRs
- Command names follow wp-cli conventions (see design principle 4.1 in the PRD)
- Default status for content creation is always `draft`
- HTTPS enforced for public addresses; HTTP allowed only for private/LAN
- Security audits: `bandit` (static analysis) and `pip-audit` (dependency vulnerabilities) run in CI on every PR

## Release Workflow

Every release follows this arc. Steps 1–3 are planning, 4–6 repeat per PR, 7–12 close the release.

1. **Collect** — capture bug reports, feature requests, and audit findings as GitHub issues as they arise.
2. **Select** — group issues into a release using the PRD roadmap as the guide. Apply the semver gate:
   any compatibility break (interpreter floor, removed flag, changed default) makes it a minor release.
3. **Plan** — organize the work into distinct, reviewable PRs (stacked if dependent). Get the plan
   approved before implementation starts.
4. **TDD loop (per PR)** — write failing tests for the new behavior first, implement until GREEN,
   refactor. Coverage stays ≥98%; only thin CLI adapter functions may use `# pragma: no cover`.
5. **CI green (per PR)** — full matrix passes, including ruff, bandit, and pip-audit. Timing notes:
   `gh pr checks <n> --watch` reports "no checks" if run within seconds of PR creation — wait ~30s
   first. Stacked PRs (base ≠ main) get no CI runs at all until rebased onto main after their base
   merges; ci.yml only triggers on PRs targeting main.
6. **Merge (per PR)** — merge-commit strategy (not squash). Surface discovered smells as new issues
   rather than widening the PR.
7. **Security audit** — human review of the full release diff (not just tool output). File findings
   as issues; fix release-blockers now, schedule the rest.
8. **Regression** — full suite + lint + audit tools on the final merged state.
9. **Docs** — update README, wpa-prd.md (Current release, §6.1 implemented commands, roadmap),
   CLAUDE.md (test count), then RELEASE-NOTES.md last, when scope is final.
10. **Version bump** — `wpa/__init__.py` (single source; `pyproject.toml` reads it dynamically).
11. **Ship** — merge the release PR, tag the merge commit `vX.Y.Z`, create the GitHub Release
    (title `vX.Y.Z — Short Name`, body = that version's RELEASE-NOTES.md section). Trusted
    publishing pushes to PyPI automatically.
12. **Verify & retro** — `pip install --upgrade wpa` in a clean venv, check `wpa --version` and
    PyPI. Hold a short retrospective; file follow-up issues. Announce (GitHub feed, LinkedIn,
    Cadent blog — outside this repo's scope).

## Key Documents

- `wpa-prd.md` — Product Requirements Document: vision, design principles, full command structure, and implementation roadmap (Phases 1–8 toward v1.0)
- `docs/wp-cli-command-inventory.md` — Complete catalog of all WP-CLI 2.12.0 commands (~280+ subcommands across 46 groups), used as the template for WPA command planning
- `docs/wp-cli-rest-api-mapping-matrix.md` — Classification of every WP-CLI command against REST API feasibility (FULL / PARTIAL / NOT POSSIBLE / N/A), drives the implementation roadmap
