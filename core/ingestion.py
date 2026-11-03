"""
Data Ingestion Service for DataChat.
Supports high-throughput multi-format ingestion into in-process DuckDB:
- CSV, TSV (with automatic delimiter and type detection)
- Excel (.xlsx, .xls) with multi-sheet inspection and selection
- JSON (records or nested objects)
- Apache Parquet
Enforces file size constraints, safe column identifiers, and registers dataset metadata.
"""

import os
import uuid
import duckdb
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from core.duckdb_engine import (
    get_connection,
    register_table_metadata,
    get_table_metadata
)
from config.settings import settings

SUPPORTED_EXTENSIONS = [".csv", ".tsv", ".xlsx", ".xls", ".json", ".parquet"]


def inspect_excel_sheets(file_path: str) -> List[str]:
    """Inspects Excel workbook and returns the list of available sheet names."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    excel_file = pd.ExcelFile(file_path)
    return excel_file.sheet_names


def sanitize_table_identifier(name: str) -> str:
    """Creates a safe, clean table name identifier."""
    clean = "".join(c if c.isalnum() else "_" for c in name).strip("_")
    if not clean or clean[0].isdigit():
        clean = f"tbl_{clean}"
    return clean


def ingest_file(
    file_path: str,
    table_name: Optional[str] = None,
    sheet_name: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Ingests tabular file into in-memory DuckDB.
    
    Args:
        file_path: Path to the data file.
        table_name: Optional custom table name.
        sheet_name: Selected sheet for Excel files.
        
    Returns:
        (table_id: str, metadata: Dict[str, Any])
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size_bytes = os.path.getsize(file_path)
    if file_size_bytes == 0:
        raise ValueError("Uploaded file is empty (0 bytes).")

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise ValueError(
            f"File size ({file_size_bytes / (1024*1024):.2f} MB) exceeds maximum allowed limit of {settings.max_file_size_mb} MB."
        )

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    table_id = str(uuid.uuid4())
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    sanitized_base = sanitize_table_identifier(base_name)
    actual_table_name = table_name or f"tbl_{sanitized_base}_{table_id[:8]}"

    conn = get_connection()
    available_sheets: List[str] = []
    selected_sheet: Optional[str] = None

    try:
        if ext == ".csv":
            # DuckDB's read_csv_auto automatically detects delimiters, headers, quotes, types
            conn.execute(
                f"CREATE OR REPLACE TABLE \"{actual_table_name}\" AS SELECT * FROM read_csv_auto(?, header=True, sample_size=-1)",
                [file_path]
            )
        elif ext == ".tsv":
            conn.execute(
                f"CREATE OR REPLACE TABLE \"{actual_table_name}\" AS SELECT * FROM read_csv_auto(?, header=True, delim='\\t', sample_size=-1)",
                [file_path]
            )
        elif ext in [".xlsx", ".xls"]:
            available_sheets = inspect_excel_sheets(file_path)
            selected_sheet = sheet_name if sheet_name in available_sheets else available_sheets[0]
            df = pd.read_excel(file_path, sheet_name=selected_sheet)
            # Register dataframe into DuckDB
            conn.register("_temp_excel_df", df)
            conn.execute(f"CREATE OR REPLACE TABLE \"{actual_table_name}\" AS SELECT * FROM _temp_excel_df")
            conn.unregister("_temp_excel_df")
        elif ext == ".json":
            try:
                # Try DuckDB native read_json_auto first
                conn.execute(
                    f"CREATE OR REPLACE TABLE \"{actual_table_name}\" AS SELECT * FROM read_json_auto(?)",
                    [file_path]
                )
            except Exception:
                # Fallback to pandas json parser
                df = pd.read_json(file_path)
                conn.register("_temp_json_df", df)
                conn.execute(f"CREATE OR REPLACE TABLE \"{actual_table_name}\" AS SELECT * FROM _temp_json_df")
                conn.unregister("_temp_json_df")
        elif ext == ".parquet":
            conn.execute(
                f"CREATE OR REPLACE TABLE \"{actual_table_name}\" AS SELECT * FROM read_parquet(?)",
                [file_path]
            )
    except Exception as e:
        raise RuntimeError(f"Failed to ingest file '{os.path.basename(file_path)}' into DuckDB: {str(e)}")

    # Retrieve row count and columns
    row_count = conn.execute(f"SELECT COUNT(*) FROM \"{actual_table_name}\"").fetchone()[0]
    col_info = conn.execute(f"DESCRIBE \"{actual_table_name}\"").fetchall()
    columns = [str(col[0]) for col in col_info]
    column_types = {str(col[0]): str(col[1]) for col in col_info}

    metadata = {
        "table_id": table_id,
        "table_name": actual_table_name,
        "file_name": os.path.basename(file_path),
        "file_size_bytes": file_size_bytes,
        "extension": ext,
        "row_count": int(row_count),
        "column_count": len(columns),
        "columns": columns,
        "column_types": column_types,
        "available_sheets": available_sheets,
        "selected_sheet": selected_sheet,
    }

    register_table_metadata(table_id, metadata)
    return table_id, metadata


def ingest_dataframe(
    df: pd.DataFrame,
    source_name: str = "dataset",
    table_name: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """Ingests an in-memory pandas DataFrame directly into DuckDB."""
    if df.empty:
        raise ValueError("DataFrame contains no records.")

    table_id = str(uuid.uuid4())
    sanitized_base = sanitize_table_identifier(source_name)
    actual_table_name = table_name or f"tbl_{sanitized_base}_{table_id[:8]}"

    conn = get_connection()
    conn.register("_temp_ingest_df", df)
    conn.execute(f"CREATE OR REPLACE TABLE \"{actual_table_name}\" AS SELECT * FROM _temp_ingest_df")
    conn.unregister("_temp_ingest_df")

    row_count = len(df)
    columns = list(df.columns)
    col_info = conn.execute(f"DESCRIBE \"{actual_table_name}\"").fetchall()
    column_types = {str(col[0]): str(col[1]) for col in col_info}

    metadata = {
        "table_id": table_id,
        "table_name": actual_table_name,
        "file_name": f"{source_name}.csv",
        "file_size_bytes": int(df.memory_usage(deep=True).sum()),
        "extension": ".csv",
        "row_count": int(row_count),
        "column_count": len(columns),
        "columns": columns,
        "column_types": column_types,
        "available_sheets": [],
        "selected_sheet": None,
    }

    register_table_metadata(table_id, metadata)
    return table_id, metadata


def replace_table_with_df(table_id: str, new_df: pd.DataFrame) -> None:
    """Overwrites an existing DuckDB table with an updated DataFrame (used in cleaning)."""
    meta = get_table_metadata(table_id)
    if not meta:
        raise ValueError(f"Table '{table_id}' not found.")

    table_name = meta["table_name"]
    conn = get_connection()
    conn.register("_temp_replace_df", new_df)
    conn.execute(f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM _temp_replace_df")
    conn.unregister("_temp_replace_df")

    meta["row_count"] = len(new_df)
    col_info = conn.execute(f"DESCRIBE \"{table_name}\"").fetchall()
    meta["columns"] = [str(c[0]) for c in col_info]
    meta["column_types"] = {str(c[0]): str(c[1]) for c in col_info}
    register_table_metadata(table_id, meta)
