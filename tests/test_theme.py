"""Tests for wpa.theme — read-only theme information."""

from unittest.mock import MagicMock

import pytest

from wpa.theme import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    THEME_STATUSES,
    get_theme,
    list_themes,
    validate_fields,
)

SAMPLE_API_THEME = {
    "stylesheet": "twentytwentyfive",
    "template": "twentytwentyfive",
    "name": {"raw": "Twenty Twenty-Five", "rendered": "Twenty Twenty-Five"},
    "status": "active",
    "version": "1.1",
    "author": {"raw": "the WordPress team", "rendered": "the WordPress team"},
    "description": {"raw": "Twenty Twenty-Five emphasizes simplicity.", "rendered": ""},
    "requires_wp": "6.7",
    "requires_php": "7.2",
}


@pytest.fixture
def mock_client():
    return MagicMock()


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields_parsed(self):
        assert validate_fields("stylesheet,template") == ["stylesheet", "template"]

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_fields("stylesheet,bogus")

    def test_defaults_are_available(self):
        for f in DEFAULT_FIELDS:
            assert f in AVAILABLE_FIELDS


class TestListThemes:
    def test_list_success(self, mock_client):
        mock_client.get.return_value = [SAMPLE_API_THEME]
        rows = list_themes(mock_client)
        assert rows[0]["stylesheet"] == "twentytwentyfive"
        assert rows[0]["name"] == "Twenty Twenty-Five"
        assert rows[0]["status"] == "active"
        mock_client.get.assert_called_once_with("themes", params={"context": "edit"})

    def test_status_filter(self, mock_client):
        mock_client.get.return_value = []
        list_themes(mock_client, status="active")
        mock_client.get.assert_called_once_with(
            "themes", params={"context": "edit", "status": "active"}
        )

    def test_invalid_status_raises(self, mock_client):
        with pytest.raises(ValueError, match="Invalid status"):
            list_themes(mock_client, status="broken")
        mock_client.get.assert_not_called()

    def test_statuses_constant(self):
        assert THEME_STATUSES == ("active", "inactive")

    def test_rendered_preferred_over_raw(self, mock_client):
        mock_client.get.return_value = [
            {**SAMPLE_API_THEME, "author": {"raw": "raw author", "rendered": ""}}
        ]
        rows = list_themes(mock_client)
        # rendered is empty -> falls back to raw
        assert rows[0]["author"] == "raw author"

    def test_missing_keys_default_empty(self, mock_client):
        mock_client.get.return_value = [{"stylesheet": "bare"}]
        rows = list_themes(mock_client)
        assert rows[0]["name"] == ""

    def test_non_list_response_returns_empty(self, mock_client):
        mock_client.get.return_value = {"unexpected": "shape"}
        assert list_themes(mock_client) == []


class TestGetTheme:
    def test_get_success(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_THEME
        row = get_theme(mock_client, "twentytwentyfive")
        assert row["stylesheet"] == "twentytwentyfive"
        mock_client.get.assert_called_once_with(
            "themes/twentytwentyfive", params={"context": "edit"}
        )

    def test_subdirectory_stylesheet(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_THEME
        get_theme(mock_client, "parent/child")
        mock_client.get.assert_called_once_with(
            "themes/parent/child", params={"context": "edit"}
        )

    def test_invalid_stylesheet_raises(self, mock_client):
        with pytest.raises(ValueError, match="Invalid theme stylesheet"):
            get_theme(mock_client, "../plugins")
        mock_client.get.assert_not_called()

    def test_empty_stylesheet_raises(self, mock_client):
        with pytest.raises(ValueError, match="Invalid theme stylesheet"):
            get_theme(mock_client, "")
        mock_client.get.assert_not_called()

    def test_too_many_segments_raises(self, mock_client):
        # Stylesheets are at most parent/child (subdirectory themes);
        # anything deeper is not a real theme path.
        with pytest.raises(ValueError, match="Invalid theme stylesheet"):
            get_theme(mock_client, "a/b/c")
        mock_client.get.assert_not_called()
