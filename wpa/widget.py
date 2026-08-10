"""Classic widget management via WordPress REST API.

Covers `/wp/v2/widgets` — list, get, update (move/reconfigure), delete,
and a wp-cli-style `deactivate` (move to the inactive sidebar). Block
themes manage widgets as blocks, so these endpoints typically return
nothing there. Requires the `edit_theme_options` capability.

Widget *creation* is deliberately not implemented: each widget type has
its own instance schema (discoverable only via `/wp/v2/widget-types`),
which makes a generic `widget add` an exercise in guessing serialized
PHP shapes. Descoped per #62; revisit if a concrete use case appears.
"""

import json

from wpa.api import build_endpoint

# WordPress's holding pen for widgets removed from live sidebars.
INACTIVE_SIDEBAR = "wp_inactive_widgets"

# Maps friendly field names to WordPress REST API response keys.
# `status` is synthesized from the sidebar (the API has no status field);
# `instance` is flattened to its raw settings dict so `widget get` shows
# the current config that `update --instance-json` would replace.
WIDGET_FIELDS = {
    "id": "id",
    "id_base": "id_base",
    "sidebar": "sidebar",
    "status": None,
    "instance": "instance",
}

AVAILABLE_FIELDS = list(WIDGET_FIELDS.keys())
DEFAULT_FIELDS = ["id", "id_base", "sidebar", "status"]


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
        if field not in WIDGET_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _widget_endpoint(widget_id):
    """Build the validated endpoint for a single widget.

    Widget IDs are slugs like 'recent-posts-3'; build_endpoint's segment
    validation rejects anything that could escape the path.
    """
    try:
        return build_endpoint("widgets", widget_id)
    except ValueError:
        raise ValueError(f"Invalid widget ID: {widget_id!r}") from None


def _extract_widget_row(api_widget):
    """Convert a WP REST API widget object to a flat dict with friendly keys."""
    sidebar = api_widget.get("sidebar", "")
    row = {}
    for friendly, api_key in WIDGET_FIELDS.items():
        if friendly == "status":
            row[friendly] = "inactive" if sidebar == INACTIVE_SIDEBAR else "active"
            continue
        value = api_widget.get(api_key, "")
        if friendly == "instance" and isinstance(value, dict):
            value = value.get("raw", "")
        row[friendly] = value
    return row


def list_widgets(client, sidebar=None):
    """Fetch widgets, optionally filtered to one sidebar.

    The widgets endpoint is not paginated — WordPress returns every widget
    in one response.

    Args:
        client: WPApiClient instance.
        sidebar: Sidebar ID to filter by (e.g. 'sidebar-1'), or None.

    Returns:
        List of widget dicts with friendly field names.
    """
    params = {"context": "edit"}
    if sidebar:
        params["sidebar"] = sidebar
    data = client.get("widgets", params=params)
    if not isinstance(data, list):
        return []
    return [_extract_widget_row(w) for w in data]


def get_widget(client, widget_id):
    """Get a single widget by ID (e.g. 'recent-posts-3')."""
    endpoint = _widget_endpoint(widget_id)
    data = client.get(endpoint, params={"context": "edit"})
    return _extract_widget_row(data)


def update_widget(client, widget_id, sidebar=None, instance_json=None):
    """Move a widget between sidebars and/or update its instance settings.

    Args:
        client: WPApiClient instance.
        widget_id: Widget ID.
        sidebar: Target sidebar ID (moves the widget), or None.
        instance_json: JSON object string of instance settings, or None.

    Returns:
        Updated widget dict from API response.

    Raises:
        ValueError: If neither field is given, or instance_json is not a
            valid JSON object.
    """
    endpoint = _widget_endpoint(widget_id)

    payload = {}
    if sidebar:
        payload["sidebar"] = sidebar
    if instance_json is not None:
        try:
            instance = json.loads(instance_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"--instance-json is not valid JSON: {e}") from None
        if not isinstance(instance, dict):
            raise ValueError("--instance-json must be a JSON object.")
        payload["instance"] = {"raw": instance}

    if not payload:
        raise ValueError(
            "No fields to update. Specify --sidebar and/or --instance-json."
        )

    return client.post(endpoint, data=payload)


def deactivate_widget(client, widget_id):
    """Move a widget to the inactive sidebar (wp-cli parity).

    The widget keeps its settings and can be moved back with
    `update_widget(..., sidebar=...)`.
    """
    endpoint = _widget_endpoint(widget_id)
    return client.post(endpoint, data={"sidebar": INACTIVE_SIDEBAR})


def delete_widget(client, widget_id, force=False):
    """Delete a widget.

    Without force, WordPress moves the widget to the inactive sidebar
    (settings preserved). With force, the widget is removed entirely.

    Args:
        client: WPApiClient instance.
        widget_id: Widget ID.
        force: Remove entirely instead of moving to inactive.

    Returns:
        Deletion response dict from API.
    """
    endpoint = _widget_endpoint(widget_id)
    params = {"force": True} if force else {}
    return client.delete(endpoint, params=params)
