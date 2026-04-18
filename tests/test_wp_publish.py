"""Tests for wpa package — TDD-equivalent backfill + v0.2.0 site config tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import wpa.config as wpa_config
from wpa.config import (
    _load_env,
    create_site_config,
    get_config_dir,
    is_private_url,
    list_sites,
    migrate_repo_env,
    resolve_config,
    validate_site_name,
)
from wpa.exceptions import WPApiError, WPConnectionError, WPTimeoutError
from wpa.publish import parse_markdown, parse_page, publish_page
from wpa.cli import main


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
    md.write_text('---\ntitle: "Minimal Page"\n---\n\nContent here.\n')
    return md


@pytest.fixture()
def no_title_md_file(tmp_path):
    """Markdown file missing the required title field."""
    md = tmp_path / "no-title.md"
    md.write_text('---\nslug: "oops"\n---\n\nNo title.\n')
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
# parse_page tests
# ---------------------------------------------------------------------------


class TestParsePage:
    def test_file_not_found_exits(self):
        """parse_page exits 1 for nonexistent file."""
        with pytest.raises(SystemExit) as exc_info:
            parse_page("/nonexistent/file.md")
        assert exc_info.value.code == 1

    def test_missing_title_exits(self, no_title_md_file):
        """parse_page exits 1 when frontmatter has no title."""
        with pytest.raises(SystemExit) as exc_info:
            parse_page(str(no_title_md_file))
        assert exc_info.value.code == 1

    def test_valid_file_returns_all_fields(self, valid_md_file):
        """parse_page returns title, slug, status, and HTML content."""
        title, slug, status, html = parse_page(str(valid_md_file))
        assert title == "Test Page"
        assert slug == "test-page"
        assert status == "draft"
        assert "<strong>world</strong>" in html

    def test_defaults_slug_empty_and_status_draft(self, minimal_md_file):
        """parse_page defaults slug to '' and status to 'draft'."""
        title, slug, status, html = parse_page(str(minimal_md_file))
        assert title == "Minimal Page"
        assert slug == ""
        assert status == "draft"

    def test_invalid_status_exits(self, tmp_path):
        """parse_page exits 1 when frontmatter has invalid status."""
        md = tmp_path / "bad-status.md"
        md.write_text(
            '---\ntitle: "Bad Status"\nstatus: publis\n---\n\nTypo in status.\n'
        )
        with pytest.raises(SystemExit) as exc_info:
            parse_page(str(md))
        assert exc_info.value.code == 1

    def test_publish_status_accepted(self, tmp_path):
        """parse_page accepts 'publish' as a valid status."""
        md = tmp_path / "publish.md"
        md.write_text(
            '---\ntitle: "Published Page"\nstatus: publish\n---\n\nGoing live.\n'
        )
        _, _, status, _ = parse_page(str(md))
        assert status == "publish"


# ---------------------------------------------------------------------------
# publish_page tests
# ---------------------------------------------------------------------------


class TestPublishPage:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.site_url = "https://example.com"
        return client

    def test_success_returns_zero(self, mock_client, capsys):
        """publish_page returns 0 and prints page info on success."""
        mock_client.post.return_value = {"id": 42}

        result = publish_page(
            mock_client, "Test Title", "test-slug", "draft", "<p>Hello</p>"
        )

        assert result == 0
        output = capsys.readouterr().out
        assert "42" in output
        assert "edit" in output.lower()

        # Verify the POST was called correctly
        mock_client.post.assert_called_once()
        data = mock_client.post.call_args[1]["data"]
        assert data["title"] == "Test Title"
        assert data["slug"] == "test-slug"

    def test_slug_omitted_when_empty(self, mock_client):
        """publish_page does not include slug in payload when empty."""
        mock_client.post.return_value = {"id": 1}

        publish_page(mock_client, "Title", "", "draft", "<p>Content</p>")

        data = mock_client.post.call_args[1]["data"]
        assert "slug" not in data

    def test_api_error_returns_one(self, mock_client, capsys):
        """publish_page returns 1 and prints error on API error."""
        mock_client.post.side_effect = WPApiError(
            403, "rest_forbidden", "Sorry, you are not allowed to create posts."
        )

        result = publish_page(mock_client, "Title", "slug", "draft", "<p>Content</p>")

        assert result == 1
        output = capsys.readouterr().out
        assert "403" in output
        assert "rest_forbidden" in output

    def test_non_json_error_body(self, mock_client, capsys):
        """publish_page handles WPApiError with non-JSON details."""
        mock_client.post.side_effect = WPApiError(
            500, "unknown", "Internal Server Error"
        )

        result = publish_page(mock_client, "Title", "slug", "draft", "<p>Content</p>")

        assert result == 1
        output = capsys.readouterr().out
        assert "500" in output
        assert "Internal Server Error" in output

    def test_connection_error_returns_one(self, mock_client, capsys):
        """publish_page returns 1 on connection failure."""
        mock_client.post.side_effect = WPConnectionError(
            "Could not connect to https://example.com"
        )

        result = publish_page(mock_client, "Title", "slug", "draft", "<p>Content</p>")

        assert result == 1
        output = capsys.readouterr().out
        assert "Could not connect" in output

    def test_timeout_returns_one(self, mock_client, capsys):
        """publish_page returns 1 on request timeout."""
        mock_client.post.side_effect = WPTimeoutError(
            "Request timed out after 30 seconds"
        )

        result = publish_page(mock_client, "Title", "slug", "draft", "<p>Content</p>")

        assert result == 1
        output = capsys.readouterr().out
        assert "timed out" in output

    def test_custom_admin_path_in_edit_url(self, mock_client, capsys):
        """publish_page uses custom admin_path in edit URL."""
        mock_client.post.return_value = {"id": 42}

        result = publish_page(
            mock_client,
            "Title",
            "slug",
            "draft",
            "<p>Content</p>",
            admin_path="secret-admin",
        )

        assert result == 0
        output = capsys.readouterr().out
        assert "secret-admin/post.php" in output

    def test_default_admin_path(self, mock_client, capsys):
        """publish_page defaults to wp-admin in edit URL."""
        mock_client.post.return_value = {"id": 42}

        result = publish_page(mock_client, "Title", "slug", "draft", "<p>Content</p>")

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
        assert get_config_dir() == Path("/custom/config/wpa")

    def test_default_config_dir(self, monkeypatch):
        """get_config_dir defaults to ~/.config/wpa."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        expected = Path.home() / ".config" / "wpa"
        assert get_config_dir() == expected


# ---------------------------------------------------------------------------
# list_sites tests
# ---------------------------------------------------------------------------


class TestListSites:
    def test_empty_when_no_config_dir(self, xdg_config):
        """list_sites returns empty list when wpa dir doesn't exist."""
        assert list_sites() == []

    def test_empty_when_no_sites(self, xdg_config):
        """list_sites returns empty list when wpa dir exists but is empty."""
        (xdg_config / "wpa").mkdir()
        assert list_sites() == []

    def test_returns_sorted_sites(self, multi_site):
        """list_sites returns site names sorted alphabetically."""
        sites = list_sites()
        assert sites == ["alpha", "beta"]

    def test_ignores_dirs_without_env(self, xdg_config):
        """list_sites ignores directories that don't have .env files."""
        wpa_dir = xdg_config / "wpa"
        wpa_dir.mkdir()
        (wpa_dir / "empty-site").mkdir()
        (wpa_dir / "valid-site").mkdir()
        (wpa_dir / "valid-site" / ".env").write_text("WP_SITE_URL=https://x.com\n")
        assert list_sites() == ["valid-site"]


# ---------------------------------------------------------------------------
# validate_site_name tests
# ---------------------------------------------------------------------------


class TestValidateSiteName:
    def test_valid_alphanumeric(self):
        assert validate_site_name("demo") is True

    def test_valid_with_hyphens(self):
        assert validate_site_name("my-site") is True

    def test_valid_with_numbers(self):
        assert validate_site_name("site1") is True

    def test_invalid_empty(self):
        assert validate_site_name("") is False

    def test_invalid_spaces(self):
        assert validate_site_name("my site") is False

    def test_invalid_special_chars(self):
        assert validate_site_name("my_site!") is False

    def test_invalid_starts_with_hyphen(self):
        assert validate_site_name("-leading") is False

    def test_invalid_path_traversal(self):
        assert validate_site_name("../etc") is False


# ---------------------------------------------------------------------------
# create_site_config tests
# ---------------------------------------------------------------------------


class TestCreateSiteConfig:
    def test_creates_config_successfully(self, xdg_config, monkeypatch):
        """create_site_config creates .env file at correct path."""
        inputs = iter(["https://example.com", "testuser", "wp-admin"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "secret-pass")

        env_path = create_site_config(site_name="mysite")

        expected = xdg_config / "wpa" / "mysite" / ".env"
        assert env_path == expected
        assert expected.exists()
        content = expected.read_text()
        assert "WP_SITE_URL=https://example.com" in content
        assert "WP_USER=testuser" in content
        assert "WP_APP_PASSWORD=secret-pass" in content
        assert "WP_ADMIN_PATH=wp-admin" in content

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Unix file permissions not supported on Windows"
    )
    def test_file_permissions_600(self, xdg_config, monkeypatch):
        """create_site_config sets .env file permissions to 600."""
        inputs = iter(["https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        env_path = create_site_config(site_name="test")

        mode = env_path.stat().st_mode & 0o777
        assert mode == 0o600

    def test_invalid_site_name_exits(self, xdg_config, monkeypatch):
        """create_site_config exits on invalid site name."""
        with pytest.raises(SystemExit) as exc_info:
            create_site_config(site_name="../bad")
        assert exc_info.value.code == 1

    def test_prompts_for_site_name(self, xdg_config, monkeypatch):
        """create_site_config prompts for name when not given."""
        inputs = iter(["mysite", "https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        env_path = create_site_config()
        assert "mysite" in str(env_path)

    def test_https_required(self, xdg_config, monkeypatch):
        """create_site_config rejects http:// and re-prompts."""
        inputs = iter(["http://bad.com", "https://good.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        env_path = create_site_config(site_name="test")
        content = env_path.read_text()
        assert "https://good.com" in content

    def test_overwrite_protection_decline(self, single_site, monkeypatch):
        """create_site_config exits when user declines overwrite."""
        monkeypatch.setattr("builtins.input", lambda prompt: "n")

        with pytest.raises(SystemExit) as exc_info:
            create_site_config(site_name="demo")
        assert exc_info.value.code == 0

    def test_overwrite_protection_accept(self, single_site, monkeypatch):
        """create_site_config overwrites when user confirms."""
        inputs = iter(["y", "https://new.example.com", "newuser", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "newpass")

        env_path = create_site_config(site_name="demo")
        content = env_path.read_text()
        assert "https://new.example.com" in content

    def test_empty_user_exits(self, xdg_config, monkeypatch):
        """create_site_config exits if WP_USER is empty."""
        inputs = iter(["https://example.com", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        with pytest.raises(SystemExit) as exc_info:
            create_site_config(site_name="test")
        assert exc_info.value.code == 1

    def test_empty_password_exits(self, xdg_config, monkeypatch):
        """create_site_config exits if password is empty."""
        inputs = iter(["https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "")

        with pytest.raises(SystemExit) as exc_info:
            create_site_config(site_name="test")
        assert exc_info.value.code == 1

    def test_default_admin_path(self, xdg_config, monkeypatch):
        """create_site_config defaults WP_ADMIN_PATH to wp-admin."""
        inputs = iter(["https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        env_path = create_site_config(site_name="test")
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
        create_site_config(site_name="test")
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

        site_url, user, password, admin_path = resolve_config(site_name="demo")
        assert site_url == "https://demo.example.com"
        assert user == "demouser"
        assert password == "demo-pass"
        assert admin_path == "wp-admin"

    def test_site_flag_not_found_exits(self, xdg_config, monkeypatch):
        """resolve_config exits 1 when named site doesn't exist."""
        (xdg_config / "wpa").mkdir(parents=True)
        with pytest.raises(SystemExit) as exc_info:
            resolve_config(site_name="nonexistent")
        assert exc_info.value.code == 1

    def test_site_flag_not_found_shows_available(self, single_site, capsys):
        """resolve_config shows available sites when named site not found."""
        with pytest.raises(SystemExit):
            resolve_config(site_name="nonexistent")
        output = capsys.readouterr().out
        assert "demo" in output

    def test_single_site_auto_selected(self, single_site, monkeypatch, capsys):
        """resolve_config auto-selects when only one config exists."""
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        site_url, user, password, admin_path = resolve_config()
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
        site_url, user, _, _ = resolve_config()
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
        site_url, _, _, _ = resolve_config()
        assert site_url == "https://alpha.example.com"

    def test_zero_configs_triggers_creation(self, xdg_config, monkeypatch):
        """resolve_config offers creation when no configs exist."""
        monkeypatch.setattr(
            wpa_config, "__file__", str(xdg_config / "fake" / "wpa" / "config.py")
        )
        (xdg_config / "wpa").mkdir(parents=True)

        # Mock the input sequence for create_site_config
        inputs = iter(["newsite", "https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        site_url, user, password, admin_path = resolve_config()
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
        monkeypatch.setattr(wpa_config, "__file__", str(repo_dir / "wpa" / "config.py"))
        (xdg_config / "wpa").mkdir(parents=True)

        inputs = iter(["migrated", "n"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        site_url, user, password, admin_path = resolve_config()
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
        resolve_config(site_name="demo")
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

        site_url, user, password, admin_path = _load_env(env)
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

        _, _, _, admin_path = _load_env(env)
        assert admin_path == "wp-admin"

    def test_http_url_rejected(self, xdg_config, monkeypatch):
        """_load_env exits 1 for HTTP URLs."""
        site_dir = xdg_config / "wpa" / "test"
        site_dir.mkdir(parents=True)
        env = site_dir / ".env"
        env.write_text(
            "WP_SITE_URL=http://insecure.com\nWP_USER=user\nWP_APP_PASSWORD=pass\n"
        )
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            _load_env(env)
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
            _load_env(env)
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# migrate_repo_env tests
# ---------------------------------------------------------------------------


class TestMigrateRepoEnv:
    def test_no_repo_env_returns_none(self, tmp_path, monkeypatch):
        """migrate_repo_env returns None when no repo-root .env."""
        monkeypatch.setattr(wpa_config, "__file__", str(tmp_path / "wpa" / "config.py"))
        assert migrate_repo_env() is None

    def test_existing_xdg_configs_skips_migration(
        self, single_site, tmp_path, monkeypatch
    ):
        """migrate_repo_env returns None when XDG configs already exist."""
        repo_env = tmp_path / ".env"
        repo_env.write_text("WP_SITE_URL=https://old.com\n")
        monkeypatch.setattr(wpa_config, "__file__", str(tmp_path / "wpa" / "config.py"))
        assert migrate_repo_env() is None

    def test_migration_creates_xdg_config(self, xdg_config, tmp_path, monkeypatch):
        """migrate_repo_env copies repo .env to XDG path."""
        repo_env = tmp_path / ".env"
        repo_env.write_text(
            "WP_SITE_URL=https://migrated.com\n"
            "WP_USER=migrateuser\n"
            "WP_APP_PASSWORD=migratepass\n"
        )
        monkeypatch.setattr(wpa_config, "__file__", str(tmp_path / "wpa" / "config.py"))
        inputs = iter(["migrated", "n"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        result = migrate_repo_env()
        assert result is not None
        content = result.read_text()
        assert "https://migrated.com" in content
        assert "WP_ADMIN_PATH=wp-admin" in content  # Added during migration

    def test_migration_user_skips(self, xdg_config, tmp_path, monkeypatch):
        """migrate_repo_env returns None when user skips."""
        repo_env = tmp_path / ".env"
        repo_env.write_text("WP_SITE_URL=https://old.com\n")
        monkeypatch.setattr(wpa_config, "__file__", str(tmp_path / "wpa" / "config.py"))
        monkeypatch.setattr("builtins.input", lambda prompt: "")

        assert migrate_repo_env() is None

    def test_migration_deletes_old_env(self, xdg_config, tmp_path, monkeypatch):
        """migrate_repo_env deletes repo .env when user confirms."""
        repo_env = tmp_path / ".env"
        repo_env.write_text(
            "WP_SITE_URL=https://old.com\nWP_USER=user\nWP_APP_PASSWORD=pass\n"
        )
        monkeypatch.setattr(wpa_config, "__file__", str(tmp_path / "wpa" / "config.py"))
        inputs = iter(["oldsite", "y"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        migrate_repo_env()
        assert not repo_env.exists()

    def test_migration_keeps_old_env(self, xdg_config, tmp_path, monkeypatch):
        """migrate_repo_env keeps repo .env when user declines deletion."""
        repo_env = tmp_path / ".env"
        repo_env.write_text(
            "WP_SITE_URL=https://old.com\nWP_USER=user\nWP_APP_PASSWORD=pass\n"
        )
        monkeypatch.setattr(wpa_config, "__file__", str(tmp_path / "wpa" / "config.py"))
        inputs = iter(["oldsite", "n"])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))

        migrate_repo_env()
        assert repo_env.exists()

    def test_migration_invalid_name_returns_none(
        self, xdg_config, tmp_path, monkeypatch
    ):
        """migrate_repo_env returns None on invalid site name."""
        repo_env = tmp_path / ".env"
        repo_env.write_text("WP_SITE_URL=https://old.com\n")
        monkeypatch.setattr(wpa_config, "__file__", str(tmp_path / "wpa" / "config.py"))
        monkeypatch.setattr("builtins.input", lambda prompt: "../bad")

        assert migrate_repo_env() is None


# ---------------------------------------------------------------------------
# is_private_url tests
# ---------------------------------------------------------------------------


class TestIsPrivateUrl:
    """Test private/LAN address detection for HTTP allowance."""

    # RFC 1918 Class C (192.168.0.0/16)
    def test_192_168_is_private(self):
        assert is_private_url("http://192.168.1.1") is True

    def test_192_168_52_25_is_private(self):
        assert is_private_url("http://192.168.52.25") is True

    # RFC 1918 Class A (10.0.0.0/8)
    def test_10_x_is_private(self):
        assert is_private_url("http://10.0.0.1") is True

    def test_10_10_1_1_is_private(self):
        assert is_private_url("http://10.10.1.1") is True

    # RFC 1918 Class B (172.16.0.0/12)
    def test_172_16_is_private(self):
        assert is_private_url("http://172.16.0.1") is True

    def test_172_31_is_private(self):
        assert is_private_url("http://172.31.255.255") is True

    def test_172_15_is_not_private(self):
        """172.15.x.x is NOT in the 172.16.0.0/12 range."""
        assert is_private_url("http://172.15.0.1") is False

    def test_172_32_is_not_private(self):
        """172.32.x.x is NOT in the 172.16.0.0/12 range."""
        assert is_private_url("http://172.32.0.1") is False

    # Loopback (127.0.0.0/8)
    def test_127_0_0_1_is_private(self):
        assert is_private_url("http://127.0.0.1") is True

    def test_127_x_is_private(self):
        assert is_private_url("http://127.255.255.255") is True

    # localhost hostname
    def test_localhost_is_private(self):
        assert is_private_url("http://localhost") is True

    def test_localhost_with_port_is_private(self):
        assert is_private_url("http://localhost:8080") is True

    # Public addresses
    def test_public_ip_is_not_private(self):
        assert is_private_url("http://93.184.216.34") is False

    def test_public_hostname_is_not_private(self):
        assert is_private_url("http://example.com") is False

    # HTTPS URLs (always valid, private check not relevant)
    def test_https_private_ip_still_private(self):
        assert is_private_url("https://192.168.1.1") is True

    # URL with port
    def test_private_ip_with_port(self):
        assert is_private_url("http://192.168.52.25:8080") is True

    def test_public_ip_with_port(self):
        assert is_private_url("http://93.184.216.34:8080") is False


# ---------------------------------------------------------------------------
# URL validation in _load_env (HTTP on private addresses)
# ---------------------------------------------------------------------------


class TestLoadEnvPrivateHttp:
    def test_http_private_ip_accepted(self, xdg_config, monkeypatch):
        """_load_env accepts http:// for private IP addresses."""
        site_dir = xdg_config / "wpa" / "test"
        site_dir.mkdir(parents=True)
        env = site_dir / ".env"
        env.write_text(
            "WP_SITE_URL=http://192.168.52.25\n"
            "WP_USER=testuser\n"
            "WP_APP_PASSWORD=testpass\n"
        )
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        site_url, user, password, admin_path = _load_env(env)
        assert site_url == "http://192.168.52.25"

    def test_http_private_ip_prints_warning(self, xdg_config, monkeypatch, capsys):
        """_load_env prints warning when HTTP used on private address."""
        site_dir = xdg_config / "wpa" / "test"
        site_dir.mkdir(parents=True)
        env = site_dir / ".env"
        env.write_text(
            "WP_SITE_URL=http://192.168.52.25\n"
            "WP_USER=testuser\n"
            "WP_APP_PASSWORD=testpass\n"
        )
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        _load_env(env)
        output = capsys.readouterr().out
        assert "Warning" in output
        assert "not encrypted" in output.lower() or "HTTP" in output

    def test_http_localhost_accepted(self, xdg_config, monkeypatch):
        """_load_env accepts http://localhost."""
        site_dir = xdg_config / "wpa" / "test"
        site_dir.mkdir(parents=True)
        env = site_dir / ".env"
        env.write_text(
            "WP_SITE_URL=http://localhost:8080\n"
            "WP_USER=testuser\n"
            "WP_APP_PASSWORD=testpass\n"
        )
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        site_url, _, _, _ = _load_env(env)
        assert site_url == "http://localhost:8080"

    def test_http_public_ip_rejected(self, xdg_config, monkeypatch):
        """_load_env rejects http:// for public IP addresses."""
        site_dir = xdg_config / "wpa" / "test"
        site_dir.mkdir(parents=True)
        env = site_dir / ".env"
        env.write_text(
            "WP_SITE_URL=http://93.184.216.34\n"
            "WP_USER=testuser\n"
            "WP_APP_PASSWORD=testpass\n"
        )
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            _load_env(env)
        assert exc_info.value.code == 1

    def test_http_public_hostname_rejected(self, xdg_config, monkeypatch):
        """_load_env rejects http:// for public hostnames."""
        site_dir = xdg_config / "wpa" / "test"
        site_dir.mkdir(parents=True)
        env = site_dir / ".env"
        env.write_text(
            "WP_SITE_URL=http://example.com\n"
            "WP_USER=testuser\n"
            "WP_APP_PASSWORD=testpass\n"
        )
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            _load_env(env)
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# create_site_config HTTP on private addresses
# ---------------------------------------------------------------------------


class TestCreateSiteConfigPrivateHttp:
    def test_http_private_accepted(self, xdg_config, monkeypatch):
        """create_site_config accepts http:// for private IP addresses."""
        inputs = iter(["http://192.168.52.25", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        env_path = create_site_config(site_name="local")
        content = env_path.read_text()
        assert "http://192.168.52.25" in content

    def test_http_public_rejected_then_https_accepted(self, xdg_config, monkeypatch):
        """create_site_config rejects http:// public, then accepts https://."""
        inputs = iter(["http://example.com", "https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        env_path = create_site_config(site_name="test")
        content = env_path.read_text()
        assert "https://example.com" in content

    def test_http_localhost_accepted(self, xdg_config, monkeypatch):
        """create_site_config accepts http://localhost."""
        inputs = iter(["http://localhost:8080", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        env_path = create_site_config(site_name="local")
        content = env_path.read_text()
        assert "http://localhost:8080" in content


# ---------------------------------------------------------------------------
# main integration tests
# ---------------------------------------------------------------------------


class TestMain:
    def test_no_args_shows_help(self):
        """main with no args prints help and returns 1."""
        result = main([])
        assert result == 1

    def test_publish_subcommand(self, single_site, valid_md_file, monkeypatch):
        """main publish runs the full pipeline and returns 0 on success."""
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        mock_client = MagicMock()
        mock_client.site_url = "https://example.com"

        with (
            patch("wpa.cli.WPApiClient.from_config", return_value=mock_client),
            patch(
                "wpa.cli.parse_page",
                return_value=("Title", "test-slug", "draft", "<p>Body</p>"),
            ) as mock_parse_page,
            patch("wpa.cli.publish_page", return_value=0) as mock_publish_page,
        ):
            result = main(["publish", "--site", "demo", str(valid_md_file)])

        assert result == 0
        mock_parse_page.assert_called_once_with(str(valid_md_file))
        mock_publish_page.assert_called_once_with(
            mock_client,
            "Title",
            "test-slug",
            "draft",
            "<p>Body</p>",
            admin_path=mock_client.admin_path,
        )

    def test_page_create_subcommand(self, single_site, valid_md_file, monkeypatch):
        """main page create runs the same pipeline as publish."""
        monkeypatch.delenv("WP_SITE_URL", raising=False)
        monkeypatch.delenv("WP_USER", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)
        monkeypatch.delenv("WP_ADMIN_PATH", raising=False)

        mock_client = MagicMock()
        mock_client.site_url = "https://example.com"

        with (
            patch("wpa.cli.WPApiClient.from_config", return_value=mock_client),
            patch(
                "wpa.cli.parse_page",
                return_value=("Title", "test-slug", "draft", "<p>Body</p>"),
            ) as mock_parse_page,
            patch("wpa.cli.publish_page", return_value=0) as mock_publish_page,
        ):
            result = main(["page", "create", "--site", "demo", str(valid_md_file)])

        assert result == 0
        mock_parse_page.assert_called_once_with(str(valid_md_file))
        mock_publish_page.assert_called_once_with(
            mock_client,
            "Title",
            "test-slug",
            "draft",
            "<p>Body</p>",
            admin_path=mock_client.admin_path,
        )

    def test_site_add_subcommand(self, xdg_config, monkeypatch, capsys):
        """main site add runs interactive creation and returns 0."""
        inputs = iter(["testsite", "https://example.com", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        result = main(["site", "add"])
        assert result == 0
        output = capsys.readouterr().out
        assert "Saved to" in output

    def test_site_list_subcommand(self, single_site, capsys):
        """main site list shows configured sites."""
        result = main(["site", "list"])
        assert result == 0
        output = capsys.readouterr().out
        assert "demo" in output

    def test_version_flag(self, capsys):
        """main --version prints version and exits."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        from wpa import __version__

        assert __version__ in output

    def test_help_flag(self, capsys):
        """--help output includes subcommand listing."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert "publish" in output
        assert "page" in output
        assert "site" in output


class TestParseMarkdown:
    """Tests for parse_markdown() — the shared markdown parser."""

    def test_returns_dict_with_all_fields(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("---\ntitle: Hello\nslug: hello\nstatus: draft\n---\nBody text\n")
        result = parse_markdown(str(md))
        assert result["title"] == "Hello"
        assert result["slug"] == "hello"
        assert result["status"] == "draft"
        assert "<p>Body text</p>" in result["content"]

    def test_preserves_extra_frontmatter(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("---\ntitle: Test\ncategories: [3, 5]\nauthor: 2\n---\nContent\n")
        result = parse_markdown(str(md))
        assert result["categories"] == [3, 5]
        assert result["author"] == 2

    def test_backward_compat_with_parse_page(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("---\ntitle: Compat Test\nstatus: publish\n---\nHello\n")
        title, slug, status, content = parse_page(str(md))
        data = parse_markdown(str(md))
        assert title == data["title"]
        assert slug == data["slug"]
        assert status == data["status"]
        assert content == data["content"]

    def test_pending_status_accepted(self, tmp_path):
        md = tmp_path / "pending.md"
        md.write_text("---\ntitle: Pending\nstatus: pending\n---\nBody\n")
        data = parse_markdown(str(md))
        assert data["status"] == "pending"

    def test_private_status_accepted(self, tmp_path):
        md = tmp_path / "private.md"
        md.write_text("---\ntitle: Private\nstatus: private\n---\nBody\n")
        data = parse_markdown(str(md))
        assert data["status"] == "private"
