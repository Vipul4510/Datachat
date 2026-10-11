"""Unit tests for Phase 1 - Loader Service & DuckDB Querying."""

import os
import pytest
from backend.services.loader import (
    load_file_into_duckdb,
    execute_query,
    get_table_metadata,
    reset_connection,
    get_excel_sheets,
    MAX_FILE_SIZE_BYTES
)

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sample_data")

@pytest.fixture(autouse=True)
def setup_teardown():
    reset_connection()
    yield
    reset_connection()


def test_load_csv_and_hardcoded_query():
    csv_path = os.path.join(SAMPLE_DIR, "sales_data.csv")
    table_id, meta = load_file_into_duckdb(csv_path)

    assert table_id is not None
    assert meta["row_count"] == 101
    assert meta["format"] == "csv"
    assert len(meta["schema"]) == 8

    # Hardcoded DuckDB SQL query test
    table_name = meta["table_name"]
    cols, rows = execute_query(
        f"SELECT category, COUNT(*) as count, ROUND(AVG(revenue), 2) as avg_rev "
        f"FROM \"{table_name}\" GROUP BY category ORDER BY count DESC"
    )
    assert cols == ["category", "count", "avg_rev"]
    assert len(rows) > 0


def test_load_excel_with_sheets():
    xlsx_path = os.path.join(SAMPLE_DIR, "student_marks.xlsx")
    sheets = get_excel_sheets(xlsx_path)
    assert "Students" in sheets
    assert "ExamScores" in sheets

    # Load specific sheet
    table_id, meta = load_file_into_duckdb(xlsx_path, sheet_name="ExamScores")
    assert meta["selected_sheet"] == "ExamScores"
    assert meta["row_count"] == 32  # 8 students * 4 subjects

    # Hardcoded SQL query
    cols, rows = execute_query(
        f"SELECT subject, ROUND(AVG(score), 1) as avg_score "
        f"FROM \"{meta['table_name']}\" GROUP BY subject ORDER BY avg_score DESC"
    )
    assert "avg_score" in cols
    assert len(rows) == 4


def test_load_json():
    json_path = os.path.join(SAMPLE_DIR, "expenses.json")
    table_id, meta = load_file_into_duckdb(json_path)

    assert meta["row_count"] == 20
    assert meta["format"] == "json"

    cols, rows = execute_query(
        f"SELECT department, SUM(budget) as total_budget "
        f"FROM \"{meta['table_name']}\" GROUP BY department"
    )
    assert len(rows) == 5


def test_load_parquet():
    parquet_path = os.path.join(SAMPLE_DIR, "sales_data.parquet")
    table_id, meta = load_file_into_duckdb(parquet_path)
    assert meta["format"] == "parquet"
    assert meta["row_count"] >= 98


def test_load_tsv():
    tsv_path = os.path.join(SAMPLE_DIR, "expenses.tsv")
    table_id, meta = load_file_into_duckdb(tsv_path)
    assert meta["format"] == "tsv"
    assert meta["row_count"] == 20


def test_empty_file_error(tmp_path):
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("")
    with pytest.raises(ValueError, match="empty"):
        load_file_into_duckdb(str(empty_file))


def test_unsupported_file_format(tmp_path):
    bad_file = tmp_path / "test.doc"
    bad_file.write_text("Hello doc")
    with pytest.raises(ValueError, match="Unsupported file format"):
        load_file_into_duckdb(str(bad_file))


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_file_into_duckdb("non_existent_file.csv")
