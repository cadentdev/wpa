"""Shared REST API client for all WPA commands."""

import base64
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
        """
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
            # Non-JSON error response
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

        data = self._handle_response(response)

        if not isinstance(data, list):
            return

        yield from data

        # Check for additional pages
        total_pages = int(response.headers.get("X-WP-TotalPages", 1))

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

    def delete(self, endpoint, params=None):
        """DELETE a resource.

        Args:
            endpoint: API path (e.g., 'posts/42').
            params: Query parameters (e.g., {'force': True}).

        Returns:
            Parsed JSON response dict.
        """
        return self._request("DELETE", self._url(endpoint), params=params)
