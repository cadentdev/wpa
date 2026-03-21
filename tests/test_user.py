"""Tests for wpa.user — WordPress user CRUD via REST API."""

from unittest.mock import MagicMock, patch

import pytest

from wpa.user import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    USER_FIELDS,
    _validate_user_id,
    create_user,
    delete_user,
    list_users,
    update_user,
    validate_fields,
)


# --- Field validation ---


class TestValidateFields:
    def test_valid_fields(self):
        result = validate_fields("id,username,email")
        assert result == ["id", "username", "email"]

    def test_default_fields_when_none(self):
        result = validate_fields(None)
        assert result == DEFAULT_FIELDS

    def test_single_field(self):
        result = validate_fields("email")
        assert result == ["email"]

    def test_strips_whitespace(self):
        result = validate_fields("id, username, email")
        assert result == ["id", "username", "email"]

    def test_invalid_field_raises_error(self):
        with pytest.raises(ValueError, match="Unknown field.*'bogus'"):
            validate_fields("id,bogus,email")

    def test_all_available_fields(self):
        all_fields = ",".join(AVAILABLE_FIELDS)
        result = validate_fields(all_fields)
        assert result == list(AVAILABLE_FIELDS)

    def test_user_fields_maps_to_api_keys(self):
        assert USER_FIELDS["username"] == "slug"
        assert USER_FIELDS["display_name"] == "name"
        assert USER_FIELDS["registered"] == "registered_date"


# --- Mock response helper ---


def _mock_response(status_code, json_data=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


MOCK_USER_LIST = [
    {
        "id": 1,
        "slug": "admin",
        "name": "Admin User",
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User",
        "url": "",
        "description": "",
        "registered_date": "2020-01-01T00:00:00",
        "roles": ["administrator"],
    },
    {
        "id": 2,
        "slug": "editor",
        "name": "Editor User",
        "email": "editor@example.com",
        "first_name": "Editor",
        "last_name": "User",
        "url": "https://example.com",
        "description": "An editor",
        "registered_date": "2021-06-15T00:00:00",
        "roles": ["editor"],
    },
]


# --- list_users ---


class TestListUsers:
    @patch("wpa.user.requests.get")
    def test_list_users_success(self, mock_get):
        mock_get.return_value = _mock_response(200, MOCK_USER_LIST)
        rows = list_users("https://example.com", "admin", "pass")
        assert len(rows) == 2
        assert rows[0]["id"] == 1
        assert rows[0]["username"] == "admin"
        assert rows[0]["email"] == "admin@example.com"
        assert rows[0]["roles"] == "administrator"

    @patch("wpa.user.requests.get")
    def test_list_users_sends_context_edit(self, mock_get):
        mock_get.return_value = _mock_response(200, [])
        list_users("https://example.com", "admin", "pass")
        call_kwargs = mock_get.call_args
        assert (
            "context=edit" in call_kwargs[1].get("params", {}).values()
            or call_kwargs[1].get("params", {}).get("context") == "edit"
        )

    @patch("wpa.user.requests.get")
    def test_list_users_with_role_filter(self, mock_get):
        mock_get.return_value = _mock_response(200, [MOCK_USER_LIST[1]])
        list_users("https://example.com", "admin", "pass", role="editor")
        params = mock_get.call_args[1]["params"]
        assert params["roles"] == "editor"

    @patch("wpa.user.requests.get")
    def test_list_users_with_search(self, mock_get):
        mock_get.return_value = _mock_response(200, [MOCK_USER_LIST[0]])
        list_users("https://example.com", "admin", "pass", search="admin")
        params = mock_get.call_args[1]["params"]
        assert params["search"] == "admin"

    @patch("wpa.user.requests.get")
    def test_list_users_multiple_roles_joined(self, mock_get):
        user_data = [{**MOCK_USER_LIST[0], "roles": ["editor", "author"]}]
        mock_get.return_value = _mock_response(200, user_data)
        rows = list_users("https://example.com", "admin", "pass")
        assert rows[0]["roles"] == "editor, author"

    @patch("wpa.user.requests.get")
    def test_list_users_403_raises(self, mock_get):
        mock_get.return_value = _mock_response(
            403,
            {
                "code": "rest_forbidden",
                "message": "Sorry, you are not allowed to list users.",
            },
        )
        with pytest.raises(SystemExit):
            list_users("https://example.com", "admin", "pass")

    @patch("wpa.user.requests.get")
    def test_list_users_connection_error(self, mock_get):
        import requests

        mock_get.side_effect = requests.ConnectionError("Connection refused")
        with pytest.raises(SystemExit):
            list_users("https://example.com", "admin", "pass")

    @patch("wpa.user.requests.get")
    def test_list_users_timeout(self, mock_get):
        import requests

        mock_get.side_effect = requests.Timeout("Timed out")
        with pytest.raises(SystemExit):
            list_users("https://example.com", "admin", "pass")


# --- create_user ---


class TestCreateUser:
    @patch("wpa.user.requests.post")
    def test_create_user_success(self, mock_post):
        created = {**MOCK_USER_LIST[0], "id": 5}
        mock_post.return_value = _mock_response(201, created)
        result = create_user(
            "https://example.com",
            "admin",
            "pass",
            username="newuser",
            email="new@example.com",
            password_new="secret123",
        )
        assert result["id"] == 5

    @patch("wpa.user.requests.post")
    def test_create_user_sends_payload(self, mock_post):
        mock_post.return_value = _mock_response(201, {"id": 5})
        create_user(
            "https://example.com",
            "admin",
            "pass",
            username="newuser",
            email="new@example.com",
            password_new="secret123",
            role="editor",
            first_name="New",
            last_name="User",
        )
        payload = mock_post.call_args[1]["json"]
        assert payload["username"] == "newuser"
        assert payload["email"] == "new@example.com"
        assert payload["password"] == "secret123"
        assert payload["roles"] == ["editor"]
        assert payload["first_name"] == "New"
        assert payload["last_name"] == "User"

    @patch("wpa.user.requests.post")
    def test_create_user_error(self, mock_post):
        mock_post.return_value = _mock_response(
            400,
            {
                "code": "existing_user_login",
                "message": "Sorry, that username already exists!",
            },
        )
        with pytest.raises(SystemExit):
            create_user(
                "https://example.com",
                "admin",
                "pass",
                username="admin",
                email="admin@example.com",
                password_new="secret",
            )


# --- update_user ---


class TestUpdateUser:
    @patch("wpa.user.requests.post")
    def test_update_user_success(self, mock_post):
        updated = {**MOCK_USER_LIST[0], "email": "newemail@example.com"}
        mock_post.return_value = _mock_response(200, updated)
        result = update_user(
            "https://example.com",
            "admin",
            "pass",
            user_id=1,
            email="newemail@example.com",
        )
        assert result["email"] == "newemail@example.com"

    @patch("wpa.user.requests.post")
    def test_update_user_sends_only_provided_fields(self, mock_post):
        mock_post.return_value = _mock_response(200, MOCK_USER_LIST[0])
        update_user(
            "https://example.com",
            "admin",
            "pass",
            user_id=1,
            email="new@example.com",
        )
        payload = mock_post.call_args[1]["json"]
        assert payload == {"email": "new@example.com"}

    @patch("wpa.user.requests.post")
    def test_update_user_role(self, mock_post):
        mock_post.return_value = _mock_response(200, MOCK_USER_LIST[0])
        update_user(
            "https://example.com",
            "admin",
            "pass",
            user_id=1,
            role="author",
        )
        payload = mock_post.call_args[1]["json"]
        assert payload["roles"] == ["author"]

    @patch("wpa.user.requests.post")
    def test_update_user_404(self, mock_post):
        mock_post.return_value = _mock_response(
            404, {"code": "rest_user_invalid_id", "message": "Invalid user ID."}
        )
        with pytest.raises(SystemExit):
            update_user(
                "https://example.com",
                "admin",
                "pass",
                user_id=999,
                email="x@example.com",
            )


# --- delete_user ---


class TestDeleteUser:
    @patch("wpa.user.requests.delete")
    def test_delete_user_success(self, mock_delete):
        mock_delete.return_value = _mock_response(
            200, {"deleted": True, "previous": MOCK_USER_LIST[1]}
        )
        result = delete_user(
            "https://example.com",
            "admin",
            "pass",
            user_id=2,
            reassign=1,
        )
        assert result["deleted"] is True

    @patch("wpa.user.requests.delete")
    def test_delete_user_sends_force_and_reassign(self, mock_delete):
        mock_delete.return_value = _mock_response(200, {"deleted": True})
        delete_user(
            "https://example.com",
            "admin",
            "pass",
            user_id=2,
            reassign=1,
        )
        params = mock_delete.call_args[1]["params"]
        assert params["force"] is True
        assert params["reassign"] == 1

    @patch("wpa.user.requests.delete")
    def test_delete_user_without_reassign(self, mock_delete):
        mock_delete.return_value = _mock_response(200, {"deleted": True})
        delete_user(
            "https://example.com",
            "admin",
            "pass",
            user_id=2,
        )
        params = mock_delete.call_args[1]["params"]
        assert params["force"] is True
        assert "reassign" not in params

    @patch("wpa.user.requests.delete")
    def test_delete_user_404(self, mock_delete):
        mock_delete.return_value = _mock_response(
            404, {"code": "rest_user_invalid_id", "message": "Invalid user ID."}
        )
        with pytest.raises(SystemExit):
            delete_user(
                "https://example.com",
                "admin",
                "pass",
                user_id=999,
            )


# --- Security: user_id validation ---


class TestUserIdValidation:
    def test_valid_positive_integer(self):
        # Should not raise
        _validate_user_id(1)
        _validate_user_id(999)

    def test_zero_rejected(self):
        with pytest.raises(SystemExit):
            _validate_user_id(0)

    def test_negative_rejected(self):
        with pytest.raises(SystemExit):
            _validate_user_id(-1)

    def test_string_rejected(self):
        with pytest.raises(SystemExit):
            _validate_user_id("1")

    def test_path_injection_rejected(self):
        with pytest.raises(SystemExit):
            _validate_user_id("1/../../wp-json/wp/v2/settings")


# --- Security: empty update payload ---


class TestEmptyUpdatePayload:
    def test_update_with_no_fields_exits(self):
        with pytest.raises(SystemExit):
            update_user(
                "https://example.com",
                "admin",
                "pass",
                user_id=1,
            )


# --- Security: invalid JSON response ---


class TestInvalidJsonResponse:
    @patch("wpa.user.requests.get")
    def test_list_users_invalid_json(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.side_effect = ValueError("No JSON")
        resp.text = "not json"
        mock_get.return_value = resp
        with pytest.raises(SystemExit):
            list_users("https://example.com", "admin", "pass")
