#!/usr/bin/env python3
"""Publish markdown files as WordPress pages via REST API."""

import argparse
import sys
from pathlib import Path

import frontmatter
import markdown
import requests
from dotenv import load_dotenv
import os


def load_config():
    """Load WordPress credentials from .env file."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"Error: {env_path} not found. Copy .env.example to .env and fill in credentials.")
        sys.exit(1)

    load_dotenv(env_path)

    site_url = os.environ.get("WP_SITE_URL")
    user = os.environ.get("WP_USER")
    password = os.environ.get("WP_APP_PASSWORD")

    if not all([site_url, user, password]):
        print("Error: WP_SITE_URL, WP_USER, and WP_APP_PASSWORD must all be set in .env")
        sys.exit(1)

    return site_url.rstrip("/"), user, password


def parse_page(filepath):
    """Parse markdown file with YAML frontmatter."""
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    post = frontmatter.load(path)

    title = post.get("title")
    if not title:
        print(f"Error: Frontmatter must include 'title' in {filepath}")
        sys.exit(1)

    slug = post.get("slug", "")
    status = post.get("status", "draft")
    html_content = markdown.markdown(post.content)

    return title, slug, status, html_content


def publish_page(site_url, user, password, title, slug, status, content):
    """POST a page to WordPress REST API."""
    endpoint = f"{site_url}/wp-json/wp/v2/pages"

    payload = {
        "title": title,
        "content": content,
        "status": status,
    }
    if slug:
        payload["slug"] = slug

    response = requests.post(
        endpoint,
        json=payload,
        auth=(user, password),
        timeout=30,
    )

    if response.status_code == 201:
        data = response.json()
        page_id = data["id"]
        edit_url = f"{site_url}/wp-admin/post.php?post={page_id}&action=edit"
        print(f"Page created successfully!")
        print(f"  ID:       {page_id}")
        print(f"  Title:    {title}")
        print(f"  Status:   {status}")
        print(f"  Edit URL: {edit_url}")
        return 0
    else:
        print(f"Error: WordPress API returned {response.status_code}")
        try:
            error = response.json()
            print(f"  Code:    {error.get('code', 'unknown')}")
            print(f"  Message: {error.get('message', 'unknown')}")
        except ValueError:
            print(f"  Body: {response.text[:200]}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Publish markdown files as WordPress pages.")
    parser.add_argument("file", help="Path to markdown file with YAML frontmatter")
    args = parser.parse_args()

    site_url, user, password = load_config()
    title, slug, status, content = parse_page(args.file)

    print(f"Publishing '{title}' as {status} to {site_url}...")
    return publish_page(site_url, user, password, title, slug, status, content)


if __name__ == "__main__":
    sys.exit(main())
