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

CI runs on ubuntu/macos/windows across Python 3.9, 3.11, 3.12, 3.13. The required status check is `test (ubuntu-latest, 3.12)`.

## Architecture

**Entry point**: `wpa/cli.py` — argparse-based CLI with subcommands (`publish`, `post list/get/create/update/delete`, `page list/get/create/update/delete`, `site add/list`, `user list/get/create/update/delete/set-role`, `media list/get/import/delete`, `comment list/get/create/update/delete/approve/unapprove/spam/unspam/trash`, `term list/get/create/update/delete`, plus `category` and `tag` aliases).

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
- `comment.py` — Comment CRUD and moderation against `/wp-json/wp/v2/comments`. Supports `list` (filter by post, status, parent, author email, search), `get`, `create`, `update`, `delete` (trash-aware, `--force` to permanently delete), plus moderation shortcuts `approve`, `unapprove`, `spam`, `unspam`, `trash`
- `term.py` — Taxonomy term CRUD against `/wp-json/wp/v2/{categories,tags,<custom>}`. One module handles built-in taxonomies (`category` → `categories`, `post_tag` → `tags`) and custom taxonomies (passed through by slug). The CLI exposes `wpa term --taxonomy <slug>` plus thin `wpa category` / `wpa tag` aliases that pre-set the taxonomy. Term `delete` is always permanent (the REST API does not support trashing terms).
- `formatter.py` — Shared output formatting (table, json, csv, tsv) with column selection via `--fields`, plus `--ids`, `--count`, `--field` output modifiers

**Global flags**: `--debug` (HTTP request/response details) available on all commands. `--site` selects a named site config.

**Tests**: All in `tests/` (437 tests), use `unittest.mock` to mock HTTP requests. No live WordPress connection needed.

## Key Conventions

- Python 3.9 minimum — ruff targets `py39`
- Version string lives in `wpa/__init__.py`
- Branch protection on `main` — use feature branches + PRs
- Command names follow wp-cli conventions (see design principle 4.1 in the PRD)
- Default status for content creation is always `draft`
- HTTPS enforced for public addresses; HTTP allowed only for private/LAN
- Security audits: `bandit` (static analysis) and `pip-audit` (dependency vulnerabilities)

## Key Documents

- `wpa-prd.md` — Product Requirements Document: vision, design principles, full command structure, and implementation roadmap (Phases 1–6 toward v1.0)
- `docs/wp-cli-command-inventory.md` — Complete catalog of all WP-CLI 2.12.0 commands (~280+ subcommands across 46 groups), used as the template for WPA command planning
- `docs/wp-cli-rest-api-mapping-matrix.md` — Classification of every WP-CLI command against REST API feasibility (FULL / PARTIAL / NOT POSSIBLE / N/A), drives the implementation roadmap
