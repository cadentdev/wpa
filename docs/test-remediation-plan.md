# Test Remediation Plan (TDD)

## Branch

`tests/consolidated-remediation`

## Objective

Address the consolidated test deficiencies by improving test quality and behavioral coverage before making any source-code changes.

## TDD Workflow

1. Update tests to reflect the expected behavior and close identified gaps.
2. Run only the updated tests against the current codebase (no source changes).
3. Record pass/fail outcomes and failing assertions in `docs/remediation-test-results.md`.
4. If tests fail, use those failures as the red phase to guide source fixes.
5. If tests pass, mark those deficiencies as remediated through test improvements alone.

## Scope of Test Updates

### `tests/test_api.py`

- Verify `WPApiClient.from_config()` sets `admin_path`.
- Add pagination security checks for page 2+ in `get_list()`:
  - scheme downgrade detection on later page.
  - response-size cap checks on later page.
- Add/strengthen request-contract assertions in core request tests:
  - auth header and timeout propagation.
  - redirect behavior for write methods.
- Add explicit redirect-disable tests for `PUT` and `PATCH`.
- Strengthen `response_at_cap_accepted` style tests to assert returned payload semantics.

### `tests/test_post.py`

- Replace type-only assertion in `_extract_rendered` tests with exact expected output assertion.
- Add bool ID validation coverage (`True`/`False`) for post ID validator.

### `tests/test_formatter.py`

- Replace weak table-alignment checks (`split()` based) with spacing/padding-aware assertions.

### `tests/test_media.py`

- Add dedicated unit tests for `_extract_media_row` behavior.
- Add bool ID validator coverage for media IDs.
- Add `delete_media` invalid/string ID parity checks where missing.
- Add `import_media` MIME fallback test (`application/octet-stream`).
- Add assertion that `list_media` sends `context="edit"`.

### `tests/test_page.py`

- Add bool ID validator coverage for page IDs.
- Add string-ID coverage for `update_page` and `delete_page`.
- Add `list_pages` assertions for `per_page` and `context="edit"`.
- Add multi-field `update_page` payload test.

### `tests/test_user.py`

- Add bool ID validator coverage for user IDs.
- Add explicit test for `update_user(display_name=...)` mapping to payload field `name`.
- Add assertion that `list_users` sets `per_page=100`.

### `tests/test_term.py`

- Add explicit bool rejection tests for term ID validation.

### `tests/test_wp_publish.py`

- Strengthen CLI integration tests that currently assert only exit code.
- Assert argument/payload forwarding into publish and page-create flows.

## Test Execution Plan

Run updated tests in focused batches first:

1. `tests/test_api.py`
2. `tests/test_post.py`
3. `tests/test_formatter.py`
4. `tests/test_media.py`
5. `tests/test_page.py`
6. `tests/test_user.py`
7. `tests/test_term.py`
8. `tests/test_wp_publish.py`

Then run full suite:

- `pytest tests`

## Deliverables

- Updated tests in `tests/`.
- TDD run log and outcomes in `docs/remediation-test-results.md`.

## Status Update

- Bool-ID validation remediation has been completed in source validators for post, media, page, and user modules.
- Green-phase verification is complete (targeted bool-ID tests pass, and remediation subset reports `418 passed`).
