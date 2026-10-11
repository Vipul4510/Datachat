"""Unit tests for Phase 3 - SQL Guard and Prompt/Self-Correction Logic."""

import pytest
from backend.services.sql_guard import validate_sql, enforce_row_limit, sanitize_sql

def test_safe_select_queries():
    is_valid, err, sql = validate_sql("SELECT * FROM \"tbl_sales\" WHERE units_sold > 10")
    assert is_valid is True
    assert err is None
    assert "LIMIT" in sql

def test_with_select_cte():
    query = """
    WITH regional_summary AS (
        SELECT region, SUM(revenue) as total_rev FROM "sales" GROUP BY region
    )
    SELECT * FROM regional_summary ORDER BY total_rev DESC
    """
    is_valid, err, sql = validate_sql(query)
    assert is_valid is True
    assert err is None

def test_reject_mutations():
    disallowed = [
        "DROP TABLE sales",
        "DELETE FROM sales WHERE id = 1",
        "UPDATE sales SET revenue = 0",
        "INSERT INTO sales VALUES (1, 2)",
        "ALTER TABLE sales ADD COLUMN test INT",
        "CREATE TABLE test (id INT)",
        "ATTACH 'other.db'",
        "COPY sales TO 'output.csv'",
        "TRUNCATE TABLE sales"
    ]
    for q in disallowed:
        is_valid, err, _ = validate_sql(q)
        assert is_valid is False
        assert err is not None

def test_reject_multiple_statements():
    multi = "SELECT * FROM sales; DROP TABLE sales;"
    is_valid, err, _ = validate_sql(multi)
    assert is_valid is False
    assert "Multiple SQL statements" in err

def test_row_limit_enforcement():
    sql = "SELECT id FROM test"
    enforced = enforce_row_limit(sql, max_rows=500)
    assert "LIMIT 500" in enforced

    # When query already has a smaller limit
    sql_small = "SELECT id FROM test LIMIT 10"
    enforced_small = enforce_row_limit(sql_small, max_rows=500)
    assert "LIMIT 10" in enforced_small

    # When query exceeds limit
    sql_big = "SELECT id FROM test LIMIT 10000"
    enforced_clamped = enforce_row_limit(sql_big, max_rows=500)
    assert "LIMIT 500" in enforced_clamped

def test_markdown_and_whitespace_sanitization():
    raw = "```sql\nSELECT name, score FROM students;\n```"
    clean = sanitize_sql(raw)
    assert clean == "SELECT name, score FROM students"
