"""Tests for wp-publish.py — TDD-equivalent backfill."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

# Add repo root to path so we can import the script
sys.path.insert(0, str(Path(__file__).parent.parent))
import importlib

wp_publish = importlib.import_module("wp-publish")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def valid_env_file(tmp_path):
    """Create a valid .env file in tmp_path."""
    env = tmp_path / ".env"
    env.write_text(
        "WP_SITE_URL=https://example.com\n"
        "WP_USER=testuser\n"
        "WP_APP_PASSWORD=xxxx xxxx xxxx xxxx\n"
    )
    return tmp_path


@pytest.fixture()
def valid_md_file(tmp_path):
    """Create a valid markdown file with frontmatter."""
    md = tmp_path / "test-page.md"
    md.write_text(
        "---\n"
        'title: "Test Page"\n'
        'slug: "test-page"\n'
        "status: draft\n"
        "---\n"
        "\n"
        "Hello **world**.\n"
    )
    return md


@pytest.fixture()
def minimal_md_file(tmp_path):
    """Markdown file with only required title — no slug or status."""
    md = tmp_path / "minimal.md"
    md.write_text(
        "---\n"
        'title: "Minimal Page"\n'
        "---\n"
        "\n"
        "Content here.\n"
    )
    return md


@pytest.fixture()
def no_title_md_file(tmp_path):
    """Markdown file missing the required title field."""
    md = tmp_path / "no-title.md"
    md.write_text(
        "---\n"
        'slug: "oops"\n'
        "---\n"
        "\n"
        "No title.\n"
    )
    return md


# ---------------------------------------------------------------------------
# load_config tests
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_missing_env_file_exits(self, tmp_path, monkeypatch):
        """load_config exits 1 when .env file doesn't exist."""
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        with pytest.raises(SystemExit) as exc_info:
            wp_publish.load_config()
        assert exc_info.value.code == 1

    def test_incomplete_env_vars_exits(self, tmp_path, monkeypatch):
        """load_config exits 1 when env vars are incomplete."""
        env = tmp_path / ".env"
        env.write_text("WP_SITE_URL=https://example.com\n")
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        # Clear any pre-existing vars
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            wp_publish.load_config()
        assert exc_info.value.code == 1

    def test_valid_env_returns_config(self, valid_env_file, monkeypatch):
        """load_config returns (site_url, user, password) from valid .env."""
        monkeypatch.setattr(
            wp_publish, "__file__", str(valid_env_file / "wp-publish.py")
        )
        # Clear env to ensure load_dotenv does the work
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        site_url, user, password = wp_publish.load_config()
        assert site_url == "https://example.com"
        assert user == "testuser"
        assert password == "xxxx xxxx xxxx xxxx"

    def test_http_url_rejected(self, tmp_path, monkeypatch):
        """load_config exits 1 when site URL uses HTTP instead of HTTPS."""
        env = tmp_path / ".env"
        env.write_text(
            "WP_SITE_URL=http://example.com\n"
            "WP_USER=testuser\n"
            "WP_APP_PASSWORD=testpass\n"
        )
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            wp_publish.load_config()
        assert exc_info.value.code == 1

    def test_trailing_slash_stripped(self, tmp_path, monkeypatch):
        """load_config strips trailing slash from site URL."""
        env = tmp_path / ".env"
        env.write_text(
            "WP_SITE_URL=https://example.com/\n"
            "WP_USER=testuser\n"
            "WP_APP_PASSWORD=testpass\n"
        )
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        site_url, _, _ = wp_publish.load_config()
        assert site_url == "https://example.com"


# ---------------------------------------------------------------------------
# parse_page tests
# ---------------------------------------------------------------------------


class TestParsePage:
    def test_file_not_found_exits(self):
        """parse_page exits 1 for nonexistent file."""
        with pytest.raises(SystemExit) as exc_info:
            wp_publish.parse_page("/nonexistent/file.md")
        assert exc_info.value.code == 1

    def test_missing_title_exits(self, no_title_md_file):
        """parse_page exits 1 when frontmatter has no title."""
        with pytest.raises(SystemExit) as exc_info:
            wp_publish.parse_page(str(no_title_md_file))
        assert exc_info.value.code == 1

    def test_valid_file_returns_all_fields(self, valid_md_file):
        """parse_page returns title, slug, status, and HTML content."""
        title, slug, status, html = wp_publish.parse_page(str(valid_md_file))
        assert title == "Test Page"
        assert slug == "test-page"
        assert status == "draft"
        assert "<strong>world</strong>" in html

    def test_defaults_slug_empty_and_status_draft(self, minimal_md_file):
        """parse_page defaults slug to '' and status to 'draft'."""
        title, slug, status, html = wp_publish.parse_page(str(minimal_md_file))
        assert title == "Minimal Page"
        assert slug == ""
        assert status == "draft"

    def test_invalid_status_exits(self, tmp_path):
        """parse_page exits 1 when frontmatter has invalid status."""
        md = tmp_path / "bad-status.md"
        md.write_text(
            "---\n"
            'title: "Bad Status"\n'
            "status: publis\n"
            "---\n"
            "\n"
            "Typo in status.\n"
        )
        with pytest.raises(SystemExit) as exc_info:
            wp_publish.parse_page(str(md))
        assert exc_info.value.code == 1

    def test_publish_status_accepted(self, tmp_path):
        """parse_page accepts 'publish' as a valid status."""
        md = tmp_path / "publish.md"
        md.write_text(
            "---\n"
            'title: "Published Page"\n'
            "status: publish\n"
            "---\n"
            "\n"
            "Going live.\n"
        )
        _, _, status, _ = wp_publish.parse_page(str(md))
        assert status == "publish"


# ---------------------------------------------------------------------------
# publish_page tests
# ---------------------------------------------------------------------------


class TestPublishPage:
    def test_success_returns_zero(self, capsys):
        """publish_page returns 0 and prints page info on 201."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 42}

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = wp_publish.publish_page(
                "https://example.com", "user", "pass",
                "Test Title", "test-slug", "draft", "<p>Hello</p>",
            )

        assert result == 0
        output = capsys.readouterr().out
        assert "42" in output
        assert "edit" in output.lower()

        # Verify the POST was called correctly
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["auth"] == ("user", "pass")
        assert call_kwargs.kwargs["json"]["title"] == "Test Title"
        assert call_kwargs.kwargs["json"]["slug"] == "test-slug"

    def test_slug_omitted_when_empty(self):
        """publish_page does not include slug in payload when empty."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1}

        with patch("requests.post", return_value=mock_response) as mock_post:
            wp_publish.publish_page(
                "https://example.com", "user", "pass",
                "Title", "", "draft", "<p>Content</p>",
            )

        payload = mock_post.call_args.kwargs["json"]
        assert "slug" not in payload

    def test_api_error_returns_one(self, capsys):
        """publish_page returns 1 and prints error on non-201."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "code": "rest_forbidden",
            "message": "Sorry, you are not allowed to create posts.",
        }

        with patch("requests.post", return_value=mock_response):
            result = wp_publish.publish_page(
                "https://example.com", "user", "pass",
                "Title", "slug", "draft", "<p>Content</p>",
            )

        assert result == 1
        output = capsys.readouterr().out
        assert "403" in output
        assert "rest_forbidden" in output

    def test_non_json_error_body(self, capsys):
        """publish_page handles non-JSON error responses gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.text = "<html>Internal Server Error</html>"

        with patch("requests.post", return_value=mock_response):
            result = wp_publish.publish_page(
                "https://example.com", "user", "pass",
                "Title", "slug", "draft", "<p>Content</p>",
            )

        assert result == 1
        output = capsys.readouterr().out
        assert "500" in output
        assert "Internal Server Error" in output

    def test_connection_error_returns_one(self, capsys):
        """publish_page returns 1 on connection failure."""
        with patch("requests.post", side_effect=requests.ConnectionError("DNS failed")):
            result = wp_publish.publish_page(
                "https://example.com", "user", "pass",
                "Title", "slug", "draft", "<p>Content</p>",
            )

        assert result == 1
        output = capsys.readouterr().out
        assert "Could not connect" in output

    def test_timeout_returns_one(self, capsys):
        """publish_page returns 1 on request timeout."""
        with patch("requests.post", side_effect=requests.Timeout("timed out")):
            result = wp_publish.publish_page(
                "https://example.com", "user", "pass",
                "Title", "slug", "draft", "<p>Content</p>",
            )

        assert result == 1
        output = capsys.readouterr().out
        assert "timed out" in output

    def test_generic_request_error_returns_one(self, capsys):
        """publish_page returns 1 on generic RequestException."""
        with patch("requests.post", side_effect=requests.RequestException("something broke")):
            result = wp_publish.publish_page(
                "https://example.com", "user", "pass",
                "Title", "slug", "draft", "<p>Content</p>",
            )

        assert result == 1
        output = capsys.readouterr().out
        assert "Request failed" in output


# ---------------------------------------------------------------------------
# main integration tests
# ---------------------------------------------------------------------------


class TestMain:
    def test_no_args_exits_with_error(self, monkeypatch):
        """main exits 2 (argparse error) when no file argument provided."""
        monkeypatch.setattr("sys.argv", ["wp-publish.py"])
        with pytest.raises(SystemExit) as exc_info:
            wp_publish.main()
        assert exc_info.value.code == 2

    def test_full_pipeline(self, valid_env_file, valid_md_file, monkeypatch):
        """main runs the full pipeline and returns 0 on success."""
        monkeypatch.setattr(
            wp_publish, "__file__", str(valid_env_file / "wp-publish.py")
        )
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.setattr("sys.argv", ["wp-publish.py", str(valid_md_file)])

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 99}

        with patch("requests.post", return_value=mock_response):
            result = wp_publish.main()

        assert result == 0
