# WPA — WordPress Page Publisher

Minimal CLI tool to publish markdown files as WordPress pages via the REST API.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your WordPress credentials
```

### WordPress Application Password

1. Log into wp-admin → Users → Your Profile
2. Scroll to "Application Passwords"
3. Enter name: "WPA CLI", click "Add New Application Password"
4. Copy the generated password into `.env` as `WP_APP_PASSWORD`

## Usage

```bash
python3 wp-publish.py pages/your-page.md
```

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

## Safety and Security

- **Default status is always `draft`** — never publishes unless frontmatter explicitly says otherwise
- **HTTPS enforced** — rejects `http://` site URLs to protect credentials in transit
- **Status validation** — rejects typos and invalid values in frontmatter
- **Connection error handling** — timeouts and network failures produce clear messages, not tracebacks
- **Credentials in `.env` only** — `.gitignore` prevents accidental commits

## Development

```bash
pip install -r requirements-dev.txt
pytest --cov=. --cov-report=term-missing
```

20 tests | 99% coverage
