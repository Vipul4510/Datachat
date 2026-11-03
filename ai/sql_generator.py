"""
SQL Generation & Self-Correction Engine.
Transforms natural language questions into safe, validated DuckDB SQL
with schema injection, conversational context, and a bounded one-shot repair loop.
"""

import re
from typing import Dict, Any, List, Optional, Tuple

from config.settings import settings
from core.duckdb_engine import get_table_schema, execute_analytical_query
from core.sql_validation import validate_and_format_sql
from ai.provider_factory import resolve_provider, BaseAIProvider
from ai.fallback_provider import DeterministicFallbackProvider


def format_schema_for_llm(table_name: str, schema: List[Dict[str, Any]]) -> str:
    """Formats table schema into a compact, unambiguous representation."""
    lines = [f"Active Table: \"{table_name}\""]
    lines.append("Columns & Types:")
    for col in schema:
        samples = ", ".join([repr(s) for s in col.get("sample_values", [])])
        null_info = f"{col.get('null_percentage', 0)}% null"
        lines.append(f"  - \"{col['column_name']}\" ({col['column_type']}) | Nulls: {null_info} | Samples: [{samples}]")
    return "\n".join(lines)


def build_sql_prompt(
    table_name: str,
    schema: List[Dict[str, Any]],
    question: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    previous_attempt: Optional[str] = None,
    error_message: Optional[str] = None
) -> List[Dict[str, str]]:
    """Builds the system and user messages for NL-to-SQL translation."""
    system_prompt = (
        "You are an expert DuckDB SQL analytics engineer.\n"
        "Your task is to convert the user's natural language question into a single, valid, read-only DuckDB SQL query.\n\n"
        "RULES:\n"
        "1. Return ONLY the raw SQL query. Do NOT include markdown code blocks, explanation, or commentary.\n"
        "2. ONLY generate SELECT or WITH...SELECT queries. NEVER generate DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, ATTACH, DETACH, PRAGMA, or COPY.\n"
        "3. Always double-quote column identifiers (e.g. \"Revenue\", \"Order Date\") to handle spaces and reserved words safely.\n"
        "4. Use the provided table name exactly as given.\n"
        "5. For date operations, use standard DuckDB functions like strftime(), date_trunc(), or date_part().\n"
        "6. Do not add multiple statements or semicolons.\n"
        "7. For top-N or ranking questions, use ORDER BY ... DESC LIMIT N.\n"
    )

    schema_text = format_schema_for_llm(table_name, schema)

    history_text = ""
    if chat_history:
        recent = chat_history[-3:]  # Include up to 3 recent exchanges for follow-up context
        hist_lines = ["Conversation Context:"]
        for h in recent:
            if h.get("question"):
                hist_lines.append(f"User: {h['question']}")
            if h.get("sql"):
                hist_lines.append(f"Generated SQL: {h['sql']}")
        history_text = "\n".join(hist_lines) + "\n\n"

    user_text = f"{schema_text}\n\n{history_text}User Question: {question}\n\n"

    if previous_attempt and error_message:
        user_text += (
            f"CORRECTION ATTEMPT:\n"
            f"Your previous query failed: {previous_attempt}\n"
            f"Error message: {error_message}\n"
            f"Please analyze the error, adjust column names, types, or syntax, and provide a corrected, safe DuckDB SQL query.\n"
        )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]


def generate_and_execute_sql(
    table_id: str,
    table_name: str,
    question: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    preferred_provider: Optional[str] = None
) -> Dict[str, Any]:
    """
    Orchestrates the entire NL-to-SQL pipeline:
    1. Schema extraction & prompt construction
    2. Model query with provider resolution
    3. AST safety validation via SQLGlot
    4. DuckDB execution
    5. One-shot bounded self-correction on failure
    """
    schema = get_table_schema(table_id)
    provider, provider_status = resolve_provider(preferred_provider)

    # Fast path: Fallback mode
    if isinstance(provider, DeterministicFallbackProvider):
        raw_sql, reasoning = provider.synthesize_sql(question, table_name, schema)
        is_valid, val_err, safe_sql = validate_and_format_sql(raw_sql, allowed_tables=[table_name])
        if is_valid:
            exec_res = execute_analytical_query(safe_sql)
            return {
                "success": exec_res["success"],
                "sql": safe_sql,
                "provider_name": provider.name,
                "provider_model": provider.model,
                "columns": exec_res["columns"],
                "rows": exec_res["rows"],
                "row_count": exec_res["row_count"],
                "latency_ms": exec_res["latency_ms"],
                "retries": 0,
                "error": exec_res["error"],
                "reasoning": reasoning,
                "is_fallback": True
            }

    # Remote LLM path with one-shot correction loop (max 1 retry)
    max_retries = settings.max_retries
    last_sql = ""
    last_error = ""
    retries_used = 0

    for attempt in range(max_retries + 1):
        # Build prompt
        messages = build_sql_prompt(
            table_name=table_name,
            schema=schema,
            question=question,
            chat_history=chat_history,
            previous_attempt=last_sql if attempt > 0 else None,
            error_message=last_error if attempt > 0 else None
        )

        try:
            raw_sql = provider.complete(messages, temperature=0.1)
        except Exception as e:
            # Model call failed: gracefully fall back to deterministic mode
            fallback = DeterministicFallbackProvider()
            raw_sql, reasoning = fallback.synthesize_sql(question, table_name, schema)
            is_valid, _, safe_sql = validate_and_format_sql(raw_sql, allowed_tables=[table_name])
            exec_res = execute_analytical_query(safe_sql)
            return {
                "success": exec_res["success"],
                "sql": safe_sql,
                "provider_name": f"{provider.name} (Failed: {str(e)[:40]}...) -> Fallback",
                "provider_model": fallback.model,
                "columns": exec_res["columns"],
                "rows": exec_res["rows"],
                "row_count": exec_res["row_count"],
                "latency_ms": exec_res["latency_ms"],
                "retries": attempt,
                "error": None,
                "reasoning": f"Primary model call encountered error. Answered via offline deterministic fallback. ({reasoning})",
                "is_fallback": True
            }

        last_sql = raw_sql

        # Validate with SQLGlot AST
        is_valid, val_err, safe_sql = validate_and_format_sql(raw_sql, allowed_tables=[table_name])
        if not is_valid:
            last_error = f"SQL Safety Guard Violation: {val_err}"
            retries_used = attempt + 1
            continue

        # Execute on DuckDB
        exec_res = execute_analytical_query(safe_sql)
        if not exec_res["success"]:
            last_error = f"DuckDB Execution Error: {exec_res['error']}"
            retries_used = attempt + 1
            continue

        # Successful execution!
        return {
            "success": True,
            "sql": safe_sql,
            "provider_name": provider.name,
            "provider_model": provider.model,
            "columns": exec_res["columns"],
            "rows": exec_res["rows"],
            "row_count": exec_res["row_count"],
            "latency_ms": exec_res["latency_ms"],
            "retries": attempt,
            "error": None,
            "reasoning": "SQL successfully validated by SQLGlot and executed on DuckDB engine.",
            "is_fallback": False
        }

    # Exhausted retries: Return failure diagnostic with sanitized error
    return {
        "success": False,
        "sql": last_sql,
        "provider_name": provider.name,
        "provider_model": provider.model,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "latency_ms": 0.0,
        "retries": retries_used,
        "error": f"Failed after {retries_used} correction attempt(s): {last_error}",
        "reasoning": "Query could not be executed safely on DuckDB.",
        "is_fallback": False
    }
