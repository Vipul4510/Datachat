"""
LLM Service for DataChat.
Handles:
1. Natural language to DuckDB SQL conversion.
2. Primary provider: Groq API (model: llama-3.3-70b-versatile).
3. Fallback provider: Google Gemini API (model: gemini-1.5-flash / gemini-2.0-flash).
4. SQL guard integration.
5. Self-correction loop: retries up to 3 times on DuckDB or SQL Guard errors.
6. Plain-English conversational summary generation.
7. Starter suggested questions generation.
"""

import os
import re
import json
import httpx
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

from backend.services.sql_guard import validate_sql
from backend.services.loader import execute_query

# Load environment variables
load_dotenv()

MAX_RETRIES = 3

def get_env_config():
    # Reload from .env in backend directory or root
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)
    return {
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", "").strip(),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "").strip(),
        "GROQ_MODEL": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
    }


def format_schema_for_prompt(table_name: str, schema: List[Dict[str, Any]]) -> str:
    """Formats schema with column names, types, and sample values into a clean prompt string."""
    lines = [f"Table: \"{table_name}\""]
    lines.append("Columns:")
    for col in schema:
        samples = ", ".join([repr(s) for s in col.get("sample_values", [])])
        lines.append(f"  - \"{col['column_name']}\" ({col['column_type']}) | Sample values: [{samples}]")
    return "\n".join(lines)


def _call_groq(messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
    """Invokes the Groq API using HTTP client."""
    config = get_env_config()
    api_key = config["GROQ_API_KEY"]
    if not api_key or "your_groq" in api_key.lower():
        raise ValueError("GROQ_API_KEY is not configured in .env (currently placeholder or empty)")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": config["GROQ_MODEL"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1024
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def _call_gemini(messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
    """Invokes Google Gemini API as fallback."""
    config = get_env_config()
    api_key = config["GEMINI_API_KEY"]
    if not api_key or "your_gemini" in api_key.lower():
        raise ValueError("GEMINI_API_KEY is not configured in .env (currently placeholder or empty)")

    # Format OpenAI style messages to Gemini contents format
    gemini_contents = []
    system_instruction = None

    for msg in messages:
        if msg["role"] == "system":
            system_instruction = {"parts": [{"text": msg["content"]}]}
        elif msg["role"] == "user":
            gemini_contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            gemini_contents.append({"role": "model", "parts": [{"text": msg["content"]}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config['GEMINI_MODEL']}:generateContent?key={api_key}"
    payload: Dict[str, Any] = {
        "contents": gemini_contents,
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 1024}
    }
    if system_instruction:
        payload["systemInstruction"] = system_instruction

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            return candidates[0]["content"]["parts"][0]["text"]
        raise RuntimeError("Gemini returned empty candidate response")


def call_llm(messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
    """Calls Groq API with fallback to Gemini API."""
    errors = []
    # Primary: Groq
    try:
        return _call_groq(messages, temperature=temperature)
    except Exception as e:
        errors.append(f"Groq failed: {str(e)}")

    # Fallback: Gemini
    try:
        return _call_gemini(messages, temperature=temperature)
    except Exception as e:
        errors.append(f"Gemini failed: {str(e)}")

    raise RuntimeError(f"All LLM providers failed: {'; '.join(errors)}")


def generate_sql(
    table_name: str,
    schema: List[Dict[str, Any]],
    question: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    previous_attempt: Optional[str] = None,
    error_message: Optional[str] = None
) -> str:
    """Generates pure DuckDB SQL statement for the user's question."""
    schema_prompt = format_schema_for_prompt(table_name, schema)

    system_prompt = (
        "You are an expert DuckDB SQL data analyst. Your job is to convert natural language questions into valid DuckDB SQL.\n"
        "STRICT RULES:\n"
        "1. Return ONLY the SQL query. Do not wrap in markdown quotes if possible, or use standard ```sql code block.\n"
        "2. Do NOT provide any conversational explanations or commentary before or after the SQL.\n"
        "3. Only use SELECT queries. Never use DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, ATTACH, or multi-statement scripts.\n"
        "4. Always quote column and table names with double quotes to prevent syntax issues with spaces or special characters.\n"
        "5. Table to query from is: \"" + table_name + "\".\n"
        "6. Use DuckDB functions (e.g. strftime, date_trunc, round, coalesce, ilike) where appropriate."
    )

    history_str = ""
    if chat_history:
        history_items = []
        for h in chat_history[-6:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            history_items.append(f"{role.capitalize()}: {content}")
        history_str = "Recent Conversation Context:\n" + "\n".join(history_items) + "\n\n"

    user_prompt = f"Schema Information:\n{schema_prompt}\n\n{history_str}User Question: {question}\n"

    if previous_attempt and error_message:
        user_prompt += (
            f"\n\nCRITICAL FIX NEEDED:\n"
            f"Your previous query was:\n{previous_attempt}\n"
            f"It failed with this error:\n{error_message}\n"
            f"Please carefully fix the query to resolve this error. Return ONLY the corrected SQL query."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    raw_response = call_llm(messages, temperature=0.0)
    # Extract SQL from code blocks if LLM enclosed it
    clean = raw_response.strip()
    sql_match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", clean, re.IGNORECASE)
    if sql_match:
        clean = sql_match.group(1).strip()
    return clean


def generate_answer_summary(
    question: str,
    sql: str,
    columns: List[str],
    rows: List[List[Any]]
) -> str:
    """Generates a concise, plain-English summary of the query results."""
    # Truncate row sample if result set is large to avoid context overload
    sample_rows = rows[:10]
    result_context = {
        "columns": columns,
        "sample_rows": sample_rows,
        "total_row_count": len(rows)
    }

    prompt = (
        f"You are a friendly data analytics assistant. A user asked a question about their dataset, "
        f"and the query executed successfully.\n\n"
        f"User Question: {question}\n"
        f"Executed SQL: {sql}\n"
        f"Results Summary: {json.dumps(result_context, default=str)}\n\n"
        f"Provide a clear, conversational, and direct answer summarizing the key insights in 2 to 4 sentences. "
        f"Mention concrete numbers or trends from the result. Do not mention SQL code or internal technical jargon."
    )

    messages = [
        {"role": "system", "content": "You provide clear, friendly business insights on data analysis results."},
        {"role": "user", "content": prompt}
    ]

    try:
        return call_llm(messages, temperature=0.3)
    except Exception:
        # Fallback summary if LLM call fails
        if not rows:
            return "The query returned no matching records."
        return f"Found {len(rows)} record(s) matching your question."


def generate_suggested_questions(table_name: str, schema: List[Dict[str, Any]]) -> List[str]:
    """Generates 4 relevant starter questions as clickable chips."""
    schema_prompt = format_schema_for_prompt(table_name, schema)

    prompt = (
        f"Based on the following dataset schema:\n{schema_prompt}\n\n"
        f"Propose exactly 4 insightful, interesting, and diverse analytical questions that a business or data user "
        f"would want to ask. Keep them concise (under 12 words each).\n"
        f"Return ONLY a JSON list of 4 strings, for example: [\"Question 1\", \"Question 2\", \"Question 3\", \"Question 4\"]."
    )

    messages = [
        {"role": "system", "content": "You are a data analyst who proposes high-value questions for business datasets. Return ONLY a JSON list of 4 strings."},
        {"role": "user", "content": prompt}
    ]

    try:
        res = call_llm(messages, temperature=0.4)
        json_match = re.search(r"\[\s*[\s\S]*?\s*\]", res)
        if json_match:
            questions = json.loads(json_match.group(0))
            if isinstance(questions, list) and len(questions) >= 4:
                return [str(q).strip() for q in questions[:4]]
    except Exception:
        pass

    # Generic high-quality fallbacks based on column names
    col_names = [c["column_name"] for c in schema]
    return [
        f"What is the total count of records in this dataset?",
        f"Show a summary breakdown by {col_names[0] if col_names else 'category'}",
        f"What are the top 5 highest values?",
        f"Are there any notable patterns or distributions?"
    ]


def run_nl_query_with_self_correction(
    table_id: str,
    question: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    table_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes natural language question:
    1. Generates SQL
    2. Validates SQL Guard
    3. Executes on DuckDB
    4. If error (SQL Guard or DuckDB), retries with error feedback up to 3 times
    5. Returns columns, rows, execution stats, and summary
    """
    if not table_metadata:
        from backend.services.loader import get_table_metadata
        table_metadata = get_table_metadata(table_id)
        if not table_metadata:
            raise ValueError(f"Table '{table_id}' not found.")

    table_name = table_metadata["table_name"]
    schema = table_metadata["schema"]

    last_sql = ""
    last_error = ""
    retries = 0

    for attempt in range(MAX_RETRIES + 1):
        try:
            # Step 1: Generate SQL (with previous error if retrying)
            sql = generate_sql(
                table_name=table_name,
                schema=schema,
                question=question,
                chat_history=chat_history,
                previous_attempt=last_sql if attempt > 0 else None,
                error_message=last_error if attempt > 0 else None
            )
            last_sql = sql

            # Step 2: Validate SQL Safety Guard
            is_valid, guard_error, sanitized_sql = validate_sql(sql)
            if not is_valid:
                last_error = f"SQL Safety Guard violation: {guard_error}"
                retries += 1
                continue

            last_sql = sanitized_sql

            # Step 3: Execute on DuckDB
            columns, rows = execute_query(sanitized_sql)

            # Success! Step 4: Generate summary
            summary = generate_answer_summary(
                question=question,
                sql=sanitized_sql,
                columns=columns,
                rows=rows
            )

            return {
                "success": True,
                "sql": sanitized_sql,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "summary": summary,
                "retries": retries,
                "attempts": attempt + 1
            }

        except Exception as e:
            last_error = f"DuckDB Execution Error: {str(e)}"
            retries += 1

    # If all attempts failed
    return {
        "success": False,
        "sql": last_sql,
        "error": f"Failed to execute query after {MAX_RETRIES} attempts. Last error: {last_error}",
        "retries": retries,
        "columns": [],
        "rows": [],
        "row_count": 0,
        "summary": "I was unable to successfully generate a working query for your question. Please try rephrasing or specifying the column names."
    }
