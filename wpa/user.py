"""User CRUD operations via WordPress REST API."""

# Maps friendly field names to WordPress REST API response keys
USER_FIELDS = {
    "id": "id",
    "username": "slug",
    "email": "email",
    "display_name": "name",
    "first_name": "first_name",
    "last_name": "last_name",
    "roles": "roles",
    "url": "url",
    "registered": "registered_date",
    "description": "description",
}

AVAILABLE_FIELDS = list(USER_FIELDS.keys())
DEFAULT_FIELDS = ["id", "username", "email", "display_name", "roles"]


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
        if field not in USER_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _validate_user_id(user_id):
    """Validate user_id is a positive integer.

    Raises:
        ValueError: If user_id is not a positive integer.
    """
    if not isinstance(user_id, int) or user_id < 1:
        raise ValueError(f"Invalid user ID: {user_id}")


def _extract_user_row(api_user):
    """Convert a WP REST API user object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in USER_FIELDS.items():
        value = api_user.get(api_key, "")
        if friendly == "roles" and isinstance(value, list):
            value = ", ".join(value)
        row[friendly] = value
    return row


def get_user(client, user_id):
    """Get a single user by ID.

    Args:
        client: WPApiClient instance.
        user_id: User ID.

    Returns:
        User dict with friendly field names.
    """
    _validate_user_id(user_id)
    params = {"context": "edit"}
    data = client.get(f"users/{user_id}", params=params)
    return _extract_user_row(data)


def set_role(client, user_id, role):
    """Set a user's role.

    Args:
        client: WPApiClient instance.
        user_id: User ID.
        role: Role name (administrator, editor, author, contributor, subscriber).

    Returns:
        Updated user dict from API response.
    """
    _validate_user_id(user_id)
    return client.post(f"users/{user_id}", data={"roles": [role]})


def list_users(client, role=None, search=None):
    """Fetch users from WordPress REST API.

    Args:
        client: WPApiClient instance.
        role: Optional role filter.
        search: Optional search term.

    Returns:
        List of user dicts with friendly field names.
    """
    params = {"context": "edit", "per_page": 100}
    if role:
        params["roles"] = role
    if search:
        params["search"] = search

    return [_extract_user_row(u) for u in client.get_list("users", params=params)]


def create_user(
    client,
    username,
    email,
    password_new,
    role=None,
    first_name=None,
    last_name=None,
):
    """Create a new WordPress user.

    Args:
        client: WPApiClient instance.
        username: Login name for the new user.
        email: Email address.
        password_new: Password for the new user.
        role: Optional role (default: subscriber on most WP installs).
        first_name: Optional first name.
        last_name: Optional last name.

    Returns:
        Created user dict from API response.
    """
    payload = {
        "username": username,
        "email": email,
        "password": password_new,
    }
    if role:
        payload["roles"] = [role]
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name

    return client.post("users", data=payload)


def update_user(
    client,
    user_id,
    email=None,
    role=None,
    first_name=None,
    last_name=None,
    display_name=None,
):
    """Update an existing WordPress user.

    Args:
        client: WPApiClient instance.
        user_id: ID of the user to update (must be a positive integer).
        email: New email address.
        role: New role.
        first_name: New first name.
        last_name: New last name.
        display_name: New display name.

    Returns:
        Updated user dict from API response.

    Raises:
        ValueError: If user_id is invalid or no fields to update.
    """
    _validate_user_id(user_id)

    payload = {}
    if email is not None:
        payload["email"] = email
    if role is not None:
        payload["roles"] = [role]
    if first_name is not None:
        payload["first_name"] = first_name
    if last_name is not None:
        payload["last_name"] = last_name
    if display_name is not None:
        payload["name"] = display_name

    if not payload:
        raise ValueError(
            "No fields to update. Specify at least one of: "
            "--email, --role, --first-name, --last-name, --display-name"
        )

    return client.post(f"users/{user_id}", data=payload)


def delete_user(client, user_id, reassign=None):
    """Delete a WordPress user.

    Args:
        client: WPApiClient instance.
        user_id: ID of the user to delete (must be a positive integer).
        reassign: User ID to reassign posts to. If None, posts are deleted.

    Returns:
        Deletion response dict from API.

    Raises:
        ValueError: If user_id is invalid.
    """
    _validate_user_id(user_id)

    params = {"force": True}
    if reassign is not None:
        params["reassign"] = reassign

    return client.delete(f"users/{user_id}", params=params)
