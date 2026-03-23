"""Shared output formatter for WPA — table, JSON, CSV, TSV."""

import csv
import io
import json

VALID_FORMATS = {"table", "json", "csv", "tsv"}


def format_output(rows, columns, fmt="table"):
    """Format a list of dicts as table, JSON, CSV, or TSV.

    Args:
        rows: List of dicts (each dict is one record).
        columns: List of column names to include (order preserved).
        fmt: Output format — "table", "json", "csv", or "tsv".

    Returns:
        Formatted string.

    Raises:
        ValueError: If fmt is not a valid format.
    """
    if fmt not in VALID_FORMATS:
        raise ValueError(
            f"Invalid format '{fmt}'. Must be one of: {', '.join(sorted(VALID_FORMATS))}"
        )

    # Normalize rows: only include requested columns, replace None/missing with ""
    normalized = []
    for row in rows:
        normalized.append({col: _normalize_value(row.get(col)) for col in columns})

    if fmt == "json":
        return json.dumps(normalized, indent=2, ensure_ascii=False)

    if fmt == "csv":
        return _format_delimited(normalized, columns, ",")

    if fmt == "tsv":
        return _format_delimited(normalized, columns, "\t")

    # table (default)
    return _format_table(normalized, columns)


def _normalize_value(value):
    """Convert None to empty string, leave everything else as-is."""
    if value is None:
        return ""
    return value


def _format_table(rows, columns):
    """Format as aligned plain-text table."""
    # Calculate column widths
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            widths[col] = max(widths[col], len(str(row.get(col, ""))))

    # Build header
    header = "  ".join(str(col).ljust(widths[col]) for col in columns)
    lines = [header]

    # Build rows
    for row in rows:
        line = "  ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns)
        lines.append(line)

    return "\n".join(lines) + "\n"


def _format_delimited(rows, columns, delimiter):
    """Format as CSV or TSV using stdlib csv module."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([str(row.get(col, "")) for col in columns])
    return output.getvalue()


def format_ids(rows):
    """Format as space-separated list of id values.

    Args:
        rows: List of dicts, each expected to have an 'id' key.

    Returns:
        Space-separated string of id values.
    """
    return " ".join(str(row.get("id", "")) for row in rows)


def format_count(rows):
    """Format as a single integer count.

    Args:
        rows: List of dicts.

    Returns:
        String representation of the count.
    """
    return str(len(rows))


def format_field(rows, field_name):
    """Format a single field value per row, one per line.

    Args:
        rows: List of dicts.
        field_name: The field to extract from each row.

    Returns:
        Newline-separated string of field values.
    """
    return "\n".join(str(row.get(field_name, "")) for row in rows)
