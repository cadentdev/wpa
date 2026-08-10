"""Tests for wpa.plugin — plugin listing and activation management."""

from unittest.mock import MagicMock

import pytest

from wpa.plugin import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    _extract_plugin_row,
    activate_plugin,
    deactivate_plugin,
    get_plugin,
    list_plugins,
    normalize_plugin_id,
    update_plugin,
    validate_fields,
)


@pytest.fixture
def mock_client():
    return MagicMock()


SAMPLE_API_PLUGIN = {
    "plugin": "akismet/akismet",
    "status": "active",
    "name": "Akismet Anti-spam",
    "version": "5.3.1",
    "author": "Automattic",
    "description": {
        "raw": "Spam protection for your site.",
        "rendered": "<p>Spam protection for your site.</p>",
    },
    "requires_wp": "5.8",
    "requires_php": "5.6.20",
    "network_only": False,
    "auto_update": False,
    "_links": {},
}


class TestNormalizePluginId:
    def test_folder_file_passes_through(self):
        assert normalize_plugin_id("akismet/akismet") == "akismet/akismet"

    def test_php_extension_stripped(self):
        # wp-cli convention accepts folder/file.php; REST wants no extension
        assert normalize_plugin_id("akismet/akismet.php") == "akismet/akismet"

    def test_single_segment_accepted(self):
        # Single-file plugins are addressed by bare slug
        assert normalize_plugin_id("hello") == "hello"

    def test_invalid_empty_raises(self):
        with pytest.raises(ValueError, match="plugin"):
            normalize_plugin_id("")

    def test_invalid_traversal_raises(self):
        with pytest.raises(ValueError, match="plugin"):
            normalize_plugin_id("../evil")

    def test_invalid_three_segments_raises(self):
        with pytest.raises(ValueError, match="plugin"):
            normalize_plugin_id("a/b/c")

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="plugin"):
            normalize_plugin_id(None)


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields_parsed(self):
        assert validate_fields("plugin,status") == ["plugin", "status"]

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_fields("plugin,bogus")

    def test_defaults_are_available(self):
        for f in DEFAULT_FIELDS:
            assert f in AVAILABLE_FIELDS


class TestExtractPluginRow:
    def test_flattens_description_to_raw(self):
        row = _extract_plugin_row(SAMPLE_API_PLUGIN)
        assert row["description"] == "Spam protection for your site."

    def test_friendly_keys_present(self):
        row = _extract_plugin_row(SAMPLE_API_PLUGIN)
        assert row["plugin"] == "akismet/akismet"
        assert row["status"] == "active"
        assert row["name"] == "Akismet Anti-spam"
        assert row["version"] == "5.3.1"
        assert row["auto_update"] is False

    def test_missing_keys_default_empty(self):
        row = _extract_plugin_row({"plugin": "hello"})
        assert row["name"] == ""
        assert row["description"] == ""


class TestListPlugins:
    def test_list_success(self, mock_client):
        mock_client.get.return_value = [SAMPLE_API_PLUGIN]
        rows = list_plugins(mock_client)
        assert rows == [_extract_plugin_row(SAMPLE_API_PLUGIN)]
        mock_client.get.assert_called_once_with("plugins", params={"context": "edit"})

    def test_status_filter(self, mock_client):
        mock_client.get.return_value = []
        list_plugins(mock_client, status="inactive")
        params = mock_client.get.call_args[1]["params"]
        assert params["status"] == "inactive"

    def test_status_all_sends_no_filter(self, mock_client):
        mock_client.get.return_value = []
        list_plugins(mock_client, status="all")
        params = mock_client.get.call_args[1]["params"]
        assert "status" not in params

    def test_invalid_status_raises(self, mock_client):
        with pytest.raises(ValueError, match="status"):
            list_plugins(mock_client, status="enabled")

    def test_search_filter(self, mock_client):
        mock_client.get.return_value = []
        list_plugins(mock_client, search="spam")
        params = mock_client.get.call_args[1]["params"]
        assert params["search"] == "spam"

    def test_non_list_response_returns_empty(self, mock_client):
        mock_client.get.return_value = {"unexpected": "shape"}
        assert list_plugins(mock_client) == []


class TestGetPlugin:
    def test_get_success(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_PLUGIN
        row = get_plugin(mock_client, "akismet/akismet")
        assert row["plugin"] == "akismet/akismet"
        mock_client.get.assert_called_once_with(
            "plugins/akismet/akismet", params={"context": "edit"}
        )

    def test_get_normalizes_php_extension(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_PLUGIN
        get_plugin(mock_client, "akismet/akismet.php")
        endpoint = mock_client.get.call_args[0][0]
        assert endpoint == "plugins/akismet/akismet"

    def test_get_invalid_id_raises(self, mock_client):
        with pytest.raises(ValueError, match="plugin"):
            get_plugin(mock_client, "a/b/c")
        mock_client.get.assert_not_called()


class TestUpdatePlugin:
    def test_activate_posts_status(self, mock_client):
        mock_client.post.return_value = {**SAMPLE_API_PLUGIN, "status": "active"}
        result = activate_plugin(mock_client, "akismet/akismet")
        mock_client.post.assert_called_once_with(
            "plugins/akismet/akismet", data={"status": "active"}
        )
        assert result["status"] == "active"

    def test_deactivate_posts_status(self, mock_client):
        mock_client.post.return_value = {**SAMPLE_API_PLUGIN, "status": "inactive"}
        result = deactivate_plugin(mock_client, "akismet/akismet")
        mock_client.post.assert_called_once_with(
            "plugins/akismet/akismet", data={"status": "inactive"}
        )
        assert result["status"] == "inactive"

    def test_update_invalid_status_raises(self, mock_client):
        with pytest.raises(ValueError, match="status"):
            update_plugin(mock_client, "akismet/akismet", status="enabled")
        mock_client.post.assert_not_called()

    def test_update_invalid_id_raises(self, mock_client):
        with pytest.raises(ValueError, match="plugin"):
            update_plugin(mock_client, "../evil", status="active")
        mock_client.post.assert_not_called()

    def test_single_segment_plugin(self, mock_client):
        mock_client.post.return_value = SAMPLE_API_PLUGIN
        activate_plugin(mock_client, "hello")
        endpoint = mock_client.post.call_args[0][0]
        assert endpoint == "plugins/hello"
