"""Taxonomy term CRUD operations via WordPress REST API.

Supports built-in taxonomies (`category`, `post_tag`) and any custom taxonomy
exposed under `/wp/v2/<taxonomy-rest-base>`. The REST API exposes built-in
taxonomies under different paths than their slugs (`category` → `categories`,
`post_tag` → `tags`); other taxonomies are addressed by their slug.
"""

import re

# Map taxonomy slugs to their REST API endpoint base. Built-in taxonomies
# are exposed under custom paths; custom taxonomies use their slug directly.
_TAXONOMY_ENDPOINTS = {
    "category": "categories",
    "post_tag": "tags",
}

_TAXONOMY_SLUG_RE = re.compile(r"^[a-z0-9_-]+$", re.IGNORECASE)
# Note: IGNORECASE allows mixed-case input; _resolve_endpoint lowercases
# before lookup so `POST_TAG` and `Category` route to the correct endpoint.
# WordPress stores taxonomy slugs as lowercase, so normalization is safe.

# Maps friendly field names to WordPress REST API response keys
TERM_FIELDS = {
    "id": "id",
    "name": "name",
    "slug": "slug",
    "description": "description",
    "count": "count",
    "parent": "parent",
    "taxonomy": "taxonomy",
    "link": "link",
}

AVAILABLE_FIELDS = list(TERM_FIELDS.keys())
DEFAULT_FIELDS = ["id", "name", "slug", "count"]


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
        if field not in TERM_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. "
                f"Available fields: {', '.join(AVAILABLE_FIELDS)}"
            )
    return fields


def _resolve_endpoint(taxonomy):
    """Resolve a taxonomy slug to its REST API endpoint base.

    Args:
        taxonomy: Taxonomy slug (e.g. 'category', 'post_tag', 'genre').
            None defaults to 'category'.

    Returns:
        Endpoint string (e.g. 'categories', 'tags', 'genre').

    Raises:
        ValueError: If the taxonomy slug is empty or contains invalid characters.
    """
    if taxonomy is None:
        taxonomy = "category"

    if not taxonomy or not _TAXONOMY_SLUG_RE.match(taxonomy):
        raise ValueError(f"Invalid taxonomy: {taxonomy!r}")

    taxonomy = taxonomy.lower()
    return _TAXONOMY_ENDPOINTS.get(taxonomy, taxonomy)


def _validate_term_id(term_id):
    """Validate term_id is a positive integer."""
    if not isinstance(term_id, int) or isinstance(term_id, bool) or term_id < 1:
        raise ValueError(f"Invalid term ID: {term_id}")


def _extract_term_row(api_term):
    """Convert a WP REST API term object to a flat dict with friendly keys."""
    row = {}
    for friendly, api_key in TERM_FIELDS.items():
        row[friendly] = api_term.get(api_key, "")
    return row


def list_terms(
    client,
    taxonomy=None,
    search=None,
    parent=None,
    hide_empty=False,
    per_page=100,
    page=None,
    orderby=None,
    order=None,
):
    """Fetch terms from a WordPress taxonomy.

    Args:
        client: WPApiClient instance.
        taxonomy: Taxonomy slug (default: 'category').
        search: Search term.
        parent: Filter by parent term ID.
        hide_empty: Hide terms with no associated posts.
        per_page: Results per page (default 100).
        page: Specific page number (fetches single page).
        orderby: Sort field (name, slug, count, etc.).
        order: Sort order (asc, desc).

    Returns:
        List of term dicts with friendly field names.
    """
    endpoint = _resolve_endpoint(taxonomy)

    params = {}
    if search:
        params["search"] = search
    if parent is not None:
        params["parent"] = parent
    if hide_empty:
        params["hide_empty"] = True
    if per_page is not None:
        params["per_page"] = per_page
    if page is not None:
        params["page"] = page
    if orderby:
        params["orderby"] = orderby
    if order:
        params["order"] = order

    if page is not None:
        items = client.get(endpoint, params=params)
        if not isinstance(items, list):
            return []
        return [_extract_term_row(t) for t in items]

    return [_extract_term_row(t) for t in client.get_list(endpoint, params=params)]


def get_term(client, term_id, taxonomy=None):
    """Get a single term by ID.

    Args:
        client: WPApiClient instance.
        term_id: Term ID.
        taxonomy: Taxonomy slug (default: 'category').

    Returns:
        Term dict with friendly field names.
    """
    _validate_term_id(term_id)
    endpoint = _resolve_endpoint(taxonomy)
    data = client.get(f"{endpoint}/{term_id}", params=None)
    return _extract_term_row(data)


def create_term(
    client,
    name,
    taxonomy=None,
    slug=None,
    description=None,
    parent=None,
):
    """Create a new term in a taxonomy.

    Args:
        client: WPApiClient instance.
        name: Term display name.
        taxonomy: Taxonomy slug (default: 'category').
        slug: URL slug.
        description: Term description.
        parent: Parent term ID for hierarchical taxonomies.

    Returns:
        Created term dict from API response.

    Raises:
        ValueError: If name is empty.
    """
    if not name:
        raise ValueError("Term name cannot be empty.")

    endpoint = _resolve_endpoint(taxonomy)

    payload = {"name": name}
    if slug is not None:
        payload["slug"] = slug
    if description is not None:
        payload["description"] = description
    if parent is not None:
        payload["parent"] = parent

    return client.post(endpoint, data=payload)


def update_term(client, term_id, taxonomy=None, **fields):
    """Update an existing term.

    Args:
        client: WPApiClient instance.
        term_id: Term ID to update.
        taxonomy: Taxonomy slug (default: 'category').
        **fields: Fields to update (name, slug, description, parent).

    Returns:
        Updated term dict from API response.

    Raises:
        ValueError: If no fields provided or term_id is invalid.
    """
    _validate_term_id(term_id)

    if not fields:
        raise ValueError(
            "No fields to update. Specify at least one of: "
            "--name, --slug, --description, --parent"
        )

    endpoint = _resolve_endpoint(taxonomy)
    return client.post(f"{endpoint}/{term_id}", data=fields)


def delete_term(client, term_id, taxonomy=None):
    """Delete a term.

    Note: The WordPress REST API requires `force=true` to delete terms
    (terms cannot be moved to trash). This is always sent.

    Args:
        client: WPApiClient instance.
        term_id: Term ID to delete.
        taxonomy: Taxonomy slug (default: 'category').

    Returns:
        Deletion response dict from API.
    """
    _validate_term_id(term_id)
    endpoint = _resolve_endpoint(taxonomy)
    return client.delete(f"{endpoint}/{term_id}", params={"force": True})
