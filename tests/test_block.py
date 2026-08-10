"""Tests for wpa.block — registered block type introspection."""

from unittest.mock import MagicMock

import pytest

from wpa.block import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    get_block,
    list_blocks,
    validate_fields,
)

SAMPLE_API_BLOCK = {
    "name": "core/paragraph",
    "title": "Paragraph",
    "category": "text",
    "description": "Start with the basic building block of all narrative.",
    "keywords": ["text"],
    "api_version": 3,
}


@pytest.fixture
def mock_client():
    return MagicMock()


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields_parsed(self):
        assert validate_fields("name,keywords") == ["name", "keywords"]

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_fields("name,bogus")

    def test_defaults_are_available(self):
        for f in DEFAULT_FIELDS:
            assert f in AVAILABLE_FIELDS


class TestListBlocks:
    def test_list_success(self, mock_client):
        mock_client.get.return_value = [SAMPLE_API_BLOCK]
        rows = list_blocks(mock_client)
        assert rows[0]["name"] == "core/paragraph"
        assert rows[0]["title"] == "Paragraph"
        assert rows[0]["category"] == "text"
        mock_client.get.assert_called_once_with(
            "block-types", params={"context": "edit"}
        )

    def test_namespace_filter(self, mock_client):
        mock_client.get.return_value = []
        list_blocks(mock_client, namespace="core")
        mock_client.get.assert_called_once_with(
            "block-types", params={"context": "edit", "namespace": "core"}
        )

    def test_keywords_list_joined(self, mock_client):
        mock_client.get.return_value = [
            {**SAMPLE_API_BLOCK, "keywords": ["text", "prose"]}
        ]
        rows = list_blocks(mock_client)
        assert rows[0]["keywords"] == "text, prose"

    def test_missing_keys_default_empty(self, mock_client):
        mock_client.get.return_value = [{"name": "core/quote"}]
        rows = list_blocks(mock_client)
        assert rows[0]["title"] == ""

    def test_non_list_response_returns_empty(self, mock_client):
        mock_client.get.return_value = {"unexpected": "shape"}
        assert list_blocks(mock_client) == []


class TestGetBlock:
    def test_get_success(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_BLOCK
        row = get_block(mock_client, "core/paragraph")
        assert row["name"] == "core/paragraph"
        mock_client.get.assert_called_once_with(
            "block-types/core/paragraph", params={"context": "edit"}
        )

    def test_unnamespaced_name_raises(self, mock_client):
        with pytest.raises(ValueError, match="namespace/name"):
            get_block(mock_client, "paragraph")
        mock_client.get.assert_not_called()

    def test_too_many_segments_raises(self, mock_client):
        with pytest.raises(ValueError, match="namespace/name"):
            get_block(mock_client, "a/b/c")
        mock_client.get.assert_not_called()

    def test_invalid_segment_raises(self, mock_client):
        with pytest.raises(ValueError, match="Invalid block name"):
            get_block(mock_client, "core/../users")
        mock_client.get.assert_not_called()
