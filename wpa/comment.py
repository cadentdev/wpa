"""Comment CRUD and moderation operations via WordPress REST API."""

from wpa.post import _extract_rendered

# Maps friendly field names to WordPress REST API response keys
COMMENT_FIELDS = {
    "id": "id",
    "post": "post",
    "parent": "parent",
    "author": "author",
    "author_name": "author_name",
    "author_email": "author_email",
    "author_url": "author_url",
    "date": "date",
    "status": "status",
    "content": "content",
    "type": "type",
    "link": "link",
}

AVAILABLE_FIELDS = list(COMMENT_FIELDS.keys())
DEFAULT_FIELDS = ["id", "post", "author_name", "status", "date"]


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
        if field not in COMMENT_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _validate_comment_id(comment_id):
    """Validate comment_id is a positive integer.

    Raises:
        ValueError: If comment_id is not a positive integer.
    """
    if (
        not isinstance(comment_id, int)
        or isinstance(comment_id, bool)
        or comment_id < 1
    ):
        raise ValueError(f"Invalid comment ID: {comment_id}")


def _validate_post_id(post_id):
    """Validate post_id is a positive integer.

    Raises:
        ValueError: If post_id is not a positive integer.
    """
    if not isinstance(post_id, int) or isinstance(post_id, bool) or post_id < 1:
        raise ValueError(f"Invalid post ID: {post_id}")


def _extract_comment_row(api_comment):
    """Convert a WP REST API comment object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in COMMENT_FIELDS.items():
        value = api_comment.get(api_key, "")
        if friendly == "content":
            value = _extract_rendered(value)
        row[friendly] = value
    return row


def list_comments(
    client,
    post=None,
    status=None,
    parent=None,
    author_email=None,
    search=None,
    per_page=10,
    page=None,
    orderby=None,
    order=None,
):
    """Fetch comments from WordPress REST API.

    Args:
        client: WPApiClient instance.
        post: Filter by post ID.
        status: Filter by comment status (approved, hold, spam, trash).
        parent: Filter by parent comment ID.
        author_email: Filter by author email.
        search: Search term.
        per_page: Results per page (default 10, max 100).
        page: Specific page number (fetches single page).
        orderby: Sort field (date, id, etc.).
        order: Sort order (asc, desc).

    Returns:
        List of comment dicts with friendly field names.
    """
    params = {"context": "edit"}
    if post is not None:
        params["post"] = post
    if status:
        # WordPress REST API is asymmetric on comment status: responses
        # serialize it as 'approved' (past tense) but the /comments list
        # query param only accepts 'approve' (imperative). Passing
        # 'approved' verbatim returns zero rows even when approved
        # comments exist. Normalize here so callers can pass either form.
        params["status"] = "approve" if status == "approved" else status
    if parent is not None:
        params["parent"] = parent
    if author_email:
        params["author_email"] = author_email
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

    if page is not None:
        items = client.get("comments", params=params)
        if not isinstance(items, list):
            return []
        return [_extract_comment_row(c) for c in items]

    return [_extract_comment_row(c) for c in client.get_list("comments", params=params)]


def get_comment(client, comment_id):
    """Get a single comment by ID.

    Args:
        client: WPApiClient instance.
        comment_id: Comment ID.

    Returns:
        Comment dict with friendly field names.
    """
    _validate_comment_id(comment_id)
    data = client.get(f"comments/{comment_id}", params={"context": "edit"})
    return _extract_comment_row(data)


def create_comment(
    client,
    post,
    content,
    author_name=None,
    author_email=None,
    parent=None,
    status=None,
):
    """Create a new comment.

    Args:
        client: WPApiClient instance.
        post: Post ID being commented on.
        content: Comment body.
        author_name: Comment author display name.
        author_email: Comment author email.
        parent: Parent comment ID for threaded replies.
        status: Comment status (approved, hold, spam).

    Returns:
        Created comment dict from API response.

    Raises:
        ValueError: If post is invalid or content is empty.
    """
    _validate_post_id(post)
    if not content:
        raise ValueError("Comment content cannot be empty.")

    payload = {
        "post": post,
        "content": content,
    }
    if author_name is not None:
        payload["author_name"] = author_name
    if author_email is not None:
        payload["author_email"] = author_email
    if parent is not None:
        payload["parent"] = parent
    if status is not None:
        payload["status"] = status

    return client.post("comments", data=payload)


def update_comment(client, comment_id, **fields):
    """Update an existing comment.

    Args:
        client: WPApiClient instance.
        comment_id: Comment ID to update.
        **fields: Fields to update (content, status, author_name, etc.).

    Returns:
        Updated comment dict from API response.

    Raises:
        ValueError: If no fields provided or comment_id is invalid.
    """
    _validate_comment_id(comment_id)

    if not fields:
        raise ValueError(
            "No fields to update. Specify at least one of: "
            "--content, --status, --author-name, --author-email"
        )

    return client.post(f"comments/{comment_id}", data=fields)


def delete_comment(client, comment_id, force=False):
    """Delete a comment.

    Args:
        client: WPApiClient instance.
        comment_id: Comment ID to delete.
        force: If True, permanently delete. If False, move to trash.

    Returns:
        Deletion response dict from API.
    """
    _validate_comment_id(comment_id)

    params = {}
    if force:
        params["force"] = True

    return client.delete(f"comments/{comment_id}", params=params or None)


def approve_comment(client, comment_id):
    """Approve a comment (set status to 'approved')."""
    _validate_comment_id(comment_id)
    return client.post(f"comments/{comment_id}", data={"status": "approved"})


def unapprove_comment(client, comment_id):
    """Unapprove a comment (set status to 'hold')."""
    _validate_comment_id(comment_id)
    return client.post(f"comments/{comment_id}", data={"status": "hold"})


def spam_comment(client, comment_id):
    """Mark a comment as spam."""
    _validate_comment_id(comment_id)
    return client.post(f"comments/{comment_id}", data={"status": "spam"})


def unspam_comment(client, comment_id):
    """Restore a spammed comment to 'approved'."""
    _validate_comment_id(comment_id)
    return client.post(f"comments/{comment_id}", data={"status": "approved"})


def trash_comment(client, comment_id):
    """Move a comment to trash (DELETE without force)."""
    return delete_comment(client, comment_id, force=False)
