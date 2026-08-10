"""Tests for wpa.post_type — registered post type introspection."""

from unittest.mock import MagicMock

import pytest

from wpa.post_type import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    get_post_type,
    list_post_types,
    validate_fields,
)

SAMPLE_API_POST_TYPE = {
    "name": "Posts",
    "slug": "post",
    "description": "",
    "hierarchical": False,
    "rest_base": "posts",
    "taxonomies": ["category", "post_tag"],
}

SAMPLE_API_POST_TYPES = {
    "post": SAMPLE_API_POST_TYPE,
    "page": {
        "name": "Pages",
        "slug": "page",
        "description": "",
        "hierarchical": True,
        "rest_base": "pages",
        "taxonomies": [],
    },
}


@pytest.fixture
def mock_client():
    return MagicMock()


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields_parsed(self):
        assert validate_fields("slug,taxonomies") == ["slug", "taxonomies"]

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_fields("slug,bogus")

    def test_defaults_are_available(self):
        for f in DEFAULT_FIELDS:
            assert f in AVAILABLE_FIELDS


class TestListPostTypes:
    def test_list_success(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_POST_TYPES
        rows = list_post_types(mock_client)
        assert [r["slug"] for r in rows] == ["page", "post"]
        assert rows[1]["name"] == "Posts"
        mock_client.get.assert_called_once_with("types", params={"context": "edit"})

    def test_taxonomies_list_joined(self, mock_client):
        mock_client.get.return_value = {"post": SAMPLE_API_POST_TYPE}
        rows = list_post_types(mock_client)
        assert rows[0]["taxonomies"] == "category, post_tag"

    def test_missing_keys_default_empty(self, mock_client):
        mock_client.get.return_value = {"post": {"slug": "post"}}
        rows = list_post_types(mock_client)
        assert rows[0]["description"] == ""

    def test_non_dict_response_returns_empty(self, mock_client):
        mock_client.get.return_value = [SAMPLE_API_POST_TYPE]
        assert list_post_types(mock_client) == []

    def test_non_dict_values_skipped(self, mock_client):
        mock_client.get.return_value = {
            "post": SAMPLE_API_POST_TYPE,
            "weird": 42,
        }
        rows = list_post_types(mock_client)
        assert len(rows) == 1


class TestGetPostType:
    def test_get_success(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_POST_TYPE
        row = get_post_type(mock_client, "post")
        assert row["slug"] == "post"
        assert row["hierarchical"] is False
        mock_client.get.assert_called_once_with(
            "types/post", params={"context": "edit"}
        )

    def test_invalid_slug_raises(self, mock_client):
        with pytest.raises(ValueError, match="Invalid post type slug"):
            get_post_type(mock_client, "a/b")
        mock_client.get.assert_not_called()
