"""
Tests for Data Ingestion Service.
"""

import os
import pytest
import pandas as pd
from core.duckdb_engine import reset_engine, get_table_metadata
from core.ingestion import ingest_file, ingest_dataframe, inspect_excel_sheets


@pytest.fixture(autouse=True)
def clean_engine():
    reset_engine()
    yield
    reset_engine()


def test_ingest_csv_sample():
    sample_path = "sample_data/sales_data.csv"
    assert os.path.exists(sample_path)
    table_id, meta = ingest_file(sample_path)
    assert table_id is not None
    assert meta["row_count"] > 0
    assert meta["column_count"] > 0
    assert "revenue" in [c.lower() for c in meta["columns"]]


def test_ingest_json_sample():
    sample_path = "sample_data/expenses.json"
    assert os.path.exists(sample_path)
    table_id, meta = ingest_file(sample_path)
    assert table_id is not None
    assert meta["row_count"] > 0
    assert "department" in [c.lower() for c in meta["columns"]]


def test_ingest_excel_sample():
    sample_path = "sample_data/student_marks.xlsx"
    assert os.path.exists(sample_path)
    sheets = inspect_excel_sheets(sample_path)
    assert len(sheets) >= 1
    table_id, meta = ingest_file(sample_path, sheet_name=sheets[0])
    assert table_id is not None
    assert meta["row_count"] > 0


def test_ingest_parquet_sample():
    sample_path = "sample_data/sales_data.parquet"
    if os.path.exists(sample_path):
        table_id, meta = ingest_file(sample_path)
        assert table_id is not None
        assert meta["row_count"] > 0


def test_ingest_dataframe_direct():
    df = pd.DataFrame({
        "product_id": [101, 102, 103],
        "product_name": ["Alpha", "Beta", "Gamma"],
        "unit_price": [19.99, 29.50, 49.00]
    })
    table_id, meta = ingest_dataframe(df, source_name="test_products")
    assert meta["row_count"] == 3
    assert meta["column_count"] == 3


def test_reject_empty_file(tmp_path):
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("")
    with pytest.raises(ValueError, match="0 bytes"):
        ingest_file(str(empty_file))


def test_reject_unsupported_format(tmp_path):
    bad_file = tmp_path / "test.exe"
    bad_file.write_text("dummy binary")
    with pytest.raises(ValueError, match="Unsupported file format"):
        ingest_file(str(bad_file))
