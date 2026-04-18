"""Tests for wpa.post — post CRUD operations."""

from unittest.mock import MagicMock

import pytest

from wpa.exceptions import WPApiError
from wpa.post import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    _extract_post_row,
    _extract_rendered,
    _validate_post_id,
    create_post,
    delete_post,
    get_post,
    list_posts,
    update_post,
    validate_fields,
)


@pytest.fixture
def mock_client():
    """Create a mock WPApiClient."""
    return MagicMock()


# Sample API response matching WordPress REST API format
SAMPLE_API_POST = {
    "id": 42,
    "title": {"rendered": "Hello World", "raw": "Hello World"},
    "status": "publish",
    "date": "2026-03-21T12:00:00",
    "author": 1,
    "slug": "hello-world",
    "excerpt": {"rendered": "<p>An excerpt</p>", "raw": "An excerpt"},
    "content": {"rendered": "<p>Post content</p>", "raw": "Post content"},
    "categories": [3, 5],
    "tags": [7],
    "featured_media": 0,
    "format": "standard",
    "link": "https://example.com/hello-world/",
    "modified": "2026-03-21T14:00:00",
}


class TestExtractRendered:
    def test_dict_with_rendered(self):
        assert _extract_rendered({"rendered": "Hello"}) == "Hello"

    def test_dict_without_rendered(self):
        result = _extract_rendered({"raw": "Hello"})
        assert result == "{'raw': 'Hello'}"

    def test_plain_string(self):
        assert _extract_rendered("Hello") == "Hello"

    def test_none(self):
        assert _extract_rendered(None) is None

    def test_integer(self):
        assert _extract_rendered(42) == 42


class TestExtractPostRow:
    def test_extracts_all_fields(self):
        row = _extract_post_row(SAMPLE_API_POST)
        assert row["id"] == 42
        assert row["title"] == "Hello World"
        assert row["status"] == "publish"
        assert row["author"] == 1
        assert row["slug"] == "hello-world"

    def test_flattens_rendered_fields(self):
        row = _extract_post_row(SAMPLE_API_POST)
        assert row["title"] == "Hello World"
        assert row["content"] == "<p>Post content</p>"
        assert row["excerpt"] == "<p>An excerpt</p>"

    def test_joins_categories(self):
        row = _extract_post_row(SAMPLE_API_POST)
        assert row["categories"] == "3, 5"

    def test_joins_tags(self):
        row = _extract_post_row(SAMPLE_API_POST)
        assert row["tags"] == "7"

    def test_missing_fields_default_to_empty(self):
        row = _extract_post_row({"id": 1})
        assert row["title"] == ""
        assert row["status"] == ""


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields(self):
        result = validate_fields("id,title,status")
        assert result == ["id", "title", "status"]

    def test_all_fields_valid(self):
        all_fields = ",".join(AVAILABLE_FIELDS)
        result = validate_fields(all_fields)
        assert result == AVAILABLE_FIELDS

    def test_invalid_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field 'bogus'"):
            validate_fields("id,bogus")

    def test_strips_whitespace(self):
        result = validate_fields("id , title , status")
        assert result == ["id", "title", "status"]


class TestListPosts:
    def test_basic_list(self, mock_client):
        mock_client.get_list.return_value = iter([SAMPLE_API_POST])
        rows = list_posts(mock_client)
        assert len(rows) == 1
        assert rows[0]["id"] == 42
        assert rows[0]["title"] == "Hello World"

    def test_passes_status_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_posts(mock_client, status="draft")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["context"] == "edit"
        assert params["status"] == "draft"

    def test_passes_author_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_posts(mock_client, author=5)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["author"] == 5

    def test_passes_search(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_posts(mock_client, search="hello")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["search"] == "hello"

    def test_passes_per_page(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_posts(mock_client, per_page=25)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["per_page"] == 25

    def test_passes_category_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_posts(mock_client, category=3)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["categories"] == 3

    def test_passes_tag_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_posts(mock_client, tag=7)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["tags"] == 7

    def test_passes_orderby_and_order(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_posts(mock_client, orderby="title", order="asc")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["orderby"] == "title"
        assert params["order"] == "asc"

    def test_specific_page_uses_get(self, mock_client):
        """When page is specified, use get() for a single page request."""
        mock_client.get.return_value = [SAMPLE_API_POST]
        rows = list_posts(mock_client, page=2)
        assert len(rows) == 1
        mock_client.get.assert_called_once()
        mock_client.get_list.assert_not_called()

    def test_specific_page_non_list_response(self, mock_client):
        mock_client.get.return_value = {"error": "bad"}
        rows = list_posts(mock_client, page=1)
        assert rows == []

    def test_empty_results(self, mock_client):
        mock_client.get_list.return_value = iter([])
        rows = list_posts(mock_client)
        assert rows == []


class TestGetPost:
    def test_get_existing_post(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_POST
        row = get_post(mock_client, 42)
        assert row["id"] == 42
        assert row["title"] == "Hello World"
        mock_client.get.assert_called_once_with("posts/42", params={"context": "edit"})

    def test_get_with_embed(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_POST
        get_post(mock_client, 42, embed=True)
        params = mock_client.get.call_args[1]["params"]
        assert params["_embed"] is True

    def test_invalid_post_id_zero(self, mock_client):
        with pytest.raises(ValueError, match="Invalid post ID"):
            get_post(mock_client, 0)

    def test_invalid_post_id_negative(self, mock_client):
        with pytest.raises(ValueError, match="Invalid post ID"):
            get_post(mock_client, -1)

    def test_invalid_post_id_string(self, mock_client):
        with pytest.raises(ValueError, match="Invalid post ID"):
            get_post(mock_client, "abc")

    def test_api_404(self, mock_client):
        mock_client.get.side_effect = WPApiError(404, "not_found", "Post not found")
        with pytest.raises(WPApiError) as exc_info:
            get_post(mock_client, 999)
        assert exc_info.value.status_code == 404


class TestCreatePost:
    def test_create_minimal(self, mock_client):
        mock_client.post.return_value = {"id": 99, "status": "draft"}
        result = create_post(mock_client, title="New Post")
        assert result["id"] == 99
        data = mock_client.post.call_args[1]["data"]
        assert data["title"] == "New Post"
        assert data["status"] == "draft"
        assert data["content"] == ""

    def test_create_with_all_fields(self, mock_client):
        mock_client.post.return_value = {"id": 100}
        create_post(
            mock_client,
            title="Full Post",
            content="<p>Content</p>",
            status="publish",
            slug="full-post",
            author=2,
            categories=[3, 5],
            tags=[7, 8],
            featured_media=50,
        )
        data = mock_client.post.call_args[1]["data"]
        assert data["title"] == "Full Post"
        assert data["content"] == "<p>Content</p>"
        assert data["status"] == "publish"
        assert data["slug"] == "full-post"
        assert data["author"] == 2
        assert data["categories"] == [3, 5]
        assert data["tags"] == [7, 8]
        assert data["featured_media"] == 50

    def test_default_status_is_draft(self, mock_client):
        mock_client.post.return_value = {"id": 101}
        create_post(mock_client, title="Test")
        data = mock_client.post.call_args[1]["data"]
        assert data["status"] == "draft"

    def test_api_error(self, mock_client):
        mock_client.post.side_effect = WPApiError(
            400, "rest_invalid_param", "Invalid parameter"
        )
        with pytest.raises(WPApiError):
            create_post(mock_client, title="Bad Post")


class TestUpdatePost:
    def test_update_title(self, mock_client):
        mock_client.post.return_value = {"id": 42, "title": {"rendered": "Updated"}}
        result = update_post(mock_client, 42, title="Updated")
        assert result["id"] == 42
        mock_client.post.assert_called_once_with("posts/42", data={"title": "Updated"})

    def test_update_multiple_fields(self, mock_client):
        mock_client.post.return_value = {"id": 42}
        update_post(mock_client, 42, title="New Title", status="publish")
        data = mock_client.post.call_args[1]["data"]
        assert data["title"] == "New Title"
        assert data["status"] == "publish"

    def test_empty_update_raises(self, mock_client):
        with pytest.raises(ValueError, match="No fields to update"):
            update_post(mock_client, 42)

    def test_invalid_post_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid post ID"):
            update_post(mock_client, 0, title="X")


class TestDeletePost:
    def test_trash_by_default(self, mock_client):
        mock_client.delete.return_value = {"id": 42, "status": "trash"}
        result = delete_post(mock_client, 42)
        assert result["status"] == "trash"
        mock_client.delete.assert_called_once_with("posts/42", params=None)

    def test_force_delete(self, mock_client):
        mock_client.delete.return_value = {"deleted": True}
        result = delete_post(mock_client, 42, force=True)
        assert result["deleted"] is True
        mock_client.delete.assert_called_once_with("posts/42", params={"force": True})

    def test_invalid_post_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid post ID"):
            delete_post(mock_client, -5)

    def test_api_404(self, mock_client):
        mock_client.delete.side_effect = WPApiError(404, "not_found", "Not found")
        with pytest.raises(WPApiError):
            delete_post(mock_client, 999)


class TestPostIdValidation:
    def test_bool_rejected(self):
        with pytest.raises(ValueError, match="Invalid post ID"):
            _validate_post_id(True)

    def test_false_rejected(self):
        with pytest.raises(ValueError, match="Invalid post ID"):
            _validate_post_id(False)
