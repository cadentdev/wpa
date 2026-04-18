"""Tests for wpa.page — page CRUD operations."""

from unittest.mock import MagicMock

import pytest

from wpa.exceptions import WPApiError
from wpa.page import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    _extract_page_row,
    _validate_page_id,
    create_page,
    delete_page,
    get_page,
    list_pages,
    update_page,
    validate_fields,
)


@pytest.fixture
def mock_client():
    """Create a mock WPApiClient."""
    return MagicMock()


# Sample API response matching WordPress REST API format
SAMPLE_API_PAGE = {
    "id": 10,
    "title": {"rendered": "About Us", "raw": "About Us"},
    "status": "publish",
    "date": "2026-03-01T10:00:00",
    "slug": "about-us",
    "parent": 0,
    "author": 1,
    "content": {"rendered": "<p>About page content</p>", "raw": "About page content"},
    "excerpt": {"rendered": "", "raw": ""},
    "menu_order": 5,
    "link": "https://example.com/about-us/",
    "modified": "2026-03-15T14:00:00",
}


class TestExtractPageRow:
    def test_extracts_all_fields(self):
        row = _extract_page_row(SAMPLE_API_PAGE)
        assert row["id"] == 10
        assert row["title"] == "About Us"
        assert row["status"] == "publish"
        assert row["slug"] == "about-us"
        assert row["parent"] == 0
        assert row["menu_order"] == 5

    def test_flattens_rendered_fields(self):
        row = _extract_page_row(SAMPLE_API_PAGE)
        assert row["title"] == "About Us"
        assert row["content"] == "<p>About page content</p>"

    def test_missing_fields_default_to_empty(self):
        row = _extract_page_row({"id": 1})
        assert row["title"] == ""
        assert row["parent"] == ""


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields(self):
        result = validate_fields("id,title,parent")
        assert result == ["id", "title", "parent"]

    def test_invalid_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field 'categories'"):
            validate_fields("id,categories")

    def test_all_fields_valid(self):
        all_fields = ",".join(AVAILABLE_FIELDS)
        result = validate_fields(all_fields)
        assert result == AVAILABLE_FIELDS


class TestListPages:
    def test_basic_list(self, mock_client):
        mock_client.get_list.return_value = iter([SAMPLE_API_PAGE])
        rows = list_pages(mock_client)
        assert len(rows) == 1
        assert rows[0]["id"] == 10
        assert rows[0]["title"] == "About Us"

    def test_passes_status_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_pages(mock_client, status="draft")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["context"] == "edit"
        assert params["status"] == "draft"

    def test_passes_search(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_pages(mock_client, search="about")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["search"] == "about"

    def test_passes_parent_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_pages(mock_client, parent=5)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["parent"] == 5

    def test_passes_orderby_and_order(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_pages(mock_client, orderby="menu_order", order="asc")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["orderby"] == "menu_order"
        assert params["order"] == "asc"

    def test_passes_per_page(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_pages(mock_client, per_page=25)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["per_page"] == 25

    def test_specific_page_uses_get(self, mock_client):
        mock_client.get.return_value = [SAMPLE_API_PAGE]
        rows = list_pages(mock_client, page=2)
        assert len(rows) == 1
        mock_client.get.assert_called_once()
        mock_client.get_list.assert_not_called()

    def test_empty_results(self, mock_client):
        mock_client.get_list.return_value = iter([])
        rows = list_pages(mock_client)
        assert rows == []


class TestGetPage:
    def test_get_existing_page(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_PAGE
        row = get_page(mock_client, 10)
        assert row["id"] == 10
        assert row["title"] == "About Us"
        mock_client.get.assert_called_once_with("pages/10", params={"context": "edit"})

    def test_get_with_embed(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_PAGE
        get_page(mock_client, 10, embed=True)
        params = mock_client.get.call_args[1]["params"]
        assert params["_embed"] is True

    def test_invalid_page_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid page ID"):
            get_page(mock_client, 0)

    def test_api_404(self, mock_client):
        mock_client.get.side_effect = WPApiError(404, "not_found", "Page not found")
        with pytest.raises(WPApiError):
            get_page(mock_client, 999)


class TestCreatePage:
    def test_create_minimal(self, mock_client):
        mock_client.post.return_value = {"id": 20, "status": "draft"}
        result = create_page(mock_client, title="New Page")
        assert result["id"] == 20
        data = mock_client.post.call_args[1]["data"]
        assert data["title"] == "New Page"
        assert data["status"] == "draft"

    def test_create_with_all_fields(self, mock_client):
        mock_client.post.return_value = {"id": 21}
        create_page(
            mock_client,
            title="Child Page",
            content="<p>Content</p>",
            status="publish",
            slug="child-page",
            parent=10,
            author=2,
            menu_order=3,
        )
        data = mock_client.post.call_args[1]["data"]
        assert data["parent"] == 10
        assert data["menu_order"] == 3
        assert data["slug"] == "child-page"

    def test_default_status_is_draft(self, mock_client):
        mock_client.post.return_value = {"id": 22}
        create_page(mock_client, title="Test")
        data = mock_client.post.call_args[1]["data"]
        assert data["status"] == "draft"


class TestUpdatePage:
    def test_update_title(self, mock_client):
        mock_client.post.return_value = {"id": 10}
        update_page(mock_client, 10, title="Updated About")
        mock_client.post.assert_called_once_with(
            "pages/10", data={"title": "Updated About"}
        )

    def test_update_multiple_fields(self, mock_client):
        mock_client.post.return_value = {"id": 10}
        update_page(mock_client, 10, title="Updated", status="publish", parent=1)
        data = mock_client.post.call_args[1]["data"]
        assert data == {"title": "Updated", "status": "publish", "parent": 1}

    def test_empty_update_raises(self, mock_client):
        with pytest.raises(ValueError, match="No fields to update"):
            update_page(mock_client, 10)

    def test_invalid_page_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid page ID"):
            update_page(mock_client, -1, title="X")


class TestDeletePage:
    def test_trash_by_default(self, mock_client):
        mock_client.delete.return_value = {"id": 10, "status": "trash"}
        result = delete_page(mock_client, 10)
        assert result["status"] == "trash"
        mock_client.delete.assert_called_once_with("pages/10", params=None)

    def test_force_delete(self, mock_client):
        mock_client.delete.return_value = {"deleted": True}
        result = delete_page(mock_client, 10, force=True)
        assert result["deleted"] is True
        mock_client.delete.assert_called_once_with("pages/10", params={"force": True})

    def test_invalid_page_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid page ID"):
            delete_page(mock_client, 0)

    def test_invalid_page_id_string(self, mock_client):
        with pytest.raises(ValueError, match="Invalid page ID"):
            delete_page(mock_client, "abc")


class TestPageIdValidation:
    def test_bool_rejected(self):
        with pytest.raises(ValueError, match="Invalid page ID"):
            _validate_page_id(True)

    def test_false_rejected(self):
        with pytest.raises(ValueError, match="Invalid page ID"):
            _validate_page_id(False)
