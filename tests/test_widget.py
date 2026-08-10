"""Tests for wpa.widget — classic widget management."""

from unittest.mock import MagicMock

import pytest

from wpa.widget import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    INACTIVE_SIDEBAR,
    _extract_widget_row,
    deactivate_widget,
    delete_widget,
    get_widget,
    list_widgets,
    update_widget,
    validate_fields,
)

SAMPLE_API_WIDGET = {
    "id": "recent-posts-3",
    "id_base": "recent-posts",
    "sidebar": "sidebar-1",
    "rendered": "<ul><li>Post</li></ul>",
    "instance": {"raw": {"title": "Latest", "number": 5}},
}

SAMPLE_INACTIVE_WIDGET = {
    "id": "calendar-2",
    "id_base": "calendar",
    "sidebar": "wp_inactive_widgets",
    "rendered": "",
    "instance": {"raw": {}},
}


@pytest.fixture
def mock_client():
    return MagicMock()


class TestValidateFields:
    def test_none_returns_defaults(self):
        assert validate_fields(None) == DEFAULT_FIELDS

    def test_valid_fields_parsed(self):
        assert validate_fields("id,sidebar") == ["id", "sidebar"]

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_fields("id,bogus")

    def test_defaults_are_available(self):
        for f in DEFAULT_FIELDS:
            assert f in AVAILABLE_FIELDS


class TestExtractWidgetRow:
    def test_status_synthesized_active(self):
        row = _extract_widget_row(SAMPLE_API_WIDGET)
        assert row["status"] == "active"
        assert row["id"] == "recent-posts-3"
        assert row["sidebar"] == "sidebar-1"

    def test_status_synthesized_inactive(self):
        row = _extract_widget_row(SAMPLE_INACTIVE_WIDGET)
        assert row["status"] == "inactive"


class TestListWidgets:
    def test_list_success(self, mock_client):
        mock_client.get.return_value = [SAMPLE_API_WIDGET]
        rows = list_widgets(mock_client)
        assert rows[0]["id"] == "recent-posts-3"
        mock_client.get.assert_called_once_with("widgets", params={"context": "edit"})

    def test_sidebar_filter(self, mock_client):
        mock_client.get.return_value = []
        list_widgets(mock_client, sidebar="sidebar-1")
        params = mock_client.get.call_args[1]["params"]
        assert params["sidebar"] == "sidebar-1"

    def test_non_list_response_returns_empty(self, mock_client):
        mock_client.get.return_value = {"unexpected": "shape"}
        assert list_widgets(mock_client) == []


class TestGetWidget:
    def test_get_success(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_WIDGET
        row = get_widget(mock_client, "recent-posts-3")
        assert row["id_base"] == "recent-posts"
        assert mock_client.get.call_args[0][0] == "widgets/recent-posts-3"

    def test_invalid_id_raises(self, mock_client):
        with pytest.raises(ValueError, match="widget"):
            get_widget(mock_client, "../evil")
        mock_client.get.assert_not_called()


class TestUpdateWidget:
    def test_move_to_sidebar(self, mock_client):
        mock_client.post.return_value = SAMPLE_API_WIDGET
        update_widget(mock_client, "recent-posts-3", sidebar="sidebar-2")
        mock_client.post.assert_called_once_with(
            "widgets/recent-posts-3", data={"sidebar": "sidebar-2"}
        )

    def test_instance_json_parsed(self, mock_client):
        mock_client.post.return_value = SAMPLE_API_WIDGET
        update_widget(
            mock_client, "recent-posts-3", instance_json='{"title": "X", "number": 3}'
        )
        data = mock_client.post.call_args[1]["data"]
        assert data["instance"] == {"raw": {"title": "X", "number": 3}}

    def test_invalid_instance_json_raises(self, mock_client):
        with pytest.raises(ValueError, match="JSON"):
            update_widget(mock_client, "recent-posts-3", instance_json="{nope")
        mock_client.post.assert_not_called()

    def test_non_object_instance_json_raises(self, mock_client):
        with pytest.raises(ValueError, match="object"):
            update_widget(mock_client, "recent-posts-3", instance_json='["a"]')
        mock_client.post.assert_not_called()

    def test_no_fields_raises(self, mock_client):
        with pytest.raises(ValueError, match="No fields"):
            update_widget(mock_client, "recent-posts-3")
        mock_client.post.assert_not_called()


class TestDeactivateWidget:
    def test_moves_to_inactive_sidebar(self, mock_client):
        mock_client.post.return_value = SAMPLE_INACTIVE_WIDGET
        deactivate_widget(mock_client, "recent-posts-3")
        mock_client.post.assert_called_once_with(
            "widgets/recent-posts-3", data={"sidebar": INACTIVE_SIDEBAR}
        )


class TestDeleteWidget:
    def test_delete_forced(self, mock_client):
        delete_widget(mock_client, "recent-posts-3", force=True)
        mock_client.delete.assert_called_once_with(
            "widgets/recent-posts-3", params={"force": True}
        )

    def test_delete_default_moves_to_inactive(self, mock_client):
        delete_widget(mock_client, "recent-posts-3")
        mock_client.delete.assert_called_once_with("widgets/recent-posts-3", params={})

    def test_invalid_id_raises(self, mock_client):
        with pytest.raises(ValueError, match="widget"):
            delete_widget(mock_client, "a/b")
        mock_client.delete.assert_not_called()
