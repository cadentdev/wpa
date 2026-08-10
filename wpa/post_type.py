"""Registered post type introspection via WordPress REST API.

Covers `/wp/v2/types` — read-only. The list endpoint returns a
slug-keyed object (not an array) and is not paginated, like
menu-locations. The command name is `post-type`, following wp-cli.
"""

from wpa.api import build_endpoint

# Maps friendly field names to WordPress REST API response keys.
# `taxonomies` (the taxonomies attached to a post type) arrives as a
# list and is joined for display.
POST_TYPE_FIELDS = {
    "slug": "slug",
    "name": "name",
    "description": "description",
    "hierarchical": "hierarchical",
    "rest_base": "rest_base",
    "taxonomies": "taxonomies",
}

AVAILABLE_FIELDS = list(POST_TYPE_FIELDS.keys())
DEFAULT_FIELDS = ["slug", "name", "hierarchical", "rest_base"]


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
        if field not in POST_TYPE_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _extract_post_type_row(api_post_type):
    """Convert a WP REST API type object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in POST_TYPE_FIELDS.items():
        value = api_post_type.get(api_key, "")
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        row[friendly] = value
    return row


def list_post_types(client):
    """Fetch registered post types.

    The REST API returns an object keyed by post type slug; rows are
    synthesized and sorted by slug.

    Args:
        client: WPApiClient instance.

    Returns:
        List of post type dicts with friendly field names.
    """
    data = client.get("types", params={"context": "edit"})
    if not isinstance(data, dict):
        return []
    return [
        _extract_post_type_row(data[key])
        for key in sorted(data)
        if isinstance(data[key], dict)
    ]


def get_post_type(client, slug):
    """Get a single registered post type by slug (e.g. 'post')."""
    try:
        endpoint = build_endpoint("types", slug)
    except ValueError:
        raise ValueError(f"Invalid post type slug: {slug!r}") from None
    data = client.get(endpoint, params={"context": "edit"})
    return _extract_post_type_row(data)
