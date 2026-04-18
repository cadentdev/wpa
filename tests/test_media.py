"""Tests for media CRUD operations."""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from wpa.media import (
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
    _extract_media_row,
    _validate_media_id,
    delete_media,
    get_media,
    import_media,
    list_media,
    validate_fields,
)


@pytest.fixture
def mock_client():
    """Create a mock WPApiClient."""
    return MagicMock()


SAMPLE_API_MEDIA = {
    "id": 101,
    "title": {"rendered": "test-image", "raw": "test-image"},
    "date": "2026-03-23T12:00:00",
    "mime_type": "image/jpeg",
    "media_type": "image",
    "alt_text": "A test image",
    "caption": {"rendered": "<p>Test caption</p>", "raw": "Test caption"},
    "description": {"rendered": "<p>Test description</p>", "raw": "Test description"},
    "source_url": "https://example.com/wp-content/uploads/2026/03/test-image.jpg",
    "post": 0,
    "author": 1,
    "link": "https://example.com/test-image/",
}


class TestExtractMediaRow:
    def test_extracts_rendered_fields(self):
        row = _extract_media_row(SAMPLE_API_MEDIA)
        assert row["title"] == "test-image"
        assert row["caption"] == "<p>Test caption</p>"
        assert row["description"] == "<p>Test description</p>"

    def test_missing_rendered_fields_default_to_empty(self):
        row = _extract_media_row({"id": 1})
        assert row["title"] == ""
        assert row["caption"] == ""
        assert row["description"] == ""


SAMPLE_API_MEDIA_2 = {
    "id": 102,
    "title": {"rendered": "logo", "raw": "logo"},
    "date": "2026-03-22T10:00:00",
    "mime_type": "image/png",
    "media_type": "image",
    "alt_text": "",
    "caption": {"rendered": "", "raw": ""},
    "description": {"rendered": "", "raw": ""},
    "source_url": "https://example.com/wp-content/uploads/2026/03/logo.png",
    "post": 42,
    "author": 1,
    "link": "https://example.com/logo/",
}


class TestValidateFields:
    def test_default_fields(self):
        fields = validate_fields(None)
        assert fields == DEFAULT_FIELDS

    def test_valid_custom_fields(self):
        fields = validate_fields("id,title,mime_type")
        assert fields == ["id", "title", "mime_type"]

    def test_invalid_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field 'bogus'"):
            validate_fields("id,bogus")

    def test_all_fields_valid(self):
        all_fields = ",".join(AVAILABLE_FIELDS)
        fields = validate_fields(all_fields)
        assert fields == AVAILABLE_FIELDS

    def test_whitespace_stripped(self):
        fields = validate_fields("id , title , mime_type")
        assert fields == ["id", "title", "mime_type"]


class TestListMedia:
    def test_basic_list(self, mock_client):
        mock_client.get_list.return_value = iter([SAMPLE_API_MEDIA, SAMPLE_API_MEDIA_2])
        rows = list_media(mock_client)
        assert len(rows) == 2
        assert rows[0]["id"] == 101
        assert rows[0]["title"] == "test-image"
        assert rows[0]["mime_type"] == "image/jpeg"
        assert rows[1]["id"] == 102

    def test_empty_list(self, mock_client):
        mock_client.get_list.return_value = iter([])
        rows = list_media(mock_client)
        assert rows == []

    def test_passes_media_type_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_media(mock_client, media_type="image")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["context"] == "edit"
        assert params["media_type"] == "image"

    def test_passes_mime_type_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_media(mock_client, mime_type="image/jpeg")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["mime_type"] == "image/jpeg"

    def test_passes_search_filter(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_media(mock_client, search="logo")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["search"] == "logo"

    def test_passes_per_page(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_media(mock_client, per_page=50)
        params = mock_client.get_list.call_args[1]["params"]
        assert params["per_page"] == 50

    def test_single_page_request(self, mock_client):
        mock_client.get.return_value = [SAMPLE_API_MEDIA]
        rows = list_media(mock_client, page=2)
        assert len(rows) == 1
        params = mock_client.get.call_args[1]["params"]
        assert params["page"] == 2

    def test_single_page_non_list_response(self, mock_client):
        mock_client.get.return_value = {}
        rows = list_media(mock_client, page=1)
        assert rows == []

    def test_extracts_rendered_title(self, mock_client):
        mock_client.get_list.return_value = iter([SAMPLE_API_MEDIA])
        rows = list_media(mock_client)
        assert rows[0]["title"] == "test-image"

    def test_extracts_rendered_caption(self, mock_client):
        mock_client.get_list.return_value = iter([SAMPLE_API_MEDIA])
        rows = list_media(mock_client)
        assert rows[0]["caption"] == "<p>Test caption</p>"

    def test_passes_orderby_and_order(self, mock_client):
        mock_client.get_list.return_value = iter([])
        list_media(mock_client, orderby="date", order="asc")
        params = mock_client.get_list.call_args[1]["params"]
        assert params["orderby"] == "date"
        assert params["order"] == "asc"


class TestGetMedia:
    def test_get_existing_media(self, mock_client):
        mock_client.get.return_value = SAMPLE_API_MEDIA
        row = get_media(mock_client, 101)
        assert row["id"] == 101
        assert row["title"] == "test-image"
        assert row["source_url"] == (
            "https://example.com/wp-content/uploads/2026/03/test-image.jpg"
        )
        mock_client.get.assert_called_once_with("media/101", params={"context": "edit"})

    def test_get_invalid_id_zero(self, mock_client):
        with pytest.raises(ValueError, match="Invalid media ID"):
            get_media(mock_client, 0)

    def test_get_invalid_id_negative(self, mock_client):
        with pytest.raises(ValueError, match="Invalid media ID"):
            get_media(mock_client, -1)

    def test_get_invalid_id_string(self, mock_client):
        with pytest.raises(ValueError, match="Invalid media ID"):
            get_media(mock_client, "abc")


class TestImportMedia:
    @patch("wpa.media.mimetypes.guess_type", return_value=("image/jpeg", None))
    @patch("builtins.open", mock_open(read_data=b"fake image data"))
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.abspath", return_value="/tmp/test-image.jpg")
    def test_import_local_file(
        self, mock_abs, mock_isfile, mock_exists, mock_mime, mock_client
    ):
        mock_client.post.return_value = {
            "id": 201,
            "source_url": "https://example.com/test.jpg",
        }
        result = import_media(mock_client, "/tmp/test-image.jpg")
        assert result["id"] == 201
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[0][0] == "media"
        assert "files" in call_kwargs[1]

    @patch("wpa.media.mimetypes.guess_type", return_value=("image/jpeg", None))
    @patch("builtins.open", mock_open(read_data=b"fake image data"))
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.abspath", return_value="/tmp/test-image.jpg")
    def test_import_with_title(
        self, mock_abs, mock_isfile, mock_exists, mock_mime, mock_client
    ):
        mock_client.post.return_value = {"id": 202}
        import_media(mock_client, "/tmp/test-image.jpg", title="My Image")
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"]["title"] == "My Image"

    @patch("wpa.media.mimetypes.guess_type", return_value=("image/jpeg", None))
    @patch("builtins.open", mock_open(read_data=b"fake image data"))
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.abspath", return_value="/tmp/test-image.jpg")
    def test_import_with_alt_text(
        self, mock_abs, mock_isfile, mock_exists, mock_mime, mock_client
    ):
        mock_client.post.return_value = {"id": 203}
        import_media(mock_client, "/tmp/test-image.jpg", alt_text="Alt text")
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"]["alt_text"] == "Alt text"

    @patch("wpa.media.mimetypes.guess_type", return_value=("image/jpeg", None))
    @patch("builtins.open", mock_open(read_data=b"fake image data"))
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.abspath", return_value="/tmp/test-image.jpg")
    def test_import_with_all_metadata(
        self, mock_abs, mock_isfile, mock_exists, mock_mime, mock_client
    ):
        mock_client.post.return_value = {"id": 204}
        import_media(
            mock_client,
            "/tmp/test-image.jpg",
            title="Title",
            alt_text="Alt",
            caption="Caption",
            description="Desc",
            post=42,
        )
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"]["title"] == "Title"
        assert call_kwargs["data"]["alt_text"] == "Alt"
        assert call_kwargs["data"]["caption"] == "Caption"
        assert call_kwargs["data"]["description"] == "Desc"
        assert call_kwargs["data"]["post"] == 42

    def test_import_file_not_found(self, mock_client):
        with pytest.raises(FileNotFoundError, match="File not found"):
            import_media(mock_client, "/nonexistent/file.jpg")

    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=False)
    @patch("os.path.abspath", return_value="/tmp/somedir")
    def test_import_not_a_file(self, mock_abs, mock_isfile, mock_exists, mock_client):
        with pytest.raises(ValueError, match="Not a file"):
            import_media(mock_client, "/tmp/somedir")

    @patch("wpa.media.mimetypes.guess_type", return_value=("image/jpeg", None))
    @patch("builtins.open", mock_open(read_data=b"fake data"))
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.abspath", return_value="/tmp/test-image.jpg")
    def test_import_no_metadata(
        self, mock_abs, mock_isfile, mock_exists, mock_mime, mock_client
    ):
        mock_client.post.return_value = {"id": 205}
        import_media(mock_client, "/tmp/test-image.jpg")
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"] == {}

    @patch("wpa.media.mimetypes.guess_type", return_value=(None, None))
    @patch("builtins.open", mock_open(read_data=b"fake image data"))
    @patch("os.path.exists", return_value=True)
    @patch("os.path.isfile", return_value=True)
    @patch("os.path.abspath", return_value="/tmp/test-image.unknown")
    def test_import_mime_fallback_application_octet_stream(
        self, mock_abs, mock_isfile, mock_exists, mock_mime, mock_client
    ):
        mock_client.post.return_value = {"id": 206}
        import_media(mock_client, "/tmp/test-image.unknown")
        files = mock_client.post.call_args[1]["files"]
        assert files["file"][2] == "application/octet-stream"


class TestDeleteMedia:
    def test_delete_to_trash(self, mock_client):
        mock_client.delete.return_value = {
            "deleted": True,
            "previous": SAMPLE_API_MEDIA,
        }
        result = delete_media(mock_client, 101)
        assert result["deleted"] is True
        mock_client.delete.assert_called_once_with("media/101", params=None)

    def test_delete_force(self, mock_client):
        mock_client.delete.return_value = {"deleted": True}
        delete_media(mock_client, 101, force=True)
        mock_client.delete.assert_called_once_with("media/101", params={"force": True})

    def test_delete_invalid_id_zero(self, mock_client):
        with pytest.raises(ValueError, match="Invalid media ID"):
            delete_media(mock_client, 0)

    def test_delete_invalid_id_negative(self, mock_client):
        with pytest.raises(ValueError, match="Invalid media ID"):
            delete_media(mock_client, -5)

    def test_delete_invalid_id_string(self, mock_client):
        with pytest.raises(ValueError, match="Invalid media ID"):
            delete_media(mock_client, "abc")


class TestMediaIdValidation:
    def test_bool_rejected(self):
        with pytest.raises(ValueError, match="Invalid media ID"):
            _validate_media_id(True)

    def test_false_rejected(self):
        with pytest.raises(ValueError, match="Invalid media ID"):
            _validate_media_id(False)
