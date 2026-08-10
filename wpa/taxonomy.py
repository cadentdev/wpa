"""Registered taxonomy introspection via WordPress REST API.

Covers `/wp/v2/taxonomies` — read-only. The list endpoint returns a
slug-keyed object (not an array) and is not paginated, like
menu-locations. Complements `wpa term`: `taxonomy list` shows which
slugs `term --taxonomy` accepts on a given site.
"""

from wpa.api import build_endpoint

# Maps friendly field names to WordPress REST API response keys.
# `types` (the object types a taxonomy attaches to) arrives as a list
# and is joined for display.
TAXONOMY_FIELDS = {
    "slug": "slug",
    "name": "name",
    "description": "description",
    "hierarchical": "hierarchical",
    "rest_base": "rest_base",
    "types": "types",
}

AVAILABLE_FIELDS = list(TAXONOMY_FIELDS.keys())
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
        if field not in TAXONOMY_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _extract_taxonomy_row(api_taxonomy):
    """Convert a WP REST API taxonomy object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in TAXONOMY_FIELDS.items():
        value = api_taxonomy.get(api_key, "")
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        row[friendly] = value
    return row


def list_taxonomies(client):
    """Fetch registered taxonomies.

    The REST API returns an object keyed by taxonomy slug; rows are
    synthesized and sorted by slug.

    Args:
        client: WPApiClient instance.

    Returns:
        List of taxonomy dicts with friendly field names.
    """
    data = client.get("taxonomies", params={"context": "edit"})
    if not isinstance(data, dict):
        return []
    return [
        _extract_taxonomy_row(data[key])
        for key in sorted(data)
        if isinstance(data[key], dict)
    ]


def get_taxonomy(client, slug):
    """Get a single registered taxonomy by slug (e.g. 'category')."""
    try:
        endpoint = build_endpoint("taxonomies", slug)
    except ValueError:
        raise ValueError(f"Invalid taxonomy slug: {slug!r}") from None
    data = client.get(endpoint, params={"context": "edit"})
    return _extract_taxonomy_row(data)
