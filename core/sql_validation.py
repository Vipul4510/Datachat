"""
SQL Validation & Safety Guard using SQLGlot AST parser.
Enforces read-only analytical query safety, prevents SQL injection and multi-statement attacks,
validates table references, and applies strict LIMIT enforcement via AST transformation.
"""

import re
from typing import Tuple, Optional, List, Set
import sqlglot
from sqlglot import exp

FORBIDDEN_EXPRESSION_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.Pragma,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
    exp.Set,
    exp.Kill,
)

FORBIDDEN_RAW_KEYWORDS = [
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
    r"\bINSTALL\b",
]


def clean_markdown_and_whitespace(raw_sql: str) -> str:
    """Strips markdown fences, comments, and trailing semicolons."""
    if not raw_sql:
        return ""
    text = raw_sql.strip()

    # Strip markdown code blocks
    if "```" in text:
        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        else:
            # Strip lines starting with ```
            lines = [l for l in text.splitlines() if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

    # Remove single line comments
    lines = []
    for line in text.splitlines():
        clean_line = re.sub(r"--.*$", "", line)
        lines.append(clean_line)
    text = "\n".join(lines).strip()

    # Remove trailing semicolons
    text = re.sub(r";+\s*$", "", text).strip()
    return text


def validate_and_format_sql(
    sql_query: str,
    allowed_tables: Optional[List[str]] = None,
    max_rows: int = 500
) -> Tuple[bool, Optional[str], str]:
    """
    Validates that a SQL query is strictly a safe read-only SELECT or WITH...SELECT statement.
    Uses SQLGlot AST analysis to reject DDL/DML, multi-statement injection, and disallowed constructs.
    
    Args:
        sql_query: The candidate SQL string.
        allowed_tables: Optional list of table names allowed in FROM / JOIN clauses.
        max_rows: Maximum rows allowed (appends or bounds LIMIT).
        
    Returns:
        (is_valid: bool, error_message: Optional[str], safe_sql: str)
    """
    cleaned = clean_markdown_and_whitespace(sql_query)
    if not cleaned:
        return False, "Query is empty.", ""

    # Check for multiple statements (semicolon chaining)
    sql_without_strings = re.sub(r"\'[^\']*\'|\"[^\"]*\"", "", cleaned)
    if ";" in sql_without_strings:
        return False, "Multiple SQL statements are not permitted (semicolon chaining blocked).", cleaned

    # Check for raw forbidden keywords as a fast first-line defense
    for pattern in FORBIDDEN_RAW_KEYWORDS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            matched = re.findall(pattern, cleaned, re.IGNORECASE)[0]
            return False, f"Disallowed SQL operation detected: '{matched.upper()}'. Only read-only queries are permitted.", cleaned

    # Parse with SQLGlot
    try:
        parsed_expressions = sqlglot.parse(cleaned, read="duckdb")
    except Exception as e:
        return False, f"SQL syntax parsing error: {str(e)}", cleaned

    if not parsed_expressions:
        return False, "No valid SQL statements found.", cleaned

    if len(parsed_expressions) > 1:
        return False, "Multiple SQL statements are not permitted (semicolon chaining blocked).", cleaned

    root_expr = parsed_expressions[0]
    if root_expr is None:
        return False, "Failed to parse SQL expression tree.", cleaned

    # Check that root expression is a SELECT or CTE with SELECT
    if not isinstance(root_expr, (exp.Select, exp.Union)):
        return False, f"Query must be an analytical SELECT statement, got '{type(root_expr).__name__}'.", cleaned

    # AST Walk: verify no forbidden DDL/DML nodes anywhere in the tree
    for node in root_expr.walk():
        if isinstance(node, FORBIDDEN_EXPRESSION_TYPES):
            return False, f"Disallowed SQL AST operation: '{type(node).__name__}'.", cleaned

    # Collect CTE names defined in query to allow them as valid table references
    cte_names: Set[str] = set()
    with_clause = root_expr.args.get("with")
    if with_clause:
        for cte in with_clause.expressions:
            if isinstance(cte, exp.CTE) and cte.alias:
                cte_names.add(cte.alias.lower())

    # Validate referenced tables if allowed_tables list is specified
    if allowed_tables:
        allowed_set = {t.lower() for t in allowed_tables}
        for table_node in root_expr.find_all(exp.Table):
            tbl_name = table_node.name.lower()
            if tbl_name and tbl_name not in allowed_set and tbl_name not in cte_names:
                return False, f"Unauthorized table access: Table '{tbl_name}' is not part of the active dataset.", cleaned

    # Enforce row limit via AST transformation
    try:
        enforced_expr = enforce_limit_ast(root_expr, max_rows=max_rows)
        safe_sql = enforced_expr.sql(dialect="duckdb")
        return True, None, safe_sql
    except Exception:
        # Fallback to string limit enforcement if AST rewrite encounters dialect nuance
        fallback_sql = enforce_limit_fallback(cleaned, max_rows=max_rows)
        return True, None, fallback_sql


def enforce_limit_ast(expression: exp.Expression, max_rows: int = 500) -> exp.Expression:
    """Enforces or bounds the LIMIT clause using AST manipulation."""
    copy_expr = expression.copy()
    limit_clause = copy_expr.args.get("limit")

    if limit_clause is None:
        # No LIMIT clause present: add LIMIT max_rows
        copy_expr = copy_expr.limit(max_rows)
    else:
        # Check existing limit value
        try:
            current_limit = int(limit_clause.expression.this)
            if current_limit > max_rows or current_limit <= 0:
                limit_clause.expression = exp.Literal.number(max_rows)
        except Exception:
            limit_clause.expression = exp.Literal.number(max_rows)

    return copy_expr


def enforce_limit_fallback(sql: str, max_rows: int = 500) -> str:
    """Regex fallback to append or clamp LIMIT."""
    limit_match = re.search(r"\bLIMIT\s+(\d+)", sql, re.IGNORECASE)
    if limit_match:
        current_limit = int(limit_match.group(1))
        if current_limit > max_rows:
            return re.sub(r"\bLIMIT\s+\d+", f"LIMIT {max_rows}", sql, flags=re.IGNORECASE)
        return sql
    return f"{sql} LIMIT {max_rows}"
