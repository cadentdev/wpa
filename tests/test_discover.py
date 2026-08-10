"""Tests for wpa.discover — REST API surface discovery."""

from unittest.mock import MagicMock

import pytest

from wpa.discover import (
    NAMESPACE_AVAILABLE_FIELDS,
    NAMESPACE_DEFAULT_FIELDS,
    ROUTE_AVAILABLE_FIELDS,
    ROUTE_DEFAULT_FIELDS,
    list_namespaces,
    list_routes,
    validate_namespace_fields,
    validate_route_fields,
)

SAMPLE_ROOT_NAMESPACES = {
    "namespaces": ["oembed/1.0", "wp/v2", "wp-site-health/v1"],
}

SAMPLE_ROOT_ROUTES = {
    "routes": {
        "/wp/v2/posts": {
            "namespace": "wp/v2",
            "methods": ["GET", "POST"],
        },
        "/wp/v2/posts/(?P<id>[\\d]+)": {
            "namespace": "wp/v2",
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        },
        "/oembed/1.0/embed": {
            "namespace": "oembed/1.0",
            "methods": ["GET"],
        },
    },
}


@pytest.fixture
def mock_client():
    return MagicMock()


class TestValidateFields:
    def test_namespace_none_returns_defaults(self):
        assert validate_namespace_fields(None) == NAMESPACE_DEFAULT_FIELDS

    def test_namespace_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_namespace_fields("bogus")

    def test_route_none_returns_defaults(self):
        assert validate_route_fields(None) == ROUTE_DEFAULT_FIELDS

    def test_route_valid_fields_parsed(self):
        assert validate_route_fields("route,methods") == ["route", "methods"]

    def test_route_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            validate_route_fields("route,bogus")

    def test_defaults_are_available(self):
        for f in NAMESPACE_DEFAULT_FIELDS:
            assert f in NAMESPACE_AVAILABLE_FIELDS
        for f in ROUTE_DEFAULT_FIELDS:
            assert f in ROUTE_AVAILABLE_FIELDS


class TestListNamespaces:
    def test_list_success(self, mock_client):
        mock_client.get_root.return_value = SAMPLE_ROOT_NAMESPACES
        rows = list_namespaces(mock_client)
        assert [r["namespace"] for r in rows] == [
            "oembed/1.0",
            "wp-site-health/v1",
            "wp/v2",
        ]
        mock_client.get_root.assert_called_once_with(params={"_fields": "namespaces"})

    def test_non_dict_response_returns_empty(self, mock_client):
        mock_client.get_root.return_value = ["unexpected"]
        assert list_namespaces(mock_client) == []

    def test_missing_namespaces_returns_empty(self, mock_client):
        mock_client.get_root.return_value = {}
        assert list_namespaces(mock_client) == []

    def test_non_string_entries_skipped(self, mock_client):
        mock_client.get_root.return_value = {"namespaces": ["wp/v2", 42]}
        rows = list_namespaces(mock_client)
        assert [r["namespace"] for r in rows] == ["wp/v2"]


class TestListRoutes:
    def test_list_success(self, mock_client):
        mock_client.get_root.return_value = SAMPLE_ROOT_ROUTES
        rows = list_routes(mock_client)
        assert len(rows) == 3
        assert rows[0]["route"] == "/oembed/1.0/embed"
        assert rows[0]["methods"] == "GET"
        assert rows[1]["namespace"] == "wp/v2"
        mock_client.get_root.assert_called_once_with(params={"_fields": "routes"})

    def test_namespace_filter(self, mock_client):
        mock_client.get_root.return_value = SAMPLE_ROOT_ROUTES
        rows = list_routes(mock_client, namespace="oembed/1.0")
        assert [r["route"] for r in rows] == ["/oembed/1.0/embed"]

    def test_methods_joined_sorted_routes(self, mock_client):
        mock_client.get_root.return_value = SAMPLE_ROOT_ROUTES
        rows = list_routes(mock_client)
        assert rows[2]["methods"] == "GET, POST, PUT, PATCH, DELETE"

    def test_non_dict_response_returns_empty(self, mock_client):
        mock_client.get_root.return_value = None
        assert list_routes(mock_client) == []

    def test_non_dict_route_values_skipped(self, mock_client):
        mock_client.get_root.return_value = {
            "routes": {"/wp/v2/posts": "not-an-object"}
        }
        assert list_routes(mock_client) == []
