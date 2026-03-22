"""Tests for wpa.formatter — shared output formatting."""

import csv
import io
import json

import pytest

from wpa.formatter import (
    format_count,
    format_field,
    format_ids,
    format_output,
    VALID_FORMATS,
)


# --- Sample data ---

SAMPLE_ROWS = [
    {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "display_name": "Admin User",
        "roles": "administrator",
    },
    {
        "id": 2,
        "username": "editor",
        "email": "editor@example.com",
        "display_name": "Editor User",
        "roles": "editor",
    },
    {
        "id": 3,
        "username": "jane",
        "email": "jane@example.com",
        "display_name": "Jane Doe",
        "roles": "author, editor",
    },
]

SAMPLE_COLUMNS = ["id", "username", "email", "display_name", "roles"]


class TestTableFormat:
    def test_table_has_header_and_rows(self):
        result = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "table")
        lines = result.strip().split("\n")
        assert len(lines) == 4  # header + 3 rows
        assert "id" in lines[0]
        assert "username" in lines[0]
        assert "admin" in lines[1]

    def test_table_columns_aligned(self):
        result = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "table")
        lines = result.strip().split("\n")
        # All lines should have the same column positions (padded)
        header_parts = lines[0].split()
        assert header_parts[0] == "id"
        assert header_parts[1] == "username"

    def test_table_is_default_format(self):
        result_default = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS)
        result_table = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "table")
        assert result_default == result_table


class TestJsonFormat:
    def test_json_is_valid_array(self):
        result = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "json")
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_json_contains_all_fields(self):
        result = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "json")
        data = json.loads(result)
        for row in data:
            for col in SAMPLE_COLUMNS:
                assert col in row

    def test_json_preserves_types(self):
        result = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "json")
        data = json.loads(result)
        assert data[0]["id"] == 1
        assert isinstance(data[0]["username"], str)


class TestCsvFormat:
    def test_csv_has_header_and_rows(self):
        result = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "csv")
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 4  # header + 3 data rows
        assert rows[0] == SAMPLE_COLUMNS

    def test_csv_handles_commas_in_values(self):
        result = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "csv")
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        # "author, editor" should be properly quoted
        jane_row = rows[3]
        assert jane_row[4] == "author, editor"

    def test_csv_rfc4180_compliant(self):
        result = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "csv")
        # Should use \r\n line endings per RFC 4180
        assert "\r\n" in result


class TestTsvFormat:
    def test_tsv_has_header_and_rows(self):
        result = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "tsv")
        lines = [line.rstrip("\r") for line in result.strip().split("\n")]
        assert len(lines) == 4
        assert lines[0] == "\t".join(SAMPLE_COLUMNS)

    def test_tsv_tab_separated(self):
        result = format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "tsv")
        lines = result.strip().split("\n")
        parts = lines[1].split("\t")
        assert parts[0] == "1"
        assert parts[1] == "admin"


class TestFieldFiltering:
    def test_subset_of_columns(self):
        subset = ["id", "email"]
        result = format_output(SAMPLE_ROWS, subset, "json")
        data = json.loads(result)
        for row in data:
            assert set(row.keys()) == {"id", "email"}

    def test_reordered_columns(self):
        reordered = ["email", "id"]
        result = format_output(SAMPLE_ROWS, reordered, "json")
        data = json.loads(result)
        # JSON doesn't guarantee order, but keys should be present
        assert set(data[0].keys()) == {"email", "id"}

    def test_single_column(self):
        result = format_output(SAMPLE_ROWS, ["username"], "table")
        lines = result.strip().split("\n")
        assert lines[0].strip() == "username"
        assert lines[1].strip() == "admin"


class TestEdgeCases:
    def test_empty_rows(self):
        result = format_output([], SAMPLE_COLUMNS, "table")
        lines = result.strip().split("\n")
        assert len(lines) == 1  # header only

    def test_empty_rows_json(self):
        result = format_output([], SAMPLE_COLUMNS, "json")
        data = json.loads(result)
        assert data == []

    def test_empty_rows_csv(self):
        result = format_output([], SAMPLE_COLUMNS, "csv")
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1  # header only

    def test_none_values_become_empty_string(self):
        rows = [{"id": 1, "username": "admin", "email": None}]
        result = format_output(rows, ["id", "username", "email"], "json")
        data = json.loads(result)
        assert data[0]["email"] == ""

    def test_missing_key_becomes_empty_string(self):
        rows = [{"id": 1, "username": "admin"}]
        result = format_output(rows, ["id", "username", "email"], "json")
        data = json.loads(result)
        assert data[0]["email"] == ""

    def test_unicode_values(self):
        rows = [{"id": 1, "username": "user", "display_name": "Rene Descartes"}]
        result = format_output(rows, ["id", "username", "display_name"], "table")
        assert "Rene Descartes" in result

    def test_invalid_format_raises_error(self):
        with pytest.raises(ValueError, match="Invalid format"):
            format_output(SAMPLE_ROWS, SAMPLE_COLUMNS, "yaml")

    def test_valid_formats_constant(self):
        assert VALID_FORMATS == {"table", "json", "csv", "tsv"}


class TestFormatIds:
    def test_basic(self):
        result = format_ids(SAMPLE_ROWS)
        assert result == "1 2 3"

    def test_empty_list(self):
        assert format_ids([]) == ""

    def test_single_row(self):
        assert format_ids([{"id": 42}]) == "42"

    def test_missing_id_key(self):
        rows = [{"name": "foo"}, {"id": 5}]
        assert format_ids(rows) == " 5"


class TestFormatCount:
    def test_basic(self):
        assert format_count(SAMPLE_ROWS) == "3"

    def test_empty_list(self):
        assert format_count([]) == "0"

    def test_single_row(self):
        assert format_count([{"id": 1}]) == "1"


class TestFormatField:
    def test_basic(self):
        result = format_field(SAMPLE_ROWS, "username")
        assert result == "admin\neditor\njane"

    def test_empty_list(self):
        assert format_field([], "username") == ""

    def test_missing_field(self):
        result = format_field(SAMPLE_ROWS, "nonexistent")
        assert result == "\n\n"

    def test_single_row(self):
        result = format_field([{"email": "a@b.com"}], "email")
        assert result == "a@b.com"

    def test_numeric_values(self):
        rows = [{"id": 1}, {"id": 2}]
        result = format_field(rows, "id")
        assert result == "1\n2"
