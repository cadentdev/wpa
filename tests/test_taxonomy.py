"""Tests for wpa.taxonomy — registered taxonomy introspection."""

from unittest.mock import MagicMock

import pytest

from wpa.taxonomy import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    get_taxonomy,
    list_taxonomies,
    validate_fields,
)

SAMPLE_API_TAXONOMY = {
    "name": "Categories",
    "slug": "category",
    "description": "",
    "hierarchical": True,
    "rest_base": "categories",
    "types": ["post"],
}

SAMPLE_API_TAXONOMIES = {
    "category": SAMPLE_API_TAXONOMY,
    "post_tag": {
        "name": "Tags",
        "slug": "post_tag",
        "description": "",
        "hierarchical": False,
        "rest_base": "tags",
        "types": ["post"],
    },
}


@pytest.fixture
def mock_client():
    return MagicMock()


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields_parsed(self):
        assert validate_fields("slug,types") == ["slug", "types"]

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_fields("slug,bogus")

    def test_defaults_are_available(self):
        for f in DEFAULT_FIELDS:
            assert f in AVAILABLE_FIELDS


class TestListTaxonomies:
    def test_list_success(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_TAXONOMIES
        rows = list_taxonomies(mock_client)
        assert [r["slug"] for r in rows] == ["category", "post_tag"]
        assert rows[0]["name"] == "Categories"
        assert rows[0]["hierarchical"] is True
        mock_client.get.assert_called_once_with(
            "taxonomies", params={"context": "edit"}
        )

    def test_rows_sorted_by_slug_key(self, mock_client):
        mock_client.get.return_value = {
            "zeta": {"slug": "zeta", "name": "Z"},
            "alpha": {"slug": "alpha", "name": "A"},
        }
        rows = list_taxonomies(mock_client)
        assert [r["slug"] for r in rows] == ["alpha", "zeta"]

    def test_types_list_joined(self, mock_client):
        mock_client.get.return_value = {
            "category": {**SAMPLE_API_TAXONOMY, "types": ["post", "page"]}
        }
        rows = list_taxonomies(mock_client)
        assert rows[0]["types"] == "post, page"

    def test_missing_keys_default_empty(self, mock_client):
        mock_client.get.return_value = {"category": {"slug": "category"}}
        rows = list_taxonomies(mock_client)
        assert rows[0]["name"] == ""

    def test_non_dict_response_returns_empty(self, mock_client):
        mock_client.get.return_value = [SAMPLE_API_TAXONOMY]
        assert list_taxonomies(mock_client) == []

    def test_non_dict_values_skipped(self, mock_client):
        mock_client.get.return_value = {
            "category": SAMPLE_API_TAXONOMY,
            "weird": "not-an-object",
        }
        rows = list_taxonomies(mock_client)
        assert len(rows) == 1


class TestGetTaxonomy:
    def test_get_success(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_TAXONOMY
        row = get_taxonomy(mock_client, "category")
        assert row["slug"] == "category"
        assert row["types"] == "post"
        mock_client.get.assert_called_once_with(
            "taxonomies/category", params={"context": "edit"}
        )

    def test_invalid_slug_raises(self, mock_client):
        with pytest.raises(ValueError, match="Invalid taxonomy slug"):
            get_taxonomy(mock_client, "../users")
        mock_client.get.assert_not_called()
