"""Tests for #82 — `menu item list` and `menu item add` accept the menu
both as a positional and as `--menu`.

Before, `add` took only the positional and `list` took only the flag.
Both commands now take either shape; every pre-existing invocation keeps
working.
"""

from unittest.mock import MagicMock, patch

import pytest

from wpa import menu as menu_module
from wpa.cli import main

SAMPLE_API_ITEM = {
    "id": 71,
    "title": {"raw": "Link", "rendered": "Link"},
    "url": "https://example.com",
    "type": "custom",
    "object": "custom",
    "object_id": 71,
    "parent": 0,
    "menu_order": 1,
    "menus": 3,
}

ADD_FLAGS = ["--title", "Link", "--url", "https://example.com"]


@pytest.fixture
def client():
    mock = MagicMock()
    mock.get_list.return_value = iter([SAMPLE_API_ITEM])
    mock.post.return_value = {"id": 71}
    with patch("wpa.cli.WPApiClient.from_config", return_value=mock):
        yield mock


class TestResolveMenuArg:
    """resolve_menu_arg merges the positional and --menu into one ID."""

    def test_positional_only(self):
        assert menu_module.resolve_menu_arg(3, None) == 3

    def test_flag_only(self):
        assert menu_module.resolve_menu_arg(None, 3) == 3

    def test_both_agreeing(self):
        assert menu_module.resolve_menu_arg(3, 3) == 3

    def test_both_conflicting_raises(self):
        with pytest.raises(ValueError, match="Conflicting menu IDs"):
            menu_module.resolve_menu_arg(3, 4)

    def test_neither_is_none_when_optional(self):
        assert menu_module.resolve_menu_arg(None, None) is None

    def test_neither_raises_when_required(self):
        with pytest.raises(ValueError, match="menu ID is required"):
            menu_module.resolve_menu_arg(None, None, required=True)

    def test_required_error_names_both_shapes(self):
        with pytest.raises(ValueError) as exc:
            menu_module.resolve_menu_arg(None, None, required=True)
        assert "<menu>" in str(exc.value)
        assert "--menu" in str(exc.value)


class TestMenuItemList:
    def _menus_param(self, client):
        return client.get_list.call_args[1]["params"].get("menus")

    def test_flag_still_works(self, client):
        assert main(["menu", "item", "list", "--menu", "3"]) == 0
        assert self._menus_param(client) == 3

    def test_positional_now_works(self, client):
        assert main(["menu", "item", "list", "3"]) == 0
        assert self._menus_param(client) == 3

    def test_positional_after_other_flags(self, client):
        assert main(["menu", "item", "list", "--site", "s", "3"]) == 0
        assert self._menus_param(client) == 3

    def test_no_menu_lists_all_items(self, client):
        assert main(["menu", "item", "list"]) == 0
        assert self._menus_param(client) is None

    def test_both_agreeing(self, client):
        assert main(["menu", "item", "list", "3", "--menu", "3"]) == 0
        assert self._menus_param(client) == 3

    def test_both_conflicting_is_an_error(self, client, capsys):
        assert main(["menu", "item", "list", "3", "--menu", "4"]) == 1
        assert "Conflicting menu IDs" in capsys.readouterr().out
        client.get_list.assert_not_called()


class TestMenuItemAdd:
    def _menus_payload(self, client):
        return client.post.call_args[1]["data"]["menus"]

    def test_positional_still_works(self, client):
        assert main(["menu", "item", "add", "3", *ADD_FLAGS]) == 0
        assert self._menus_payload(client) == 3

    def test_positional_after_other_flags_still_works(self, client):
        assert main(["menu", "item", "add", "--site", "s", "3", *ADD_FLAGS]) == 0
        assert self._menus_payload(client) == 3

    def test_flag_now_works(self, client):
        assert main(["menu", "item", "add", "--menu", "3", *ADD_FLAGS]) == 0
        assert self._menus_payload(client) == 3

    def test_both_agreeing(self, client):
        assert main(["menu", "item", "add", "3", "--menu", "3", *ADD_FLAGS]) == 0
        assert self._menus_payload(client) == 3

    def test_both_conflicting_is_an_error(self, client, capsys):
        assert main(["menu", "item", "add", "3", "--menu", "4", *ADD_FLAGS]) == 1
        assert "Conflicting menu IDs" in capsys.readouterr().out
        client.post.assert_not_called()

    def test_missing_menu_is_an_error_naming_both_shapes(self, client, capsys):
        assert main(["menu", "item", "add", *ADD_FLAGS]) == 1
        out = capsys.readouterr().out
        assert "menu ID is required" in out
        assert "--menu" in out
        client.post.assert_not_called()


class TestHelpShowsBothShapes:
    @pytest.mark.parametrize("command", ["list", "add"])
    def test_usage_names_positional_and_flag(self, command, capsys):
        with pytest.raises(SystemExit):
            main(["menu", "item", command, "--help"])
        usage = " ".join(capsys.readouterr().out.split())
        assert "--menu" in usage
        assert "[menu]" in usage
