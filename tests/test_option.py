"""Tests for wpa.option — registered-settings management."""

from unittest.mock import MagicMock

import pytest

from wpa.option import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    _parse_value,
    get_setting,
    list_settings,
    update_setting,
    validate_fields,
)

SAMPLE_SETTINGS = {
    "title": "My Site",
    "description": "Just another WordPress site",
    "timezone": "Europe/London",
    "posts_per_page": 10,
    "use_smilies": True,
    "site_icon": None,
}


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.get.return_value = dict(SAMPLE_SETTINGS)
    return client


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields_parsed(self):
        assert validate_fields("name,value") == ["name", "value"]

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_fields("bogus")

    def test_defaults_are_available(self):
        for f in DEFAULT_FIELDS:
            assert f in AVAILABLE_FIELDS


class TestParseValue:
    def test_integer(self):
        assert _parse_value("20") == 20

    def test_boolean(self):
        assert _parse_value("true") is True

    def test_null(self):
        assert _parse_value("null") is None

    def test_quoted_string_stays_string(self):
        assert _parse_value('"20"') == "20"

    def test_plain_string_falls_back(self):
        assert _parse_value("Europe/London") == "Europe/London"


class TestListSettings:
    def test_rows_sorted_by_name(self, mock_client):
        rows = list_settings(mock_client)
        names = [r["name"] for r in rows]
        assert names == sorted(names)
        mock_client.get.assert_called_once_with("settings", params=None)

    def test_row_shape(self, mock_client):
        rows = list_settings(mock_client)
        by_name = {r["name"]: r["value"] for r in rows}
        assert by_name["title"] == "My Site"
        assert by_name["posts_per_page"] == 10

    def test_non_dict_response_returns_empty(self, mock_client):
        mock_client.get.return_value = ["unexpected"]
        assert list_settings(mock_client) == []


class TestGetSetting:
    def test_known_setting_returned(self, mock_client):
        assert get_setting(mock_client, "title") == "My Site"

    def test_none_value_returned(self, mock_client):
        assert get_setting(mock_client, "site_icon") is None

    def test_unknown_setting_raises_with_hint(self, mock_client):
        with pytest.raises(ValueError, match="show_in_rest"):
            get_setting(mock_client, "secret_option")

    def test_invalid_name_shape_raises(self, mock_client):
        with pytest.raises(ValueError, match="setting"):
            get_setting(mock_client, "../bad")
        mock_client.get.assert_not_called()


class TestUpdateSetting:
    def test_posts_parsed_value(self, mock_client):
        mock_client.post.return_value = {**SAMPLE_SETTINGS, "posts_per_page": 20}
        result = update_setting(mock_client, "posts_per_page", "20")
        mock_client.post.assert_called_once_with(
            "settings", data={"posts_per_page": 20}
        )
        assert result == 20

    def test_string_value_passes_through(self, mock_client):
        mock_client.post.return_value = {**SAMPLE_SETTINGS, "title": "New Name"}
        result = update_setting(mock_client, "title", "New Name")
        mock_client.post.assert_called_once_with("settings", data={"title": "New Name"})
        assert result == "New Name"

    def test_unknown_setting_raises_without_post(self, mock_client):
        with pytest.raises(ValueError, match="show_in_rest"):
            update_setting(mock_client, "secret_option", "x")
        mock_client.post.assert_not_called()

    def test_invalid_name_shape_raises(self, mock_client):
        with pytest.raises(ValueError, match="setting"):
            update_setting(mock_client, "bad name", "x")
        mock_client.get.assert_not_called()
        mock_client.post.assert_not_called()
