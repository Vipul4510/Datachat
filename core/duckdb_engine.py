"""
DuckDB In-Process Engine Management.
Provides high-performance, in-memory analytical query execution,
schema extraction, connection lifecycle management, and query execution controls.
"""

import os
import time
import uuid
import duckdb
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

_connection: Optional[duckdb.DuckDBPyConnection] = None
_tables_metadata: Dict[str, Dict[str, Any]] = {}


def get_connection() -> duckdb.DuckDBPyConnection:
    """Returns the singleton DuckDB in-memory connection."""
    global _connection
    if _connection is None:
        _connection = duckdb.connect(database=":memory:")
        # Optimize DuckDB settings for analytical workloads
        _connection.execute("PRAGMA threads=4")
        _connection.execute("PRAGMA memory_limit='1GB'")
    return _connection


def reset_engine() -> None:
    """Resets the DuckDB connection and registered tables."""
    global _connection, _tables_metadata
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
        _connection = None
    _tables_metadata.clear()


def register_table_metadata(table_id: str, metadata: Dict[str, Any]) -> None:
    """Registers table metadata in memory."""
    _tables_metadata[table_id] = metadata


def get_table_metadata(table_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves metadata for a registered table."""
    return _tables_metadata.get(table_id)


def list_tables() -> List[Dict[str, Any]]:
    """Returns metadata for all registered tables."""
    return list(_tables_metadata.values())


def get_table_schema(table_id: str) -> List[Dict[str, Any]]:
    """
    Extracts rich schema information from a table:
    - Column name
    - Data type
    - Null count & null percentage
    - Distinct value count
    - Up to 3 representative non-null sample values
    """
    meta = get_table_metadata(table_id)
    if not meta:
        raise ValueError(f"Table '{table_id}' is not registered.")

    table_name = meta["table_name"]
    conn = get_connection()

    # Get column names and types from DuckDB
    col_info = conn.execute(f"DESCRIBE \"{table_name}\"").fetchall()
    total_rows = conn.execute(f"SELECT COUNT(*) FROM \"{table_name}\"").fetchone()[0]

    schema: List[Dict[str, Any]] = []

    for col in col_info:
        col_name = str(col[0])
        col_type = str(col[1])

        # Get null count and distinct count
        stats = conn.execute(
            f"SELECT COUNT(*) - COUNT(\"{col_name}\"), COUNT(DISTINCT \"{col_name}\") FROM \"{table_name}\""
        ).fetchone()
        null_count = stats[0] if stats else 0
        distinct_count = stats[1] if stats else 0
        null_pct = round((null_count / total_rows * 100), 2) if total_rows > 0 else 0.0

        # Sample 3 non-null values
        samples = conn.execute(
            f"SELECT DISTINCT \"{col_name}\" FROM \"{table_name}\" WHERE \"{col_name}\" IS NOT NULL LIMIT 3"
        ).fetchall()
        sample_values = [s[0] for s in samples]

        # Convert complex objects like timestamps to strings for JSON safety
        cleaned_samples = []
        for v in sample_values:
            if isinstance(v, (pd.Timestamp, pd.Timedelta)):
                cleaned_samples.append(str(v))
            else:
                cleaned_samples.append(v)

        schema.append({
            "column_name": col_name,
            "column_type": col_type,
            "null_count": int(null_count),
            "null_percentage": float(null_pct),
            "distinct_count": int(distinct_count),
            "sample_values": cleaned_samples,
        })

    return schema


def execute_analytical_query(sql_query: str, timeout_seconds: float = 15.0) -> Dict[str, Any]:
    """
    Executes a read-only SQL query on the DuckDB in-memory database.
    Measures execution latency and converts results to serializable rows and columns.
    
    Returns:
        {
            "success": bool,
            "columns": List[str],
            "rows": List[List[Any]],
            "row_count": int,
            "latency_ms": float,
            "error": Optional[str]
        }
    """
    conn = get_connection()
    start_time = time.perf_counter()

    try:
        # Execute query
        rel = conn.execute(sql_query)
        col_names = [desc[0] for desc in rel.description] if rel.description else []
        records = rel.fetchall()
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Convert records to JSON-serializable structures
        serialized_rows: List[List[Any]] = []
        for row in records:
            clean_row = []
            for val in row:
                if pd.isna(val):
                    clean_row.append(None)
                elif isinstance(val, (pd.Timestamp, pd.Timedelta)):
                    clean_row.append(str(val))
                elif isinstance(val, (int, float, str, bool)):
                    clean_row.append(val)
                else:
                    clean_row.append(str(val))
            serialized_rows.append(clean_row)

        return {
            "success": True,
            "columns": col_names,
            "rows": serialized_rows,
            "row_count": len(serialized_rows),
            "latency_ms": elapsed_ms,
            "error": None
        }

    except Exception as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "latency_ms": elapsed_ms,
            "error": str(e)
        }


def query_to_dataframe(sql_query: str) -> pd.DataFrame:
    """Executes query and returns a pandas DataFrame directly."""
    conn = get_connection()
    return conn.execute(sql_query).df()
