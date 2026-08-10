# WPA Development Recommendations

**Date:** 2026-03-21 (updated)
**Context:** Post-v0.5.1 — user CRUD, formatter, security hardening, and documentation all shipped
**Audience:** Development team (Neil + Claude Code)
**Reference:** [WPA PRD](wpa-prd.md) — Phase 2 (v0.6.0)

---

## Summary

The `wpa` project has completed its first phase. v0.4.0 delivered the package structure, PyPI distribution, and subcommand CLI. v0.5.0–v0.5.1 added user CRUD, a shared output formatter (`formatter.py` with table/json/csv/tsv and `--fields`), security hardening, and comprehensive documentation (PRD, command inventory, mapping matrix, CLAUDE.md).

The next development cycle should focus on extracting a reusable API client layer from the existing modules, then building the most important user-facing command group: `wpa post`. This aligns with PRD Phase 2 (v0.6.0).

---

## 1. Immediate priority: Extract `api.py` — the shared REST API client

### Why this is the highest-leverage task

Right now, `publish.py` and `user.py` each contain their own HTTP logic for talking to the WordPress REST API. `user.py` has a consolidated `_request()` helper (added in v0.5.1), but it's internal to the user module. Every new command group (post, comment, media, term, plugin, menu, widget) will need the same core operations: authenticated HTTP requests, JSON parsing, pagination, and error handling.

Without a shared `api.py`, each new module reinvents this logic, introduces inconsistencies, and makes the codebase progressively harder to maintain. With `api.py`, adding a new command group becomes a thin layer of CLI argument parsing on top of well-tested HTTP primitives.

### Recommended `api.py` interface

```python
class WPApiClient:
    """Shared REST API client for all wpa commands."""

    def __init__(self, site_url, username, app_password):
        """Initialize with site credentials from config."""

    def get(self, endpoint, params=None):
        """GET request. Returns parsed JSON response.
        Handles: auth, HTTPS enforcement, error mapping.
        """

    def get_list(self, endpoint, params=None):
        """GET request with automatic pagination.
        Yields all items across pages using X-WP-Total
        and X-WP-TotalPages headers.
        Respects per_page (max 100) and page params.
        """

    def post(self, endpoint, data=None, files=None):
        """POST request for create/update operations.
        Handles: JSON body, multipart for media uploads.
        """

    def delete(self, endpoint, params=None):
        """DELETE request. Supports force=true param."""

    def discover(self):
        """GET /wp-json/ — returns site API index
        for endpoint discovery.
        """
```

### Key behaviors to implement

- **Authentication:** HTTP Basic Auth with Application Password, sent on every request. Header: `Authorization: Basic base64(username:app_password)`.
- **Base URL construction:** `{WP_SITE_URL}/wp-json/wp/v2/{endpoint}`. Strip trailing slashes from site URL.
- **Pagination:** `get_list()` should handle multi-page retrieval transparently. Read `X-WP-Total` and `X-WP-TotalPages` from response headers. Support `--per-page` (default 10, max 100) and automatic fetching of all pages when needed.
- **Error mapping:** Translate HTTP status codes to clear error messages:
  - 401 → "Authentication failed. Check your username and application password."
  - 403 → "Permission denied. Your user account does not have the required capability."
  - 404 → "Resource not found."
  - 500 → "Server error. The WordPress site returned an internal error."
  - Connection errors → "Could not connect to {site_url}. Check the URL and your network connection."
- **Timeout:** Default 30-second timeout, configurable.
- **Debug mode:** When `--debug` is passed, print the full HTTP request method, URL, headers (with password masked), and response status/body.

### Refactoring plan

Once `api.py` is working and tested:

1. Refactor `publish.py` to use `WPApiClient` instead of its own `requests` calls
2. Refactor the user module to use `WPApiClient`
3. Verify all existing tests still pass (no behavior change to users)

---

## 2. Extend `formatter.py` — add missing output modes

### Status

`formatter.py` already exists (shipped in v0.5.0) with `format_output(rows, columns, fmt)` supporting `table`, `json`, `csv`, and `tsv` formats, plus `--fields` for column selection. The user module already uses it.

### What to add

The PRD specifies additional output modes not yet implemented:

| Format | Flag | Behavior |
|---|---|---|
| IDs | `--ids` | Space-separated list of `id` values |
| Count | `--count` | Single integer: total number of results |
| Field | `--field <name>` | Single field value per result, one per line |

These should be added to `formatter.py` as new `fmt` values (or a separate code path for `--field` singular).

### Default table fields per resource

Each resource type should define sensible default columns for table output:

| Resource | Default table fields |
|---|---|
| post | `id`, `title.rendered`, `status`, `date`, `author` |
| page | `id`, `title.rendered`, `status`, `date`, `slug` |
| user | `id`, `username`, `email`, `display_name`, `roles` |
| comment | `id`, `post`, `author_name`, `status`, `date` |
| media | `id`, `title.rendered`, `mime_type`, `date` |
| plugin | `plugin`, `name`, `status`, `version` |

The `--fields` flag overrides these defaults. The `--json` flag bypasses table formatting entirely and returns the full API response.

---

## 3. First command group on the new architecture: `wpa post`

### Why post, not finishing user

The user subcommand is already functional (shipped v0.5.0, hardened v0.5.1). Building `wpa post` on the new `api.py` + existing `formatter.py` architecture serves three purposes:

1. **Validates the architecture.** Posts exercise every REST API pattern: list with filters, get by ID, create with JSON body, update with partial fields, delete with force/trash semantics, embedded resources via `_embed`, and pagination. If the architecture works for posts, it works for everything.

2. **Highest user value.** `wpa post list` is the command people try first. It's the "hello world" of WordPress CLI tools.

3. **Agent use case.** An AI agent managing WordPress content will use `wpa post list --json`, `wpa post create`, and `wpa post update` more than any other commands. Getting these right with structured output makes `wpa` immediately useful for the agentic AI use case.

### Subcommands to implement

| Command | REST API | Key flags |
|---|---|---|
| `wpa post list` | `GET /wp/v2/posts` | `--status`, `--author`, `--search`, `--per-page`, `--page`, `--orderby`, `--order`, `--category`, `--tag` |
| `wpa post get <id>` | `GET /wp/v2/posts/<id>` | `--embed` (include linked resources) |
| `wpa post create` | `POST /wp/v2/posts` | `--title`, `--content`, `--status` (default: draft), `--slug`, `--author`, `--category`, `--tag`, `--featured-media` |
| `wpa post update <id>` | `POST /wp/v2/posts/<id>` | Same as create (partial updates — only send fields that are provided) |
| `wpa post delete <id>` | `DELETE /wp/v2/posts/<id>` | `--force` (bypass trash, permanent delete) |

### Design note: `wpa post create` from stdin or file

Consider supporting content from stdin or a file, similar to how `wpa publish` works with markdown files:

```bash
# From flags
wpa post create --title "My Post" --content "<p>Hello</p>" --status draft

# From markdown file (like wpa publish, but for posts)
wpa post create --from-file post.md

# From stdin (useful for piping)
echo "<p>Hello</p>" | wpa post create --title "My Post" --stdin
```

This makes `wpa post create` composable with other CLI tools and useful in scripting contexts.

---

## 4. Repo housekeeping recommendations

These are lower priority than the architecture work but should be addressed in the v0.6.0 cycle:

### 4.1 Update GitHub repo description

**Current:** "Publish markdown files as WordPress pages via REST API"
**Recommended:** "Python CLI for WordPress automation via the REST API"

The current description accurately described v0.1.0 but undersells the project's scope now that it has user management, multi-site config, and a PRD targeting full content management.

### 4.2 Add GitHub topics

Current topics: `python`, `markdown`, `cli`, `wordpress`, `rest-api`

Add: `automation`, `wp-cli`, `agentic-ai`, `wordpress-rest-api`

These improve discoverability for people searching for wp-cli alternatives or AI-compatible WordPress tooling.

### 4.3 ~~Organize docs into a `docs/` directory~~ DONE

Reference documents are now in `docs/`. PRD remains in repo root as `wpa-prd.md`.

### 4.4 ~~Update README~~ PARTIALLY DONE

README now includes user commands in Usage and links to PRD, command inventory, and mapping matrix. Still could benefit from a brief "What is WPA?" section near the top reflecting the broader vision (2–3 sentences from PRD Section 1).

---

## 5. Suggested development sequence

This is a recommended ordering for the v0.6.0 development sprint, designed so each step builds on the previous one and tests stay green throughout:

| Step | Task | Tests |
|---|---|---|
| 1 | Create `api.py` with `WPApiClient` class | Unit tests with mocked HTTP responses for all methods, error codes, pagination |
| 2 | Extend `formatter.py` with `ids`, `count`, `field` modes | Unit tests for each new format type |
| 3 | Implement `wpa post list` using `api.py` + `formatter.py` | Integration tests verifying CLI output in all formats |
| 4 | Implement `wpa post get <id>` | Tests for existing/missing posts, `--embed` flag |
| 5 | Implement `wpa post create` | Tests for required fields, default draft status, content from flags/file/stdin |
| 6 | Implement `wpa post update <id>` | Tests for partial updates |
| 7 | Implement `wpa post delete <id>` | Tests for trash (default) vs force delete |
| 8 | Expand `wpa page` to full CRUD (list/get/update/delete) | Tests mirroring post tests |
| 9 | Refactor `publish.py` to use `api.py` | Verify all existing publish tests still pass |
| 10 | Refactor `user.py` to use `api.py` | Verify all existing user tests still pass |
| 11 | Repo housekeeping (GitHub description, topics, README "What is WPA?" section) | — |

**Definition of done for v0.6.0:** All commands working with `--json` output, 99% test coverage maintained, CI green across full matrix, `api.py` used by all modules (no direct `requests` calls outside `api.py`).

---

## 6. Looking ahead: v0.7.0 and beyond

Once v0.6.0 establishes the shared `api.py` architecture, subsequent phases from the PRD become primarily additive — each new command group is a thin module on top of `api.py` + `formatter.py`:

- **v0.7.0:** `wpa media import/list/get/delete` + `wpa user get` + `wpa user set-role`
- **v0.8.0:** `wpa comment` (full CRUD + moderation) + `wpa term` (categories, tags)
- **v0.9.0:** `wpa plugin` + `wpa menu` + `wpa widget` + `wpa option`
- **v0.10.0:** Introspection commands (`taxonomy`, `post-type`, `block`, `api discover`)
- **v1.0.0:** Shell completion, MCP server, stable API contract

The key insight is that v0.6.0 is the hardest release because it builds the foundation. Every release after that is faster because the patterns are established.
