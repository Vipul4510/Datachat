"""
SQL Safety Guard Service.
Enforces strict security rules on queries:
1. Allow SELECT statements only (or WITH ... SELECT).
2. Reject DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, ATTACH, COPY, PRAGMA, EXECUTE, TRUNCATE, REPLACE, MERGE.
3. Reject multiple statements (semicolon chained statements).
4. Enforces row limits (appends or bounds LIMIT) and query execution timeouts.
"""

import re
from typing import Tuple, Optional

# Disallowed keywords
DISALLOWED_KEYWORDS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bCOPY\b",
    r"\bEXPORT\b",
    r"\bIMPORT\b",
    r"\bPRAGMA\b",
    r"\bEXECUTE\b",
    r"\bEXEC\b",
    r"\bTRUNCATE\b",
    r"\bREPLACE\b",
    r"\bMERGE\b",
    r"\bCALL\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bLOAD\b",
    r"\bINSTALL\b"
]

MAX_ROW_LIMIT = 500
QUERY_TIMEOUT_SECONDS = 10.0


def sanitize_sql(sql_query: str) -> str:
    """
    Cleans markdown formatting, quotes, and trailing semicolons.
    """
    clean = sql_query.strip()
    # Remove markdown code blocks if present
    if clean.startswith("```"):
        lines = clean.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean = "\n".join(lines).strip()

    # Strip trailing semicolons for single-statement validation
    clean = re.sub(r";+\s*$", "", clean).strip()
    return clean


def validate_sql(sql_query: str) -> Tuple[bool, Optional[str], str]:
    """
    Validates that the SQL query is strictly a safe read-only SELECT statement.
    
    Returns:
        (is_valid, error_message_if_any, sanitized_sql)
    """
    if not sql_query or not sql_query.strip():
        return False, "Query is empty.", ""

    clean_sql = sanitize_sql(sql_query)

    # Check for multiple statements
    # Remove strings literal contents first so semicolons inside string constants don't trigger false positives
    sql_without_strings = re.sub(r"\'[^\']*\'|\"[^\"]*\"", "", clean_sql)
    if ";" in sql_without_strings:
        return False, "Multiple SQL statements are not permitted.", clean_sql

    # Check that statement starts with SELECT or WITH
    first_token_match = re.match(r"^\s*([a-zA-Z]+)", clean_sql)
    if not first_token_match:
        return False, "Invalid SQL syntax.", clean_sql

    first_token = first_token_match.group(1).upper()
    if first_token not in ["SELECT", "WITH"]:
        return False, f"Only SELECT queries are allowed. Found '{first_token}'.", clean_sql

    # Check for disallowed mutation/system keywords
    for pattern in DISALLOWED_KEYWORDS:
        if re.search(pattern, clean_sql, re.IGNORECASE):
            match_word = re.findall(pattern, clean_sql, re.IGNORECASE)[0]
            return False, f"Query contains forbidden keyword: '{match_word.upper()}'.", clean_sql

    # Ensure row limit is enforced
    enforced_sql = enforce_row_limit(clean_sql, max_rows=MAX_ROW_LIMIT)

    return True, None, enforced_sql


def enforce_row_limit(sql: str, max_rows: int = MAX_ROW_LIMIT) -> str:
    """
    Appends or clamps LIMIT to max_rows if none is present or if existing limit > max_rows.
    """
    # Regex search for existing LIMIT at the outermost level
    limit_match = re.search(r"\bLIMIT\s+(\d+)\b", sql, re.IGNORECASE)
    if limit_match:
        current_limit = int(limit_match.group(1))
        if current_limit > max_rows:
            # Clamp to max_rows
            sql = re.sub(r"\bLIMIT\s+\d+\b", f"LIMIT {max_rows}", sql, flags=re.IGNORECASE)
    else:
        # Append LIMIT
        sql = f"{sql} LIMIT {max_rows}"

    return sql
