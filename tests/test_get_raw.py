"""Tests for #79 — `--raw` on every `get` command.

`get` flattens the API response to a friendly-field subset, even with
`--format json`. `--raw` prints the unflattened API response as JSON, so
the deep data (block `attributes`/`supports`, taxonomy `capabilities`/
`labels`, post-type `supports`, ...) is reachable.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from wpa import cli
from wpa.block import get_block
from wpa.cli import main
from wpa.comment import get_comment
from wpa.exceptions import WPApiError
from wpa.media import get_media
from wpa.menu import get_menu
from wpa.page import get_page
from wpa.plugin import get_plugin
from wpa.post import get_post
from wpa.post_type import get_post_type
from wpa.taxonomy import get_taxonomy
from wpa.term import get_term
from wpa.theme import get_theme
from wpa.user import get_user
from wpa.widget import get_widget

# A response with nested data and keys that no friendly-field map knows
# about. If any of it survives to the output, nothing was flattened.
RAW = {
    "id": 42,
    "name": "core/paragraph",
    "slug": "sample",
    "title": {"raw": "Sample", "rendered": "Sample"},
    "attributes": {"dropCap": {"type": "boolean", "default": False}},
    "supports": {"color": {"gradients": True, "link": True}},
    "capabilities": {"manage_terms": "manage_categories"},
    "labels": {"name": "Categories", "singular_name": "Category"},
    "_links": {"self": [{"href": "https://example.com/wp-json/wp/v2/x/42"}]},
}

ROW = {"id": 42, "title": "Sample"}
SETTINGS = {"title": "My Site", "posts_per_page": 10, "use_smilies": True}

# (module get function, its identifier arguments)
MODULE_GETS = [
    (get_post, (42,)),
    (get_page, (42,)),
    (get_user, (5,)),
    (get_media, (9,)),
    (get_comment, (7,)),
    (get_term, (5,)),
    (get_plugin, ("akismet/akismet",)),
    (get_menu, (3,)),
    (get_widget, ("text-2",)),
    (get_taxonomy, ("category",)),
    (get_post_type, ("post",)),
    (get_block, ("core/paragraph",)),
    (get_theme, ("twentytwentyfive",)),
]

# Every `get` command that returns a resource object.
OBJECT_GET_COMMANDS = [
    ["post", "get", "42"],
    ["page", "get", "42"],
    ["user", "get", "5"],
    ["media", "get", "9"],
    ["comment", "get", "7"],
    ["term", "get", "5"],
    ["category", "get", "5"],
    ["tag", "get", "5"],
    ["plugin", "get", "akismet/akismet"],
    ["menu", "get", "3"],
    ["widget", "get", "text-2"],
    ["taxonomy", "get", "category"],
    ["post-type", "get", "post"],
    ["block", "get", "core/paragraph"],
    ["theme", "get", "twentytwentyfive"],
]
ALL_GET_COMMANDS = [*OBJECT_GET_COMMANDS, ["option", "get", "title"]]


def _id(value):
    return " ".join(value) if isinstance(value, list) else None


@pytest.fixture
def client():
    mock = MagicMock()
    mock.get.return_value = RAW
    with patch("wpa.cli.WPApiClient.from_config", return_value=mock):
        yield mock


class TestModuleGetRaw:
    """get_x(..., raw=True) hands back exactly what the API returned."""

    @pytest.mark.parametrize(("func", "ident"), MODULE_GETS)
    def test_raw_returns_api_response_untouched(self, func, ident):
        client = MagicMock()
        client.get.return_value = RAW
        assert func(client, *ident, raw=True) is RAW

    @pytest.mark.parametrize(("func", "ident"), MODULE_GETS)
    def test_default_is_still_flattened(self, func, ident):
        client = MagicMock()
        client.get.return_value = RAW
        row = func(client, *ident)
        assert row is not RAW
        assert "_links" not in row

    @pytest.mark.parametrize(("func", "ident"), MODULE_GETS)
    def test_raw_sends_the_same_request(self, func, ident):
        flat_client, raw_client = MagicMock(), MagicMock()
        flat_client.get.return_value = RAW
        raw_client.get.return_value = RAW
        func(flat_client, *ident)
        func(raw_client, *ident, raw=True)
        assert raw_client.get.call_args == flat_client.get.call_args

    def test_raw_still_validates_the_identifier(self):
        client = MagicMock()
        with pytest.raises(ValueError):
            get_block(client, "../users", raw=True)
        client.get.assert_not_called()


class TestFormatGetOutput:
    """The one shared renderer behind every `get` handler."""

    def test_table_is_key_value_lines(self):
        assert cli._format_get_output(ROW, "table") == "id: 42\ntitle: Sample"

    def test_json_format(self):
        out = cli._format_get_output(ROW, "json")
        assert json.loads(out) == ROW

    def test_raw_is_json(self):
        out = cli._format_get_output(RAW, "table", raw=True)
        assert json.loads(out) == RAW

    def test_raw_overrides_format(self):
        assert cli._format_get_output(RAW, "table", raw=True) == (
            cli._format_get_output(RAW, "json", raw=True)
        )

    def test_non_ascii_is_not_escaped(self):
        out = cli._format_get_output({"title": "Café"}, "table", raw=True)
        assert "Café" in out

    def test_scalar_table_value_prints_bare(self):
        """`option get` returns a bare value, not a dict."""
        assert cli._format_get_output("My Site", "table") == "My Site"


class TestGetRawCli:
    @pytest.mark.parametrize("argv", OBJECT_GET_COMMANDS, ids=_id)
    def test_raw_prints_the_full_api_object(self, argv, client, capsys):
        assert main([*argv, "--raw"]) == 0
        assert json.loads(capsys.readouterr().out) == RAW

    @pytest.mark.parametrize("argv", OBJECT_GET_COMMANDS, ids=_id)
    def test_format_json_without_raw_is_unchanged(self, argv, client, capsys):
        """--format json keeps printing the friendly subset."""
        assert main([*argv, "--format", "json"]) == 0
        row = json.loads(capsys.readouterr().out)
        assert "_links" not in row
        assert row != RAW

    @pytest.mark.parametrize("argv", OBJECT_GET_COMMANDS, ids=_id)
    def test_raw_wins_over_format_table(self, argv, client, capsys):
        assert main([*argv, "--raw", "--format", "table"]) == 0
        assert json.loads(capsys.readouterr().out) == RAW

    @pytest.mark.parametrize("argv", ALL_GET_COMMANDS, ids=_id)
    def test_help_documents_raw(self, argv, capsys):
        with pytest.raises(SystemExit):
            main([*argv[:2], "--help"])
        assert "--raw" in capsys.readouterr().out

    def test_block_get_raw_exposes_attributes_and_supports(self, client, capsys):
        main(["block", "get", "core/paragraph", "--raw"])
        data = json.loads(capsys.readouterr().out)
        assert data["attributes"] == RAW["attributes"]
        assert data["supports"] == RAW["supports"]

    def test_taxonomy_get_raw_exposes_capabilities_and_labels(self, client, capsys):
        main(["taxonomy", "get", "category", "--raw"])
        data = json.loads(capsys.readouterr().out)
        assert data["capabilities"] == RAW["capabilities"]
        assert data["labels"] == RAW["labels"]

    def test_term_get_raw_honours_taxonomy(self, client, capsys):
        assert main(["term", "get", "5", "--taxonomy", "post_tag", "--raw"]) == 0
        assert client.get.call_args[0][0] == "tags/5"

    def test_post_get_raw_keeps_embed(self, client, capsys):
        assert main(["post", "get", "42", "--embed", "--raw"]) == 0
        assert client.get.call_args[1]["params"]["_embed"] is True

    def test_api_error_is_reported_not_raised(self, client, capsys):
        client.get.side_effect = WPApiError(404, "rest_no_route", "No route")
        assert main(["block", "get", "core/nope", "--raw"]) == 1
        assert "rest_no_route" in capsys.readouterr().out


class TestOptionGetRaw:
    """Settings are one flat object; a setting's value is already unflattened.

    `option get --raw` prints that value as JSON — never the whole
    settings object.
    """

    @pytest.fixture
    def settings_client(self):
        mock = MagicMock()
        mock.get.return_value = SETTINGS
        with patch("wpa.cli.WPApiClient.from_config", return_value=mock):
            yield mock

    def test_raw_prints_the_typed_value_as_json(self, settings_client, capsys):
        assert main(["option", "get", "title", "--raw"]) == 0
        assert json.loads(capsys.readouterr().out) == "My Site"

    def test_raw_matches_format_json(self, settings_client, capsys):
        main(["option", "get", "use_smilies", "--raw"])
        raw_out = capsys.readouterr().out
        main(["option", "get", "use_smilies", "--format", "json"])
        assert raw_out == capsys.readouterr().out == "true\n"

    def test_default_output_is_unchanged(self, settings_client, capsys):
        assert main(["option", "get", "title"]) == 0
        assert capsys.readouterr().out == "My Site\n"
