"""REST API surface discovery via the /wp-json/ root index.

`wpa api discover` shows what a site actually exposes: which namespaces
are registered (core, plugins) and, with --routes, every route and its
methods. Useful for diagnosing which wpa commands a site can support —
block themes, disabled endpoints, or WAF filtering all show up here.

The root index is fetched with `_fields` narrowing so only the requested
section (namespaces or routes) crosses the wire; the client's response
size cap still applies.
"""

NAMESPACE_FIELDS = ["namespace"]
ROUTE_FIELDS = ["route", "namespace", "methods"]

NAMESPACE_AVAILABLE_FIELDS = list(NAMESPACE_FIELDS)
NAMESPACE_DEFAULT_FIELDS = list(NAMESPACE_FIELDS)

ROUTE_AVAILABLE_FIELDS = list(ROUTE_FIELDS)
ROUTE_DEFAULT_FIELDS = list(ROUTE_FIELDS)


def _validate(fields_str, available, defaults):
    if fields_str is None:
        return defaults
    fields = [f.strip() for f in fields_str.split(",")]
    for field in fields:
        if field not in available:
            raise ValueError(
                f"Unknown field '{field}'. Available fields: {', '.join(available)}"
            )
    return fields


def validate_namespace_fields(fields_str):
    """Validate a --fields string for namespace listings."""
    return _validate(fields_str, NAMESPACE_AVAILABLE_FIELDS, NAMESPACE_DEFAULT_FIELDS)


def validate_route_fields(fields_str):
    """Validate a --fields string for route listings."""
    return _validate(fields_str, ROUTE_AVAILABLE_FIELDS, ROUTE_DEFAULT_FIELDS)


def list_namespaces(client):
    """Fetch the namespaces registered on a site.

    Args:
        client: WPApiClient instance.

    Returns:
        List of {'namespace': str} rows, sorted.
    """
    data = client.get_root(params={"_fields": "namespaces"})
    if not isinstance(data, dict):
        return []
    namespaces = data.get("namespaces", [])
    if not isinstance(namespaces, list):
        return []
    names = sorted(ns for ns in namespaces if isinstance(ns, str))
    return [{"namespace": ns} for ns in names]


def list_routes(client, namespace=None):
    """Fetch the routes a site exposes, optionally scoped to one namespace.

    Args:
        client: WPApiClient instance.
        namespace: Namespace to filter by (e.g. 'wp/v2'), or None for all.

    Returns:
        List of {'route', 'namespace', 'methods'} rows, sorted by route.
    """
    data = client.get_root(params={"_fields": "routes"})
    if not isinstance(data, dict):
        return []
    routes = data.get("routes", {})
    if not isinstance(routes, dict):
        return []

    rows = []
    for route in sorted(routes):
        info = routes[route]
        if not isinstance(info, dict):
            continue
        if namespace and info.get("namespace") != namespace:
            continue
        methods = info.get("methods", [])
        rows.append(
            {
                "route": route,
                "namespace": info.get("namespace", ""),
                "methods": ", ".join(str(m) for m in methods),
            }
        )
    return rows
