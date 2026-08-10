"""Tests for wpa.api — shared REST API client."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from wpa.api import WPApiClient, build_endpoint
from wpa.exceptions import WPApiError, WPConnectionError, WPTimeoutError


@pytest.fixture
def client():
    """Create a test client with dummy credentials."""
    return WPApiClient("https://example.com", "admin", "xxxx xxxx xxxx")


class TestInit:
    def test_stores_credentials(self, client):
        assert client.site_url == "https://example.com"
        assert client.username == "admin"
        assert client.app_password == "xxxx xxxx xxxx"

    def test_strips_trailing_slash(self):
        c = WPApiClient("https://example.com/", "admin", "pass")
        assert c.site_url == "https://example.com"

    def test_default_timeout(self, client):
        assert client.timeout == 30

    def test_custom_timeout(self):
        c = WPApiClient("https://example.com", "admin", "pass", timeout=60)
        assert c.timeout == 60

    def test_debug_default_false(self, client):
        assert client.debug is False

    def test_debug_enabled(self):
        c = WPApiClient("https://example.com", "admin", "pass", debug=True)
        assert c.debug is True


class TestUrl:
    def test_builds_endpoint_url(self, client):
        assert client._url("posts") == "https://example.com/wp-json/wp/v2/posts"

    def test_builds_resource_url(self, client):
        assert client._url("posts/42") == "https://example.com/wp-json/wp/v2/posts/42"

    def test_builds_nested_url(self, client):
        assert (
            client._url("users/5/application-passwords")
            == "https://example.com/wp-json/wp/v2/users/5/application-passwords"
        )


class TestEndpointValidation:
    """Defense-in-depth — _url() must reject traversal / injection patterns."""

    @pytest.mark.parametrize(
        "bad",
        [
            "../users/1",
            "posts/../users",
            "posts//42",
            "/posts",
            "posts\rSet-Cookie: evil",
            "posts\nX-Injected: 1",
            "posts%2f..%2fusers",
            "posts%2F..%2Fusers",
            "posts\\..\\users",
            "",
            "posts/../../wp-admin/admin-ajax.php",
        ],
    )
    def test_rejects_malicious_endpoints(self, client, bad):
        with pytest.raises(ValueError):
            client._url(bad)

    def test_rejects_non_string_endpoint(self, client):
        with pytest.raises(ValueError):
            client._url(None)

    @pytest.mark.parametrize(
        "good",
        [
            "posts",
            "posts/42",
            "users/me",
            "categories",
            "tags/5",
            "users/5/application-passwords",
            "custom_taxonomy",
            "custom-taxonomy",
        ],
    )
    def test_accepts_valid_endpoints(self, client, good):
        # Just verify it doesn't raise and builds a string.
        url = client._url(good)
        assert url == f"https://example.com/wp-json/wp/v2/{good}"


class TestFromConfig:
    @patch("wpa.api.resolve_config")
    def test_creates_client_from_config(self, mock_resolve):
        mock_resolve.return_value = (
            "https://blog.example.com",
            "editor",
            "yyyy yyyy yyyy",
            "wp-admin",
        )
        c = WPApiClient.from_config(site_name="myblog")
        assert c.site_url == "https://blog.example.com"
        assert c.username == "editor"
        assert c.app_password == "yyyy yyyy yyyy"
        mock_resolve.assert_called_once_with(site_name="myblog")

    @patch("wpa.api.resolve_config")
    def test_passes_debug_flag(self, mock_resolve):
        mock_resolve.return_value = ("https://x.com", "u", "p", "wp-admin")
        c = WPApiClient.from_config(debug=True)
        assert c.debug is True

    @patch("wpa.api.resolve_config")
    def test_auto_selects_when_no_site_name(self, mock_resolve):
        mock_resolve.return_value = ("https://x.com", "u", "p", "wp-admin")
        WPApiClient.from_config()
        mock_resolve.assert_called_once_with(site_name=None)


class TestHandleResponse:
    def test_success_returns_json(self, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"id": 1}'
        resp.json.return_value = {"id": 1}
        assert client._handle_response(resp) == {"id": 1}

    def test_success_empty_body(self, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b""
        assert client._handle_response(resp) == {}

    def test_success_invalid_json(self, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b"not json"
        resp.json.side_effect = ValueError("bad json")
        resp.status_code = 200
        with pytest.raises(WPApiError, match="Invalid JSON"):
            client._handle_response(resp)

    def test_401_raises_auth_error(self, client):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 401
        resp.json.return_value = {
            "code": "rest_cannot_access",
            "message": "Sorry, you are not allowed.",
        }
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "rest_cannot_access"

    def test_403_raises_permission_error(self, client):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 403
        resp.json.return_value = {
            "code": "rest_forbidden",
            "message": "Sorry, you are not allowed to do that.",
        }
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 403

    def test_404_raises_not_found(self, client):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 404
        resp.json.return_value = {
            "code": "rest_post_invalid_id",
            "message": "Invalid post ID.",
        }
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 404

    def test_500_raises_server_error(self, client):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 500
        resp.json.return_value = {
            "code": "internal_server_error",
            "message": "There has been a critical error.",
        }
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 500

    def test_error_non_json_response(self, client):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 502
        resp.json.side_effect = ValueError("not json")
        resp.text = "<html>Bad Gateway</html>"
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.status_code == 502
        assert "Bad Gateway" in exc_info.value.message

    def test_error_non_json_truncates_long_body(self, client):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 502
        resp.json.side_effect = ValueError("not json")
        resp.text = "x" * 500
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(resp)
        assert len(exc_info.value.message) <= 200


class TestGet:
    @patch("wpa.api.requests.request")
    def test_get_success(self, mock_request, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"id": 42}'
        resp.json.return_value = {"id": 42}
        mock_request.return_value = resp

        result = client.get("posts/42")
        assert result == {"id": 42}
        mock_request.assert_called_once()
        args, _kwargs = mock_request.call_args
        assert args == ("GET", "https://example.com/wp-json/wp/v2/posts/42")

    @patch("wpa.api.requests.request")
    def test_get_with_params(self, mock_request, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"id": 42}'
        resp.json.return_value = {"id": 42}
        mock_request.return_value = resp

        client.get("posts/42", params={"_embed": True})
        _, kwargs = mock_request.call_args
        assert kwargs["params"] == {"_embed": True}

    @patch("wpa.api.requests.request")
    def test_get_connection_error(self, mock_request, client):
        mock_request.side_effect = requests.ConnectionError("refused")
        with pytest.raises(WPConnectionError, match="Could not connect"):
            client.get("posts/42")

    @patch("wpa.api.requests.request")
    def test_get_timeout(self, mock_request, client):
        mock_request.side_effect = requests.Timeout("timed out")
        with pytest.raises(WPTimeoutError, match="timed out"):
            client.get("posts/42")

    @patch("wpa.api.requests.request")
    def test_get_generic_request_error(self, mock_request, client):
        mock_request.side_effect = requests.RequestException("something broke")
        with pytest.raises(WPConnectionError, match="Request failed"):
            client.get("posts/42")


class TestPost:
    @patch("wpa.api.requests.request")
    def test_post_with_json_body(self, mock_request, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"id": 99}'
        resp.json.return_value = {"id": 99}
        mock_request.return_value = resp

        result = client.post("posts", data={"title": "Hello", "status": "draft"})
        assert result == {"id": 99}
        _, kwargs = mock_request.call_args
        assert kwargs["json"] == {"title": "Hello", "status": "draft"}

    @patch("wpa.api.requests.request")
    def test_post_with_files(self, mock_request, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"id": 100}'
        resp.json.return_value = {"id": 100}
        mock_request.return_value = resp

        files = {"file": ("photo.jpg", b"fake-image-data", "image/jpeg")}
        result = client.post("media", files=files)
        assert result == {"id": 100}
        _, kwargs = mock_request.call_args
        assert kwargs["files"] == files
        # Content-Type should not be set for multipart
        assert "Content-Type" not in kwargs["headers"]

    @patch("wpa.api.requests.request")
    def test_post_error_response(self, mock_request, client):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 400
        resp.json.return_value = {
            "code": "rest_invalid_param",
            "message": "Invalid parameter: title",
        }
        mock_request.return_value = resp

        with pytest.raises(WPApiError) as exc_info:
            client.post("posts", data={"title": ""})
        assert exc_info.value.status_code == 400


class TestDelete:
    @patch("wpa.api.requests.request")
    def test_delete_success(self, mock_request, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"deleted": true}'
        resp.json.return_value = {"deleted": True}
        mock_request.return_value = resp

        result = client.delete("posts/42", params={"force": True})
        assert result == {"deleted": True}
        args, kwargs = mock_request.call_args
        assert args == ("DELETE", "https://example.com/wp-json/wp/v2/posts/42")
        assert kwargs["params"] == {"force": True}

    @patch("wpa.api.requests.request")
    def test_delete_without_force(self, mock_request, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"id": 42, "status": "trash"}'
        resp.json.return_value = {"id": 42, "status": "trash"}
        mock_request.return_value = resp

        result = client.delete("posts/42")
        assert result["status"] == "trash"


class TestGetList:
    @patch("wpa.api.requests.get")
    def test_single_page(self, mock_get, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b'[{"id": 1}, {"id": 2}]'
        resp.json.return_value = [{"id": 1}, {"id": 2}]
        resp.headers = {"X-WP-TotalPages": "1", "X-WP-Total": "2"}
        mock_get.return_value = resp

        items = list(client.get_list("posts"))
        assert len(items) == 2
        assert items[0]["id"] == 1
        assert items[1]["id"] == 2
        mock_get.assert_called_once()

    @patch("wpa.api.requests.get")
    def test_multi_page(self, mock_get, client):
        resp1 = MagicMock()
        resp1.ok = True
        resp1.content = b'[{"id": 1}, {"id": 2}]'
        resp1.json.return_value = [{"id": 1}, {"id": 2}]
        resp1.headers = {"X-WP-TotalPages": "3", "X-WP-Total": "5"}

        resp2 = MagicMock()
        resp2.ok = True
        resp2.content = b'[{"id": 3}, {"id": 4}]'
        resp2.json.return_value = [{"id": 3}, {"id": 4}]
        resp2.headers = {"X-WP-TotalPages": "3", "X-WP-Total": "5"}

        resp3 = MagicMock()
        resp3.ok = True
        resp3.content = b'[{"id": 5}]'
        resp3.json.return_value = [{"id": 5}]
        resp3.headers = {"X-WP-TotalPages": "3", "X-WP-Total": "5"}

        mock_get.side_effect = [resp1, resp2, resp3]

        items = list(client.get_list("posts"))
        assert len(items) == 5
        assert [i["id"] for i in items] == [1, 2, 3, 4, 5]
        assert mock_get.call_count == 3

    @patch("wpa.api.requests.get")
    def test_empty_results(self, mock_get, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b"[]"
        resp.json.return_value = []
        resp.headers = {"X-WP-TotalPages": "0", "X-WP-Total": "0"}
        mock_get.return_value = resp

        items = list(client.get_list("posts"))
        assert items == []

    @patch("wpa.api.requests.get")
    def test_default_per_page_100(self, mock_get, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b"[]"
        resp.json.return_value = []
        resp.headers = {"X-WP-TotalPages": "1"}
        mock_get.return_value = resp

        list(client.get_list("posts"))
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["per_page"] == 100

    @patch("wpa.api.requests.get")
    def test_respects_custom_per_page(self, mock_get, client):
        resp = MagicMock()
        resp.ok = True
        resp.content = b"[]"
        resp.json.return_value = []
        resp.headers = {"X-WP-TotalPages": "1"}
        mock_get.return_value = resp

        list(client.get_list("posts", params={"per_page": 10}))
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["per_page"] == 10

    @patch("wpa.api.requests.get")
    def test_connection_error(self, mock_get, client):
        mock_get.side_effect = requests.ConnectionError("refused")
        with pytest.raises(WPConnectionError):
            list(client.get_list("posts"))

    @patch("wpa.api.requests.get")
    def test_timeout(self, mock_get, client):
        mock_get.side_effect = requests.Timeout("timed out")
        with pytest.raises(WPTimeoutError):
            list(client.get_list("posts"))

    @patch("wpa.api.requests.get")
    def test_non_list_response_returns_nothing(self, mock_get, client):
        """If the API returns a non-list (e.g., an object), yield nothing."""
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"id": 1}'
        resp.json.return_value = {"id": 1}
        resp.headers = {"X-WP-TotalPages": "1"}
        mock_get.return_value = resp

        items = list(client.get_list("posts"))
        assert items == []

    @patch("wpa.api.requests.get")
    def test_missing_total_pages_header(self, mock_get, client):
        """Default to 1 page if header is missing."""
        resp = MagicMock()
        resp.ok = True
        resp.content = b'[{"id": 1}]'
        resp.json.return_value = [{"id": 1}]
        resp.headers = {}
        mock_get.return_value = resp

        items = list(client.get_list("posts"))
        assert len(items) == 1
        mock_get.assert_called_once()


class TestDebugMode:
    @patch("wpa.api.requests.request")
    def test_debug_prints_to_stderr(self, mock_request, capsys):
        client = WPApiClient("https://example.com", "admin", "pass", debug=True)
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"id": 1}'
        resp.json.return_value = {"id": 1}
        mock_request.return_value = resp

        client.get("posts/1")
        captured = capsys.readouterr()
        assert "DEBUG: GET" in captured.err
        assert "https://example.com/wp-json/wp/v2/posts/1" in captured.err

    @patch("wpa.api.requests.request")
    def test_no_debug_output_when_disabled(self, mock_request, capsys):
        client = WPApiClient("https://example.com", "admin", "pass", debug=False)
        resp = MagicMock()
        resp.ok = True
        resp.content = b'{"id": 1}'
        resp.json.return_value = {"id": 1}
        mock_request.return_value = resp

        client.get("posts/1")
        captured = capsys.readouterr()
        assert captured.err == ""


class TestAuthHeader:
    def test_basic_auth_header(self, client):
        header = client._auth_header()
        assert header.startswith("Basic ")
        # Verify it decodes correctly
        import base64

        decoded = base64.b64decode(header.split(" ")[1]).decode()
        assert decoded == "admin:xxxx xxxx xxxx"


class TestSecurityHardening:
    """Tests for M1-M4 security hardening (added pre-v0.8.0 release)."""

    # --- M2: response size cap ---

    @patch("wpa.api.requests.request")
    def test_response_size_over_cap_raises(self, mock_request, client):
        from wpa.api import DEFAULT_MAX_RESPONSE_BYTES

        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.url = "https://example.com/wp-json/wp/v2/posts"
        resp.content = b"x" * (DEFAULT_MAX_RESPONSE_BYTES + 1)
        mock_request.return_value = resp

        with pytest.raises(WPApiError) as exc_info:
            client.get("posts")
        assert (
            "response_too_large" in str(exc_info.value)
            or exc_info.value.code == "response_too_large"
        )

    @patch("wpa.api.requests.request")
    def test_response_at_cap_accepted(self, mock_request, client):
        from wpa.api import DEFAULT_MAX_RESPONSE_BYTES

        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.url = "https://example.com/wp-json/wp/v2/posts"
        resp.content = b"x" * DEFAULT_MAX_RESPONSE_BYTES
        resp.json.return_value = {"id": 1}
        mock_request.return_value = resp

        # Does not raise.
        client.get("posts")

    # --- M2: total_pages cap ---

    @patch("wpa.api.requests.get")
    def test_total_pages_clamped(self, mock_get, client):
        from wpa.api import DEFAULT_MAX_TOTAL_PAGES

        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.url = "https://example.com/wp-json/wp/v2/posts"
        resp.content = b"[]"
        resp.json.return_value = []
        resp.headers = {"X-WP-TotalPages": "999999"}
        mock_get.return_value = resp

        # Exhaust the iterator — should stop at DEFAULT_MAX_TOTAL_PAGES requests, not 999999.
        list(client.get_list("posts"))
        # First request + (DEFAULT_MAX_TOTAL_PAGES - 1) more = DEFAULT_MAX_TOTAL_PAGES total.
        assert mock_get.call_count == DEFAULT_MAX_TOTAL_PAGES

    @patch("wpa.api.requests.get")
    def test_total_pages_bad_header_defaults_to_one(self, mock_get, client):
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.url = "https://example.com/wp-json/wp/v2/posts"
        resp.content = b"[]"
        resp.json.return_value = []
        resp.headers = {"X-WP-TotalPages": "not-a-number"}
        mock_get.return_value = resp

        list(client.get_list("posts"))
        assert mock_get.call_count == 1

    # --- M3: redirects disabled on writes ---

    @patch("wpa.api.requests.request")
    def test_post_disables_redirects(self, mock_request, client):
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.url = "https://example.com/wp-json/wp/v2/posts"
        resp.content = b'{"id": 1}'
        resp.json.return_value = {"id": 1}
        mock_request.return_value = resp

        client.post("posts", data={"title": "x"})
        kwargs = mock_request.call_args.kwargs
        assert kwargs.get("allow_redirects") is False

    @patch("wpa.api.requests.request")
    def test_delete_disables_redirects(self, mock_request, client):
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.url = "https://example.com/wp-json/wp/v2/posts/1"
        resp.content = b"{}"
        resp.json.return_value = {}
        mock_request.return_value = resp

        client.delete("posts/1")
        kwargs = mock_request.call_args.kwargs
        assert kwargs.get("allow_redirects") is False

    @patch("wpa.api.requests.request")
    def test_get_allows_redirects_by_default(self, mock_request, client):
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.url = "https://example.com/wp-json/wp/v2/posts/1"
        resp.content = b'{"id": 1}'
        resp.json.return_value = {"id": 1}
        mock_request.return_value = resp

        client.get("posts/1")
        kwargs = mock_request.call_args.kwargs
        # GET does not explicitly disable redirects — requests default is True.
        assert "allow_redirects" not in kwargs or kwargs["allow_redirects"] is True

    # --- M3: scheme-downgrade detection ---

    @patch("wpa.api.requests.request")
    def test_https_to_http_downgrade_refused(self, mock_request, client):
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.url = "http://example.com/wp-json/wp/v2/posts/1"  # downgraded
        resp.content = b'{"id": 1}'
        resp.json.return_value = {"id": 1}
        mock_request.return_value = resp

        with pytest.raises(WPApiError) as exc_info:
            client.get("posts/1")
        assert exc_info.value.code == "tls_downgrade"

    @patch("wpa.api.requests.request")
    def test_http_site_no_downgrade_check(self, mock_request):
        # Private-network sites may legitimately be http://; downgrade check
        # only triggers when the configured site_url is https://.
        c = WPApiClient("http://192.168.1.10", "admin", "pass")
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.url = "http://192.168.1.10/wp-json/wp/v2/posts/1"
        resp.content = b'{"id": 1}'
        resp.json.return_value = {"id": 1}
        mock_request.return_value = resp

        # Does not raise.
        c.get("posts/1")


class TestBuildEndpoint:
    """build_endpoint() — shared sanitizer for dynamic endpoint paths."""

    def test_joins_base_and_id(self):
        assert build_endpoint("posts", 42) == "posts/42"

    def test_single_segment(self):
        assert build_endpoint("users") == "users"

    def test_accepts_slug_segments(self):
        assert build_endpoint("genre", 7) == "genre/7"
        assert build_endpoint("users", 5, "application-passwords") == (
            "users/5/application-passwords"
        )

    def test_accepts_numeric_string(self):
        assert build_endpoint("posts", "42") == "posts/42"

    def test_rejects_no_segments(self):
        with pytest.raises(ValueError, match="at least one segment"):
            build_endpoint()

    @pytest.mark.parametrize(
        "segment",
        [
            "..",
            "42/../users",
            "a/b",
            "/posts",
            "posts/",
            "%2e%2e",
            "posts?x=1",
            "-leading-dash",
            "_leading_underscore",
            "",
            "with space",
            "crlf\r\n",
        ],
    )
    def test_rejects_bad_string_segments(self, segment):
        with pytest.raises(ValueError, match="Invalid endpoint segment"):
            build_endpoint("posts", segment)

    @pytest.mark.parametrize("segment", [0, -1, True, False, None, 4.2, ["posts"]])
    def test_rejects_bad_types(self, segment):
        with pytest.raises(ValueError, match="Invalid endpoint segment"):
            build_endpoint("posts", segment)


class TestWafDetection:
    """HTML error pages from REST endpoints are flagged as possible WAF blocks."""

    def _html_response(self, status_code, body="<!DOCTYPE html><html>Blocked</html>"):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = status_code
        resp.json.side_effect = ValueError("not json")
        resp.text = body
        return resp

    @pytest.mark.parametrize("status", [403, 404, 406, 429, 503])
    def test_html_error_page_flagged(self, client, status):
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(self._html_response(status))
        assert exc_info.value.code == "possible_waf_block"
        assert exc_info.value.status_code == status

    def test_html_tag_without_doctype_flagged(self, client):
        resp = self._html_response(404, "<html><body>Not Found</body></html>")
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.code == "possible_waf_block"

    def test_leading_whitespace_still_flagged(self, client):
        resp = self._html_response(403, "\n  <!doctype html><html></html>")
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.code == "possible_waf_block"

    def test_non_html_body_not_flagged(self, client):
        resp = self._html_response(404, "plain text error")
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.code == "unknown"

    def test_html_on_other_status_not_flagged(self, client):
        # 502 from a reverse proxy is a gateway problem, not a WAF block
        resp = self._html_response(502)
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.code == "unknown"

    def test_json_error_unaffected(self, client):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 404
        resp.json.return_value = {"code": "rest_no_route", "message": "No route"}
        with pytest.raises(WPApiError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.code == "rest_no_route"


class TestRequestPasswordReset:
    """request_password_reset() — core lost-password flow for --send-email."""

    def _redirect_response(self, status_code=302, location=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.headers = {"Location": location} if location is not None else {}
        resp.url = "https://example.com/wp-login.php?action=lostpassword"
        resp.content = b""
        return resp

    @patch("wpa.api.requests.post")
    def test_success_on_checkemail_redirect(self, mock_post, client):
        mock_post.return_value = self._redirect_response(
            302, "https://example.com/wp-login.php?checkemail=confirm"
        )
        assert client.request_password_reset("newuser") is True

    @patch("wpa.api.requests.post")
    def test_posts_form_to_lostpassword(self, mock_post, client):
        mock_post.return_value = self._redirect_response(
            302, "https://example.com/wp-login.php?checkemail=confirm"
        )
        client.request_password_reset("newuser")
        args, kwargs = mock_post.call_args
        assert args == ("https://example.com/wp-login.php",)
        assert kwargs["params"] == {"action": "lostpassword"}
        assert kwargs["data"] == {"user_login": "newuser"}
        assert kwargs["allow_redirects"] is False
        # The lost-password form is public — credentials must never be sent
        assert "auth" not in kwargs
        assert "headers" not in kwargs

    @patch("wpa.api.requests.post")
    def test_failure_on_200_error_form(self, mock_post, client):
        resp = self._redirect_response(200)
        resp.text = "<html>Error: invalid username</html>"
        mock_post.return_value = resp
        assert client.request_password_reset("newuser") is False

    @patch("wpa.api.requests.post")
    def test_failure_on_redirect_without_confirm(self, mock_post, client):
        mock_post.return_value = self._redirect_response(
            302,
            "https://example.com/wp-login.php?action=lostpassword&error=invalidcombo",
        )
        assert client.request_password_reset("ghost") is False

    @patch("wpa.api.requests.post")
    def test_failure_on_waf_403(self, mock_post, client):
        mock_post.return_value = self._redirect_response(403)
        assert client.request_password_reset("newuser") is False

    @patch("wpa.api.requests.post")
    def test_connection_error(self, mock_post, client):
        mock_post.side_effect = requests.ConnectionError("refused")
        with pytest.raises(WPConnectionError):
            client.request_password_reset("newuser")

    @patch("wpa.api.requests.post")
    def test_timeout(self, mock_post, client):
        mock_post.side_effect = requests.Timeout("timed out")
        with pytest.raises(WPTimeoutError):
            client.request_password_reset("newuser")

    @patch("wpa.api.requests.post")
    def test_refuses_tls_downgrade(self, mock_post, client):
        resp = self._redirect_response(
            302, "http://example.com/wp-login.php?checkemail=confirm"
        )
        resp.url = "http://example.com/wp-login.php"
        mock_post.return_value = resp
        with pytest.raises(WPApiError, match="tls_downgrade|http"):
            client.request_password_reset("newuser")


class TestGetTotal:
    """get_total() — X-WP-Total via a single-item fetch."""

    def _response(self, total="1423", items=None):
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.headers = {"X-WP-Total": total} if total is not None else {}
        resp.content = b"[{}]"
        resp.json.return_value = items if items is not None else [{}]
        resp.url = "https://example.com/wp-json/wp/v2/comments"
        return resp

    @patch("wpa.api.requests.get")
    def test_returns_header_total(self, mock_get, client):
        mock_get.return_value = self._response("1423")
        assert client.get_total("comments") == 1423

    @patch("wpa.api.requests.get")
    def test_fetches_single_item(self, mock_get, client):
        mock_get.return_value = self._response()
        client.get_total("comments", params={"status": "hold"})
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["per_page"] == 1
        assert kwargs["params"]["status"] == "hold"

    @patch("wpa.api.requests.get")
    def test_does_not_mutate_caller_params(self, mock_get, client):
        mock_get.return_value = self._response()
        params = {"status": "hold"}
        client.get_total("comments", params=params)
        assert params == {"status": "hold"}

    @patch("wpa.api.requests.get")
    def test_missing_header_falls_back_to_body_length(self, mock_get, client):
        mock_get.return_value = self._response(total=None, items=[{}, {}])
        assert client.get_total("comments") == 2

    @patch("wpa.api.requests.get")
    def test_malformed_header_falls_back(self, mock_get, client):
        mock_get.return_value = self._response(total="lots")
        assert client.get_total("comments") == 1

    @patch("wpa.api.requests.get")
    def test_error_response_raises(self, mock_get, client):
        resp = MagicMock()
        resp.ok = False
        resp.status_code = 403
        resp.headers = {}
        resp.content = b'{"code": "rest_forbidden"}'
        resp.json.return_value = {"code": "rest_forbidden", "message": "No."}
        resp.url = "https://example.com/wp-json/wp/v2/comments"
        mock_get.return_value = resp
        with pytest.raises(WPApiError):
            client.get_total("comments")

    @patch("wpa.api.requests.get")
    def test_connection_error(self, mock_get, client):
        mock_get.side_effect = requests.ConnectionError("refused")
        with pytest.raises(WPConnectionError):
            client.get_total("comments")


class TestConfigurableCaps:
    """Tests for env-var-configurable response/pagination caps (#37)."""

    def test_response_cap_default(self):
        from wpa.api import DEFAULT_MAX_RESPONSE_BYTES, max_response_bytes

        assert max_response_bytes() == DEFAULT_MAX_RESPONSE_BYTES

    def test_total_pages_default(self):
        from wpa.api import DEFAULT_MAX_TOTAL_PAGES, max_total_pages

        assert max_total_pages() == DEFAULT_MAX_TOTAL_PAGES

    def test_response_cap_env_override(self, monkeypatch):
        from wpa.api import max_response_bytes

        monkeypatch.setenv("WPA_MAX_RESPONSE_BYTES", "1024")
        assert max_response_bytes() == 1024

    def test_total_pages_env_override(self, monkeypatch):
        from wpa.api import max_total_pages

        monkeypatch.setenv("WPA_MAX_TOTAL_PAGES", "5")
        assert max_total_pages() == 5

    def test_non_integer_env_falls_back_with_warning(self, monkeypatch, capsys):
        from wpa.api import DEFAULT_MAX_RESPONSE_BYTES, max_response_bytes

        monkeypatch.setenv("WPA_MAX_RESPONSE_BYTES", "lots")
        assert max_response_bytes() == DEFAULT_MAX_RESPONSE_BYTES
        assert "WPA_MAX_RESPONSE_BYTES" in capsys.readouterr().err

    def test_non_positive_env_falls_back_with_warning(self, monkeypatch, capsys):
        from wpa.api import DEFAULT_MAX_TOTAL_PAGES, max_total_pages

        monkeypatch.setenv("WPA_MAX_TOTAL_PAGES", "0")
        assert max_total_pages() == DEFAULT_MAX_TOTAL_PAGES
        assert "WPA_MAX_TOTAL_PAGES" in capsys.readouterr().err

    @patch("wpa.api.requests.request")
    def test_response_cap_env_enforced(self, mock_request, client, monkeypatch):
        monkeypatch.setenv("WPA_MAX_RESPONSE_BYTES", "10")

        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.url = "https://example.com/wp-json/wp/v2/posts"
        resp.content = b"x" * 11
        mock_request.return_value = resp

        with pytest.raises(WPApiError) as exc_info:
            client.get("posts")
        assert exc_info.value.code == "response_too_large"

    @patch("wpa.api.requests.get")
    def test_total_pages_env_enforced(self, mock_get, client, monkeypatch):
        monkeypatch.setenv("WPA_MAX_TOTAL_PAGES", "3")

        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.url = "https://example.com/wp-json/wp/v2/posts"
        resp.content = b"[]"
        resp.json.return_value = []
        resp.headers = {"X-WP-TotalPages": "999999"}
        mock_get.return_value = resp

        list(client.get_list("posts"))
        assert mock_get.call_count == 3
