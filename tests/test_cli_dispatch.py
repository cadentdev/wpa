"""Tests for wpa.cli dispatch — bare group commands print help (#75).

A group invoked without a subcommand (`wpa plugin`, `wpa menu item`) has
no handler bound. main() must print that group's help and return 1, for
every group, without a per-group guard that has to be remembered each
time a group is added.
"""

import argparse

import pytest

from wpa import cli
from wpa.cli import main

# Every command group, including nested ones. `publish` is a leaf command
# (it requires a file), so it is not a group.
TOP_LEVEL_GROUPS = [
    "post",
    "page",
    "site",
    "user",
    "media",
    "comment",
    "term",
    "category",
    "tag",
    "taxonomy",
    "post-type",
    "api",
    "block",
    "theme",
    "plugin",
    "menu",
    "option",
    "sidebar",
    "widget",
]
NESTED_GROUPS = [["menu", "item"], ["menu", "location"]]


class TestBareGroupPrintsHelp:
    @pytest.mark.parametrize("group", TOP_LEVEL_GROUPS)
    def test_bare_group_prints_its_own_help(self, group, capsys):
        result = main([group])
        out = capsys.readouterr().out
        assert result == 1
        assert out.startswith(f"usage: wpa {group} ")

    @pytest.mark.parametrize("argv", NESTED_GROUPS)
    def test_bare_nested_group_prints_nested_help(self, argv, capsys):
        result = main(argv)
        out = capsys.readouterr().out
        assert result == 1
        assert out.startswith(f"usage: wpa {' '.join(argv)} ")

    @pytest.mark.parametrize("group", ["plugin", "menu", "widget", "option", "sidebar"])
    def test_phase_6_groups_no_longer_crash(self, group):
        """The five groups named in #75 raised AttributeError."""
        assert main([group]) == 1

    def test_no_command_prints_top_level_help(self, capsys):
        result = main([])
        out = capsys.readouterr().out
        assert result == 1
        assert out.startswith("usage: wpa ")
        assert "plugin" in out

    def test_help_lists_the_groups_subcommands(self, capsys):
        main(["plugin"])
        out = capsys.readouterr().out
        for sub in ("list", "get", "activate", "deactivate"):
            assert sub in out


class TestEveryGroupIsCovered:
    """Guard the guard: a group added later must not need a new entry."""

    def test_group_lists_match_the_parser(self, capsys):
        """TOP_LEVEL_GROUPS is exactly the set of commands with subcommands."""
        main([])
        out = capsys.readouterr().out
        # The top-level usage line names every command: {publish,post,...}
        listed = out.split("{", 1)[1].split("}", 1)[0].split(",")
        leaves = {"publish"}
        assert set(listed) - leaves == set(TOP_LEVEL_GROUPS)


class TestGroupParser:
    """_group_parser walks to the deepest group the user actually named."""

    def _tree(self):
        root = argparse.ArgumentParser(prog="x")
        sub = root.add_subparsers(dest="command")
        a = sub.add_parser("a")
        a_sub = a.add_subparsers(dest="a_command")
        b = a_sub.add_parser("b")
        b_sub = b.add_subparsers(dest="a_b_command")
        b_sub.add_parser("leaf")
        sub.add_parser("solo")
        return root, a, b

    def test_no_command_returns_root(self):
        root, _, _ = self._tree()
        assert cli._group_parser(root, root.parse_args([])) is root

    def test_one_level(self):
        root, a, _ = self._tree()
        assert cli._group_parser(root, root.parse_args(["a"])) is a

    def test_two_levels(self):
        root, _, b = self._tree()
        assert cli._group_parser(root, root.parse_args(["a", "b"])) is b

    def test_parser_without_subcommands_returns_itself(self):
        root, _, _ = self._tree()
        solo = cli._group_parser(root, root.parse_args(["solo"]))
        assert solo.prog == "x solo"
