"""Tests for wpa.api — shared REST API client."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from wpa.api import WPApiClient
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
        args, kwargs = mock_request.call_args
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
