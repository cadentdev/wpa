"""Media CRUD operations via WordPress REST API."""

import mimetypes
import os

# Maps friendly field names to WordPress REST API response keys
MEDIA_FIELDS = {
    "id": "id",
    "title": "title",
    "date": "date",
    "mime_type": "mime_type",
    "media_type": "media_type",
    "alt_text": "alt_text",
    "caption": "caption",
    "description": "description",
    "source_url": "source_url",
    "post": "post",
    "author": "author",
    "link": "link",
}

AVAILABLE_FIELDS = list(MEDIA_FIELDS.keys())
DEFAULT_FIELDS = ["id", "title", "mime_type", "date", "source_url"]


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
        if field not in MEDIA_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _validate_media_id(media_id):
    """Validate media_id is a positive integer.

    Raises:
        ValueError: If media_id is not a positive integer.
    """
    if not isinstance(media_id, int) or media_id < 1:
        raise ValueError(f"Invalid media ID: {media_id}")


def _extract_rendered(value):
    """Extract rendered content from WP API response fields.

    The API returns title, caption, description as {"rendered": "...", "raw": "..."}.
    This extracts the rendered string for display.
    """
    if isinstance(value, dict):
        return value.get("rendered", str(value))
    return value


def _extract_media_row(api_media):
    """Convert a WP REST API media object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in MEDIA_FIELDS.items():
        value = api_media.get(api_key, "")
        if friendly in ("title", "caption", "description"):
            value = _extract_rendered(value)
        row[friendly] = value
    return row


def list_media(
    client,
    media_type=None,
    mime_type=None,
    search=None,
    per_page=10,
    page=None,
    orderby=None,
    order=None,
):
    """Fetch media from WordPress REST API.

    Args:
        client: WPApiClient instance.
        media_type: Filter by media type (image, video, audio, application).
        mime_type: Filter by MIME type (e.g., image/jpeg).
        search: Search term.
        per_page: Results per page (default 10, max 100).
        page: Specific page number (fetches single page).
        orderby: Sort field (date, title, id, etc.).
        order: Sort order (asc, desc).

    Returns:
        List of media dicts with friendly field names.
    """
    params = {"context": "edit"}
    if media_type:
        params["media_type"] = media_type
    if mime_type:
        params["mime_type"] = mime_type
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
        items = client.get("media", params=params)
        if not isinstance(items, list):
            return []
        return [_extract_media_row(m) for m in items]

    return [_extract_media_row(m) for m in client.get_list("media", params=params)]


def get_media(client, media_id):
    """Get a single media item by ID.

    Args:
        client: WPApiClient instance.
        media_id: Media ID.

    Returns:
        Media dict with friendly field names.
    """
    _validate_media_id(media_id)
    params = {"context": "edit"}
    data = client.get(f"media/{media_id}", params=params)
    return _extract_media_row(data)


def import_media(
    client,
    file_path,
    title=None,
    alt_text=None,
    caption=None,
    description=None,
    post=None,
):
    """Upload a local file as a WordPress media attachment.

    Args:
        client: WPApiClient instance.
        file_path: Path to the local file to upload.
        title: Optional media title (defaults to filename without extension).
        alt_text: Optional alt text for images.
        caption: Optional caption.
        description: Optional description.
        post: Optional parent post ID.

    Returns:
        Created media dict from API response.

    Raises:
        FileNotFoundError: If file_path does not exist.
        ValueError: If file_path is not a file.
    """
    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if not os.path.isfile(file_path):
        raise ValueError(f"Not a file: {file_path}")

    filename = os.path.basename(file_path)
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    with open(file_path, "rb") as f:
        files = {"file": (filename, f, content_type)}

        # Build form data for metadata
        data = {}
        if title is not None:
            data["title"] = title
        if alt_text is not None:
            data["alt_text"] = alt_text
        if caption is not None:
            data["caption"] = caption
        if description is not None:
            data["description"] = description
        if post is not None:
            data["post"] = post

        return client.post("media", files=files, data=data)


def delete_media(client, media_id, force=False):
    """Delete a media attachment.

    Args:
        client: WPApiClient instance.
        media_id: Media ID to delete.
        force: If True, permanently delete. If False, move to trash.

    Returns:
        Deletion response dict from API.
    """
    _validate_media_id(media_id)

    params = {}
    if force:
        params["force"] = True

    return client.delete(f"media/{media_id}", params=params or None)
