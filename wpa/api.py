"""Shared REST API client for all WPA commands."""

import base64
import os
import re
import sys

import requests

from wpa.config import resolve_config
from wpa.exceptions import WPApiError, WPConnectionError, WPTimeoutError

# Map HTTP status codes to user-friendly error messages
_ERROR_MESSAGES = {
    401: "Authentication failed. Check your username and application password.",
    403: "Permission denied. Your user account does not have the required capability.",
    404: "Resource not found.",
}

# Defense-in-depth caps against hostile / buggy upstream responses.
# Tuned for "WP REST API payloads that any reasonable site produces."
# Overridable per-environment via WPA_MAX_RESPONSE_BYTES / WPA_MAX_TOTAL_PAGES.
DEFAULT_MAX_RESPONSE_BYTES = 50 * 1024 * 1024  # 50 MB — any single response
DEFAULT_MAX_TOTAL_PAGES = 1000  # pagination ceiling regardless of X-WP-TotalPages


def _env_cap(name, default):
    """Read a positive-int cap from the environment, falling back to default.

    Invalid values (non-integer, zero, negative) warn on stderr and keep the
    default so a misconfigured environment can never disable the cap.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value < 1:
        print(
            f"Warning: ignoring {name}={raw!r} (expected a positive integer); "
            f"using {default}",
            file=sys.stderr,
        )
        return default
    return value


def max_response_bytes():
    """Response-size cap in bytes (WPA_MAX_RESPONSE_BYTES or default)."""
    return _env_cap("WPA_MAX_RESPONSE_BYTES", DEFAULT_MAX_RESPONSE_BYTES)


def max_total_pages():
    """Pagination ceiling (WPA_MAX_TOTAL_PAGES or default)."""
    return _env_cap("WPA_MAX_TOTAL_PAGES", DEFAULT_MAX_TOTAL_PAGES)


# Endpoint path sanitizer — defense-in-depth against traversal. All legitimate
# WP REST endpoints are ASCII slugs with optional numeric IDs and literal
# slashes, e.g. "posts", "posts/42", "users/me". Anything else is suspicious.
_ENDPOINT_ALLOWED = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-/]*$")
_ENDPOINT_FORBIDDEN = ("..", "//", "\\", "\r", "\n", "%2f", "%2F", "%5c", "%5C")


# A single path segment: an ASCII slug or numeric ID, no slashes, and a
# leading alphanumeric (matches the first-character rule in _ENDPOINT_ALLOWED).
_SEGMENT_ALLOWED = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def build_endpoint(*segments):
    """Join path segments into a validated REST endpoint string.

    Shared helper for modules that build dynamic endpoints like
    ``posts/{id}``. Each segment is validated individually before joining,
    so an ID or slug sourced from user input can never smuggle a slash,
    traversal sequence, or encoded separator into the path.

    Args:
        segments: One or more path segments. Strings must match
            [A-Za-z0-9][A-Za-z0-9_-]*; integers must be positive.

    Returns:
        The joined endpoint string (e.g. 'posts/42').

    Raises:
        ValueError: If no segments are given or any segment is invalid.
    """
    if not segments:
        raise ValueError("build_endpoint requires at least one segment")

    parts = []
    for segment in segments:
        # ValueError (not TypeError) on wrong types too: callers catch
        # ValueError as the single "bad input" signal, same as the ID
        # validators in each module.
        if isinstance(segment, int) and not isinstance(segment, bool):
            if segment < 1:
                raise ValueError(f"Invalid endpoint segment: {segment!r}")
            segment = str(segment)
        if not isinstance(segment, str) or not _SEGMENT_ALLOWED.match(segment):
            raise ValueError(f"Invalid endpoint segment: {segment!r}")
        parts.append(segment)

    endpoint = "/".join(parts)
    # Last gate — same guard every endpoint passes through in _url().
    _validate_endpoint(endpoint)
    return endpoint


def _validate_endpoint(endpoint):
    """Reject endpoint strings that could escape the /wp-json/wp/v2/ prefix.

    This is defense-in-depth — individual modules already validate their
    inputs (see term._resolve_endpoint), but we want a central guard so any
    future caller that forgets to validate still can't smuggle traversal or
    CRLF sequences into the URL.
    """
    if not endpoint or not isinstance(endpoint, str):
        raise ValueError(f"Invalid endpoint: {endpoint!r}")
    if endpoint.startswith("/"):
        raise ValueError(f"Endpoint must be relative, got {endpoint!r}")
    for bad in _ENDPOINT_FORBIDDEN:
        if bad in endpoint:
            raise ValueError(
                f"Endpoint {endpoint!r} contains forbidden sequence {bad!r}"
            )
    if not _ENDPOINT_ALLOWED.match(endpoint):
        raise ValueError(
            f"Endpoint {endpoint!r} contains characters outside [A-Za-z0-9_-/]"
        )


# Status codes WAFs and security plugins typically answer with when they
# reject a request outright (Wordfence uses 403 for blocked methods and 404
# for author-enumeration protection).
_WAF_STATUS_CODES = frozenset({403, 404, 406, 429, 503})


def _looks_like_html(body):
    """True if a response body starts like an HTML document."""
    if not isinstance(body, str):
        return False
    head = body.lstrip()[:15].lower()
    return head.startswith(("<!doctype", "<html"))


class WPApiClient:
    """WordPress REST API client with auth, pagination, and error handling."""

    def __init__(self, site_url, username, app_password, timeout=30, debug=False):
        """Initialize with site credentials.

        Args:
            site_url: WordPress site URL (e.g., https://example.com).
            username: WordPress username.
            app_password: WordPress Application Password.
            timeout: Request timeout in seconds (default 30).
            debug: Print HTTP request/response details when True.
        """
        self.site_url = site_url.rstrip("/")
        self.username = username
        self.app_password = app_password
        self.timeout = timeout
        self.debug = debug
        self.admin_path = "wp-admin"

    @classmethod
    def from_config(cls, site_name=None, debug=False):
        """Create a client from a saved site configuration.

        Args:
            site_name: Named site config, or None for auto-select.
            debug: Print HTTP request/response details when True.

        Returns:
            WPApiClient instance.
        """
        site_url, username, app_password, admin_path = resolve_config(
            site_name=site_name
        )
        client = cls(site_url, username, app_password, debug=debug)
        client.admin_path = admin_path
        return client

    def _url(self, endpoint):
        """Build full REST API URL.

        Args:
            endpoint: API path (e.g., 'posts', 'users/42').

        Returns:
            Full URL like https://example.com/wp-json/wp/v2/posts

        Raises:
            ValueError: If endpoint contains traversal or injection patterns.
        """
        _validate_endpoint(endpoint)
        return f"{self.site_url}/wp-json/wp/v2/{endpoint}"

    def _auth_header(self):
        """Build HTTP Basic Auth header value."""
        credentials = f"{self.username}:{self.app_password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _headers(self):
        """Build request headers."""
        return {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
        }

    def _debug_log(self, method, url, params=None, data=None, response=None):
        """Print debug info with masked credentials."""
        if not self.debug:
            return

        print(f"DEBUG: {method} {url}", file=sys.stderr)
        if params:
            print(f"DEBUG: Params: {params}", file=sys.stderr)
        if data:
            print(f"DEBUG: Body: {data}", file=sys.stderr)
        if response is not None:
            print(
                f"DEBUG: Response: {response.status_code} "
                f"({len(response.content)} bytes)",
                file=sys.stderr,
            )

    def _check_response_size(self, response):
        """Raise WPApiError if the response body exceeds the size cap."""
        # Content-Length is advisory; check actual bytes too. requests has
        # already read the body at this point (we don't use stream=True), so
        # len(response.content) is authoritative.
        cap = max_response_bytes()
        if len(response.content) > cap:
            raise WPApiError(
                response.status_code,
                "response_too_large",
                f"Response from {self.site_url} exceeded "
                f"{cap} bytes ({len(response.content)} bytes).",
            )

    def _check_no_scheme_downgrade(self, response):
        """Refuse a response whose URL downgraded from https to http."""
        final_url = getattr(response, "url", None)
        if not isinstance(final_url, str):
            return
        if self.site_url.startswith("https://") and final_url.startswith("http://"):
            raise WPApiError(
                0,
                "tls_downgrade",
                f"Refusing to trust response: request was https but "
                f"final URL is http ({final_url}). Possible MITM.",
            )

    def _handle_response(self, response):
        """Check response status and parse JSON.

        Args:
            response: requests.Response object.

        Returns:
            Parsed JSON response as dict or list.

        Raises:
            WPApiError: If the response indicates an error.
        """
        if response.ok:
            if not response.content:
                return {}
            try:
                return response.json()
            except ValueError:
                raise WPApiError(
                    response.status_code,
                    "invalid_json",
                    f"Invalid JSON in response from {self.site_url}",
                )

        # Error response — try to extract WP error details
        default_message = _ERROR_MESSAGES.get(
            response.status_code,
            f"Server error ({response.status_code}).",
        )

        try:
            error = response.json()
            raise WPApiError(
                response.status_code,
                error.get("code", "unknown"),
                error.get("message", default_message),
            )
        except ValueError:
            # Non-JSON error response. An HTML error page from a REST
            # endpoint is the signature of a WAF / security plugin (e.g.
            # Wordfence) rejecting the request before WordPress sees it —
            # WordPress itself always returns JSON errors from /wp-json/.
            if response.status_code in _WAF_STATUS_CODES and _looks_like_html(
                response.text
            ):
                raise WPApiError(
                    response.status_code,
                    "possible_waf_block",
                    f"Server returned an HTML page (HTTP "
                    f"{response.status_code}) instead of a REST API JSON "
                    f"response.",
                )
            body = response.text[:200].replace("\n", " ").replace("\r", "")
            raise WPApiError(
                response.status_code,
                "unknown",
                body or default_message,
            )

    def _request(self, method, url, params=None, json_data=None, files=None):
        """Make an authenticated request with error handling.

        Args:
            method: HTTP method string ('GET', 'POST', 'DELETE').
            url: Full request URL.
            params: Query parameters dict.
            json_data: JSON body dict.
            files: Files dict for multipart upload.

        Returns:
            Parsed JSON response.

        Raises:
            WPApiError: On API error responses.
            WPConnectionError: On connection failure.
            WPTimeoutError: On timeout.
        """
        headers = self._headers()
        # Don't set Content-Type for multipart uploads
        if files:
            del headers["Content-Type"]

        kwargs = {
            "headers": headers,
            "timeout": self.timeout,
        }
        # Write methods never follow redirects — a redirect on POST/DELETE is
        # almost always a misconfigured server or an attack (e.g., a redirect
        # that causes a retry with the body replayed to a different host).
        if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            kwargs["allow_redirects"] = False
        if params:
            kwargs["params"] = params
        if json_data is not None:
            if files:
                # Multipart upload — send metadata as form fields, not JSON
                kwargs["data"] = json_data
            else:
                kwargs["json"] = json_data
        if files:
            kwargs["files"] = files

        self._debug_log(method, url, params=params, data=json_data)

        try:
            response = requests.request(method, url, **kwargs)
        except requests.ConnectionError:
            raise WPConnectionError(
                f"Could not connect to {self.site_url}. "
                "Check the URL and your network connection."
            )
        except requests.Timeout:
            raise WPTimeoutError(
                f"Request to {self.site_url} timed out after {self.timeout} seconds."
            )
        except requests.RequestException as e:
            raise WPConnectionError(f"Request failed: {e}")

        self._debug_log(method, url, response=response)

        self._check_no_scheme_downgrade(response)
        self._check_response_size(response)

        return self._handle_response(response)

    def get(self, endpoint, params=None):
        """GET a single resource.

        Args:
            endpoint: API path (e.g., 'posts/42').
            params: Optional query parameters.

        Returns:
            Parsed JSON response dict.
        """
        return self._request("GET", self._url(endpoint), params=params)

    def get_root(self, params=None):
        """GET the REST API root index (/wp-json/).

        The root index lives outside the wp/v2 namespace, so this is the
        one request that bypasses _url(). The URL is fixed — no
        user-supplied path segments are involved — and the request still
        goes through _request(), so auth, the response-size cap, the
        TLS-downgrade check, and WAF detection all apply.

        Args:
            params: Optional query parameters (e.g. {'_fields': 'routes'}
                to keep the potentially large index response small).

        Returns:
            Parsed JSON response dict.
        """
        return self._request("GET", f"{self.site_url}/wp-json/", params=params)

    def get_total(self, endpoint, params=None):
        """Return the total number of items in a collection.

        Fetches a single item (per_page=1) and reads the X-WP-Total header,
        so counting a large collection costs one lightweight request instead
        of paginating through everything.

        Args:
            endpoint: API path (e.g., 'comments').
            params: Optional query parameters (filters).

        Returns:
            Total item count as an int.
        """
        params = {**(params or {}), "per_page": 1}
        url = self._url(endpoint)

        self._debug_log("GET", url, params=params)

        try:
            response = requests.get(
                url, headers=self._headers(), params=params, timeout=self.timeout
            )
        except requests.ConnectionError:
            raise WPConnectionError(
                f"Could not connect to {self.site_url}. "
                "Check the URL and your network connection."
            )
        except requests.Timeout:
            raise WPTimeoutError(
                f"Request to {self.site_url} timed out after {self.timeout} seconds."
            )
        except requests.RequestException as e:
            raise WPConnectionError(f"Request failed: {e}")

        self._debug_log("GET", url, response=response)

        self._check_no_scheme_downgrade(response)
        self._check_response_size(response)

        # Raises on error responses; the body itself is discarded.
        data = self._handle_response(response)

        try:
            return int(response.headers.get("X-WP-Total"))
        except (TypeError, ValueError):
            # Header missing or malformed — fall back to what we can see.
            return len(data) if isinstance(data, list) else 0

    def get_list(self, endpoint, params=None):
        """GET a paginated list of resources.

        Yields individual items across all pages. Reads X-WP-TotalPages
        header to determine page count. Default per_page=100 (WP max).

        Args:
            endpoint: API path (e.g., 'posts').
            params: Optional query parameters.

        Yields:
            Individual resource dicts.
        """
        if params is None:
            params = {}

        params.setdefault("per_page", 100)

        # First page
        url = self._url(endpoint)
        headers = self._headers()

        self._debug_log("GET", url, params=params)

        try:
            response = requests.get(
                url, headers=headers, params=params, timeout=self.timeout
            )
        except requests.ConnectionError:
            raise WPConnectionError(
                f"Could not connect to {self.site_url}. "
                "Check the URL and your network connection."
            )
        except requests.Timeout:
            raise WPTimeoutError(
                f"Request to {self.site_url} timed out after {self.timeout} seconds."
            )
        except requests.RequestException as e:
            raise WPConnectionError(f"Request failed: {e}")

        self._debug_log("GET", url, response=response)

        self._check_no_scheme_downgrade(response)
        self._check_response_size(response)

        data = self._handle_response(response)

        if not isinstance(data, list):
            return

        yield from data

        # Check for additional pages — clamp to the pagination cap to defend
        # against a hostile or buggy server that returns an absurd
        # X-WP-TotalPages value (e.g., 999999) and forces an infinite loop.
        try:
            total_pages = int(response.headers.get("X-WP-TotalPages", 1))
        except (TypeError, ValueError):
            total_pages = 1
        total_pages = min(total_pages, max_total_pages())

        for page_num in range(2, total_pages + 1):
            page_params = {**params, "page": page_num}

            self._debug_log("GET", url, params=page_params)

            try:
                response = requests.get(
                    url, headers=headers, params=page_params, timeout=self.timeout
                )
            except requests.ConnectionError:
                raise WPConnectionError(
                    f"Could not connect to {self.site_url}. "
                    "Check the URL and your network connection."
                )
            except requests.Timeout:
                raise WPTimeoutError(
                    f"Request to {self.site_url} timed out "
                    f"after {self.timeout} seconds."
                )
            except requests.RequestException as e:
                raise WPConnectionError(f"Request failed: {e}")

            self._debug_log("GET", url, response=response)

            self._check_no_scheme_downgrade(response)
            self._check_response_size(response)

            page_data = self._handle_response(response)
            if isinstance(page_data, list):
                yield from page_data

    def post(self, endpoint, data=None, files=None):
        """POST to create or update a resource.

        Args:
            endpoint: API path (e.g., 'posts', 'posts/42').
            data: JSON body dict.
            files: Files dict for multipart upload.

        Returns:
            Parsed JSON response dict.
        """
        return self._request("POST", self._url(endpoint), json_data=data, files=files)

    def request_password_reset(self, user_login):
        """Ask WordPress core to email a one-time set-password link.

        POSTs the site's lost-password form (wp-login.php?action=lostpassword)
        — the same flow as the "Lost your password?" link. This is the only
        way to trigger a new-user email without server access: the REST
        users endpoint never sends notifications.

        The request is deliberately unauthenticated (the form is public) so
        credentials are never sent to wp-login.php.

        Args:
            user_login: Username or email address of the target user.

        Returns:
            True if WordPress confirmed the request (redirect to
            checkemail=confirm), False otherwise. Note this confirms the
            request was accepted, not that the email was delivered.

        Raises:
            WPConnectionError: On connection failure.
            WPTimeoutError: On timeout.
        """
        url = f"{self.site_url}/wp-login.php"
        params = {"action": "lostpassword"}

        self._debug_log("POST", url, params=params, data={"user_login": user_login})

        try:
            response = requests.post(
                url,
                params=params,
                data={"user_login": user_login},
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.ConnectionError:
            raise WPConnectionError(
                f"Could not connect to {self.site_url}. "
                "Check the URL and your network connection."
            )
        except requests.Timeout:
            raise WPTimeoutError(
                f"Request to {self.site_url} timed out after {self.timeout} seconds."
            )
        except requests.RequestException as e:
            raise WPConnectionError(f"Request failed: {e}")

        self._debug_log("POST", url, response=response)

        self._check_no_scheme_downgrade(response)

        # Success is a redirect back to the login page with
        # checkemail=confirm; anything else (200 with an error form, a WAF
        # block page, a rate-limit rejection) means no email is coming.
        location = response.headers.get("Location", "")
        return (
            response.status_code in (301, 302, 303) and "checkemail=confirm" in location
        )

    def delete(self, endpoint, params=None):
        """DELETE a resource.

        Args:
            endpoint: API path (e.g., 'posts/42').
            params: Query parameters (e.g., {'force': True}).

        Returns:
            Parsed JSON response dict.
        """
        return self._request("DELETE", self._url(endpoint), params=params)
