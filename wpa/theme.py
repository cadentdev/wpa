"""Read-only theme information via WordPress REST API.

Covers `/wp/v2/themes` — list and get only. The REST API does not
expose theme activation, installation, or deletion; those stay out of
scope. Listing every theme requires the `switch_themes` capability;
`status=active` works with lower capabilities.
"""

from wpa.api import build_endpoint

THEME_STATUSES = ("active", "inactive")

# Maps friendly field names to WordPress REST API response keys.
# name/author/description arrive as {raw, rendered} objects and are
# flattened (rendered preferred, raw as fallback).
THEME_FIELDS = {
    "stylesheet": "stylesheet",
    "name": "name",
    "status": "status",
    "version": "version",
    "author": "author",
    "template": "template",
    "description": "description",
    "requires_wp": "requires_wp",
    "requires_php": "requires_php",
}

AVAILABLE_FIELDS = list(THEME_FIELDS.keys())
DEFAULT_FIELDS = ["stylesheet", "name", "status", "version"]


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
        if field not in THEME_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _extract_theme_row(api_theme):
    """Convert a WP REST API theme object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in THEME_FIELDS.items():
        value = api_theme.get(api_key, "")
        if isinstance(value, dict):
            value = value.get("rendered") or value.get("raw", "")
        row[friendly] = value
    return row


def _theme_endpoint(stylesheet):
    """Build the validated endpoint for a single theme.

    Stylesheets are usually a bare slug, but child themes on some hosts
    live in subdirectories (`parent/child`); each segment is validated
    via build_endpoint.
    """
    parts = stylesheet.split("/") if stylesheet else []
    if not parts or not all(parts):
        raise ValueError(f"Invalid theme stylesheet: {stylesheet!r}")
    try:
        return build_endpoint("themes", *parts)
    except ValueError:
        raise ValueError(f"Invalid theme stylesheet: {stylesheet!r}") from None


def list_themes(client, status=None):
    """Fetch installed themes, optionally filtered by status.

    The themes collection is not paginated. Listing all themes requires
    `switch_themes`; a lower-capability user can still request
    `status=active`.

    Args:
        client: WPApiClient instance.
        status: 'active', 'inactive', or None for all.

    Returns:
        List of theme dicts with friendly field names.

    Raises:
        ValueError: If status is not a valid theme status.
    """
    params = {"context": "edit"}
    if status:
        if status not in THEME_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. "
                f"Valid statuses: {', '.join(THEME_STATUSES)}"
            )
        params["status"] = status
    data = client.get("themes", params=params)
    if not isinstance(data, list):
        return []
    return [_extract_theme_row(t) for t in data]


def get_theme(client, stylesheet):
    """Get a single installed theme by stylesheet (e.g. 'twentytwentyfive')."""
    endpoint = _theme_endpoint(stylesheet)
    data = client.get(endpoint, params={"context": "edit"})
    return _extract_theme_row(data)
