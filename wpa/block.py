"""Registered block type introspection via WordPress REST API.

Covers `/wp/v2/block-types` — read-only. Sites register hundreds of
blocks, so default fields stay narrow; use `--namespace` to scope the
listing. Block names are namespaced (`core/paragraph`), so `get` takes
exactly two path segments. Requires the `edit_posts` capability.
"""

from wpa.api import build_endpoint

# Maps friendly field names to WordPress REST API response keys.
# `keywords` arrives as a list and is joined for display.
BLOCK_FIELDS = {
    "name": "name",
    "title": "title",
    "category": "category",
    "description": "description",
    "keywords": "keywords",
    "api_version": "api_version",
}

AVAILABLE_FIELDS = list(BLOCK_FIELDS.keys())
DEFAULT_FIELDS = ["name", "title", "category"]


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
        if field not in BLOCK_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _extract_block_row(api_block):
    """Convert a WP REST API block type object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in BLOCK_FIELDS.items():
        value = api_block.get(api_key, "")
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        row[friendly] = value
    return row


def _block_endpoint(name):
    """Build the validated endpoint for a single block type.

    Block names are namespaced (`core/paragraph`); each segment is
    validated via build_endpoint so nothing can escape the path.
    """
    parts = name.split("/") if name else []
    if len(parts) != 2 or not all(parts):
        raise ValueError(
            f"Invalid block name: {name!r} "
            "(expected namespace/name, e.g. core/paragraph)"
        )
    try:
        return build_endpoint("block-types", *parts)
    except ValueError:
        raise ValueError(f"Invalid block name: {name!r}") from None


def list_blocks(client, namespace=None):
    """Fetch registered block types, optionally scoped to one namespace.

    Args:
        client: WPApiClient instance.
        namespace: Block namespace to filter by (e.g. 'core'), or None.

    Returns:
        List of block type dicts with friendly field names.
    """
    params = {"context": "edit"}
    if namespace:
        params["namespace"] = namespace
    data = client.get("block-types", params=params)
    if not isinstance(data, list):
        return []
    return [_extract_block_row(b) for b in data]


def get_block(client, name):
    """Get a single registered block type by namespaced name."""
    endpoint = _block_endpoint(name)
    data = client.get(endpoint, params={"context": "edit"})
    return _extract_block_row(data)
