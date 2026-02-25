# Release Notes

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
