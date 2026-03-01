"""Publishing logic for WPA — parse markdown, POST to WordPress REST API."""

import sys
from pathlib import Path

import frontmatter
import markdown
import requests

VALID_STATUSES = {"draft", "publish", "pending", "private"}


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

    if status not in VALID_STATUSES:
        print(
            f"Error: Invalid status '{status}' in {filepath}. Must be one of: {', '.join(sorted(VALID_STATUSES))}"
        )
        sys.exit(1)

    html_content = markdown.markdown(post.content)

    return title, slug, status, html_content


def publish_page(
    site_url, user, password, title, slug, status, content, admin_path="wp-admin"
):
    """POST a page to WordPress REST API."""
    endpoint = f"{site_url}/wp-json/wp/v2/pages"

    payload = {
        "title": title,
        "content": content,
        "status": status,
    }
    if slug:
        payload["slug"] = slug

    try:
        response = requests.post(
            endpoint,
            json=payload,
            auth=(user, password),
            timeout=30,
        )
    except requests.ConnectionError:
        print(
            f"Error: Could not connect to {site_url}. Check the URL and your network connection."
        )
        return 1
    except requests.Timeout:
        print(f"Error: Request to {site_url} timed out after 30 seconds.")
        return 1
    except requests.RequestException as e:
        print(f"Error: Request failed: {e}")
        return 1

    if response.status_code == 201:
        data = response.json()
        page_id = data["id"]
        edit_url = f"{site_url}/{admin_path}/post.php?post={page_id}&action=edit"
        print("Page created successfully!")
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
