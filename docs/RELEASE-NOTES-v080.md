# v0.8.0 — Comments + Taxonomy Terms (DRAFT)

**Status:** Draft — not yet released. Slot into `RELEASE-NOTES.md` when tagging.
**Branch:** `claude/phase-4-tdd-implementation-vJMmZ`
**Roadmap phase:** Phase 4 (Comments and terms)

---

## What's New

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

## Design Notes

- **Taxonomy endpoint resolution.** WordPress exposes the built-in `category` and `post_tag` taxonomies under the paths `/wp/v2/categories` and `/wp/v2/tags` rather than their slugs. Custom taxonomies are typically addressed by their own slug (`/wp/v2/<slug>`). A single `_resolve_endpoint` function centralizes this quirk so callers can pass the taxonomy slug they already know (`category`, `post_tag`, or a custom one) without having to learn the REST-API-specific path.
- **Term delete is always forced.** The REST API refuses a term `DELETE` unless `force=true` is supplied (terms have no trash state). Instead of exposing a `--force` flag that would be required in every invocation, `delete_term` always sends `force=true`. This is surfaced in `--help` and the release notes.
- **Moderation shortcuts over general `update`.** We ship dedicated subcommands (`approve`, `unapprove`, `spam`, `unspam`, `trash`) rather than forcing callers to learn the underlying status values. This matches wp-cli's surface area (`wp comment approve 42`), makes agent usage more discoverable, and keeps `wpa comment update` available for arbitrary field edits.
- **Trash vs. delete for comments.** `wpa comment trash <id>` performs a soft delete (`DELETE /comments/<id>` without `force`), matching the WordPress REST API's behavior where a trashing `DELETE` transitions the comment to `status=trash`. `wpa comment delete <id>` continues to default to trash, with `--force` for permanent removal, matching the `post`/`page`/`media` conventions.

## Scope — Deferred

Phase 4 in the roadmap also called for a **reusable meta handler** (shared logic for `meta add/get/update/delete/list` across post/page/comment/term/user). This has been **deferred to a follow-up sprint** pending a closer look at how REST-exposed meta varies across sites and plugins. Tracked as [#33](https://github.com/cadentdev/wpa/issues/33). Two other follow-ups were also filed during the v0.8.0 FeatureDev cycle: [#34 `wpa comment count`](https://github.com/cadentdev/wpa/issues/34) and [#35 `wpa term merge`](https://github.com/cadentdev/wpa/issues/35). No meta, count, or merge commands ship in v0.8.0.

## Bug fixes

- **`term._resolve_endpoint` case normalization.** The taxonomy slug regex used `re.IGNORECASE`, so mixed-case input (`POST_TAG`, `Category`, `Genre`) passed validation — but the `_TAXONOMY_ENDPOINTS` lookup was case-sensitive, so those inputs fell through to `/wp/v2/POST_TAG` (404) instead of `/wp/v2/tags`. Now normalizes to lowercase before lookup. Three regression tests cover the fix. Caught during the Phase 4 refactor pass.

## Quality

- **Tests:** 405 total, **+94 new** (44 in `test_comment.py`, 50 in `test_term.py`). All TDD-first — tests written against the public API of each module before the implementation existed, then iterated red → green → refactor.
- **Coverage:** `wpa/comment.py` and `wpa/term.py` at **100% line coverage**; overall package at **99%**.
- **Lint:** `ruff check .` clean, `ruff format --check .` clean.
- **Security:** `bandit -r wpa/` clean (0 findings across 3100 LOC). `pip-audit` clean after upgrading dev venv to `requests 2.33.1`, `cryptography 46.0.7`, `pygments 2.20.0`, `pytest 9.0.3`. Runtime deps in `pyproject.toml` remain unpinned so end-users on fresh install always pull the patched versions.
- **No regressions:** Full suite (`test_api`, `test_post`, `test_page`, `test_user`, `test_media`, `test_formatter`, `test_wp_publish`, `test_comment`, `test_term`) passes after CLI rewiring.
- **No new runtime dependencies.**

## Files Changed

- `wpa/comment.py` (new)
- `wpa/term.py` (new)
- `tests/test_comment.py` (new)
- `tests/test_term.py` (new)
- `wpa/cli.py` — imports, 14 new handler functions, 4 new top-level subparsers (`comment`, `term`, `category`, `tag`); the three taxonomy-oriented parsers share a `_add_term_subparsers` factory
- `CLAUDE.md` — module list and test count updated
- `README.md` — usage sections for comments and terms, coverage badge refreshed
- `examples/bootstrap-site.sh` — v0.8.0 smoke test sections 5 (comments) and 6 (terms/categories/tags)

## Closes

- Phase 4 (comment + term + category/tag aliases) from `wpa-prd.md`
- Meta handler portion of Phase 4 → tracked as [#33](https://github.com/cadentdev/wpa/issues/33)

## Release Checklist (pre-tag)

- [ ] Bump `wpa/__init__.py` version to `0.8.0`
- [ ] Move this file's contents into `RELEASE-NOTES.md` as the new top entry
- [ ] Update `wpa-prd.md` Phase 4 row to **COMPLETE** (with a note that meta is deferred)
- [x] Run `bandit` and `pip-audit` and record results in the "Quality" section
- [ ] Live-test `examples/bootstrap-site.sh` against CT 118 (wp-stage-18 @ 192.168.52.18) after rollback to the `wpa-baseline` snapshot, exercising the full v0.8.0 surface (user/media/page/post/comment/term/category/tag)
- [ ] Tag `v0.8.0` and publish to PyPI
