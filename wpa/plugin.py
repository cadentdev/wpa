"""Plugin management via WordPress REST API.

Covers `/wp/v2/plugins` — list, get, activate, deactivate. Requires an
authenticated user with the `activate_plugins` capability (administrator on
most installs). Install/delete are deliberately not implemented yet (#41
defers them to follow-up issues).
"""

from wpa.api import build_endpoint

# Plugin identifiers are "folder/file" (e.g. "akismet/akismet") or a bare
# slug for single-file plugins. wp-cli also accepts "folder/file.php"; the
# REST API wants the identifier without the extension.
PLUGIN_STATUSES = ("active", "inactive")

# Maps friendly field names to WordPress REST API response keys
PLUGIN_FIELDS = {
    "plugin": "plugin",
    "name": "name",
    "status": "status",
    "version": "version",
    "author": "author",
    "description": "description",
    "requires_wp": "requires_wp",
    "requires_php": "requires_php",
    "network_only": "network_only",
    "auto_update": "auto_update",
}

AVAILABLE_FIELDS = list(PLUGIN_FIELDS.keys())
DEFAULT_FIELDS = ["plugin", "name", "status", "version"]


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
        if field not in PLUGIN_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def normalize_plugin_id(plugin_id):
    """Normalize a plugin identifier to the REST API's expected shape.

    Accepts "folder/file", "folder/file.php" (wp-cli convention), or a bare
    slug for single-file plugins, and validates each path segment so an
    identifier sourced from user input can never smuggle traversal into the
    endpoint.

    Args:
        plugin_id: Plugin identifier string.

    Returns:
        Normalized identifier (e.g. 'akismet/akismet' or 'hello').

    Raises:
        ValueError: If the identifier is empty, has more than two segments,
            or any segment is invalid.
    """
    if not isinstance(plugin_id, str) or not plugin_id:
        raise ValueError(f"Invalid plugin identifier: {plugin_id!r}")

    plugin_id = plugin_id.removesuffix(".php")

    segments = plugin_id.split("/")
    if len(segments) > 2:
        raise ValueError(f"Invalid plugin identifier: {plugin_id!r}")

    # build_endpoint validates each segment (slug shape, no traversal) and
    # raises ValueError mentioning the offending segment; re-raise with the
    # plugin framing callers expect.
    try:
        build_endpoint(*segments)
    except ValueError:
        raise ValueError(f"Invalid plugin identifier: {plugin_id!r}") from None

    return "/".join(segments)


def _plugin_endpoint(plugin_id):
    """Build the validated endpoint for a single plugin."""
    normalized = normalize_plugin_id(plugin_id)
    return build_endpoint("plugins", *normalized.split("/"))


def _extract_plugin_row(api_plugin):
    """Convert a WP REST API plugin object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in PLUGIN_FIELDS.items():
        value = api_plugin.get(api_key, "")
        if friendly == "description" and isinstance(value, dict):
            value = value.get("raw", "")
        row[friendly] = value
    return row


def list_plugins(client, status=None, search=None):
    """Fetch installed plugins.

    Note: `/wp/v2/plugins` is not paginated — WordPress returns every
    installed plugin in one response, so there is no per_page handling.

    Args:
        client: WPApiClient instance.
        status: Filter by 'active' or 'inactive'; 'all' or None for no filter.
        search: Search installed plugins' metadata.

    Returns:
        List of plugin dicts with friendly field names.

    Raises:
        ValueError: If status is not one of active, inactive, all.
    """
    params = {"context": "edit"}
    if status is not None and status != "all":
        if status not in PLUGIN_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. "
                f"Must be one of: {', '.join(PLUGIN_STATUSES)}, all"
            )
        params["status"] = status
    if search:
        params["search"] = search

    data = client.get("plugins", params=params)
    if not isinstance(data, list):
        return []
    return [_extract_plugin_row(p) for p in data]


def get_plugin(client, plugin_id):
    """Get a single installed plugin.

    Args:
        client: WPApiClient instance.
        plugin_id: Plugin identifier ('folder/file', 'folder/file.php',
            or bare slug).

    Returns:
        Plugin dict with friendly field names.
    """
    endpoint = _plugin_endpoint(plugin_id)
    data = client.get(endpoint, params={"context": "edit"})
    return _extract_plugin_row(data)


def update_plugin(client, plugin_id, status):
    """Set a plugin's activation status.

    Args:
        client: WPApiClient instance.
        plugin_id: Plugin identifier.
        status: 'active' or 'inactive'.

    Returns:
        Updated plugin dict with friendly field names.

    Raises:
        ValueError: If status is invalid or the identifier is malformed.
    """
    if status not in PLUGIN_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(PLUGIN_STATUSES)}"
        )
    endpoint = _plugin_endpoint(plugin_id)
    data = client.post(endpoint, data={"status": status})
    return _extract_plugin_row(data)


def activate_plugin(client, plugin_id):
    """Activate an installed plugin (shortcut for status='active')."""
    return update_plugin(client, plugin_id, status="active")


def deactivate_plugin(client, plugin_id):
    """Deactivate an installed plugin (shortcut for status='inactive')."""
    return update_plugin(client, plugin_id, status="inactive")
