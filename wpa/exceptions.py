"""Custom exceptions for WPA WordPress API operations."""


class WPApiError(Exception):
    """WordPress REST API returned an error response."""

    def __init__(self, status_code, code="unknown", message="Unknown error"):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"WordPress API error {status_code}: {code} — {message}")


class WPConnectionError(Exception):
    """Could not connect to the WordPress site."""


class WPTimeoutError(Exception):
    """Request to the WordPress site timed out."""
