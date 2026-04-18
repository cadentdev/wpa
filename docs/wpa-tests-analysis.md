# WPA Tests: Analysis April 16, 2026

Prompt:

> Review the tests in @tests and look for tests that do not adequately test the target code. Lists the tests that don't test the source code well and your reasons for the deficiencies. Don't change any code, this is simply an analysis task

Date: Saturday, April 18, 2026

Model GLM-5.1

## Model GLM-5.1 -- Test Quality Analysis

After reviewing all 9 test files against their corresponding source modules, here are the tests with inadequate coverage and the reasons why.

---

### 1. [test_api.py](../tests/test_api.py:0:0-0:0) — Missing [from_config()](../wpa/api.py:73:4-89:21) admin_path verification

**Test:** [TestFromConfig.test_creates_client_from_config](../tests/test_api.py:103:4-115:64) (tests/test_api.py:105-116)

The source at `wpa/api.py:89` explicitly sets `client.admin_path = admin_path` from the resolved config, but the test only asserts `site_url`, `username`, and `app_password`. The `admin_path` attribute — which affects edit URLs in [publish_page](../wpa/publish.py:76:0-118:16) — is never verified.

---

### 2. [test_api.py](../tests/test_api.py:0:0-0:0) — [get_list()](../wpa/api.py:286:4-377:36) pagination security checks untested

The [get_list()](../wpa/api.py:286:4-377:36) method applies [_check_no_scheme_downgrade()](../wpa/api.py:149:4-160:13) and [_check_response_size()](../wpa/api.py:136:4-147:13) on **every** page request (lines 329-330, 373-374 of [api.py](../wpa/api.py:0:0-0:0)), but the security tests in [TestSecurityHardening](../tests/test_api.py:504:0-651:24) only verify these checks on the first page. No test confirms that a scheme downgrade or oversized response on page 2+ is caught. A malicious server could return a safe first page and a downgraded second page without any test catching it.

---

### 3. [test_api.py](../tests/test_api.py:0:0-0:0) — [_headers()](../wpa/api.py:112:4-117:9) and [_request()](../wpa/api.py:208:4-272:46) PUT/PATCH untested

- **[_headers()](../wpa/api.py:112:4-117:9)** constructs the `Authorization` and `Content-Type` headers but is never directly tested. The [TestAuthHeader](../tests/test_api.py:493:0-501:48) class only tests [_auth_header()](../wpa/api.py:106:4-110:33), not the full header dict.
- **[_request()](../wpa/api.py:208:4-272:46)** disables redirects for `PUT` and `PATCH` (`api.py:239`), but only `POST` and `DELETE` redirect-disabling are tested ([test_post_disables_redirects](../tests/test_api.py:578:4-590:53), [test_delete_disables_redirects](../tests/test_api.py:592:4-604:53)). `PUT`/`PATCH` redirect behavior is untested.

---

### 4. [test_media.py](../tests/test_media.py:0:0-0:0) — No dedicated [_extract_media_row](../wpa/media.py:71:0-79:14) tests

Every other domain module (`comment`, [post](../wpa/api.py:379:4-390:86), `term`, `page`) has a dedicated `TestExtract*Row` class that tests field extraction, rendered-content flattening, and missing-field defaults in isolation. [test_media.py](../tests/test_media.py:0:0-0:0) tests extraction only indirectly through [list_media](../wpa/media.py:82:0-129:83) and [get_media](../wpa/media.py:132:0-145:35), making it harder to pinpoint extraction bugs and leaving edge cases like missing `title`/`caption` dicts untested.

---

### 5. [test_media.py](../tests/test_media.py:0:0-0:0) — Missing validation and import edge cases

- **[_validate_media_id](../wpa/media.py:50:0-57:57) accepts `True`** — The source at `wpa/media.py:57` uses `isinstance(media_id, int)` without excluding `bool` (a subclass of `int`). `True` passes as valid ID `1`. Unlike [comment.py](../wpa/comment.py:0:0-0:0) and [term.py](../wpa/term.py:0:0-0:0) which have explicit `isinstance(id, bool)` guards, [media.py](../wpa/media.py:0:0-0:0) does not, and no test exposes this bug.
- **[delete_media](../wpa/media.py:204:0-221:68) with string ID** — [get_media](../wpa/media.py:132:0-145:35) tests string IDs but [delete_media](../wpa/media.py:204:0-221:68) does not.
- **[import_media](../wpa/media.py:148:0-201:59) MIME fallback** — Source falls back to `"application/octet-stream"` (`media.py:184`) when `mimetypes.guess_type` returns `None`. No test verifies this fallback path.
- **[list_media](../wpa/media.py:82:0-129:83) doesn't verify `context: "edit"`** — Source sets it (`media.py:108`) but no test asserts it's sent.

---

### 6. [test_page.py](../tests/test_page.py:0:0-0:0) — Missing ID validation and parameter tests

- **[_validate_page_id](../wpa/page.py:49:0-56:55) accepts `True`** — Same bool-as-int bug as media. Source at `page.py:56` lacks the `isinstance(page_id, bool)` guard present in [comment.py](../wpa/comment.py:0:0-0:0)/[term.py](../wpa/term.py:0:0-0:0). No test catches this.
- **String ID not tested for [update_page](../wpa/page.py:181:0-203:55)/[delete_page](../wpa/page.py:206:0-223:67)** — [get_page](../wpa/page.py:120:0-136:34) tests string IDs, but [update_page](../wpa/page.py:181:0-203:55) and [delete_page](../wpa/page.py:206:0-223:67) do not.
- **[list_pages](../wpa/page.py:70:0-117:82) missing `per_page` and `context` tests** — Source accepts `per_page` (`page.py:103`) and sets `context: "edit"` (`page.py:96`), but no test verifies either is passed.
- **[update_page](../wpa/page.py:181:0-203:55) only tests single-field update** — No test for updating multiple fields simultaneously, unlike [test_post.py](../tests/test_post.py:0:0-0:0) and [test_comment.py](../tests/test_comment.py:0:0-0:0).

---

### 7. [test_post.py](../tests/test_post.py:0:0-0:0) — Missing validation edge cases

- **[_validate_post_id](../wpa/comment.py:63:0-70:55) accepts `True`** — Source at `post.py:56` lacks `isinstance(post_id, bool)` guard. No test for boolean inputs.
- **[list_posts](../wpa/post.py:85:0-141:82) doesn't verify `context: "edit"`** — Source sets it (`post.py:115`) but no test asserts it.
- **[_extract_post_row](../wpa/post.py:70:0-82:14) with empty categories/tags lists** — Source joins list values (`post.py:79-81`), but an empty list `[]` would produce `""`. Not tested.
- **[update_post](../wpa/post.py:209:0-231:55) doesn't test `categories`/`tags`/`featured_media` updates** — Only `title` and `status` updates are tested, leaving the most complex fields unverified.

---

### 8. [test_user.py](../tests/test_user.py:0:0-0:0) — Missing row extraction and validation tests

- **No [_extract_user_row](../wpa/user.py:55:0-63:14) test class** — Unlike comment/post/term, there's no isolated test for the row extraction function. The `roles` list-to-string join logic (`user.py:61-62`) and the `slug`→`username` / `name`→`display_name` remapping are only tested indirectly.
- **[_validate_user_id](../wpa/user.py:45:0-52:55) accepts `True`** — Source at `user.py:52` lacks `isinstance(user_id, bool)` guard. No test for boolean inputs.
- **[delete_user](../wpa/user.py:204:0-224:59) with invalid ID** — Not tested, unlike every other domain module.
- **[update_user](../wpa/user.py:155:0-201:56) with `display_name`** — Source maps `display_name` → `name` in the payload (`user.py:194`), but no test verifies this non-obvious field mapping.
- **[list_users](../wpa/user.py:97:0-114:82) doesn't verify `per_page: 100`** — Source hardcodes it (`user.py:109`) but no test asserts it.

---

### 9. [test_term.py](../tests/test_term.py:0:0-0:0) — Missing bool validation test

- **[_validate_term_id](../wpa/term.py:86:0-89:55) with `bool`** — The source at `term.py:89` has an explicit `isinstance(term_id, bool)` guard (correctly rejecting `True`/`False`), but no test verifies this. The guard is untested despite being the reason the check exists.

---

### 10. [test_formatter.py](../tests/test_formatter.py:0:0-0:0) — [format_field](../wpa/formatter.py:107:0-117:66)/[format_ids](../wpa/formatter.py:83:0-92:59) don't normalize `None`

[format_output()](../wpa/formatter.py:9:0-43:45) normalizes `None` → `""` via [_normalize_value()](../wpa/formatter.py:46:0-50:16), but [format_field()](../wpa/formatter.py:107:0-117:66) and [format_ids()](../wpa/formatter.py:83:0-92:59) use `str(row.get(...))` which converts `None` to the string `"None"`. The test at line 203-205 ([test_missing_id_key](../tests/test_formatter.py:202:4-204:39)) tests missing keys (which return `""`), but no test checks what happens when a value is explicitly `None`. This is an inconsistency that no test catches.

---

### 11. [test_wp_publish.py](../tests/test_wp_publish.py:0:0-0:0) — Minimal CLI coverage and missing parse edge cases

- **[cli.py](../wpa/cli.py:0:0-0:0) (55KB) has only 6 integration tests** — The CLI is the largest source module but has near-zero unit test coverage. Subcommands for post, comment, media, term, user CRUD are entirely untested.
- **[parse_markdown](../wpa/publish.py:13:0-60:17) missing status values** — Only `draft` and `publish` are tested. `pending` and `private` are valid statuses (`publish.py:11`) but have no test.
- **[publish_page](../wpa/publish.py:76:0-118:16) with missing `id` in response** — Source does `data["id"]` (`publish.py:101`), which raises `KeyError` if the API response lacks an `id`. No test covers this.
- **[publish_page](../wpa/publish.py:76:0-118:16) always tested with `status="draft"`** — No test verifies behavior with `publish`, `pending`, or `private` status.
- **[parse_markdown](../wpa/publish.py:13:0-60:17) with no frontmatter** — What happens when a markdown file has no `---` delimiter? Untested.

---

### Summary of Cross-Cutting Deficiencies

| Pattern | Affected Tests |
|---|---|
| **Boolean ID accepted as valid** (source bug, no test catches it) | `test_media`, `test_page`, `test_post`, `test_user` |
| **Boolean ID rejection untested** (guard exists but untested) | `test_comment`, `test_term` |
| **No dedicated `_extract_*_row` test class** | `test_media`, `test_user` |
| **`context: "edit"` param not verified** | `test_media`, `test_page`, `test_post` |
| **String ID not tested for update/delete** | `test_page`, `test_media` |
| **CLI has near-zero unit test coverage** | `test_wp_publish` |

## Consolidated Confidence Audit

This section consolidates the second-pass review into a cleaned summary and removes duplicated transcript content.

### Weakest Individual Tests

- `tests/test_post.py:51` ([TestExtractRendered.test_dict_without_rendered](../tests/test_post.py:50:4-52:38))
  The assertion only checks type (`str`), not expected content, so regressions in fallback rendering can pass.
- `tests/test_api.py:227` ([TestGet.test_get_success](../tests/test_api.py:225:4-237:76))
  Verifies URL/method and result, but omits key request-contract checks (auth header, timeout propagation).
- `tests/test_api.py:273` ([TestPost.test_post_with_json_body](../tests/test_api.py:271:4-282:70))
  Validates JSON body but not write-path request options like redirect handling.
- `tests/test_api.py:529` ([TestSecurityHardening.test_response_at_cap_accepted](../tests/test_api.py:527:4-540:27))
  Only checks that no exception is raised; it does not verify returned parsing semantics.
- `tests/test_formatter.py:56` ([TestTableFormat.test_table_columns_aligned](../tests/test_formatter.py:55:4-61:44))
  Uses `split()` and therefore does not actually validate fixed-width column alignment.
- `tests/test_wp_publish.py:1000` ([TestMain.test_publish_subcommand](../tests/test_wp_publish.py:999:4-1013:26))
  Exit-code-only assertion with heavy patching; weak for argument/payload wiring regressions.
- `tests/test_wp_publish.py:1016` ([TestMain.test_page_create_subcommand](../tests/test_wp_publish.py:1015:4-1029:26))
  Same issue: weakly diagnostic because dispatch argument mapping is not asserted.
- `tests/test_user.py:251` ([TestUserIdValidation.test_valid_positive_integer](../tests/test_user.py:251:4-254:30))
  Misses the `bool` edge case (`True` passes current `isinstance(..., int)` validation path).

### Confidence Table

| Test File | Confidence | Why |
|---|---|---|
| `tests/test_api.py` | `strong` | Deep coverage of auth, errors, pagination, and hardening; a few assertions are still loose (`:227`, `:273`, `:529`). |
| `tests/test_comment.py` | `adequate` | Good validation/status/payload checks, but mostly mocked client interaction. |
| `tests/test_formatter.py` | `adequate` | Good format/edge coverage, but table alignment assertion is weak (`:56`). |
| `tests/test_media.py` | `adequate` | Good import/file-path negative paths and payload checks; network/client path is mocked. |
| `tests/test_page.py` | `adequate` | Good CRUD and parameter forwarding tests, but mostly wrapper-level assertions against mocks. |
| `tests/test_post.py` | `weak` | Over-reliance on mocked call-shape checks and non-diagnostic assertion in `_extract_rendered` (`:51`). |
| `tests/test_term.py` | `strong` | Strong module-specific logic coverage (`_resolve_endpoint`, taxonomy routing/validation), despite mocked API boundary. |
| `tests/test_user.py` | `adequate` | Solid CRUD/validation coverage, but misses bool-ID edge coverage around `_validate_user_id` (`:251` area). |
| `tests/test_wp_publish.py` | `adequate (mixed)` | `config` tests are strong; some CLI tests are exit-code-only and weakly diagnostic (`:1000`, `:1016`). |

**Roll-up:** `strong = 2`, `adequate = 6`, `weak = 1`.
