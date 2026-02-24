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
- `status` (optional): `draft` (default) or `publish`
