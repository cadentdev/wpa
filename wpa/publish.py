"""Publishing logic for WPA — parse markdown, POST to WordPress REST API."""

import sys
from pathlib import Path

import frontmatter
import markdown

from wpa.exceptions import WPApiError, WPConnectionError, WPTimeoutError

VALID_STATUSES = {"draft", "publish", "pending", "private"}


def parse_markdown(filepath):
    """Parse a markdown file with YAML frontmatter.

    Returns a dict with all frontmatter fields plus 'content' (as HTML).
    Validates that 'title' exists and 'status' is valid.

    Args:
        filepath: Path to the markdown file.

    Returns:
        Dict with keys: title, slug, status, content, plus any extra
        frontmatter fields (categories, tags, author, etc.).

    Raises:
        SystemExit: If file not found, title missing, or status invalid.
    """
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
            f"Error: Invalid status '{status}' in {filepath}. "
            f"Must be one of: {', '.join(sorted(VALID_STATUSES))}"
        )
        sys.exit(1)

    html_content = markdown.markdown(post.content)

    # Build result with all frontmatter fields
    result = dict(post.metadata)
    result["title"] = title
    result["slug"] = slug
    result["status"] = status
    result["content"] = html_content

    return result


def parse_page(filepath):
    """Parse markdown file with YAML frontmatter.

    Legacy wrapper around parse_markdown() that returns a 4-tuple
    for backward compatibility with existing callers.

    Returns:
        Tuple of (title, slug, status, html_content).
    """
    data = parse_markdown(filepath)
    return data["title"], data["slug"], data["status"], data["content"]


def publish_page(client, title, slug, status, content, admin_path="wp-admin"):
    """POST a page to WordPress REST API using WPApiClient.

    Args:
        client: WPApiClient instance.
        title: Page title.
        slug: URL slug.
        status: Publication status.
        content: HTML content.
        admin_path: WordPress admin path (default: wp-admin).

    Returns:
        0 on success, 1 on error.
    """
    payload = {
        "title": title,
        "content": content,
        "status": status,
    }
    if slug:
        payload["slug"] = slug

    try:
        data = client.post("pages", data=payload)
        page_id = data["id"]
        edit_url = f"{client.site_url}/{admin_path}/post.php?post={page_id}&action=edit"
        print("Page created successfully!")
        print(f"  ID:       {page_id}")
        print(f"  Title:    {title}")
        print(f"  Status:   {status}")
        print(f"  Edit URL: {edit_url}")
        return 0
    except WPApiError as e:
        print(f"Error: WordPress API returned {e.status_code}")
        print(f"  Code:    {e.code}")
        print(f"  Message: {e.message}")
        return 1
    except WPConnectionError as e:
        print(f"Error: {e}")
        return 1
    except WPTimeoutError as e:
        print(f"Error: {e}")
        return 1
