"""Tests for wp-publish.py — TDD-equivalent backfill + v0.2.0 site config tests."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

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


@pytest.fixture()
def xdg_config(tmp_path, monkeypatch):
    """Set up XDG_CONFIG_HOME to a temp directory."""
    config_home = tmp_path / "config"
    config_home.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    return config_home


@pytest.fixture()
def single_site(xdg_config):
    """Create a single site config in XDG dir."""
    site_dir = xdg_config / "wpa" / "demo"
    site_dir.mkdir(parents=True)
    env = site_dir / ".env"
    env.write_text(
        "WP_SITE_URL=https://demo.example.com\n"
        "WP_USER=demouser\n"
        "WP_APP_PASSWORD=demo-pass\n"
        "WP_ADMIN_PATH=wp-admin\n"
    )
    return xdg_config


@pytest.fixture()
def multi_site(xdg_config):
    """Create multiple site configs in XDG dir."""
    for name, domain in [("alpha", "alpha.example.com"), ("beta", "beta.example.com")]:
        site_dir = xdg_config / "wpa" / name
        site_dir.mkdir(parents=True)
        env = site_dir / ".env"
        env.write_text(
            f"WP_SITE_URL=https://{domain}\n"
            f"WP_USER={name}user\n"
            f"WP_APP_PASSWORD={name}-pass\n"
            "WP_ADMIN_PATH=wp-admin\n"
        )
    return xdg_config


# ---------------------------------------------------------------------------
# load_config tests (legacy interface)
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_missing_env_file_exits(self, tmp_path, monkeypatch):
        """load_config exits 1 when .env file doesn't exist."""
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        with pytest.raises(SystemExit) as exc_info:
            wp_publish.load_config(env_path=str(tmp_path / ".env"))
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
            wp_publish.load_config(env_path=str(env))
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
        site_url, user, password = wp_publish.load_config(env_path=str(valid_env_file / ".env"))
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
            wp_publish.load_config(env_path=str(env))
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
        site_url, _, _ = wp_publish.load_config(env_path=str(env))
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

    def test_custom_admin_path_in_edit_url(self, capsys):
        """publish_page uses custom admin_path in edit URL."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 42}

        with patch("requests.post", return_value=mock_response):
            result = wp_publish.publish_page(
                "https://example.com", "user", "pass",
                "Title", "slug", "draft", "<p>Content</p>",
                admin_path="secret-admin",
            )

        assert result == 0
        output = capsys.readouterr().out
        assert "secret-admin/post.php" in output

    def test_default_admin_path(self, capsys):
        """publish_page defaults to wp-admin in edit URL."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 42}

        with patch("requests.post", return_value=mock_response):
            result = wp_publish.publish_page(
                "https://example.com", "user", "pass",
                "Title", "slug", "draft", "<p>Content</p>",
            )

        assert result == 0
        output = capsys.readouterr().out
        assert "wp-admin/post.php" in output


# ---------------------------------------------------------------------------
# get_config_dir tests
# ---------------------------------------------------------------------------


class TestGetConfigDir:
    def test_xdg_config_home_respected(self, monkeypatch):
        """get_config_dir uses XDG_CONFIG_HOME when set."""
        monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
        assert wp_publish.get_config_dir() == Path("/custom/config/wpa")

    def test_default_config_dir(self, monkeypatch):
        """get_config_dir defaults to ~/.config/wpa."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        expected = Path.home() / ".config" / "wpa"
        assert wp_publish.get_config_dir() == expected


# ---------------------------------------------------------------------------
# list_sites tests
# ---------------------------------------------------------------------------


class TestListSites:
    def test_empty_when_no_config_dir(self, xdg_config):
        """list_sites returns empty list when wpa dir doesn't exist."""
        assert wp_publish.list_sites() == []

    def test_empty_when_no_sites(self, xdg_config):
        """list_sites returns empty list when wpa dir exists but is empty."""
        (xdg_config / "wpa").mkdir()
        assert wp_publish.list_sites() == []

    def test_returns_sorted_sites(self, multi_site):
        """list_sites returns site names sorted alphabetically."""
        sites = wp_publish.list_sites()
        assert sites == ["alpha", "beta"]

    def test_ignores_dirs_without_env(self, xdg_config):
        """list_sites ignores directories that don't have .env files."""
        wpa_dir = xdg_config / "wpa"
        wpa_dir.mkdir()
        (wpa_dir / "empty-site").mkdir()
        (wpa_dir / "valid-site").mkdir()
        (wpa_dir / "valid-site" / ".env").write_text("WP_SITE_URL=https://x.com\n")
        assert wp_publish.list_sites() == ["valid-site"]


# ---------------------------------------------------------------------------
# validate_site_name tests
# ---------------------------------------------------------------------------


class TestValidateSiteName:
    def test_valid_alphanumeric(self):
        assert wp_publish.validate_site_name("demo") is True

    def test_valid_with_hyphens(self):
        assert wp_publish.validate_site_name("my-site") is True

    def test_valid_with_numbers(self):
        assert wp_publish.validate_site_name("site1") is True

    def test_invalid_empty(self):
        assert wp_publish.validate_site_name("") is False

    def test_invalid_spaces(self):
        assert wp_publish.validate_site_name("my site") is False

    def test_invalid_special_chars(self):
        assert wp_publish.validate_site_name("my_site!") is False

    def test_invalid_starts_with_hyphen(self):
        assert wp_publish.validate_site_name("-leading") is False

    def test_invalid_path_traversal(self):
        assert wp_publish.validate_site_name("../etc") is False


# ---------------------------------------------------------------------------
# create_site_config tests
# ---------------------------------------------------------------------------


class TestCreateSiteConfig:
    def test_creates_config_successfully(self, xdg_config, monkeypatch):
        """create_site_config creates .env file at correct path."""
        inputs = iter(["https://example.com", "testuser", "wp-admin"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "secret-pass")

        env_path = wp_publish.create_site_config(site_name="mysite")

        expected = xdg_config / "wpa" / "mysite" / ".env"
        assert env_path == expected
        assert expected.exists()
        content = expected.read_text()
        assert "WP_SITE_URL=https://example.com" in content
        assert "WP_USER=testuser" in content
        assert "WP_APP_PASSWORD=secret-pass" in content
        assert "WP_ADMIN_PATH=wp-admin" in content

    def test_file_permissions_600(self, xdg_config, monkeypatch):
        """create_site_config sets .env file permissions to 600."""
        inputs = iter(["https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        env_path = wp_publish.create_site_config(site_name="test")

        import stat
        mode = env_path.stat().st_mode & 0o777
        assert mode == 0o600

    def test_invalid_site_name_exits(self, xdg_config, monkeypatch):
        """create_site_config exits on invalid site name."""
        with pytest.raises(SystemExit) as exc_info:
            wp_publish.create_site_config(site_name="../bad")
        assert exc_info.value.code == 1

    def test_prompts_for_site_name(self, xdg_config, monkeypatch):
        """create_site_config prompts for name when not given."""
        inputs = iter(["mysite", "https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        env_path = wp_publish.create_site_config()
        assert "mysite" in str(env_path)

    def test_https_required(self, xdg_config, monkeypatch):
        """create_site_config rejects http:// and re-prompts."""
        inputs = iter(["http://bad.com", "https://good.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        env_path = wp_publish.create_site_config(site_name="test")
        content = env_path.read_text()
        assert "https://good.com" in content

    def test_overwrite_protection_decline(self, single_site, monkeypatch):
        """create_site_config exits when user declines overwrite."""
        monkeypatch.setattr("builtins.input", lambda prompt: "n")

        with pytest.raises(SystemExit) as exc_info:
            wp_publish.create_site_config(site_name="demo")
        assert exc_info.value.code == 0

    def test_overwrite_protection_accept(self, single_site, monkeypatch):
        """create_site_config overwrites when user confirms."""
        inputs = iter(["y", "https://new.example.com", "newuser", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "newpass")

        env_path = wp_publish.create_site_config(site_name="demo")
        content = env_path.read_text()
        assert "https://new.example.com" in content

    def test_empty_user_exits(self, xdg_config, monkeypatch):
        """create_site_config exits if WP_USER is empty."""
        inputs = iter(["https://example.com", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        with pytest.raises(SystemExit) as exc_info:
            wp_publish.create_site_config(site_name="test")
        assert exc_info.value.code == 1

    def test_empty_password_exits(self, xdg_config, monkeypatch):
        """create_site_config exits if password is empty."""
        inputs = iter(["https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "")

        with pytest.raises(SystemExit) as exc_info:
            wp_publish.create_site_config(site_name="test")
        assert exc_info.value.code == 1

    def test_default_admin_path(self, xdg_config, monkeypatch):
        """create_site_config defaults WP_ADMIN_PATH to wp-admin."""
        inputs = iter(["https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        env_path = wp_publish.create_site_config(site_name="test")
        content = env_path.read_text()
        assert "WP_ADMIN_PATH=wp-admin" in content

    def test_uses_getpass_for_password(self, xdg_config, monkeypatch):
        """create_site_config uses getpass.getpass for password input."""
        inputs = iter(["https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        getpass_called = []
        def mock_getpass(prompt):
            getpass_called.append(prompt)
            return "secret"

        monkeypatch.setattr("getpass.getpass", mock_getpass)
        wp_publish.create_site_config(site_name="test")
        assert len(getpass_called) == 1


# ---------------------------------------------------------------------------
# resolve_config tests
# ---------------------------------------------------------------------------


class TestResolveConfig:
    def test_site_flag_loads_named_config(self, single_site, monkeypatch):
        """resolve_config with site_name loads that config directly."""
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        site_url, user, password, admin_path = wp_publish.resolve_config(site_name="demo")
        assert site_url == "https://demo.example.com"
        assert user == "demouser"
        assert password == "demo-pass"
        assert admin_path == "wp-admin"

    def test_site_flag_not_found_exits(self, xdg_config, monkeypatch):
        """resolve_config exits 1 when named site doesn't exist."""
        (xdg_config / "wpa").mkdir(parents=True)
        with pytest.raises(SystemExit) as exc_info:
            wp_publish.resolve_config(site_name="nonexistent")
        assert exc_info.value.code == 1

    def test_site_flag_not_found_shows_available(self, single_site, capsys):
        """resolve_config shows available sites when named site not found."""
        with pytest.raises(SystemExit):
            wp_publish.resolve_config(site_name="nonexistent")
        output = capsys.readouterr().out
        assert "demo" in output

    def test_single_site_auto_selected(self, single_site, monkeypatch, capsys):
        """resolve_config auto-selects when only one config exists."""
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        site_url, user, password, admin_path = wp_publish.resolve_config()
        assert site_url == "https://demo.example.com"
        output = capsys.readouterr().out
        assert "Using site: demo" in output

    def test_multiple_sites_prompt_select(self, multi_site, monkeypatch):
        """resolve_config prompts for selection with multiple configs."""
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        monkeypatch.setattr("builtins.input", lambda prompt: "2")
        site_url, user, _, _ = wp_publish.resolve_config()
        assert site_url == "https://beta.example.com"
        assert user == "betauser"

    def test_multiple_sites_invalid_then_valid(self, multi_site, monkeypatch):
        """resolve_config re-prompts on invalid selection."""
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        inputs = iter(["99", "abc", "1"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        site_url, _, _, _ = wp_publish.resolve_config()
        assert site_url == "https://alpha.example.com"

    def test_zero_configs_triggers_creation(self, xdg_config, monkeypatch):
        """resolve_config offers creation when no configs exist."""
        monkeypatch.setattr(wp_publish, "__file__", str(xdg_config / "fake" / "wp-publish.py"))
        (xdg_config / "wpa").mkdir(parents=True)

        # Mock the input sequence for create_site_config
        inputs = iter(["newsite", "https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        site_url, user, password, admin_path = wp_publish.resolve_config()
        assert site_url == "https://example.com"

    def test_zero_configs_migration_path(self, xdg_config, tmp_path, monkeypatch):
        """resolve_config uses migration when repo .env exists and no XDG configs."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo_env = repo_dir / ".env"
        repo_env.write_text(
            "WP_SITE_URL=https://migrated.example.com\n"
            "WP_USER=migrateuser\n"
            "WP_APP_PASSWORD=migratepass\n"
        )
        monkeypatch.setattr(wp_publish, "__file__", str(repo_dir / "wp-publish.py"))
        (xdg_config / "wpa").mkdir(parents=True)

        inputs = iter(["migrated", "n"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        site_url, user, password, admin_path = wp_publish.resolve_config()
        assert site_url == "https://migrated.example.com"
        assert user == "migrateuser"

    def test_site_flag_no_interactive_prompts(self, single_site, monkeypatch):
        """resolve_config with --site never calls input()."""
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        input_called = []
        original_input = input
        def tracking_input(prompt):
            input_called.append(prompt)
            return original_input(prompt)

        monkeypatch.setattr("builtins.input", tracking_input)
        wp_publish.resolve_config(site_name="demo")
        assert len(input_called) == 0


# ---------------------------------------------------------------------------
# _load_env tests
# ---------------------------------------------------------------------------


class TestLoadEnv:
    def test_loads_all_fields(self, xdg_config, monkeypatch):
        """_load_env returns all four fields from .env."""
        site_dir = xdg_config / "wpa" / "test"
        site_dir.mkdir(parents=True)
        env = site_dir / ".env"
        env.write_text(
            "WP_SITE_URL=https://test.example.com/\n"
            "WP_USER=testuser\n"
            "WP_APP_PASSWORD=testpass\n"
            "WP_ADMIN_PATH=secret-admin\n"
        )
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        site_url, user, password, admin_path = wp_publish._load_env(env)
        assert site_url == "https://test.example.com"  # trailing slash stripped
        assert user == "testuser"
        assert password == "testpass"
        assert admin_path == "secret-admin"

    def test_default_admin_path(self, xdg_config, monkeypatch):
        """_load_env defaults admin_path to wp-admin."""
        site_dir = xdg_config / "wpa" / "test"
        site_dir.mkdir(parents=True)
        env = site_dir / ".env"
        env.write_text(
            "WP_SITE_URL=https://test.example.com\n"
            "WP_USER=testuser\n"
            "WP_APP_PASSWORD=testpass\n"
        )
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        _, _, _, admin_path = wp_publish._load_env(env)
        assert admin_path == "wp-admin"

    def test_http_url_rejected(self, xdg_config, monkeypatch):
        """_load_env exits 1 for HTTP URLs."""
        site_dir = xdg_config / "wpa" / "test"
        site_dir.mkdir(parents=True)
        env = site_dir / ".env"
        env.write_text(
            "WP_SITE_URL=http://insecure.com\n"
            "WP_USER=user\n"
            "WP_APP_PASSWORD=pass\n"
        )
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            wp_publish._load_env(env)
        assert exc_info.value.code == 1

    def test_missing_vars_exits(self, xdg_config, monkeypatch):
        """_load_env exits 1 when required vars are missing."""
        site_dir = xdg_config / "wpa" / "test"
        site_dir.mkdir(parents=True)
        env = site_dir / ".env"
        env.write_text("WP_SITE_URL=https://example.com\n")
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            wp_publish._load_env(env)
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# migrate_repo_env tests
# ---------------------------------------------------------------------------


class TestMigrateRepoEnv:
    def test_no_repo_env_returns_none(self, tmp_path, monkeypatch):
        """migrate_repo_env returns None when no repo-root .env."""
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        assert wp_publish.migrate_repo_env() is None

    def test_existing_xdg_configs_skips_migration(self, single_site, tmp_path, monkeypatch):
        """migrate_repo_env returns None when XDG configs already exist."""
        repo_env = tmp_path / ".env"
        repo_env.write_text("WP_SITE_URL=https://old.com\n")
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        assert wp_publish.migrate_repo_env() is None

    def test_migration_creates_xdg_config(self, xdg_config, tmp_path, monkeypatch):
        """migrate_repo_env copies repo .env to XDG path."""
        repo_env = tmp_path / ".env"
        repo_env.write_text(
            "WP_SITE_URL=https://migrated.com\n"
            "WP_USER=migrateuser\n"
            "WP_APP_PASSWORD=migratepass\n"
        )
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        inputs = iter(["migrated", "n"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        result = wp_publish.migrate_repo_env()
        assert result is not None
        content = result.read_text()
        assert "https://migrated.com" in content
        assert "WP_ADMIN_PATH=wp-admin" in content  # Added during migration

    def test_migration_user_skips(self, xdg_config, tmp_path, monkeypatch):
        """migrate_repo_env returns None when user skips."""
        repo_env = tmp_path / ".env"
        repo_env.write_text("WP_SITE_URL=https://old.com\n")
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        monkeypatch.setattr("builtins.input", lambda prompt: "")

        assert wp_publish.migrate_repo_env() is None

    def test_migration_deletes_old_env(self, xdg_config, tmp_path, monkeypatch):
        """migrate_repo_env deletes repo .env when user confirms."""
        repo_env = tmp_path / ".env"
        repo_env.write_text(
            "WP_SITE_URL=https://old.com\n"
            "WP_USER=user\n"
            "WP_APP_PASSWORD=pass\n"
        )
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        inputs = iter(["oldsite", "y"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        wp_publish.migrate_repo_env()
        assert not repo_env.exists()

    def test_migration_keeps_old_env(self, xdg_config, tmp_path, monkeypatch):
        """migrate_repo_env keeps repo .env when user declines deletion."""
        repo_env = tmp_path / ".env"
        repo_env.write_text(
            "WP_SITE_URL=https://old.com\n"
            "WP_USER=user\n"
            "WP_APP_PASSWORD=pass\n"
        )
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        inputs = iter(["oldsite", "n"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        wp_publish.migrate_repo_env()
        assert repo_env.exists()

    def test_migration_invalid_name_returns_none(self, xdg_config, tmp_path, monkeypatch):
        """migrate_repo_env returns None on invalid site name."""
        repo_env = tmp_path / ".env"
        repo_env.write_text("WP_SITE_URL=https://old.com\n")
        monkeypatch.setattr(wp_publish, "__file__", str(tmp_path / "wp-publish.py"))
        monkeypatch.setattr("builtins.input", lambda prompt: "../bad")

        assert wp_publish.migrate_repo_env() is None


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

    def test_full_pipeline(self, single_site, valid_md_file, monkeypatch):
        """main runs the full pipeline and returns 0 on success."""
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)
        monkeypatch.setattr("sys.argv", ["wp-publish.py", "--site", "demo", str(valid_md_file)])

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 99}

        with patch("requests.post", return_value=mock_response):
            result = wp_publish.main()

        assert result == 0

    def test_new_site_flag(self, xdg_config, monkeypatch, capsys):
        """main --new-site runs interactive creation and returns 0."""
        monkeypatch.setattr("sys.argv", ["wp-publish.py", "--new-site"])
        inputs = iter(["testsite", "https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        result = wp_publish.main()
        assert result == 0
        output = capsys.readouterr().out
        assert "Saved to" in output

    def test_version_flag(self, monkeypatch, capsys):
        """main --version prints version and exits."""
        monkeypatch.setattr("sys.argv", ["wp-publish.py", "--version"])
        with pytest.raises(SystemExit) as exc_info:
            wp_publish.main()
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert "0.2.0" in output
