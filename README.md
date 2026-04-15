# WPA — WordPress Automation

[![CI](https://github.com/cadentdev/wpa/actions/workflows/ci.yml/badge.svg)](https://github.com/cadentdev/wpa/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen)](https://github.com/cadentdev/wpa)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org)
[![PyPI](https://img.shields.io/pypi/v/wpa)](https://pypi.org/project/wpa/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

CLI tool for WordPress automation — manage posts, pages, users, media, comments, and taxonomy terms via the REST API.

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

# Get a single user
wpa user get 42 --site mysite

# Create a user
wpa user create --site mysite --username jdoe --email jdoe@example.com --role author

# Update a user
wpa user update 42 --site mysite --email newemail@example.com --role editor

# Set a user's role (shortcut for update --role)
wpa user set-role 42 editor --site mysite

# Delete a user (reassign their posts to user 1)
wpa user delete 42 --site mysite --reassign 1
```

### Manage media

```bash
# List media items
wpa media list --site mysite
wpa media list --site mysite --media-type image --per-page 50

# List media as JSON, specific fields only
wpa media list --site mysite --format json --fields id,title,source_url,media_type

# Get a single media item
wpa media get 123 --site mysite

# Import (upload) a local file as a WordPress media item
wpa media import /path/to/photo.jpg --site mysite
wpa media import /path/to/photo.jpg --site mysite --title "Cover photo" --alt-text "Team at launch"

# Delete a media item (moves to trash; use --force to permanently delete)
wpa media delete 123 --site mysite
wpa media delete 123 --site mysite --force
```

Output formats: `table` (default), `json`, `csv`, `tsv`. Use `--fields` to select columns (available: `id`, `username`, `email`, `first_name`, `last_name`, `display_name`, `roles`, `registered`, `url`).

### Manage comments

```bash
# List comments (default shows approved only; filter by status, post, author)
wpa comment list --site mysite
wpa comment list --site mysite --status hold
wpa comment list --site mysite --post 42 --status approved
wpa comment list --site mysite --author-email "reviewer@example.com"

# Get a single comment
wpa comment get 123 --site mysite

# Create a comment
wpa comment create --site mysite --post 42 --content "<p>Thanks for posting!</p>" \
    --author-name "Reviewer" --author-email "reviewer@example.com"

# Update comment content or metadata
wpa comment update 123 --site mysite --content "<p>Edited.</p>"

# Moderation shortcuts (wp-cli parity)
wpa comment approve   123 --site mysite
wpa comment unapprove 123 --site mysite   # move back to "hold"
wpa comment spam      123 --site mysite
wpa comment unspam    123 --site mysite   # restore from spam to approved
wpa comment trash     123 --site mysite   # soft delete

# Hard delete (moves to trash by default; --force skips trash)
wpa comment delete 123 --site mysite
wpa comment delete 123 --site mysite --force
```

### Manage taxonomy terms (categories, tags, custom)

```bash
# Categories via the alias (pre-sets --taxonomy=category)
wpa category list --site mysite
wpa category list --site mysite --search "news"
wpa category create --site mysite --name "Announcements" --description "Site announcements"
wpa category update 7 --site mysite --description "Major site announcements"
wpa category delete 7 --site mysite   # always permanent; terms cannot be trashed

# Tags via the alias (pre-sets --taxonomy=post_tag)
wpa tag list --site mysite
wpa tag create --site mysite --name "wordpress" --description "Posts about WordPress"
wpa tag delete 12 --site mysite

# Generic term interface for built-in or custom taxonomies
wpa term list --site mysite --taxonomy category
wpa term list --site mysite --taxonomy post_tag
wpa term list --site mysite --taxonomy genre      # custom taxonomy

wpa term get 7 --site mysite --taxonomy category
wpa term create --site mysite --taxonomy post_tag --name "api"
wpa term update 7 --site mysite --taxonomy category --name "Big Announcements"
wpa term delete 7 --site mysite --taxonomy category
```

**Note on `delete`:** The WordPress REST API does not support trashing taxonomy terms, so `wpa term delete` (and the `category` / `tag` aliases) always performs a permanent delete. There is no `--force` flag — force is implicit.

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
