"""
Tests for SQLGlot-based SQL Validation & Safety Guard.
"""

import pytest
from core.sql_validation import (
    validate_and_format_sql,
    clean_markdown_and_whitespace
)


def test_clean_markdown_fences():
    sql_with_md = "```sql\nSELECT * FROM tbl;\n```"
    cleaned = clean_markdown_and_whitespace(sql_with_md)
    assert cleaned == "SELECT * FROM tbl"


def test_valid_select_query():
    sql = "SELECT id, revenue FROM sales WHERE profit > 100"
    is_valid, err, safe_sql = validate_and_format_sql(sql)
    assert is_valid is True
    assert err is None
    assert "LIMIT 500" in safe_sql


def test_valid_cte_query():
    sql = "WITH regional AS (SELECT region, SUM(revenue) as rev FROM sales GROUP BY region) SELECT * FROM regional"
    is_valid, err, safe_sql = validate_and_format_sql(sql)
    assert is_valid is True
    assert err is None
    assert "LIMIT 500" in safe_sql


def test_block_drop_table():
    sql = "DROP TABLE sales"
    is_valid, err, _ = validate_and_format_sql(sql)
    assert is_valid is False
    assert "Disallowed SQL operation" in err or "SELECT statement" in err


def test_block_delete_from():
    sql = "DELETE FROM sales WHERE id = 1"
    is_valid, err, _ = validate_and_format_sql(sql)
    assert is_valid is False


def test_block_insert_into():
    sql = "INSERT INTO sales VALUES (1, 2, 3)"
    is_valid, err, _ = validate_and_format_sql(sql)
    assert is_valid is False


def test_block_attach_database():
    sql = "ATTACH 'other.duckdb' AS other"
    is_valid, err, _ = validate_and_format_sql(sql)
    assert is_valid is False


def test_block_multiple_statements_semicolon():
    sql = "SELECT * FROM sales; DROP TABLE sales;"
    is_valid, err, _ = validate_and_format_sql(sql)
    assert is_valid is False
    assert "Multiple SQL statements" in err or "Disallowed" in err


def test_clamp_excessive_limit():
    sql = "SELECT * FROM sales LIMIT 5000"
    is_valid, err, safe_sql = validate_and_format_sql(sql, max_rows=500)
    assert is_valid is True
    assert "LIMIT 500" in safe_sql
    assert "5000" not in safe_sql


def test_disallow_unauthorized_table():
    sql = "SELECT * FROM secret_passwords"
    is_valid, err, _ = validate_and_format_sql(sql, allowed_tables=["sales_table"])
    assert is_valid is False
    assert "Unauthorized table access" in err
