"""Post CRUD operations via WordPress REST API."""

# Maps friendly field names to WordPress REST API response keys
POST_FIELDS = {
    "id": "id",
    "title": "title",
    "status": "status",
    "date": "date",
    "author": "author",
    "slug": "slug",
    "excerpt": "excerpt",
    "content": "content",
    "categories": "categories",
    "tags": "tags",
    "featured_media": "featured_media",
    "format": "format",
    "link": "link",
    "modified": "modified",
}

AVAILABLE_FIELDS = list(POST_FIELDS.keys())
DEFAULT_FIELDS = ["id", "title", "status", "date", "author"]


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
        if field not in POST_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _validate_post_id(post_id):
    """Validate post_id is a positive integer.

    Raises:
        ValueError: If post_id is not a positive integer.
    """
    if (
        isinstance(post_id, bool)
        or not isinstance(post_id, int)
        or post_id < 1
    ):
        raise ValueError(f"Invalid post ID: {post_id}")


def _extract_rendered(value):
    """Extract rendered content from WP API response fields.

    The API returns title, content, excerpt as {"rendered": "...", "raw": "..."}.
    This extracts the rendered string for display.
    """
    if isinstance(value, dict):
        return value.get("rendered", str(value))
    return value


def _extract_post_row(api_post):
    """Convert a WP REST API post object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in POST_FIELDS.items():
        value = api_post.get(api_key, "")
        if friendly in ("title", "content", "excerpt"):
            value = _extract_rendered(value)
        if friendly == "categories" and isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        if friendly == "tags" and isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        row[friendly] = value
    return row


def list_posts(
    client,
    status=None,
    author=None,
    search=None,
    per_page=10,
    page=None,
    orderby=None,
    order=None,
    category=None,
    tag=None,
):
    """Fetch posts from WordPress REST API.

    Args:
        client: WPApiClient instance.
        status: Filter by post status (draft, publish, etc.).
        author: Filter by author ID.
        search: Search term.
        per_page: Results per page (default 10, max 100).
        page: Specific page number (fetches single page).
        orderby: Sort field (date, title, id, etc.).
        order: Sort order (asc, desc).
        category: Filter by category ID.
        tag: Filter by tag ID.

    Returns:
        List of post dicts with friendly field names.
    """
    params = {"context": "edit"}
    if status:
        params["status"] = status
    if author is not None:
        params["author"] = author
    if search:
        params["search"] = search
    if per_page is not None:
        params["per_page"] = per_page
    if page is not None:
        params["page"] = page
    if orderby:
        params["orderby"] = orderby
    if order:
        params["order"] = order
    if category is not None:
        params["categories"] = category
    if tag is not None:
        params["tags"] = tag

    if page is not None:
        # Single page request — use get() not get_list()
        items = client.get("posts", params=params)
        if not isinstance(items, list):
            return []
        return [_extract_post_row(p) for p in items]

    return [_extract_post_row(p) for p in client.get_list("posts", params=params)]


def get_post(client, post_id, embed=False):
    """Get a single post by ID.

    Args:
        client: WPApiClient instance.
        post_id: Post ID.
        embed: Include linked resources (_embed parameter).

    Returns:
        Post dict with friendly field names.
    """
    _validate_post_id(post_id)
    params = {"context": "edit"}
    if embed:
        params["_embed"] = True
    data = client.get(f"posts/{post_id}", params=params)
    return _extract_post_row(data)


def create_post(
    client,
    title,
    content="",
    status="draft",
    slug=None,
    author=None,
    categories=None,
    tags=None,
    featured_media=None,
):
    """Create a new post.

    Args:
        client: WPApiClient instance.
        title: Post title.
        content: Post content (HTML).
        status: Post status (default: draft).
        slug: URL slug.
        author: Author user ID.
        categories: List of category IDs.
        tags: List of tag IDs.
        featured_media: Featured image media ID.

    Returns:
        Created post dict from API response.
    """
    payload = {
        "title": title,
        "content": content,
        "status": status,
    }
    if slug:
        payload["slug"] = slug
    if author is not None:
        payload["author"] = author
    if categories:
        payload["categories"] = categories
    if tags:
        payload["tags"] = tags
    if featured_media is not None:
        payload["featured_media"] = featured_media

    return client.post("posts", data=payload)


def update_post(client, post_id, **fields):
    """Update an existing post.

    Args:
        client: WPApiClient instance.
        post_id: Post ID to update.
        **fields: Fields to update (title, content, status, slug, etc.).

    Returns:
        Updated post dict from API response.

    Raises:
        ValueError: If no fields provided or post_id is invalid.
    """
    _validate_post_id(post_id)

    if not fields:
        raise ValueError(
            "No fields to update. Specify at least one of: "
            "--title, --content, --status, --slug, --author"
        )

    return client.post(f"posts/{post_id}", data=fields)


def delete_post(client, post_id, force=False):
    """Delete a post.

    Args:
        client: WPApiClient instance.
        post_id: Post ID to delete.
        force: If True, permanently delete. If False, move to trash.

    Returns:
        Deletion response dict from API.
    """
    _validate_post_id(post_id)

    params = {}
    if force:
        params["force"] = True

    return client.delete(f"posts/{post_id}", params=params or None)
