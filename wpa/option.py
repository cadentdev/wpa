"""Site settings management via WordPress REST API.

Covers `/wp/v2/settings` — a single settings object, not a collection.
Only options registered with `show_in_rest=true` are exposed: core settings
like `title`, `description`, `timezone`, `posts_per_page`, plus whatever
plugins register. Unlike wp-cli's `wp option`, arbitrary `wp_options` rows
are not reachable. Requires the `manage_options` capability.
"""

import json
import re

_SETTING_NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")

# The settings object is flat name→value; rows are synthesized client-side.
OPTION_FIELDS = {
    "name": "name",
    "value": "value",
}

AVAILABLE_FIELDS = list(OPTION_FIELDS.keys())
DEFAULT_FIELDS = ["name", "value"]


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
        if field not in OPTION_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _validate_setting_name(name):
    """Reject setting names that aren't plain identifiers."""
    if not isinstance(name, str) or not _SETTING_NAME_RE.match(name):
        raise ValueError(f"Invalid setting name: {name!r}")


def _parse_value(value):
    """Interpret a CLI value string as JSON when possible.

    "20" round-trips as an integer, "true" as a boolean, "null" as None,
    and '"20"' as the literal string "20". Anything that isn't valid JSON
    is passed through as a plain string.
    """
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _fetch_settings(client):
    """GET the settings object, normalized to a dict."""
    data = client.get("settings", params=None)
    if not isinstance(data, dict):
        return {}
    return data


def _unknown_setting_error(name, settings):
    """Build the honest-boundaries error for a name the API doesn't expose."""
    return ValueError(
        f"Unknown setting '{name}'. The REST API only exposes options "
        f"registered with show_in_rest=true. Available settings: "
        f"{', '.join(sorted(settings))}"
    )


def list_settings(client):
    """Fetch all registered settings as name/value rows.

    Args:
        client: WPApiClient instance.

    Returns:
        List of {'name': ..., 'value': ...} dicts, sorted by name.
    """
    settings = _fetch_settings(client)
    return [{"name": k, "value": settings[k]} for k in sorted(settings)]


def get_setting(client, name):
    """Get a single registered setting's value.

    Args:
        client: WPApiClient instance.
        name: Setting name (e.g. 'title', 'posts_per_page').

    Returns:
        The setting value (may be any JSON type, including None).

    Raises:
        ValueError: If the name is malformed or not exposed by the API.
    """
    _validate_setting_name(name)
    settings = _fetch_settings(client)
    if name not in settings:
        raise _unknown_setting_error(name, settings)
    return settings[name]


def update_setting(client, name, value):
    """Update a single registered setting.

    The existence check runs before the write so an unregistered name
    fails with a clear explanation instead of WordPress's opaque 400.

    Args:
        client: WPApiClient instance.
        name: Setting name.
        value: New value as a string; JSON-parsed when possible so numbers
            and booleans round-trip typed.

    Returns:
        The updated value as returned by the API.

    Raises:
        ValueError: If the name is malformed or not exposed by the API.
    """
    _validate_setting_name(name)
    settings = _fetch_settings(client)
    if name not in settings:
        raise _unknown_setting_error(name, settings)

    parsed = _parse_value(value)
    data = client.post("settings", data={name: parsed})
    if isinstance(data, dict) and name in data:
        return data[name]
    return parsed
