"""Tests for wpa.menu — nav menu, menu item, and menu location management."""

from unittest.mock import MagicMock

import pytest

from wpa.menu import (
    ITEM_AVAILABLE_FIELDS,
    ITEM_DEFAULT_FIELDS,
    LOCATION_DEFAULT_FIELDS,
    MENU_AVAILABLE_FIELDS,
    MENU_DEFAULT_FIELDS,
    create_menu,
    create_menu_item,
    delete_menu,
    delete_menu_item,
    get_menu,
    list_menu_items,
    list_menu_locations,
    list_menus,
    update_menu_item,
    validate_item_fields,
    validate_menu_fields,
)

SAMPLE_API_MENU = {
    "id": 3,
    "name": "Primary",
    "slug": "primary",
    "description": "Main navigation",
    "locations": ["header"],
    "auto_add": False,
}

SAMPLE_API_ITEM = {
    "id": 71,
    "title": {"raw": "About us", "rendered": "About us"},
    "status": "publish",
    "url": "https://example.com/about",
    "type": "post_type",
    "object": "page",
    "object_id": 12,
    "parent": 0,
    "menu_order": 2,
    "menus": 3,
}

SAMPLE_API_LOCATIONS = {
    "header": {"name": "header", "description": "Header menu", "menu": 3},
    "footer": {"name": "footer", "description": "Footer menu", "menu": 0},
}


@pytest.fixture
def mock_client():
    return MagicMock()


class TestValidateFields:
    def test_menu_defaults(self):
        assert validate_menu_fields(None) == MENU_DEFAULT_FIELDS

    def test_menu_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_menu_fields("id,bogus")

    def test_item_defaults(self):
        assert validate_item_fields(None) == ITEM_DEFAULT_FIELDS

    def test_item_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_item_fields("bogus")

    def test_defaults_are_available(self):
        for f in MENU_DEFAULT_FIELDS:
            assert f in MENU_AVAILABLE_FIELDS
        for f in ITEM_DEFAULT_FIELDS:
            assert f in ITEM_AVAILABLE_FIELDS


class TestListMenus:
    def test_list_success(self, mock_client):
        mock_client.get_list.return_value = iter([SAMPLE_API_MENU])
        rows = list_menus(mock_client)
        assert rows[0]["id"] == 3
        assert rows[0]["name"] == "Primary"
        endpoint = mock_client.get_list.call_args[0][0]
        params = mock_client.get_list.call_args[1]["params"]
        assert endpoint == "menus"
        assert params["context"] == "edit"


class TestGetMenu:
    def test_get_success(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_MENU
        row = get_menu(mock_client, 3)
        assert row["name"] == "Primary"
        assert mock_client.get.call_args[0][0] == "menus/3"

    def test_invalid_id_raises(self, mock_client):
        with pytest.raises(ValueError, match="menu ID"):
            get_menu(mock_client, 0)
        mock_client.get.assert_not_called()


class TestCreateMenu:
    def test_create_success(self, mock_client):
        mock_client.post.return_value = SAMPLE_API_MENU
        create_menu(mock_client, "Primary", description="Main navigation")
        mock_client.post.assert_called_once_with(
            "menus", data={"name": "Primary", "description": "Main navigation"}
        )

    def test_empty_name_raises(self, mock_client):
        with pytest.raises(ValueError, match="name"):
            create_menu(mock_client, "")
        mock_client.post.assert_not_called()


class TestDeleteMenu:
    def test_delete_is_always_forced(self, mock_client):
        delete_menu(mock_client, 3)
        mock_client.delete.assert_called_once_with("menus/3", params={"force": True})

    def test_invalid_id_raises(self, mock_client):
        with pytest.raises(ValueError, match="menu ID"):
            delete_menu(mock_client, -1)


class TestListMenuItems:
    def test_list_filters_by_menu(self, mock_client):
        mock_client.get_list.return_value = iter([SAMPLE_API_ITEM])
        rows = list_menu_items(mock_client, menu=3)
        assert rows[0]["id"] == 71
        assert rows[0]["title"] == "About us"
        params = mock_client.get_list.call_args[1]["params"]
        assert params["menus"] == 3

    def test_title_rendered_flattened(self, mock_client):
        mock_client.get_list.return_value = iter([SAMPLE_API_ITEM])
        rows = list_menu_items(mock_client, menu=3)
        assert rows[0]["title"] == "About us"

    def test_invalid_menu_raises(self, mock_client):
        with pytest.raises(ValueError, match="menu ID"):
            list_menu_items(mock_client, menu=0)


class TestCreateMenuItem:
    def test_custom_item_needs_title_and_url(self, mock_client):
        mock_client.post.return_value = SAMPLE_API_ITEM
        create_menu_item(mock_client, 3, title="Docs", url="https://example.com/docs")
        data = mock_client.post.call_args[1]["data"]
        assert data["menus"] == 3
        assert data["type"] == "custom"
        assert data["title"] == "Docs"
        assert data["url"] == "https://example.com/docs"

    def test_object_item_defaults_to_post_type(self, mock_client):
        mock_client.post.return_value = SAMPLE_API_ITEM
        create_menu_item(mock_client, 3, object_type="page", object_id=12)
        data = mock_client.post.call_args[1]["data"]
        assert data["type"] == "post_type"
        assert data["object"] == "page"
        assert data["object_id"] == 12

    def test_taxonomy_object_maps_to_taxonomy_type(self, mock_client):
        mock_client.post.return_value = SAMPLE_API_ITEM
        create_menu_item(mock_client, 3, object_type="category", object_id=7)
        data = mock_client.post.call_args[1]["data"]
        assert data["type"] == "taxonomy"
        assert data["object"] == "category"

    def test_parent_and_position_forwarded(self, mock_client):
        mock_client.post.return_value = SAMPLE_API_ITEM
        create_menu_item(
            mock_client, 3, title="Docs", url="https://x.test", parent=71, position=4
        )
        data = mock_client.post.call_args[1]["data"]
        assert data["parent"] == 71
        assert data["menu_order"] == 4

    def test_url_without_title_raises(self, mock_client):
        with pytest.raises(ValueError, match="title"):
            create_menu_item(mock_client, 3, url="https://example.com/docs")
        mock_client.post.assert_not_called()

    def test_neither_url_nor_object_raises(self, mock_client):
        with pytest.raises(ValueError, match="url"):
            create_menu_item(mock_client, 3, title="Dangling")
        mock_client.post.assert_not_called()

    def test_object_id_without_object_raises(self, mock_client):
        with pytest.raises(ValueError, match="object"):
            create_menu_item(mock_client, 3, object_id=12)
        mock_client.post.assert_not_called()


class TestUpdateMenuItem:
    def test_update_forwards_fields(self, mock_client):
        mock_client.post.return_value = SAMPLE_API_ITEM
        update_menu_item(mock_client, 71, title="Renamed", menu_order=1)
        mock_client.post.assert_called_once_with(
            "menu-items/71", data={"title": "Renamed", "menu_order": 1}
        )

    def test_no_fields_raises(self, mock_client):
        with pytest.raises(ValueError, match="No fields"):
            update_menu_item(mock_client, 71)

    def test_invalid_id_raises(self, mock_client):
        with pytest.raises(ValueError, match="menu item ID"):
            update_menu_item(mock_client, 0, title="x")


class TestDeleteMenuItem:
    def test_delete_is_always_forced(self, mock_client):
        delete_menu_item(mock_client, 71)
        mock_client.delete.assert_called_once_with(
            "menu-items/71", params={"force": True}
        )


class TestListMenuLocations:
    def test_locations_dict_to_rows(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_LOCATIONS
        rows = list_menu_locations(mock_client)
        names = [r["name"] for r in rows]
        assert names == sorted(names)
        by_name = {r["name"]: r for r in rows}
        assert by_name["header"]["menu"] == 3
        for f in LOCATION_DEFAULT_FIELDS:
            assert f in rows[0]

    def test_non_dict_response_returns_empty(self, mock_client):
        mock_client.get.return_value = ["unexpected"]
        assert list_menu_locations(mock_client) == []
