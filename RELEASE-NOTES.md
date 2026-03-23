# Release Notes

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
