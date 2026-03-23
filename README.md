# WPA — WordPress Automation

[![CI](https://github.com/cadentdev/wpa/actions/workflows/ci.yml/badge.svg)](https://github.com/cadentdev/wpa/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-75%25-yellow)](https://github.com/cadentdev/wpa)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org)
[![PyPI](https://img.shields.io/pypi/v/wpa)](https://pypi.org/project/wpa/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

CLI tool for WordPress automation — manage posts, pages, and users via the REST API.

## Install

```bash
pip install wpa
```

Or install from source:

```bash
git clone https://github.com/cadentdev/wpa.git
cd wpa
pip install -e .
```

### Create a site config

```bash
wpa site add
```

This prompts for your WordPress URL, username, application password (hidden), and optional admin path. Configs are stored at `~/.config/wpa/<site-name>/.env` with `600` permissions.

### WordPress Application Password

1. Log into wp-admin → Users → Your Profile
2. Scroll to "Application Passwords"
3. Enter name: "WPA CLI", click "Add New Application Password"
4. Copy the generated password (use it during `--new-site` setup)

## Usage

### Manage posts

```bash
# List posts (with filtering)
wpa post list --site mysite
wpa post list --site mysite --status draft --author 1
wpa post list --site mysite --category 5 --tag 12
wpa post list --site mysite --search "announcement" --orderby date --order desc

# Get a single post
wpa post get 42 --site mysite

# Create a post
wpa post create --site mysite --title "My Post" --content "<p>Hello</p>" --status draft

# Update a post
wpa post update 42 --site mysite --title "Updated Title" --status publish

# Delete a post (moves to trash; use --force to permanently delete)
wpa post delete 42 --site mysite
wpa post delete 42 --site mysite --force
```

### Manage pages

```bash
# List pages
wpa page list --site mysite
wpa page list --site mysite --status publish --parent 10

# Get a single page
wpa page get 42 --site mysite

# Create a page from markdown file
wpa page create --site mysite pages/about.md

# Create a page from flags
wpa page create --site mysite --title "About" --content "<p>About us</p>"

# Publish shortcut (equivalent to wpa page create with markdown)
wpa publish pages/your-page.md --site mysite

# Update a page
wpa page update 42 --site mysite --title "New Title" --parent 10

# Delete a page
wpa page delete 42 --site mysite
```

### Manage users

```bash
# List all users
wpa user list --site mysite

# List users as JSON, specific fields only
wpa user list --site mysite --format json --fields id,username,email,roles

# Export users to TSV
wpa user list --site mysite --format tsv > users.tsv

# Filter by role or search term
wpa user list --site mysite --role editor
wpa user list --site mysite --search "jane"

# Create a user
wpa user create --site mysite --username jdoe --email jdoe@example.com --role author

# Update a user
wpa user update 42 --site mysite --email newemail@example.com --role editor

# Delete a user (reassign their posts to user 1)
wpa user delete 42 --site mysite --reassign 1
```

Output formats: `table` (default), `json`, `csv`, `tsv`. Use `--fields` to select columns (available: `id`, `username`, `email`, `first_name`, `last_name`, `display_name`, `roles`, `registered`, `url`).

### Output options

All list commands support these output modifiers:

```bash
# Output only IDs
wpa post list --site mysite --ids

# Output only the count
wpa post list --site mysite --count

# Output a single field per result
wpa post list --site mysite --field title

# Select specific columns
wpa user list --site mysite --fields id,username,email

# Debug mode (print HTTP request/response details)
wpa post list --site mysite --debug
```

### Site management

```bash
wpa site add
wpa site list
wpa --version
```

### Multi-site behavior

| Configs | `--site` flag | Behavior |
|---------|---------------|----------|
| 0 | No | Prompts to create a new config |
| 1 | No | Uses the single config automatically |
| 2+ | No | Prompts to select from list |
| Any | Yes | Uses the named config (error if not found) |

### Markdown file format

```yaml
---
title: "Your Page Title"
slug: "your-page-slug"
status: draft
---

Page content in markdown here...
```

- `title` (required): Page title
- `slug` (optional): URL slug
- `status` (optional): `draft` (default), `publish`, `pending`, or `private`

### Site config format

Each site config is stored at `~/.config/wpa/<name>/.env`:

```
WP_SITE_URL=https://example.com
WP_USER=your-username
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx
WP_ADMIN_PATH=wp-admin
```

- `WP_ADMIN_PATH` is optional (defaults to `wp-admin`). Override it if your site uses a custom admin URL.
- The `XDG_CONFIG_HOME` environment variable is respected if set.

### Migration from repo-root .env

If you have an existing `.env` in the repo root and no XDG configs, the tool will offer to migrate it on first run.

## Safety and Security

- **Default status is always `draft`** — never publishes unless frontmatter explicitly says otherwise
- **HTTPS enforced for public addresses** — rejects `http://` for public URLs; allows HTTP for private/LAN addresses (RFC 1918, localhost, `.lan`/`.local`/`.test`/`.internal` TLDs) with a warning
- **Credentials in XDG config** — stored outside the repo at `~/.config/wpa/` with 600 permissions
- **Password input hidden** — uses `getpass` during interactive setup
- **Status validation** — rejects typos and invalid values in frontmatter
- **Site name validation** — only alphanumeric characters and hyphens allowed
- **Connection error handling** — timeouts and network failures produce clear messages, not tracebacks

## Development

```bash
pip install -e '.[dev]'
pytest --cov=wpa --cov-report=term-missing
```

## Links

- [Product Requirements Document](wpa-prd.md) — Vision, design principles, command structure, and implementation roadmap
- [Getting Started](GETTING-STARTED.md) — REST API setup, Wordfence notes, staging guide
- [Release Notes](RELEASE-NOTES.md)
- [Contributing](CONTRIBUTING.md)
- [WP-CLI Command Inventory](docs/wp-cli-command-inventory.md) — Complete catalog of WP-CLI 2.12.0 commands used as the template for WPA planning
- [WP-CLI REST API Mapping Matrix](docs/wp-cli-rest-api-mapping-matrix.md) — Feasibility classification of every WP-CLI command against the REST API
