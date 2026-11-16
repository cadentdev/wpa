"""Tests for #57 — `wpa post create --stdin` reads content from stdin.

    echo "<p>Hello</p>" | wpa post create --title "My Post" --stdin

--stdin is a third content source alongside --content and --file; the
three are mutually exclusive.
"""

import io
from unittest.mock import MagicMock, patch

import pytest

from wpa import post as post_module
from wpa.cli import main


class _ExplodingStdin:
    """A stdin that fails the test if anything reads it."""

    def read(self, *args):  # pragma: no cover - only runs on regression
        raise AssertionError("stdin was read without --stdin")

    readline = read


@pytest.fixture
def client():
    mock = MagicMock()
    mock.post.return_value = {"id": 101, "status": "draft"}
    with patch("wpa.cli.WPApiClient.from_config", return_value=mock):
        yield mock


def _pipe(monkeypatch, text):
    monkeypatch.setattr("sys.stdin", io.StringIO(text))


def _payload(client):
    return client.post.call_args[1]["data"]


class TestReadStdinContent:
    def test_returns_content(self):
        stream = io.StringIO("<p>Hello</p>")
        assert post_module.read_stdin_content(stream) == "<p>Hello</p>"

    def test_content_is_not_altered(self):
        text = "<p>One</p>\n\n<p>Two</p>\n"
        assert post_module.read_stdin_content(io.StringIO(text)) == text

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="standard input was empty"):
            post_module.read_stdin_content(io.StringIO(""))

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="standard input was empty"):
            post_module.read_stdin_content(io.StringIO("  \n\n"))

    def test_defaults_to_sys_stdin(self, monkeypatch):
        _pipe(monkeypatch, "<p>From sys.stdin</p>")
        assert post_module.read_stdin_content() == "<p>From sys.stdin</p>"


class TestPostCreateStdin:
    def test_content_comes_from_stdin(self, client, monkeypatch, capsys):
        _pipe(monkeypatch, "<p>Hello</p>\n")
        result = main(["post", "create", "--title", "My Post", "--stdin"])
        assert result == 0
        assert _payload(client)["title"] == "My Post"
        assert _payload(client)["content"] == "<p>Hello</p>\n"
        assert "Post created successfully!" in capsys.readouterr().out

    def test_default_status_is_draft(self, client, monkeypatch):
        _pipe(monkeypatch, "<p>Hello</p>")
        main(["post", "create", "--title", "My Post", "--stdin"])
        assert _payload(client)["status"] == "draft"

    def test_other_flags_still_apply(self, client, monkeypatch):
        _pipe(monkeypatch, "<p>Hello</p>")
        result = main(
            [
                "post",
                "create",
                "--title",
                "My Post",
                "--stdin",
                "--status",
                "publish",
                "--slug",
                "my-post",
                "--categories",
                "3,7",
            ]
        )
        assert result == 0
        payload = _payload(client)
        assert payload["status"] == "publish"
        assert payload["slug"] == "my-post"
        assert payload["categories"] == [3, 7]

    def test_stdin_and_content_are_mutually_exclusive(
        self, client, monkeypatch, capsys
    ):
        _pipe(monkeypatch, "<p>Hello</p>")
        result = main(
            ["post", "create", "--title", "T", "--stdin", "--content", "<p>x</p>"]
        )
        assert result == 1
        assert "mutually exclusive" in capsys.readouterr().out
        client.post.assert_not_called()

    def test_stdin_and_file_are_mutually_exclusive(
        self, client, monkeypatch, capsys, tmp_path
    ):
        md = tmp_path / "a.md"
        md.write_text("---\ntitle: From file\n---\nBody\n")
        _pipe(monkeypatch, "<p>Hello</p>")
        result = main(["post", "create", "--stdin", "--file", str(md)])
        assert result == 1
        assert "mutually exclusive" in capsys.readouterr().out
        client.post.assert_not_called()

    def test_title_is_still_required(self, client, monkeypatch, capsys):
        _pipe(monkeypatch, "<p>Hello</p>")
        result = main(["post", "create", "--stdin"])
        assert result == 1
        assert "--title" in capsys.readouterr().out
        client.post.assert_not_called()

    def test_empty_stdin_creates_nothing(self, client, monkeypatch, capsys):
        _pipe(monkeypatch, "")
        result = main(["post", "create", "--title", "My Post", "--stdin"])
        assert result == 1
        assert "standard input was empty" in capsys.readouterr().out
        client.post.assert_not_called()


class TestStdinUntouchedWithoutFlag:
    def test_content_flag_does_not_read_stdin(self, client, monkeypatch):
        monkeypatch.setattr("sys.stdin", _ExplodingStdin())
        result = main(["post", "create", "--title", "T", "--content", "<p>x</p>"])
        assert result == 0
        assert _payload(client)["content"] == "<p>x</p>"

    def test_file_and_content_still_mutually_exclusive(self, client, capsys, tmp_path):
        md = tmp_path / "a.md"
        md.write_text("---\ntitle: From file\n---\nBody\n")
        result = main(["post", "create", "--file", str(md), "--content", "<p>x</p>"])
        assert result == 1
        assert "mutually exclusive" in capsys.readouterr().out
        client.post.assert_not_called()


class TestStdinWithInteractiveSiteSelection:
    """stdin carries the content, so it cannot also answer a site prompt."""

    def test_multiple_sites_without_site_flag_is_a_clear_error(
        self, tmp_path, monkeypatch, capsys
    ):
        config_home = tmp_path / "config"
        for name in ("alpha", "beta"):
            site_dir = config_home / "wpa" / name
            site_dir.mkdir(parents=True)
            (site_dir / ".env").write_text(
                f"WP_SITE_URL=https://{name}.example.com\n"
                "WP_USER=u\nWP_APP_PASSWORD=p\n"
            )
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
        _pipe(monkeypatch, "<p>Hello</p>")

        with patch("wpa.api.requests.request") as request:
            result = main(["post", "create", "--title", "My Post", "--stdin"])

        assert result == 1
        assert "--site" in capsys.readouterr().out
        request.assert_not_called()
