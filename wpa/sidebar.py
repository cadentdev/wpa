"""Sidebar listing via WordPress REST API.

Covers `/wp/v2/sidebars` (read-only). Sidebars are registered by classic
themes; a block theme typically reports none. Requires the
`edit_theme_options` capability.
"""

# Maps friendly field names to WordPress REST API response keys
SIDEBAR_FIELDS = {
    "id": "id",
    "name": "name",
    "description": "description",
    "class": "class",
    "status": "status",
}

AVAILABLE_FIELDS = list(SIDEBAR_FIELDS.keys())
DEFAULT_FIELDS = ["id", "name", "status"]


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
        if field not in SIDEBAR_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _extract_sidebar_row(api_sidebar):
    """Convert a WP REST API sidebar object to a flat dict with friendly keys."""
    return {
        friendly: api_sidebar.get(api_key, "")
        for friendly, api_key in SIDEBAR_FIELDS.items()
    }


def list_sidebars(client):
    """Fetch registered sidebars.

    The sidebars endpoint is not paginated — WordPress returns every
    registered sidebar in one response.

    Args:
        client: WPApiClient instance.

    Returns:
        List of sidebar dicts with friendly field names.
    """
    data = client.get("sidebars", params={"context": "edit"})
    if not isinstance(data, list):
        return []
    return [_extract_sidebar_row(s) for s in data]
