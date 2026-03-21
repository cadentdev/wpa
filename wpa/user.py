"""User CRUD operations via WordPress REST API."""

import sys

import requests

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
    """Validate user_id is a positive integer to prevent path injection."""
    if not isinstance(user_id, int) or user_id < 1:
        print(f"Error: Invalid user ID: {user_id}")
        sys.exit(1)


def _extract_user_row(api_user):
    """Convert a WP REST API user object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in USER_FIELDS.items():
        value = api_user.get(api_key, "")
        if friendly == "roles" and isinstance(value, list):
            value = ", ".join(value)
        row[friendly] = value
    return row


def _handle_request_error(e, site_url):
    """Handle requests library exceptions consistently."""
    if isinstance(e, requests.ConnectionError):
        print(
            f"Error: Could not connect to {site_url}. "
            "Check the URL and your network connection."
        )
    elif isinstance(e, requests.Timeout):
        print(f"Error: Request to {site_url} timed out after 30 seconds.")
    else:
        print(f"Error: Request failed: {e}")
    sys.exit(1)


def _handle_api_error(response):
    """Handle non-success API responses consistently."""
    print(f"Error: WordPress API returned {response.status_code}")
    try:
        error = response.json()
        print(f"  Code:    {error.get('code', 'unknown')}")
        print(f"  Message: {error.get('message', 'unknown')}")
    except ValueError:
        # Truncate and sanitize non-JSON response body
        body = response.text[:200].replace("\n", " ").replace("\r", "")
        print(f"  Body: {body}")
    sys.exit(1)


def _users_endpoint(site_url):
    """Return the WordPress users REST API endpoint URL."""
    return f"{site_url}/wp-json/wp/v2/users"


def _request(method, url, site_url, auth, expected_status, **kwargs):
    """Make an authenticated request and handle errors consistently.

    Returns the parsed JSON response.
    """
    try:
        response = method(url, auth=auth, timeout=30, **kwargs)
    except requests.RequestException as e:
        _handle_request_error(e, site_url)

    if response.status_code != expected_status:
        _handle_api_error(response)

    try:
        return response.json()
    except ValueError:
        print(f"Error: Invalid JSON in response from {site_url}")
        sys.exit(1)


def list_users(site_url, user, password, role=None, search=None):
    """Fetch users from WordPress REST API.

    Args:
        site_url: WordPress site URL.
        user: Username for authentication.
        password: Application password.
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

    data = _request(
        requests.get,
        _users_endpoint(site_url),
        site_url,
        auth=(user, password),
        expected_status=200,
        params=params,
    )
    return [_extract_user_row(u) for u in data]


def create_user(
    site_url,
    user,
    password,
    username,
    email,
    password_new,
    role=None,
    first_name=None,
    last_name=None,
):
    """Create a new WordPress user.

    Args:
        site_url: WordPress site URL.
        user: Username for authentication.
        password: Application password.
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

    return _request(
        requests.post,
        _users_endpoint(site_url),
        site_url,
        auth=(user, password),
        expected_status=201,
        json=payload,
    )


def update_user(
    site_url,
    user,
    password,
    user_id,
    email=None,
    role=None,
    first_name=None,
    last_name=None,
    display_name=None,
):
    """Update an existing WordPress user.

    Args:
        site_url: WordPress site URL.
        user: Username for authentication.
        password: Application password.
        user_id: ID of the user to update (must be a positive integer).
        email: New email address.
        role: New role.
        first_name: New first name.
        last_name: New last name.
        display_name: New display name.

    Returns:
        Updated user dict from API response.
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
        print(
            "Error: No fields to update. Specify at least one of: "
            "--email, --role, --first-name, --last-name, --display-name"
        )
        sys.exit(1)

    return _request(
        requests.post,
        f"{_users_endpoint(site_url)}/{user_id}",
        site_url,
        auth=(user, password),
        expected_status=200,
        json=payload,
    )


def delete_user(site_url, user, password, user_id, reassign=None):
    """Delete a WordPress user.

    Args:
        site_url: WordPress site URL.
        user: Username for authentication.
        password: Application password.
        user_id: ID of the user to delete (must be a positive integer).
        reassign: User ID to reassign posts to. If None, posts are deleted.

    Returns:
        Deletion response dict from API.
    """
    _validate_user_id(user_id)

    params = {"force": True}
    if reassign is not None:
        params["reassign"] = reassign

    return _request(
        requests.delete,
        f"{_users_endpoint(site_url)}/{user_id}",
        site_url,
        auth=(user, password),
        expected_status=200,
        params=params,
    )
