"""Tests for wpa.comment — comment CRUD and moderation."""

from unittest.mock import MagicMock

import pytest

from wpa.exceptions import WPApiError
from wpa.comment import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    _extract_comment_row,
    approve_comment,
    create_comment,
    delete_comment,
    get_comment,
    list_comments,
    spam_comment,
    trash_comment,
    unapprove_comment,
    unspam_comment,
    update_comment,
    validate_fields,
)


@pytest.fixture
def mock_client():
    return MagicMock()


SAMPLE_API_COMMENT = {
    "id": 11,
    "post": 42,
    "parent": 0,
    "author": 1,
    "author_name": "Jane Doe",
    "author_email": "jane@example.com",
    "author_url": "https://jane.example.com",
    "date": "2026-04-10T12:00:00",
    "status": "approved",
    "content": {"rendered": "<p>Nice post!</p>", "raw": "Nice post!"},
    "type": "comment",
    "link": "https://example.com/post/42#comment-11",
}


class TestExtractCommentRow:
    def test_extracts_all_fields(self):
        row = _extract_comment_row(SAMPLE_API_COMMENT)
        assert row["id"] == 11
        assert row["post"] == 42
        assert row["author_name"] == "Jane Doe"
        assert row["author_email"] == "jane@example.com"
        assert row["status"] == "approved"

    def test_flattens_rendered_content(self):
        row = _extract_comment_row(SAMPLE_API_COMMENT)
        assert row["content"] == "<p>Nice post!</p>"

    def test_missing_fields_default_to_empty(self):
        row = _extract_comment_row({"id": 1})
        assert row["author_name"] == ""
        assert row["status"] == ""
        assert row["content"] == ""


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields(self):
        result = validate_fields("id,post,status")
        assert result == ["id", "post", "status"]

    def test_all_fields_valid(self):
        all_fields = ",".join(AVAILABLE_FIELDS)
        assert validate_fields(all_fields) == AVAILABLE_FIELDS

    def test_invalid_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field 'bogus'"):
            validate_fields("id,bogus")

    def test_strips_whitespace(self):
        assert validate_fields("id , post , status") == ["id", "post", "status"]


class TestListComments:
    def test_basic_list(self, mock_client):
        mock_client.get_list.return_value = iter([SAMPLE_API_COMMENT])
        rows = list_comments(mock_client)
        assert len(rows) == 1
        assert rows[0]["id"] == 11
        assert rows[0]["author_name"] == "Jane Doe"

    def test_passes_post_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_comments(mock_client, post=42)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["post"] == 42

    def test_passes_status_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_comments(mock_client, status="hold")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["status"] == "hold"

    def test_passes_parent_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_comments(mock_client, parent=5)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["parent"] == 5

    def test_passes_author_email(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_comments(mock_client, author_email="jane@example.com")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["author_email"] == "jane@example.com"

    def test_passes_search(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_comments(mock_client, search="hello")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["search"] == "hello"

    def test_passes_per_page(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_comments(mock_client, per_page=25)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["per_page"] == 25

    def test_passes_orderby_and_order(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_comments(mock_client, orderby="date", order="asc")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["orderby"] == "date"
        assert params["order"] == "asc"

    def test_uses_edit_context(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_comments(mock_client)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["context"] == "edit"

    def test_empty_results(self, mock_client):
        mock_client.get_list.return_value = iter([])
        assert list_comments(mock_client) == []

    def test_specific_page_uses_get(self, mock_client):
        mock_client.get.return_value = [SAMPLE_API_COMMENT]
        rows = list_comments(mock_client, page=2)
        assert len(rows) == 1
        mock_client.get.assert_called_once()
        mock_client.get_list.assert_not_called()

    def test_specific_page_non_list_response(self, mock_client):
        mock_client.get.return_value = {"error": "bad"}
        rows = list_comments(mock_client, page=1)
        assert rows == []


class TestGetComment:
    def test_get_existing_comment(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_COMMENT
        row = get_comment(mock_client, 11)
        assert row["id"] == 11
        mock_client.get.assert_called_once_with(
            "comments/11", params={"context": "edit"}
        )

    def test_invalid_comment_id_zero(self, mock_client):
        with pytest.raises(ValueError, match="Invalid comment ID"):
            get_comment(mock_client, 0)

    def test_invalid_comment_id_negative(self, mock_client):
        with pytest.raises(ValueError, match="Invalid comment ID"):
            get_comment(mock_client, -1)

    def test_invalid_comment_id_string(self, mock_client):
        with pytest.raises(ValueError, match="Invalid comment ID"):
            get_comment(mock_client, "abc")

    def test_api_404(self, mock_client):
        mock_client.get.side_effect = WPApiError(404, "not_found", "Not found")
        with pytest.raises(WPApiError):
            get_comment(mock_client, 999)


class TestCreateComment:
    def test_create_minimal(self, mock_client):
        mock_client.post.return_value = {"id": 99}
        result = create_comment(mock_client, post=42, content="Hi")
        assert result["id"] == 99
        data = mock_client.post.call_args[1]["data"]
        assert data["post"] == 42
        assert data["content"] == "Hi"

    def test_create_with_all_fields(self, mock_client):
        mock_client.post.return_value = {"id": 100}
        create_comment(
            mock_client,
            post=42,
            content="Reply",
            author_name="Bob",
            author_email="bob@example.com",
            parent=11,
            status="approved",
        )
        data = mock_client.post.call_args[1]["data"]
        assert data["post"] == 42
        assert data["content"] == "Reply"
        assert data["author_name"] == "Bob"
        assert data["author_email"] == "bob@example.com"
        assert data["parent"] == 11
        assert data["status"] == "approved"

    def test_invalid_post_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid post ID"):
            create_comment(mock_client, post=0, content="Hi")

    def test_empty_content_raises(self, mock_client):
        with pytest.raises(ValueError, match="content"):
            create_comment(mock_client, post=42, content="")

    def test_api_error(self, mock_client):
        mock_client.post.side_effect = WPApiError(400, "rest_invalid", "Bad")
        with pytest.raises(WPApiError):
            create_comment(mock_client, post=42, content="Hi")


class TestUpdateComment:
    def test_update_content(self, mock_client):
        mock_client.post.return_value = {"id": 11}
        update_comment(mock_client, 11, content="Edited")
        mock_client.post.assert_called_once_with(
            "comments/11", data={"content": "Edited"}
        )

    def test_update_multiple_fields(self, mock_client):
        mock_client.post.return_value = {"id": 11}
        update_comment(mock_client, 11, content="Edited", status="approved")
        data = mock_client.post.call_args[1]["data"]
        assert data["content"] == "Edited"
        assert data["status"] == "approved"

    def test_empty_update_raises(self, mock_client):
        with pytest.raises(ValueError, match="No fields to update"):
            update_comment(mock_client, 11)

    def test_invalid_comment_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid comment ID"):
            update_comment(mock_client, 0, content="X")


class TestDeleteComment:
    def test_trash_by_default(self, mock_client):
        mock_client.delete.return_value = {"id": 11, "status": "trash"}
        result = delete_comment(mock_client, 11)
        assert result["status"] == "trash"
        mock_client.delete.assert_called_once_with("comments/11", params=None)

    def test_force_delete(self, mock_client):
        mock_client.delete.return_value = {"deleted": True}
        result = delete_comment(mock_client, 11, force=True)
        assert result["deleted"] is True
        mock_client.delete.assert_called_once_with(
            "comments/11", params={"force": True}
        )

    def test_invalid_comment_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid comment ID"):
            delete_comment(mock_client, -5)


class TestModerationActions:
    def test_approve(self, mock_client):
        mock_client.post.return_value = {"id": 11, "status": "approved"}
        result = approve_comment(mock_client, 11)
        assert result["status"] == "approved"
        mock_client.post.assert_called_once_with(
            "comments/11", data={"status": "approved"}
        )

    def test_unapprove(self, mock_client):
        mock_client.post.return_value = {"id": 11, "status": "hold"}
        unapprove_comment(mock_client, 11)
        mock_client.post.assert_called_once_with("comments/11", data={"status": "hold"})

    def test_spam(self, mock_client):
        mock_client.post.return_value = {"id": 11, "status": "spam"}
        spam_comment(mock_client, 11)
        mock_client.post.assert_called_once_with("comments/11", data={"status": "spam"})

    def test_unspam_restores_to_approved(self, mock_client):
        mock_client.post.return_value = {"id": 11, "status": "approved"}
        unspam_comment(mock_client, 11)
        mock_client.post.assert_called_once_with(
            "comments/11", data={"status": "approved"}
        )

    def test_trash_uses_delete_without_force(self, mock_client):
        mock_client.delete.return_value = {"id": 11, "status": "trash"}
        result = trash_comment(mock_client, 11)
        assert result["status"] == "trash"
        mock_client.delete.assert_called_once_with("comments/11", params=None)

    def test_approve_invalid_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid comment ID"):
            approve_comment(mock_client, 0)

    def test_spam_invalid_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid comment ID"):
            spam_comment(mock_client, -1)
