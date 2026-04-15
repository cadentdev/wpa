# Release Notes

## v0.8.0 — Comments + Taxonomy Terms (2026-04-15)

### What's New

- **`wpa comment` subcommand** — Full CRUD plus moderation shortcuts for WordPress comments via `/wp/v2/comments`:
  - `wpa comment list` — List comments with `--post`, `--status` (approved/hold/spam/trash), `--parent`, `--author-email`, `--search`, `--per-page`, `--orderby`, `--order`. Supports all standard output modifiers (`--format`, `--fields`, `--ids`, `--count`, `--field`).
  - `wpa comment get <id>` — Fetch a single comment. `--format json` for scripted access.
  - `wpa comment create --post <id> --content <body>` — Create a comment. Optional `--author-name`, `--author-email`, `--parent` (for threaded replies), `--status`.
  - `wpa comment update <id>` — Update `--content`, `--status`, `--author-name`, `--author-email`.
  - `wpa comment delete <id>` — Trash by default; `--force` permanently deletes.
  - **Moderation shortcuts** (wp-cli parity): `wpa comment approve <id>`, `unapprove <id>`, `spam <id>`, `unspam <id>`, `trash <id>`. Each is a thin, self-documenting wrapper over the underlying status update (or the soft-delete for `trash`).

- **`wpa term` subcommand** — CRUD for any taxonomy — built-in or custom — via a single module:
  - `wpa term list --taxonomy <slug>` — Default taxonomy is `category`. Filtering: `--search`, `--parent`, `--hide-empty`, `--per-page`, `--orderby`, `--order`.
  - `wpa term get <id> --taxonomy <slug>` — Fetch a single term. `--format json` supported.
  - `wpa term create --name <n>` — Optional `--slug`, `--description`, `--parent` for hierarchical taxonomies.
  - `wpa term update <id>` — Update `--name`, `--slug`, `--description`, `--parent`.
  - `wpa term delete <id>` — **Always permanent.** The WordPress REST API does not support trashing terms, so `delete_term` always sends `force=true`.

- **`wpa category` and `wpa tag` aliases** — Thin convenience wrappers that pre-set the taxonomy and reuse the same handlers:
  - `wpa category ...` == `wpa term --taxonomy=category ...` (no `--taxonomy` flag is exposed on the alias)
  - `wpa tag ...` == `wpa term --taxonomy=post_tag ...`
  - Custom taxonomies remain accessible via the generic `wpa term --taxonomy=<slug>` form.

- **Module additions**
  - `wpa/comment.py` — `list_comments`, `get_comment`, `create_comment`, `update_comment`, `delete_comment`, `approve_comment`, `unapprove_comment`, `spam_comment`, `unspam_comment`, `trash_comment`, `validate_fields`. Field extractor flattens the `content.rendered` shape the REST API returns.
  - `wpa/term.py` — `list_terms`, `get_term`, `create_term`, `update_term`, `delete_term`, `validate_fields`, plus `_resolve_endpoint` which maps taxonomy slugs to their REST endpoint base (`category` → `categories`, `post_tag` → `tags`, everything else passes through as its own slug). Taxonomy slugs are validated against `^[a-z0-9_-]+$` to prevent path traversal.
  - `wpa/cli.py` — New subparsers for `comment`, `term`, `category`, `tag`. All handlers are wired to `WPApiClient`, use the shared `_shared_parser`/`_list_parser`/`_format_list_output` plumbing, and follow the same error-handling pattern as `post`/`page`/`media`.

### Design Notes

- **Taxonomy endpoint resolution.** WordPress exposes the built-in `category` and `post_tag` taxonomies under the paths `/wp/v2/categories` and `/wp/v2/tags` rather than their slugs. Custom taxonomies are typically addressed by their own slug (`/wp/v2/<slug>`). A single `_resolve_endpoint` function centralizes this quirk so callers can pass the taxonomy slug they already know (`category`, `post_tag`, or a custom one) without having to learn the REST-API-specific path.
- **Term delete is always forced.** The REST API refuses a term `DELETE` unless `force=true` is supplied (terms have no trash state). Instead of exposing a `--force` flag that would be required in every invocation, `delete_term` always sends `force=true`. This is surfaced in `--help` and the release notes.
- **Moderation shortcuts over general `update`.** We ship dedicated subcommands (`approve`, `unapprove`, `spam`, `unspam`, `trash`) rather than forcing callers to learn the underlying status values. This matches wp-cli's surface area (`wp comment approve 42`), makes agent usage more discoverable, and keeps `wpa comment update` available for arbitrary field edits.
- **Trash vs. delete for comments.** `wpa comment trash <id>` performs a soft delete (`DELETE /comments/<id>` without `force`), matching the WordPress REST API's behavior where a trashing `DELETE` transitions the comment to `status=trash`. `wpa comment delete <id>` continues to default to trash, with `--force` for permanent removal, matching the `post`/`page`/`media` conventions.

### Scope — Deferred

Phase 4 in the roadmap also called for a **reusable meta handler** (shared logic for `meta add/get/update/delete/list` across post/page/comment/term/user). This has been **deferred to a follow-up sprint** pending a closer look at how REST-exposed meta varies across sites and plugins. Tracked as [#33](https://github.com/cadentdev/wpa/issues/33). Two other follow-ups were also filed during the v0.8.0 FeatureDev cycle: [#34 `wpa comment count`](https://github.com/cadentdev/wpa/issues/34) and [#35 `wpa term merge`](https://github.com/cadentdev/wpa/issues/35). No meta, count, or merge commands ship in v0.8.0.

### Bug fixes

- **`term._resolve_endpoint` case normalization.** The taxonomy slug regex used `re.IGNORECASE`, so mixed-case input (`POST_TAG`, `Category`, `Genre`) passed validation — but the `_TAXONOMY_ENDPOINTS` lookup was case-sensitive, so those inputs fell through to `/wp/v2/POST_TAG` (404) instead of `/wp/v2/tags`. Now normalizes to lowercase before lookup. Three regression tests cover the fix. Caught during the Phase 4 refactor pass.

### Security hardening (pre-release audit)

FeatureRelease Step 1 ran a Pentester sub-agent plus a STRIDE threat model against the v0.8.0 branch. No blockers, no highs. Four medium-severity findings were fixed in commit `f7aec26` before shipping:

- **M1 — CLI credential exposure.** `wpa user create --password` now emits a deprecation warning; new `--password-stdin` reads from stdin safely without leaking via `ps(1)` / shell history / CI logs.
- **M2 — Unbounded response ingestion.** Added `MAX_RESPONSE_BYTES = 50 MB` hard cap and `MAX_TOTAL_PAGES = 1000` clamp on `X-WP-TotalPages` to defend against OOM from a hostile or buggy upstream.
- **M3 — Redirect handling.** `POST`/`PUT`/`PATCH`/`DELETE` now pass `allow_redirects=False`; any response whose final URL downgraded from `https://` to `http://` is rejected with `tls_downgrade`.
- **M4 — Endpoint traversal defense-in-depth.** New `api._validate_endpoint()` rejects `..`, CRLF, `%2f`/`%2F`/`%5c`/`%5C`, backslashes, and anything outside `[A-Za-z0-9_-/]`. Complements existing per-module validators.

29 new tests cover the hardening. All pre-existing 408 tests continue to pass.

### Quality

- **Tests:** 437 total, **+126 from v0.7.0** (44 in `test_comment.py`, 50 in `test_term.py`, 3 taxonomy-case regressions, 3 comment-status regressions, 29 security-hardening tests in `test_api.py`). All TDD-first for the feature work; security tests added alongside the M1–M4 fixes.
- **Coverage:** `wpa/comment.py` and `wpa/term.py` at **100% line coverage**; overall package at **99%**.
- **Lint:** `ruff check .` clean, `ruff format --check .` clean.
- **Security:** `bandit -r wpa/` clean (0 findings across 3100 LOC). `pip-audit` clean after upgrading dev venv to `requests 2.33.1`, `cryptography 46.0.7`, `pygments 2.20.0`, `pytest 9.0.3`. Runtime deps in `pyproject.toml` remain unpinned so end-users on fresh install always pull the patched versions.
- **No regressions:** Full suite (`test_api`, `test_post`, `test_page`, `test_user`, `test_media`, `test_formatter`, `test_wp_publish`, `test_comment`, `test_term`) passes after CLI rewiring.
- **No new runtime dependencies.**

### Files Changed

- `wpa/comment.py` (new)
- `wpa/term.py` (new)
- `tests/test_comment.py` (new)
- `tests/test_term.py` (new)
- `wpa/cli.py` — imports, 14 new handler functions, 4 new top-level subparsers (`comment`, `term`, `category`, `tag`); the three taxonomy-oriented parsers share a `_add_term_subparsers` factory
- `CLAUDE.md` — module list and test count updated
- `README.md` — usage sections for comments and terms, coverage badge refreshed
- `examples/bootstrap-site.sh` — v0.8.0 smoke test sections 5 (comments) and 6 (terms/categories/tags)

### Closes

- Phase 4 (comment + term + category/tag aliases) from `wpa-prd.md`
- Meta handler portion of Phase 4 → tracked as [#33](https://github.com/cadentdev/wpa/issues/33)

### Retrospective

v0.8.0 was a two-session FeatureDev cycle: a Claude Code Web session built the initial TDD implementation on branch `claude/phase-4-tdd-implementation-vJMmZ` (commits `d36b146` + `b88b057` — comment and term modules with 91 TDD tests and a draft of these release notes), and a local flicky session resumed the branch at Phase 4 and took it through Phases 4–9 of the FeatureDev workflow. The local resume caught two real bugs, filed three follow-up issues, wrote an ad-hoc ansible rollback playbook that became its own PR in a sister repo, and propagated five lessons back to the master FeatureDev checklist.

### Bugs caught after CCW's initial implementation

Both of these were on the happy path of "the unit tests are green, 99% coverage, let's go" — neither was visible from the TDD harness CCW built, and both shipped silently in v0.8.0-draft until a later phase caught them.

**1. `term._resolve_endpoint` — taxonomy slug case-sensitivity (caught in Phase 4 refactor).** The slug validation regex used `re.IGNORECASE`, so mixed-case input (`POST_TAG`, `Category`, `Genre`) passed validation. But the `_TAXONOMY_ENDPOINTS` lookup that maps built-in slugs to REST API paths was case-sensitive, so those inputs fell through to `/wp/v2/POST_TAG` instead of `/wp/v2/tags` and came back 404. Fix: lowercase the slug after validation, before lookup. Three TDD tests added (red → green confirmed). Would have shipped to any user passing mixed-case taxonomy slugs.

**2. `list_comments` — WordPress REST API `status` asymmetry (caught in Phase 8c live smoke test).** Much more interesting. The `/wp/v2/comments` endpoint accepts `status=approve|hold|spam|trash` (imperative verbs) as a query-string filter, but serializes responses with `status=approved|hold|spam|trash` (past tense). Only three of the four values round-trip; the fourth (`approve`/`approved`) is asymmetric. Passing `?status=approved` silently returns zero rows even when approved comments exist. Our smoke test's "list approved comments on Featured post" step came back empty immediately after a successful `wpa comment approve` — which is how we noticed. Direct curl confirmed: `?status=approved → []`, `?status=approve → [comment]`. Fix: normalize `approved → approve` at the boundary in `list_comments`, accept both forms from the caller. Three TDD tests added.

The critical observation: **this bug was literally undetectable by the unit tests CCW wrote.** Every existing test mocked `client.get_list` and asserted on the params dict the module passed — which is the right thing to test for the module's own logic, but doesn't know anything about what the upstream API actually accepts. The bug only surfaced when the test harness hit a real WordPress instance. This is the primary motivation for treating Phase 8c (live smoke test against a realistic target) as a hard gate in the updated FeatureDev checklist.

### Follow-up issues filed

Three enhancement issues were opened during Phase 7 team review for post-v0.8.0 work:

- [#33](https://github.com/cadentdev/wpa/issues/33) — Meta handler (`wpa <entity> meta list/get/add/update/delete`). Originally in PRD Phase 4, deferred here pending a closer look at how REST-exposed meta varies across vanilla WP vs plugins like ACF and Meta Box.
- [#34](https://github.com/cadentdev/wpa/issues/34) — `wpa comment count`. Low-priority quality-of-life: single command that returns counts across all moderation states (`approved`, `hold`, `spam`, `trash`) instead of requiring three separate list calls. Aligns with the `wp comment list --format=count --status=hold` wp-cli pattern.
- [#35](https://github.com/cadentdev/wpa/issues/35) — `wpa term merge`. Medium priority, real user demand: consolidate duplicate categories or tags by reassigning all posts from a source term to a target term and then deleting the source. Needs a dry-run mode and explicit children-handling flag for hierarchical taxonomies.

One cross-repo follow-up was opened in `cadentdev/ansible`: [#8](https://github.com/cadentdev/ansible/issues/8) / [PR #9](https://github.com/cadentdev/ansible/pull/9) adds `playbooks/on_demand/pve_ct_rollback.yml`, a minimal rollback playbook extracted from the ad-hoc `pct rollback 118 wpa_baseline` work that made Phase 8c repeatable. The playbook runs idempotently, asserts the snapshot exists before touching disk state, and optionally probes a verify URL after starting the container. It was used for the final three smoke-test runs of this cycle.

### Lessons propagated to FeatureDev workflow

Five load-bearing lessons were propagated from this cycle's `.dev/checklist-phase-4-comments-terms.md` retrospective back to the master `FeatureDevelopmentChecklist.md` (v2.3 → v2.4):

1. **Agent handoff protocol** (new Progress Tracking Rule 4). If you're resuming a branch from a previous session — including Claude Code Web → local, or any prior-agent work — and the branch has feature commits but no `.dev/checklist-*.md` file, creating one is Phase-0 of the resume. Reconstruct state from git log, release notes drafts, and the PRD. Mark phases `[x]` based on **verified artifacts**, not presence in commit messages. CCW's v0.8.0 work would have been faster to resume if the checklist had been there.

2. **Mocked-client unit tests vs upstream-API quirks** (new Phase 5 lesson callout). Unit tests that mock `client.get/post/delete` verify what params the module passes, not what the upstream API accepts. API asymmetries like WP's comment `status=approve`/`status=approved` are undetectable at the unit-test layer no matter how good the coverage is. Phase 5 now explicitly flags this class of bug and points at Phase 8c as the catching mechanism.

3. **Phase 8 split into 8a / 8b / 8c** (structural change). Previously Phase 8 was "Update Docs and Help" as a single monolithic phase. Now:
   - **8a** — Update smoke-test / example scripts. Must run before 8b so 8c has something to execute.
   - **8b** — Update user-facing docs (README, RELEASE-NOTES, CLAUDE.md, etc.).
   - **8c** — Live smoke test against a realistic target. **Hard gate** for any feature that talks to a remote API. Roll target to baseline, run script, observe in a browser, isolate any bugs with direct API probes, TDD fix, re-run end-to-end, capture output for the PR body.

4. **Fixture visibility rule** (new Phase 8a guidance). A 1×1 red PNG is a valid bit-level fixture — it uploads, it serves at 200 OK with the correct MIME type, `file` identifies it as a valid PNG — but it's invisible to a human browsing the rendered site. "Fit for purpose" for a smoke test that includes browser validation must include "visible to a human at a glance." The updated `bootstrap-site.sh` uses a 256×256 red block with a white X across both diagonals, clearly a placeholder, hand-rolled with stdlib PNG writer so there are still zero external fixture dependencies.

5. **Persistent + transient pattern for state-machine smoke tests** (new Phase 8a guidance). For any feature with a state machine (comment moderation, publish workflow, user roles), the smoke test should create **two** artifacts: one persistent that's approved immediately and left in place as a rendered-site artifact, and one transient that walks the full state machine and gets cleaned up at the end. The mid-run list exercises multi-result handling; the post-exit state proves the rendered-site integration works without accumulating cruft across runs.

### Cycle shape — by the numbers

- **Branch commits:** 11 total (2 from CCW + 9 from local resume)
- **Tests:** 311 at start → 405 after CCW's Phase 3 → 408 after local resume's Phase 4 refactor (3 taxonomy-case tests) and Phase 8c fix (3 comment-status tests). Net: +97 from v0.7.0.
- **Coverage:** 99% overall package, 100% on `wpa/comment.py` and `wpa/term.py`.
- **CI runs:** ~5 on the branch across all phases, every one of them green on all 6 jobs (ubuntu 3.9/3.11/3.12/3.13, macos 3.12, windows 3.12).
- **Live smoke-test runs:** 5 full end-to-end runs against CT 118, each preceded by a `pct rollback 118 wpa_baseline`. First caught the `status=approved` bug, second reproduced it, third verified the fix, fourth verified the new 256×256 fixture, fifth verified the persistent+transient comment pattern.
- **Follow-up issues:** 3 in this repo + 1 cross-repo issue + 1 cross-repo PR.
- **Master workflow updates:** FeatureDevelopmentChecklist v2.3 → v2.4, 5 lessons propagated.

### Release Checklist (pre-tag, archived)

- [ ] Bump `wpa/__init__.py` version to `0.8.0`
- [ ] Move this file's contents into `RELEASE-NOTES.md` as the new top entry
- [ ] Update `wpa-prd.md` Phase 4 row to **COMPLETE** (with a note that meta is deferred)
- [x] Run `bandit` and `pip-audit` and record results in the "Quality" section
- [x] Live-test `examples/bootstrap-site.sh` against CT 118 (wp-stage-18 @ 192.168.52.18) after rollback to the `wpa_baseline` snapshot, exercising the full v0.8.0 surface (user/media/page/post/comment/term/category/tag). Final run: clean end-to-end with visible red-X fixture image and persistent approved comment on Featured post.
- [ ] Tag `v0.8.0` and publish to PyPI

## v0.7.0 — Media CRUD + User Role Management (2026-04-14)

### What's New

- **`wpa media` subcommand** — Full CRUD for WordPress media via the REST API:
  - `wpa media list` — List media items with `--media-type` (image/video/audio/application), `--mime-type`, `--search`, `--per-page`. Supports all standard output formats and field selection.
  - `wpa media get <id>` — Fetch a single media item.
  - `wpa media import <file>` — Upload a local file as a WordPress media item (multipart upload) with optional `--title`, `--alt-text`, `--caption`, `--description`, and `--post` (parent post ID).
  - `wpa media delete <id>` — Trash a media item; `--force` permanently deletes.
- **`wpa user get <id>`** — Retrieve a single WordPress user, complementing the existing `list` / `create` / `update` / `delete` commands.
- **`wpa user set-role <id> <role>`** — Shortcut for changing a user's role without going through `wpa user update`. Follows the wp-cli `wp user set-role` convention.
- **Module additions** — New `wpa/media.py` module (`list_media`, `get_media`, `import_media`, `delete_media`, `validate_fields`). `wpa/user.py` extended with `get_user` and role management. CLI wired via argparse subparsers following the existing `post`/`page`/`user` patterns.

### Quality

- 311 tests (+39 from v0.6.0), 98% coverage | bandit clean | pip-audit: 5 pre-existing transitive CVEs noted (unpinned deps, unrelated to release scope)
- Media upload uses multipart form data via `WPApiClient` — no new dependencies

### Closes

- #23 — Media CRUD + user enhancements

---

## v0.6.0 — API Client Layer + Post/Page CRUD (2026-03-23)

### What's New

- **Shared API client** (`WPApiClient`) — All HTTP requests now go through a single, centralized REST client in `api.py`. Only `api.py` imports `requests`. Custom exceptions (`WPApiError`, `WPConnectionError`, `WPTimeoutError`) replace the old `sys.exit(1)` error pattern.
- **`wpa post` subcommand** — Full CRUD for WordPress posts: `list`, `get`, `create`, `update`, `delete`. Rich filtering with `--status`, `--author`, `--category`, `--tag`, `--search`, `--orderby`, `--order`, `--per-page`.
- **`wpa page` expansion** — Full CRUD for pages: `list`, `get`, `create`, `update`, `delete`. Filtering with `--status`, `--search`, `--parent`, `--orderby`, `--order`. Page create accepts markdown files or `--title`/`--content` flags.
- **Formatter extensions** — New output modifiers across all list commands: `--ids` (output only IDs), `--count` (output only count), `--field` (output a single field per result).
- **`--debug` flag** — Available on all commands, prints HTTP request/response details for troubleshooting.
- **Module refactor** — `publish.py` and `user.py` refactored to use `WPApiClient`. Dead code removed, double config load fixed.

### Quality

- 272 tests (+120 from v0.5.1) | 75% coverage | ruff clean | bandit clean | pip-audit clean
- Coverage note: `cli.py` argparse wiring is 44% covered — business logic modules are 91-100%

### Closes

- #21 — API client layer + post/page CRUD

---

## v0.5.1 — Security Hardening & Refactor (2026-03-21)

### What's New

- **User ID validation** — `update` and `delete` now validate that `user_id` is a positive integer before interpolating into the API URL, preventing path injection via the library interface
- **Invalid JSON handling** — API responses with valid status codes but malformed JSON now produce a clean error message instead of an unhandled traceback
- **Response body sanitization** — Non-JSON error responses are stripped of newlines before display
- **Empty update guard** — `wpa user update` with no field flags now exits with a helpful message instead of sending an empty payload
- **Internal refactor** — Consolidated duplicated request/error handling into shared `_request()` helper; extracted `_users_endpoint()` to eliminate 4x URL construction

### Quality

- 152 tests (+7 security tests) | ruff clean | bandit clean | pip-audit clean

### Tools Used

- `bandit` — static security analysis (0 findings)
- `pip-audit` — dependency vulnerability scan (0 findings)

---

## v0.5.0 — User Management (2026-03-21)

### What's New

- **`wpa user` subcommand** — Full CRUD for WordPress users via the REST API, following wp-cli conventions: `list`, `create`, `update`, `delete`
- **Shared output formatter** — `--format` flag supports `table` (default), `json`, `csv`, `tsv` output. Reusable across future list commands.
- **Field selection** — `--fields id,username,email,roles` to control which columns appear in output
- **List filtering** — `--role editor` and `--search "jane"` narrow results server-side
- **Private TLD recognition** — `.lan`, `.local`, `.test`, `.internal` hostnames now recognized as private addresses (HTTP allowed with warning)
- **GETTING-STARTED.md** — Setup guide covering REST API configuration, Application Passwords, Wordfence compatibility, and HTTP staging sites

### Known Limitations

- **Wordfence WAF blocks DELETE** — Sites running Wordfence may return 403 on `wpa user delete`. See [GETTING-STARTED.md](GETTING-STARTED.md#wordfence-waf-blocks-delete-requests) for workarounds.

### Quality

- 145 tests | 99% coverage
- Live-tested against WordPress 6.x staging site (list, create, update verified; delete blocked by Wordfence WAF)

### Closes

- #16 — User management subcommand

---

## v0.4.0 — Python Package with Subcommand CLI (2026-03-01)

### What's New

- **Proper Python package** — Restructured from single-file script (`wp-publish.py`) to `wpa/` package directory with `config.py`, `publish.py`, and `cli.py` modules
- **Subcommand CLI** — New command structure: `wpa publish`, `wpa page create`, `wpa site add`, `wpa site list`
- **PyPI-ready** — `pyproject.toml` with console script entry point, installable via `pip install wpa`
- **Python 3.9+ support** — Expanded compatibility from 3.11+ to 3.9+, CI matrix now includes 3.9

### Breaking Changes

- The old `python3 wp-publish.py` invocation is replaced by `wpa` commands
- `--new-site` flag replaced by `wpa site add` subcommand
- `--site` flag now used with subcommands: `wpa publish --site mysite file.md`
- `requirements.txt` and `requirements-dev.txt` replaced by `pyproject.toml`

### Quality

- 97 tests | 99% coverage
- CI matrix: 6 jobs across 3 OS × 4 Python versions (3.9, 3.11, 3.12, 3.13)

### Closes

- #13 — Refactor for PyPI package distribution

---

## v0.3.0 — HTTP for Private/LAN Addresses + Multi-Platform CI (2026-02-25)

### What's New

- **HTTP allowed for private/LAN addresses** — `http://` URLs accepted for RFC 1918 private IPs (10.x, 172.16-31.x, 192.168.x), loopback (127.x), and `localhost`. HTTPS still required for all public addresses.
- **Credential warning** — Prints a warning when HTTP is used on a private address: credentials are not encrypted in transit.
- **Multi-platform CI** — Test matrix expanded to Linux (Python 3.11/3.12/3.13), macOS (3.12), and Windows (3.12) — 5 jobs total.

### Security

- HTTPS enforcement unchanged for public addresses — no regression
- HTTP on private addresses prints explicit warning about unencrypted credentials
- Uses Python's `ipaddress` module for reliable RFC 1918/loopback detection
- `localhost` hostname special-cased as private

### Quality

- 97 tests | 99% coverage
- CI matrix: 5 jobs across 3 OS × 3 Python versions

### Closes

- #7 — Allow HTTP for private/LAN addresses
- #9 — Multi-platform CI test matrix

---

## v0.2.1 — CI Pipeline and Improved CLI Help (2026-02-25)

### What's New

- **GitHub Actions CI** — Automated testing on push and PR: pytest with coverage, ruff lint, ruff format
- **Improved CLI help** — `--help` now shows usage examples, config file location, and first-run guidance
- **3 new tests** for CLI help output validation

### Quality

- 72 tests | 99% coverage
- CI pipeline: pytest + ruff check + ruff format on Ubuntu / Python 3.12

### Closes

- #2 — CI pipeline
- #5 — Improved CLI help

---

## v0.2.0 — Interactive Site Config with XDG Storage (2026-02-25)

### What's New

- **Multi-site support** — Store configs for multiple WordPress sites at `~/.config/wpa/<site-name>/.env`
- **`--site` flag** — Select a named config non-interactively (`--site mysite`)
- **`--new-site` flag** — Interactive config creation with password masking via `getpass`
- **`WP_ADMIN_PATH`** — Configurable admin path per site (defaults to `wp-admin`)
- **Auto-selection** — Single config used automatically; multiple configs prompt for selection
- **Migration** — Offers to migrate existing repo-root `.env` to XDG location
- **`--version` flag** — Display current version

### Security

- Credentials stored outside repo at `~/.config/wpa/` with `600` permissions
- Password input hidden during interactive setup
- HTTPS enforced during config creation and loading
- Site names validated (alphanumeric + hyphens only — prevents path traversal)
- Overwrite protection for existing configs

### Quality

- 69 tests | 99% coverage
- All 20 original v0.1.0 tests still passing

### Closes

- #1 — Multi-site support
- #3 — Configurable wp-admin path
- #4 — Interactive site config management with XDG storage

---

## v0.1.0 — WordPress Page Publisher (2026-02-25)

### Features

- Parse markdown files with YAML frontmatter (title, slug, status)
- Convert markdown to HTML and POST to WordPress REST API `/wp-json/wp/v2/pages`
- WordPress Application Password authentication (WP 5.6+)
- Default status is always `draft` — never publishes unless explicitly set

### Security

- HTTPS enforced for site URL — rejects HTTP to protect credentials in transit
- Status validation — only accepts `draft`, `publish`, `pending`, `private`
- Connection error handling — timeouts and network failures produce clear messages
- Credentials stored in `.env` only, excluded from git

### Quality

- 20 tests | 99% coverage
- All HTTP calls mocked — no real API calls in tests
- pytest + pytest-cov test infrastructure

### Stack

- Python 3.12, requests, python-frontmatter, markdown, python-dotenv
- Zero server-side dependencies — pure REST API client
