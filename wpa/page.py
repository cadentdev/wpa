"""Page CRUD operations via WordPress REST API."""

from wpa.post import _extract_rendered

# Maps friendly field names to WordPress REST API response keys
PAGE_FIELDS = {
    "id": "id",
    "title": "title",
    "status": "status",
    "date": "date",
    "slug": "slug",
    "parent": "parent",
    "author": "author",
    "content": "content",
    "excerpt": "excerpt",
    "menu_order": "menu_order",
    "link": "link",
    "modified": "modified",
}

AVAILABLE_FIELDS = list(PAGE_FIELDS.keys())
DEFAULT_FIELDS = ["id", "title", "status", "date", "slug"]


def validate_fields(fields_str):
    """Parse and validate a comma-separated fields string.

    Args:
        fields_str: Comma-separated field names, or None for defaults.

    Returns:
        List of validated field names.

    Raises:
        ValueError: If any field name is not in AVAILABLE_FIELDS.
    """
    if fields_str is None:
        return DEFAULT_FIELDS

    fields = [f.strip() for f in fields_str.split(",")]
    for field in fields:
        if field not in PAGE_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _validate_page_id(page_id):
    """Validate page_id is a positive integer.

    Raises:
        ValueError: If page_id is not a positive integer.
    """
    if not isinstance(page_id, int) or page_id < 1:
        raise ValueError(f"Invalid page ID: {page_id}")


def _extract_page_row(api_page):
    """Convert a WP REST API page object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in PAGE_FIELDS.items():
        value = api_page.get(api_key, "")
        if friendly in ("title", "content", "excerpt"):
            value = _extract_rendered(value)
        row[friendly] = value
    return row


def list_pages(
    client,
    status=None,
    search=None,
    parent=None,
    per_page=10,
    page=None,
    orderby=None,
    order=None,
):
    """Fetch pages from WordPress REST API.

    Args:
        client: WPApiClient instance.
        status: Filter by page status.
        search: Search term.
        parent: Filter by parent page ID.
        per_page: Results per page (default 10, max 100).
        page: Specific page number (fetches single page).
        orderby: Sort field.
        order: Sort order (asc, desc).

    Returns:
        List of page dicts with friendly field names.
    """
    params = {"context": "edit"}
    if status:
        params["status"] = status
    if search:
        params["search"] = search
    if parent is not None:
        params["parent"] = parent
    if per_page is not None:
        params["per_page"] = per_page
    if page is not None:
        params["page"] = page
    if orderby:
        params["orderby"] = orderby
    if order:
        params["order"] = order

    if page is not None:
        items = client.get("pages", params=params)
        if not isinstance(items, list):
            return []
        return [_extract_page_row(p) for p in items]

    return [_extract_page_row(p) for p in client.get_list("pages", params=params)]


def get_page(client, page_id, embed=False):
    """Get a single page by ID.

    Args:
        client: WPApiClient instance.
        page_id: Page ID.
        embed: Include linked resources.

    Returns:
        Page dict with friendly field names.
    """
    _validate_page_id(page_id)
    params = {"context": "edit"}
    if embed:
        params["_embed"] = True
    data = client.get(f"pages/{page_id}", params=params)
    return _extract_page_row(data)


def create_page(
    client,
    title,
    content="",
    status="draft",
    slug=None,
    parent=None,
    author=None,
    menu_order=None,
):
    """Create a new page.

    Args:
        client: WPApiClient instance.
        title: Page title.
        content: Page content (HTML).
        status: Page status (default: draft).
        slug: URL slug.
        parent: Parent page ID.
        author: Author user ID.
        menu_order: Menu order integer.

    Returns:
        Created page dict from API response.
    """
    payload = {
        "title": title,
        "content": content,
        "status": status,
    }
    if slug:
        payload["slug"] = slug
    if parent is not None:
        payload["parent"] = parent
    if author is not None:
        payload["author"] = author
    if menu_order is not None:
        payload["menu_order"] = menu_order

    return client.post("pages", data=payload)


def update_page(client, page_id, **fields):
    """Update an existing page.

    Args:
        client: WPApiClient instance.
        page_id: Page ID to update.
        **fields: Fields to update.

    Returns:
        Updated page dict from API response.

    Raises:
        ValueError: If no fields provided or page_id is invalid.
    """
    _validate_page_id(page_id)

    if not fields:
        raise ValueError(
            "No fields to update. Specify at least one of: "
            "--title, --content, --status, --slug, --parent"
        )

    return client.post(f"pages/{page_id}", data=fields)


def delete_page(client, page_id, force=False):
    """Delete a page.

    Args:
        client: WPApiClient instance.
        page_id: Page ID to delete.
        force: If True, permanently delete. If False, move to trash.

    Returns:
        Deletion response dict from API.
    """
    _validate_page_id(page_id)

    params = {}
    if force:
        params["force"] = True

    return client.delete(f"pages/{page_id}", params=params or None)
