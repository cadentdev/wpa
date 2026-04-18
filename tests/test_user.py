"""Tests for wpa.user — WordPress user CRUD via REST API."""

from unittest.mock import MagicMock

import pytest

from wpa.exceptions import WPApiError
from wpa.user import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    USER_FIELDS,
    _validate_user_id,
    create_user,
    delete_user,
    get_user,
    list_users,
    set_role,
    update_user,
    validate_fields,
)


@pytest.fixture
def mock_client():
    """Create a mock WPApiClient."""
    return MagicMock()


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


# --- list_users ---


class TestListUsers:
    def test_list_users_success(self, mock_client):
        mock_client.get_list.return_value = iter(MOCK_USER_LIST)
        rows = list_users(mock_client)
        assert len(rows) == 2
        assert rows[0]["id"] == 1
        assert rows[0]["username"] == "admin"
        assert rows[0]["email"] == "admin@example.com"
        assert rows[0]["roles"] == "administrator"

    def test_list_users_sends_context_edit(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_users(mock_client)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["context"] == "edit"

    def test_list_users_sends_per_page_100(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_users(mock_client)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["per_page"] == 100

    def test_list_users_with_role_filter(self, mock_client):
        mock_client.get_list.return_value = iter([MOCK_USER_LIST[1]])
        list_users(mock_client, role="editor")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["roles"] == "editor"

    def test_list_users_with_search(self, mock_client):
        mock_client.get_list.return_value = iter([MOCK_USER_LIST[0]])
        list_users(mock_client, search="admin")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["search"] == "admin"

    def test_list_users_multiple_roles_joined(self, mock_client):
        user_data = [{**MOCK_USER_LIST[0], "roles": ["editor", "author"]}]
        mock_client.get_list.return_value = iter(user_data)
        rows = list_users(mock_client)
        assert rows[0]["roles"] == "editor, author"

    def test_list_users_api_error(self, mock_client):
        mock_client.get_list.side_effect = WPApiError(
            403, "rest_forbidden", "Sorry, not allowed."
        )
        with pytest.raises(WPApiError):
            list_users(mock_client)


# --- create_user ---


class TestCreateUser:
    def test_create_user_success(self, mock_client):
        created = {**MOCK_USER_LIST[0], "id": 5}
        mock_client.post.return_value = created
        result = create_user(
            mock_client,
            username="newuser",
            email="new@example.com",
            password_new="secret123",
        )
        assert result["id"] == 5

    def test_create_user_sends_payload(self, mock_client):
        mock_client.post.return_value = {"id": 5}
        create_user(
            mock_client,
            username="newuser",
            email="new@example.com",
            password_new="secret123",
            role="editor",
            first_name="New",
            last_name="User",
        )
        data = mock_client.post.call_args[1]["data"]
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert data["password"] == "secret123"
        assert data["roles"] == ["editor"]
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"

    def test_create_user_error(self, mock_client):
        mock_client.post.side_effect = WPApiError(
            400, "existing_user_login", "Sorry, that username already exists!"
        )
        with pytest.raises(WPApiError):
            create_user(
                mock_client,
                username="admin",
                email="admin@example.com",
                password_new="secret",
            )


# --- update_user ---


class TestUpdateUser:
    def test_update_user_success(self, mock_client):
        updated = {**MOCK_USER_LIST[0], "email": "newemail@example.com"}
        mock_client.post.return_value = updated
        result = update_user(mock_client, user_id=1, email="newemail@example.com")
        assert result["email"] == "newemail@example.com"

    def test_update_user_sends_only_provided_fields(self, mock_client):
        mock_client.post.return_value = MOCK_USER_LIST[0]
        update_user(mock_client, user_id=1, email="new@example.com")
        data = mock_client.post.call_args[1]["data"]
        assert data == {"email": "new@example.com"}

    def test_update_user_role(self, mock_client):
        mock_client.post.return_value = MOCK_USER_LIST[0]
        update_user(mock_client, user_id=1, role="author")
        data = mock_client.post.call_args[1]["data"]
        assert data["roles"] == ["author"]

    def test_update_user_display_name_maps_to_name(self, mock_client):
        mock_client.post.return_value = MOCK_USER_LIST[0]
        update_user(mock_client, user_id=1, display_name="New Display")
        data = mock_client.post.call_args[1]["data"]
        assert data == {"name": "New Display"}

    def test_update_user_404(self, mock_client):
        mock_client.post.side_effect = WPApiError(
            404, "rest_user_invalid_id", "Invalid user ID."
        )
        with pytest.raises(WPApiError):
            update_user(mock_client, user_id=999, email="x@example.com")


# --- delete_user ---


class TestDeleteUser:
    def test_delete_user_success(self, mock_client):
        mock_client.delete.return_value = {
            "deleted": True,
            "previous": MOCK_USER_LIST[1],
        }
        result = delete_user(mock_client, user_id=2, reassign=1)
        assert result["deleted"] is True

    def test_delete_user_sends_force_and_reassign(self, mock_client):
        mock_client.delete.return_value = {"deleted": True}
        delete_user(mock_client, user_id=2, reassign=1)
        params = mock_client.delete.call_args[1]["params"]
        assert params["force"] is True
        assert params["reassign"] == 1

    def test_delete_user_without_reassign(self, mock_client):
        mock_client.delete.return_value = {"deleted": True}
        delete_user(mock_client, user_id=2)
        params = mock_client.delete.call_args[1]["params"]
        assert params["force"] is True
        assert "reassign" not in params

    def test_delete_user_404(self, mock_client):
        mock_client.delete.side_effect = WPApiError(
            404, "rest_user_invalid_id", "Invalid user ID."
        )
        with pytest.raises(WPApiError):
            delete_user(mock_client, user_id=999)


# --- Security: user_id validation ---


class TestUserIdValidation:
    def test_valid_positive_integer(self):
        # Should not raise
        _validate_user_id(1)
        _validate_user_id(999)

    def test_zero_rejected(self):
        with pytest.raises(ValueError, match="Invalid user ID"):
            _validate_user_id(0)

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="Invalid user ID"):
            _validate_user_id(-1)

    def test_string_rejected(self):
        with pytest.raises(ValueError, match="Invalid user ID"):
            _validate_user_id("1")

    def test_bool_rejected(self):
        with pytest.raises(ValueError, match="Invalid user ID"):
            _validate_user_id(True)

    def test_false_rejected(self):
        with pytest.raises(ValueError, match="Invalid user ID"):
            _validate_user_id(False)

    def test_path_injection_rejected(self):
        with pytest.raises(ValueError, match="Invalid user ID"):
            _validate_user_id("1/../../wp-json/wp/v2/settings")


# --- Security: empty update payload ---


class TestEmptyUpdatePayload:
    def test_update_with_no_fields_raises(self, mock_client):
        with pytest.raises(ValueError, match="No fields to update"):
            update_user(mock_client, user_id=1)


# --- get_user ---


class TestGetUser:
    def test_get_existing_user(self, mock_client):
        mock_client.get.return_value = MOCK_USER_LIST[0]
        row = get_user(mock_client, 1)
        assert row["id"] == 1
        assert row["username"] == "admin"
        assert row["email"] == "admin@example.com"
        assert row["display_name"] == "Admin User"
        mock_client.get.assert_called_once_with("users/1", params={"context": "edit"})

    def test_get_user_invalid_id_zero(self, mock_client):
        with pytest.raises(ValueError, match="Invalid user ID"):
            get_user(mock_client, 0)

    def test_get_user_invalid_id_negative(self, mock_client):
        with pytest.raises(ValueError, match="Invalid user ID"):
            get_user(mock_client, -1)

    def test_get_user_invalid_id_string(self, mock_client):
        with pytest.raises(ValueError, match="Invalid user ID"):
            get_user(mock_client, "abc")

    def test_get_user_404(self, mock_client):
        mock_client.get.side_effect = WPApiError(
            404, "rest_user_invalid_id", "Invalid user ID."
        )
        with pytest.raises(WPApiError):
            get_user(mock_client, 999)


# --- set_role ---


class TestSetRole:
    def test_set_role_success(self, mock_client):
        mock_client.post.return_value = {**MOCK_USER_LIST[1], "roles": ["author"]}
        result = set_role(mock_client, 2, "author")
        assert result["roles"] == ["author"]
        mock_client.post.assert_called_once_with("users/2", data={"roles": ["author"]})

    def test_set_role_invalid_id(self, mock_client):
        with pytest.raises(ValueError, match="Invalid user ID"):
            set_role(mock_client, 0, "editor")

    def test_set_role_404(self, mock_client):
        mock_client.post.side_effect = WPApiError(
            404, "rest_user_invalid_id", "Invalid user ID."
        )
        with pytest.raises(WPApiError):
            set_role(mock_client, 999, "subscriber")
