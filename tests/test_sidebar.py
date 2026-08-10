"""Tests for wpa.sidebar — registered sidebar listing."""

from unittest.mock import MagicMock

import pytest

from wpa.sidebar import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    list_sidebars,
    validate_fields,
)

SAMPLE_API_SIDEBAR = {
    "id": "sidebar-1",
    "name": "Main Sidebar",
    "description": "Widgets in this area appear in the sidebar.",
    "class": "widget-area",
    "status": "active",
    "widgets": ["block-2", "block-3"],
}


@pytest.fixture
def mock_client():
    return MagicMock()


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields_parsed(self):
        assert validate_fields("id,status") == ["id", "status"]

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_fields("id,bogus")

    def test_defaults_are_available(self):
        for f in DEFAULT_FIELDS:
            assert f in AVAILABLE_FIELDS


class TestListSidebars:
    def test_list_success(self, mock_client):
        mock_client.get.return_value = [SAMPLE_API_SIDEBAR]
        rows = list_sidebars(mock_client)
        assert rows[0]["id"] == "sidebar-1"
        assert rows[0]["name"] == "Main Sidebar"
        assert rows[0]["status"] == "active"
        mock_client.get.assert_called_once_with("sidebars", params={"context": "edit"})

    def test_missing_keys_default_empty(self, mock_client):
        mock_client.get.return_value = [{"id": "sidebar-9"}]
        rows = list_sidebars(mock_client)
        assert rows[0]["name"] == ""

    def test_non_list_response_returns_empty(self, mock_client):
        mock_client.get.return_value = {"unexpected": "shape"}
        assert list_sidebars(mock_client) == []
