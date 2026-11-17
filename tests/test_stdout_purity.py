"""Regression tests for #81 — diagnostics must not pollute stdout.

Machine-readable output (`--format json/csv/tsv`, `--field`, `--ids`,
`--count`) is consumed by other programs. The HTTP-on-private-address
warning is diagnostic output and belongs on stderr; over HTTPS the bug is
invisible, so every test here runs against an `http://` private-address
site.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from wpa.cli import main
from wpa.config import _load_env, create_site_config, resolve_config

WARNING = "Warning: Using HTTP on a private/LAN address."

SAMPLE_THEMES = [
    {
        "stylesheet": "twentytwentyfive",
        "template": "twentytwentyfive",
        "name": {"raw": "Twenty Twenty-Five", "rendered": "Twenty Twenty-Five"},
        "status": "active",
        "version": "1.3",
    }
]


@pytest.fixture()
def lan_site(tmp_path, monkeypatch):
    """A site config named 'lan' at an http:// private address."""
    config_home = tmp_path / "config"
    site_dir = config_home / "wpa" / "lan"
    site_dir.mkdir(parents=True)
    env = site_dir / ".env"
    env.write_text(
        "WP_SITE_URL=http://192.168.52.18\nWP_USER=testuser\nWP_APP_PASSWORD=testpass\n"
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    for var in ("WP_SITE_URL", "WP_USER", "WP_APP_PASSWORD", "WP_ADMIN_PATH"):
        monkeypatch.delenv(var, raising=False)
    return env


def _response(payload, base="http://192.168.52.18"):
    """Build a stand-in for a successful requests.Response."""
    body = json.dumps(payload).encode()
    response = MagicMock()
    response.ok = True
    response.status_code = 200
    response.content = body
    response.url = f"{base}/wp-json/wp/v2/themes"
    response.headers = {}
    response.json.return_value = payload
    return response


class TestLoadEnvWarningStream:
    def test_warning_goes_to_stderr(self, lan_site, capsys):
        _load_env(lan_site)
        captured = capsys.readouterr()
        assert WARNING in captured.err

    def test_warning_not_on_stdout(self, lan_site, capsys):
        _load_env(lan_site)
        captured = capsys.readouterr()
        assert captured.out == ""


class TestSiteAddWarningStream:
    def test_warning_goes_to_stderr(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
        inputs = iter(["http://192.168.52.18", "user", ""])
        monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
        monkeypatch.setattr("getpass.getpass", lambda prompt: "pass")

        create_site_config(site_name="lan")

        captured = capsys.readouterr()
        assert WARNING in captured.err
        assert WARNING not in captured.out


class TestMachineReadableStdout:
    """End to end through main(): stdout carries the payload and nothing else."""

    def _run(self, argv, capsys):
        with patch("wpa.api.requests.request", return_value=_response(SAMPLE_THEMES)):
            code = main(argv)
        return code, capsys.readouterr()

    def test_format_json_stdout_is_valid_json(self, lan_site, capsys):
        code, captured = self._run(
            ["theme", "list", "--site", "lan", "--format", "json"], capsys
        )
        assert code == 0
        rows = json.loads(captured.out)
        assert rows[0]["stylesheet"] == "twentytwentyfive"
        assert WARNING in captured.err

    def test_field_stdout_is_only_the_value(self, lan_site, capsys):
        code, captured = self._run(
            ["theme", "list", "--site", "lan", "--field", "stylesheet"], capsys
        )
        assert code == 0
        assert captured.out == "twentytwentyfive\n"

    def test_count_stdout_is_only_the_number(self, lan_site, capsys):
        code, captured = self._run(
            ["theme", "list", "--site", "lan", "--count"], capsys
        )
        assert code == 0
        assert captured.out == "1\n"

    def test_format_csv_first_line_is_the_header(self, lan_site, capsys):
        code, captured = self._run(
            ["theme", "list", "--site", "lan", "--format", "csv"], capsys
        )
        assert code == 0
        assert captured.out.splitlines()[0].startswith("stylesheet,")


@pytest.fixture()
def only_site(tmp_path, monkeypatch):
    """Exactly one configured site (HTTPS), so --site can be omitted."""
    config_home = tmp_path / "config"
    site_dir = config_home / "wpa" / "only"
    site_dir.mkdir(parents=True)
    (site_dir / ".env").write_text(
        "WP_SITE_URL=https://only.example.com\nWP_USER=testuser\nWP_APP_PASSWORD=testpass\n"
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    for var in ("WP_SITE_URL", "WP_USER", "WP_APP_PASSWORD", "WP_ADMIN_PATH"):
        monkeypatch.delenv(var, raising=False)
    return config_home


class TestUsingSiteNoticeStream:
    """#91 — the auto-selected-site notice is a diagnostic, not data."""

    NOTICE = "Using site: only"

    def test_notice_goes_to_stderr(self, only_site, capsys):
        resolve_config()
        captured = capsys.readouterr()
        assert self.NOTICE in captured.err
        assert captured.out == ""

    def _run(self, argv, capsys):
        response = _response(SAMPLE_THEMES, base="https://only.example.com")
        with patch("wpa.api.requests.request", return_value=response):
            code = main(argv)
        return code, capsys.readouterr()

    def test_format_json_without_site_flag_is_valid_json(self, only_site, capsys):
        code, captured = self._run(["theme", "list", "--format", "json"], capsys)
        assert code == 0
        assert json.loads(captured.out)[0]["stylesheet"] == "twentytwentyfive"
        assert self.NOTICE in captured.err

    def test_field_without_site_flag_is_only_the_value(self, only_site, capsys):
        code, captured = self._run(["theme", "list", "--field", "stylesheet"], capsys)
        assert code == 0
        assert captured.out == "twentytwentyfive\n"

    def test_count_without_site_flag_is_only_the_number(self, only_site, capsys):
        code, captured = self._run(["theme", "list", "--count"], capsys)
        assert code == 0
        assert captured.out == "1\n"
