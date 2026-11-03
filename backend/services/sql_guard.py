"""
SQL Safety Guard Service for DataChat.
Uses SQLGlot AST analysis to enforce strict read-only analytical rules:
1. Allow SELECT statements only (or WITH ... SELECT).
2. Reject DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, ATTACH, COPY, PRAGMA, EXECUTE, TRUNCATE, REPLACE, MERGE.
3. Reject multiple statements (semicolon chained statements).
4. Enforces row limits (appends or bounds LIMIT) and query execution timeouts.
"""

import re
from typing import Tuple, Optional
from core.sql_validation import (
    validate_and_format_sql,
    clean_markdown_and_whitespace,
    enforce_limit_fallback
)

MAX_ROW_LIMIT = 500
QUERY_TIMEOUT_SECONDS = 15.0


def sanitize_sql(sql_query: str) -> str:
    """Cleans markdown formatting, quotes, and trailing semicolons."""
    return clean_markdown_and_whitespace(sql_query)


def enforce_row_limit(sql: str, max_rows: int = 500) -> str:
    """Enforces or bounds row limits."""
    return enforce_limit_fallback(sql, max_rows=max_rows)


def validate_sql(sql_query: str, allowed_tables: Optional[list] = None) -> Tuple[bool, Optional[str], str]:
    """
    Validates that the SQL query is strictly a safe read-only SELECT statement.
    Uses AST analysis via SQLGlot.
    
    Returns:
        (is_valid, error_message_if_any, sanitized_sql)
    """
    return validate_and_format_sql(sql_query, allowed_tables=allowed_tables, max_rows=MAX_ROW_LIMIT)
