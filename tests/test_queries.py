"""
Tests for DuckDB Engine and Analytical Query Execution.
"""

import os
import pytest
import pandas as pd
from core.duckdb_engine import (
    reset_engine,
    get_connection,
    execute_analytical_query,
    get_table_schema,
    query_to_dataframe
)
from core.ingestion import ingest_dataframe


@pytest.fixture(autouse=True)
def setup_test_table():
    reset_engine()
    df = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5],
        "category": ["Tech", "Tech", "Office", "Office", "Furniture"],
        "revenue": [100.0, 250.0, 75.0, 120.0, 500.0],
        "profit": [20.0, 60.0, 15.0, -10.0, 120.0]
    })
    table_id, meta = ingest_dataframe(df, source_name="orders", table_name="test_orders")
    yield table_id, meta
    reset_engine()


def test_execute_simple_select(setup_test_table):
    table_id, meta = setup_test_table
    res = execute_analytical_query("SELECT * FROM \"test_orders\"")
    assert res["success"] is True
    assert res["row_count"] == 5
    assert len(res["columns"]) == 4
    assert res["latency_ms"] >= 0


def test_execute_group_by_aggregation(setup_test_table):
    table_id, meta = setup_test_table
    res = execute_analytical_query("SELECT category, SUM(revenue) as total_rev FROM \"test_orders\" GROUP BY category")
    assert res["success"] is True
    assert res["row_count"] == 3
    assert "total_rev" in res["columns"]


def test_schema_extraction(setup_test_table):
    table_id, meta = setup_test_table
    schema = get_table_schema(table_id)
    assert len(schema) == 4
    col_names = [c["column_name"] for c in schema]
    assert "revenue" in col_names
    assert "category" in col_names

    # Check sample values
    rev_col = [c for c in schema if c["column_name"] == "revenue"][0]
    assert len(rev_col["sample_values"]) > 0
    assert rev_col["null_count"] == 0


def test_syntax_error_handling():
    res = execute_analytical_query("SELECT FROM WHERE INVALID")
    assert res["success"] is False
    assert res["error"] is not None
    assert res["row_count"] == 0
