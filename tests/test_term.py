"""Tests for wpa.term — taxonomy term CRUD."""

from unittest.mock import MagicMock

import pytest

from wpa.exceptions import WPApiError
from wpa.term import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    _extract_term_row,
    _resolve_endpoint,
    create_term,
    delete_term,
    get_term,
    list_terms,
    update_term,
    validate_fields,
)


@pytest.fixture
def mock_client():
    return MagicMock()


SAMPLE_API_TERM = {
    "id": 7,
    "name": "Tutorials",
    "slug": "tutorials",
    "description": "Helpful guides",
    "count": 12,
    "parent": 0,
    "taxonomy": "category",
    "link": "https://example.com/category/tutorials/",
}


class TestResolveEndpoint:
    def test_category_maps_to_categories(self):
        assert _resolve_endpoint("category") == "categories"

    def test_post_tag_maps_to_tags(self):
        assert _resolve_endpoint("post_tag") == "tags"

    def test_custom_taxonomy_passes_through(self):
        # Custom taxonomies usually expose under their own slug
        assert _resolve_endpoint("genre") == "genre"

    def test_default_is_category(self):
        assert _resolve_endpoint(None) == "categories"

    def test_invalid_taxonomy_raises(self):
        with pytest.raises(ValueError, match="Invalid taxonomy"):
            _resolve_endpoint("")

    def test_invalid_taxonomy_chars_raises(self):
        with pytest.raises(ValueError, match="Invalid taxonomy"):
            _resolve_endpoint("../etc/passwd")


class TestExtractTermRow:
    def test_extracts_all_fields(self):
        row = _extract_term_row(SAMPLE_API_TERM)
        assert row["id"] == 7
        assert row["name"] == "Tutorials"
        assert row["slug"] == "tutorials"
        assert row["count"] == 12
        assert row["taxonomy"] == "category"

    def test_missing_fields_default_to_empty(self):
        row = _extract_term_row({"id": 1})
        assert row["name"] == ""
        assert row["slug"] == ""
        assert row["count"] == ""


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields(self):
        assert validate_fields("id,name,slug") == ["id", "name", "slug"]

    def test_all_fields_valid(self):
        all_fields = ",".join(AVAILABLE_FIELDS)
        assert validate_fields(all_fields) == AVAILABLE_FIELDS

    def test_invalid_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field 'bogus'"):
            validate_fields("id,bogus")

    def test_strips_whitespace(self):
        assert validate_fields("id , name , slug") == ["id", "name", "slug"]


class TestListTerms:
    def test_basic_list_default_taxonomy(self, mock_client):
        mock_client.get_list.return_value = iter([SAMPLE_API_TERM])
        rows = list_terms(mock_client)
        assert len(rows) == 1
        assert rows[0]["id"] == 7
        # Default taxonomy is category → endpoint = categories
        endpoint = mock_client.get_list.call_args[0][0]
        assert endpoint == "categories"

    def test_uses_post_tag_endpoint(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_terms(mock_client, taxonomy="post_tag")
        endpoint = mock_client.get_list.call_args[0][0]
        assert endpoint == "tags"

    def test_uses_custom_taxonomy_endpoint(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_terms(mock_client, taxonomy="genre")
        endpoint = mock_client.get_list.call_args[0][0]
        assert endpoint == "genre"

    def test_passes_search(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_terms(mock_client, search="tutorial")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["search"] == "tutorial"

    def test_passes_parent(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_terms(mock_client, parent=3)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["parent"] == 3

    def test_passes_hide_empty(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_terms(mock_client, hide_empty=True)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["hide_empty"] is True

    def test_passes_per_page(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_terms(mock_client, per_page=50)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["per_page"] == 50

    def test_passes_orderby_and_order(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_terms(mock_client, orderby="name", order="asc")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["orderby"] == "name"
        assert params["order"] == "asc"

    def test_empty_results(self, mock_client):
        mock_client.get_list.return_value = iter([])
        assert list_terms(mock_client) == []

    def test_specific_page_uses_get(self, mock_client):
        mock_client.get.return_value = [SAMPLE_API_TERM]
        rows = list_terms(mock_client, page=2)
        assert len(rows) == 1
        mock_client.get.assert_called_once()
        mock_client.get_list.assert_not_called()

    def test_specific_page_non_list_response(self, mock_client):
        mock_client.get.return_value = {"error": "bad"}
        rows = list_terms(mock_client, page=1)
        assert rows == []


class TestGetTerm:
    def test_get_existing_term(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_TERM
        row = get_term(mock_client, 7)
        assert row["id"] == 7
        mock_client.get.assert_called_once_with("categories/7", params=None)

    def test_get_with_post_tag(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_TERM
        get_term(mock_client, 7, taxonomy="post_tag")
        mock_client.get.assert_called_once_with("tags/7", params=None)

    def test_get_with_custom_taxonomy(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_TERM
        get_term(mock_client, 7, taxonomy="genre")
        mock_client.get.assert_called_once_with("genre/7", params=None)

    def test_invalid_term_id_zero(self, mock_client):
        with pytest.raises(ValueError, match="Invalid term ID"):
            get_term(mock_client, 0)

    def test_invalid_term_id_negative(self, mock_client):
        with pytest.raises(ValueError, match="Invalid term ID"):
            get_term(mock_client, -1)

    def test_invalid_term_id_string(self, mock_client):
        with pytest.raises(ValueError, match="Invalid term ID"):
            get_term(mock_client, "abc")

    def test_api_404(self, mock_client):
        mock_client.get.side_effect = WPApiError(404, "not_found", "Not found")
        with pytest.raises(WPApiError):
            get_term(mock_client, 999)


class TestCreateTerm:
    def test_create_minimal(self, mock_client):
        mock_client.post.return_value = {"id": 99, "name": "News"}
        result = create_term(mock_client, name="News")
        assert result["id"] == 99
        endpoint = mock_client.post.call_args[0][0]
        assert endpoint == "categories"
        data = mock_client.post.call_args[1]["data"]
        assert data["name"] == "News"

    def test_create_with_all_fields(self, mock_client):
        mock_client.post.return_value = {"id": 100}
        create_term(
            mock_client,
            name="News",
            slug="news",
            description="News items",
            parent=3,
            taxonomy="category",
        )
        data = mock_client.post.call_args[1]["data"]
        assert data["name"] == "News"
        assert data["slug"] == "news"
        assert data["description"] == "News items"
        assert data["parent"] == 3

    def test_create_tag(self, mock_client):
        mock_client.post.return_value = {"id": 101}
        create_term(mock_client, name="howto", taxonomy="post_tag")
        endpoint = mock_client.post.call_args[0][0]
        assert endpoint == "tags"

    def test_empty_name_raises(self, mock_client):
        with pytest.raises(ValueError, match="name"):
            create_term(mock_client, name="")

    def test_api_error(self, mock_client):
        mock_client.post.side_effect = WPApiError(400, "term_exists", "Exists")
        with pytest.raises(WPApiError):
            create_term(mock_client, name="Dup")


class TestUpdateTerm:
    def test_update_name(self, mock_client):
        mock_client.post.return_value = {"id": 7}
        update_term(mock_client, 7, name="Renamed")
        mock_client.post.assert_called_once_with(
            "categories/7", data={"name": "Renamed"}
        )

    def test_update_uses_post_tag(self, mock_client):
        mock_client.post.return_value = {"id": 7}
        update_term(mock_client, 7, taxonomy="post_tag", name="Renamed")
        mock_client.post.assert_called_once_with("tags/7", data={"name": "Renamed"})

    def test_update_multiple_fields(self, mock_client):
        mock_client.post.return_value = {"id": 7}
        update_term(mock_client, 7, name="A", slug="a", description="d")
        data = mock_client.post.call_args[1]["data"]
        assert data["name"] == "A"
        assert data["slug"] == "a"
        assert data["description"] == "d"

    def test_empty_update_raises(self, mock_client):
        with pytest.raises(ValueError, match="No fields to update"):
            update_term(mock_client, 7)

    def test_update_does_not_send_taxonomy_in_payload(self, mock_client):
        mock_client.post.return_value = {"id": 7}
        update_term(mock_client, 7, name="A")
        data = mock_client.post.call_args[1]["data"]
        assert "taxonomy" not in data

    def test_invalid_term_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid term ID"):
            update_term(mock_client, 0, name="X")


class TestDeleteTerm:
    def test_delete_always_forces(self, mock_client):
        """Terms cannot be trashed; the REST API requires force=true."""
        mock_client.delete.return_value = {"deleted": True}
        result = delete_term(mock_client, 7)
        assert result["deleted"] is True
        mock_client.delete.assert_called_once_with(
            "categories/7", params={"force": True}
        )

    def test_delete_tag(self, mock_client):
        mock_client.delete.return_value = {"deleted": True}
        delete_term(mock_client, 7, taxonomy="post_tag")
        mock_client.delete.assert_called_once_with("tags/7", params={"force": True})

    def test_delete_custom_taxonomy(self, mock_client):
        mock_client.delete.return_value = {"deleted": True}
        delete_term(mock_client, 7, taxonomy="genre")
        mock_client.delete.assert_called_once_with("genre/7", params={"force": True})

    def test_invalid_term_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid term ID"):
            delete_term(mock_client, -5)

    def test_api_404(self, mock_client):
        mock_client.delete.side_effect = WPApiError(404, "not_found", "Not found")
        with pytest.raises(WPApiError):
            delete_term(mock_client, 999)
