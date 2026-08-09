"""Tests for wpa.cli — user-facing error formatting."""

from wpa.cli import _format_api_error
from wpa.exceptions import WPApiError, WPConnectionError


class TestFormatApiError:
    def test_tls_downgrade_is_friendly(self):
        e = WPApiError(0, "tls_downgrade", "Refusing to trust response")
        msg = _format_api_error(e)
        assert "downgraded from https to http" in msg
        assert "WP_SITE_URL" in msg
        assert "TLS troubleshooting" in msg
        # 2-3 sentences of guidance, not a raw code dump
        assert "tls_downgrade" not in msg

    def test_possible_waf_block_is_friendly(self):
        e = WPApiError(404, "possible_waf_block", "Server returned an HTML page")
        msg = _format_api_error(e)
        assert "HTML page (HTTP 404)" in msg
        assert "Wordfence" in msg
        assert "waf-compatibility" in msg

    def test_generic_api_error_keeps_status_code_message(self):
        e = WPApiError(403, "rest_forbidden", "Sorry, you are not allowed.")
        msg = _format_api_error(e)
        assert "WordPress API returned 403" in msg
        assert "rest_forbidden" in msg
        assert "Sorry, you are not allowed." in msg

    def test_non_api_error_passthrough(self):
        e = WPConnectionError("Could not connect to https://example.com.")
        msg = _format_api_error(e)
        assert msg == "Error: Could not connect to https://example.com."
