"""Navigation menu management via WordPress REST API.

Covers `/wp/v2/menus`, `/wp/v2/menu-items`, and `/wp/v2/menu-locations`
(classic nav menus; block themes typically have none). All three require
the `edit_theme_options` capability.

Menu items are structure, not content, so creation follows wp-cli parity
and publishes immediately — the "default draft" convention applies to
content creation only.
"""

from wpa.api import build_endpoint

# Objects that hang off taxonomies rather than post types, for the
# type-inference in create_menu_item. Custom taxonomies must pass an
# explicit item_type; these two cover the built-ins.
_TAXONOMY_OBJECTS = {"category", "post_tag"}

# Maps friendly field names to WordPress REST API response keys
MENU_FIELDS = {
    "id": "id",
    "name": "name",
    "slug": "slug",
    "description": "description",
    "locations": "locations",
    "auto_add": "auto_add",
}

ITEM_FIELDS = {
    "id": "id",
    "title": "title",
    "status": "status",
    "url": "url",
    "type": "type",
    "object": "object",
    "object_id": "object_id",
    "parent": "parent",
    "menu_order": "menu_order",
    "menus": "menus",
}

LOCATION_FIELDS = {
    "name": "name",
    "description": "description",
    "menu": "menu",
}

MENU_AVAILABLE_FIELDS = list(MENU_FIELDS.keys())
MENU_DEFAULT_FIELDS = ["id", "name", "slug", "locations"]

ITEM_AVAILABLE_FIELDS = list(ITEM_FIELDS.keys())
ITEM_DEFAULT_FIELDS = ["id", "title", "type", "url", "menu_order"]

LOCATION_AVAILABLE_FIELDS = list(LOCATION_FIELDS.keys())
LOCATION_DEFAULT_FIELDS = ["name", "description", "menu"]


def _make_validate_fields(field_map, available):
    def validate(fields_str, defaults):
        if fields_str is None:
            return defaults
        fields = [f.strip() for f in fields_str.split(",")]
        for field in fields:
            if field not in field_map:
                raise ValueError(
                    f"Unknown field '{field}'. Available fields: {', '.join(available)}"
                )
        return fields

    return validate


_validate_menu = _make_validate_fields(MENU_FIELDS, MENU_AVAILABLE_FIELDS)
_validate_item = _make_validate_fields(ITEM_FIELDS, ITEM_AVAILABLE_FIELDS)


def validate_menu_fields(fields_str):
    """Validate a --fields string for menu listings."""
    return _validate_menu(fields_str, MENU_DEFAULT_FIELDS)


def validate_item_fields(fields_str):
    """Validate a --fields string for menu-item listings."""
    return _validate_item(fields_str, ITEM_DEFAULT_FIELDS)


def _validate_id(value, label):
    """Validate an ID is a positive integer."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"Invalid {label}: {value}")


def _extract_row(api_obj, field_map):
    """Convert an API object to a flat dict, flattening rendered titles."""
    row = {}
    for friendly, api_key in field_map.items():
        value = api_obj.get(api_key, "")
        if friendly == "title" and isinstance(value, dict):
            value = value.get("rendered") or value.get("raw", "")
        row[friendly] = value
    return row


# --- Menus ---


def list_menus(client, search=None):
    """Fetch nav menus.

    Args:
        client: WPApiClient instance.
        search: Optional search term.

    Returns:
        List of menu dicts with friendly field names.
    """
    params = {"context": "edit", "per_page": 100}
    if search:
        params["search"] = search
    return [
        _extract_row(m, MENU_FIELDS) for m in client.get_list("menus", params=params)
    ]


def get_menu(client, menu_id):
    """Get a single nav menu by ID."""
    _validate_id(menu_id, "menu ID")
    data = client.get(build_endpoint("menus", menu_id), params={"context": "edit"})
    return _extract_row(data, MENU_FIELDS)


def create_menu(client, name, description=None):
    """Create a nav menu.

    Args:
        client: WPApiClient instance.
        name: Menu name (required, non-empty).
        description: Optional description.

    Returns:
        Created menu dict from API response.
    """
    if not name:
        raise ValueError("Menu name cannot be empty.")
    payload = {"name": name}
    if description is not None:
        payload["description"] = description
    return client.post("menus", data=payload)


def delete_menu(client, menu_id):
    """Delete a nav menu.

    The REST API requires `force=true` — menus cannot be trashed. Items in
    the menu are deleted with it.
    """
    _validate_id(menu_id, "menu ID")
    return client.delete(build_endpoint("menus", menu_id), params={"force": True})


# --- Menu items ---


def list_menu_items(client, menu=None):
    """Fetch menu items, optionally filtered to one menu.

    Args:
        client: WPApiClient instance.
        menu: Menu ID to filter by, or None for all items.

    Returns:
        List of item dicts with friendly field names (title flattened).
    """
    params = {"context": "edit", "per_page": 100}
    if menu is not None:
        _validate_id(menu, "menu ID")
        params["menus"] = menu
    return [
        _extract_row(i, ITEM_FIELDS)
        for i in client.get_list("menu-items", params=params)
    ]


def create_menu_item(
    client,
    menu,
    title=None,
    url=None,
    object_type=None,
    object_id=None,
    item_type=None,
    parent=None,
    position=None,
):
    """Add an item to a nav menu.

    Two shapes, mirroring wp-cli:
    - Custom link: title + url (type=custom).
    - Object link: object_type + object_id (type inferred: post_type for
      posts/pages/CPTs, taxonomy for category/post_tag; pass item_type to
      override for custom taxonomies).

    Args:
        client: WPApiClient instance.
        menu: Menu ID the item belongs to.
        title: Link text (required for custom links; object links default
            to the object's own title).
        url: Target URL for custom links.
        object_type: REST object slug (page, post, category, post_tag, ...).
        object_id: ID of the linked object.
        item_type: Explicit REST item type, overriding inference.
        parent: Parent item ID for nested menus.
        position: Menu order (1-based).

    Returns:
        Created item dict from API response.

    Raises:
        ValueError: If the argument combination is incomplete.
    """
    _validate_id(menu, "menu ID")

    payload = {"menus": menu}

    if url:
        if not title:
            raise ValueError("Custom link items require a title (--title).")
        payload["type"] = item_type or "custom"
        payload["title"] = title
        payload["url"] = url
    elif object_id is not None:
        if not object_type:
            raise ValueError("Object items require an object type (--object).")
        _validate_id(object_id, "object ID")
        inferred = "taxonomy" if object_type in _TAXONOMY_OBJECTS else "post_type"
        payload["type"] = item_type or inferred
        payload["object"] = object_type
        payload["object_id"] = object_id
        if title:
            payload["title"] = title
    else:
        raise ValueError(
            "Menu items need either a url (custom link) or an "
            "object/object ID pair (--object/--object-id)."
        )

    if parent is not None:
        _validate_id(parent, "parent item ID")
        payload["parent"] = parent
    if position is not None:
        payload["menu_order"] = position

    return client.post("menu-items", data=payload)


def update_menu_item(client, item_id, **fields):
    """Update a menu item.

    Args:
        client: WPApiClient instance.
        item_id: Menu item ID.
        **fields: REST fields to update (title, url, parent, menu_order, ...).

    Returns:
        Updated item dict from API response.

    Raises:
        ValueError: If no fields are provided or the ID is invalid.
    """
    _validate_id(item_id, "menu item ID")
    if not fields:
        raise ValueError(
            "No fields to update. Specify at least one of: "
            "--title, --url, --parent, --position"
        )
    return client.post(build_endpoint("menu-items", item_id), data=fields)


def delete_menu_item(client, item_id):
    """Delete a menu item (force-only; items cannot be trashed)."""
    _validate_id(item_id, "menu item ID")
    return client.delete(build_endpoint("menu-items", item_id), params={"force": True})


# --- Menu locations ---


def list_menu_locations(client):
    """Fetch registered menu locations.

    The REST API returns an object keyed by location slug; rows are
    synthesized and sorted by name. Read-only — assigning a menu to a
    location is not exposed by the REST API (theme-dependent).

    Args:
        client: WPApiClient instance.

    Returns:
        List of location dicts (name, description, menu).
    """
    data = client.get("menu-locations", params=None)
    if not isinstance(data, dict):
        return []
    return [
        _extract_row(data[key], LOCATION_FIELDS)
        for key in sorted(data)
        if isinstance(data[key], dict)
    ]
