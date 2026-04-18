# Remediation Test Run Results

## Scope
Run the newly-updated remediation tests against the current codebase **without source changes** (TDD red phase).

## Environment
- Repo: `cadentdev/wpa`
- Python: `3.12.13`
- Test runner: `pytest 9.0.3`
- Virtual environment: `.venv`

## Setup
The system Python is externally managed (PEP 668), so dependencies were installed in a local virtualenv:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

## Command Run
```bash
.venv/bin/python -m pytest \
  tests/test_api.py \
  tests/test_post.py \
  tests/test_formatter.py \
  tests/test_media.py \
  tests/test_page.py \
  tests/test_user.py \
  tests/test_term.py \
  tests/test_wp_publish.py
```

## Result Summary
- Total: `418`
- Passed: `414`
- Failed: `4`
- Duration: `2.07s`

## Failing Tests (Red Phase)
1. `tests/test_post.py::TestPostIdValidation::test_bool_rejected`
   - Expected: `ValueError("Invalid post ID")`
   - Actual: no exception raised for bool ID
2. `tests/test_media.py::TestMediaIdValidation::test_bool_rejected`
   - Expected: `ValueError("Invalid media ID")`
   - Actual: no exception raised for bool ID
3. `tests/test_page.py::TestPageIdValidation::test_bool_rejected`
   - Expected: `ValueError("Invalid page ID")`
   - Actual: no exception raised for bool ID
4. `tests/test_user.py::TestUserIdValidation::test_bool_rejected`
   - Expected: `ValueError("Invalid user ID")`
   - Actual: no exception raised for bool ID

## Interpretation
The updated tests successfully expose a behavioral gap in ID validation: `bool` values are currently accepted where strict positive integer IDs are expected. This is the intended red-phase outcome and provides concrete targets for the next implementation step in source modules.

## Green Phase Source Fixes
Applied minimal source changes to ID validators so `bool` values are rejected explicitly:

- `wpa/post.py` (`_validate_post_id`)
- `wpa/media.py` (`_validate_media_id`)
- `wpa/page.py` (`_validate_page_id`)
- `wpa/user.py` (`_validate_user_id`)

Each validator now checks `isinstance(value, bool)` before the existing positive-integer validation.

## Green Phase Verification

### Targeted Previously-Failing Tests
```bash
.venv/bin/python -m pytest \
  tests/test_post.py::TestPostIdValidation::test_bool_rejected \
  tests/test_media.py::TestMediaIdValidation::test_bool_rejected \
  tests/test_page.py::TestPageIdValidation::test_bool_rejected \
  tests/test_user.py::TestUserIdValidation::test_bool_rejected
```

Result: `4 passed`

### Remediation Subset Re-Run
```bash
.venv/bin/python -m pytest \
  tests/test_api.py \
  tests/test_post.py \
  tests/test_formatter.py \
  tests/test_media.py \
  tests/test_page.py \
  tests/test_user.py \
  tests/test_term.py \
  tests/test_wp_publish.py
```

Result: `418 passed`
