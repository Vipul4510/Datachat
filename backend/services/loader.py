"""
Database and table loader service using in-process DuckDB.
Supports CSV, TSV, Excel (.xlsx/.xls with sheet selector), JSON, and Parquet.
Enforces a 200 MB file limit.
"""

import os
import uuid
import duckdb
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB

# In-memory global duckdb connection for fast in-process query execution
_duckdb_conn: Optional[duckdb.DuckDBPyConnection] = None
# In-memory registry to store metadata about loaded tables
_tables_registry: Dict[str, Dict[str, Any]] = {}


def get_connection() -> duckdb.DuckDBPyConnection:
    """Returns the shared in-process DuckDB connection."""
    global _duckdb_conn
    if _duckdb_conn is None:
        _duckdb_conn = duckdb.connect(database=":memory:")
    return _duckdb_conn


def reset_connection() -> None:
    """Closes and resets the DuckDB connection (useful for clean testing)."""
    global _duckdb_conn, _tables_registry
    if _duckdb_conn is not None:
        try:
            _duckdb_conn.close()
        except Exception:
            pass
        _duckdb_conn = None
    _tables_registry.clear()


def get_excel_sheets(file_path: str) -> List[str]:
    """Inspects Excel workbook and returns list of sheet names."""
    excel_file = pd.ExcelFile(file_path)
    return excel_file.sheet_names


def load_file_into_duckdb(
    file_path: str,
    table_name: Optional[str] = None,
    sheet_name: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Loads a file into an in-memory DuckDB table.
    
    Args:
        file_path: Absolute or relative path to the file.
        table_name: Optional target table name. If None, generated automatically.
        sheet_name: Sheet name for Excel files. If None, first sheet is used.
        
    Returns:
        (table_id, metadata_dict)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        raise ValueError("Uploaded file is empty (0 bytes).")
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed limit of 200 MB."
        )

    ext = os.path.splitext(file_path)[1].lower()
    supported_extensions = [".csv", ".tsv", ".xlsx", ".xls", ".json", ".parquet"]
    if ext not in supported_extensions:
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats: {', '.join(supported_extensions)}"
        )

    # Generate unique table ID and sanitized table name
    table_id = str(uuid.uuid4())
    if not table_name:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        sanitized_name = "".join(c if c.isalnum() else "_" for c in base_name).strip("_")
        table_name = f"tbl_{sanitized_name}_{table_id[:8]}"

    conn = get_connection()
    available_sheets: List[str] = []
    selected_sheet: Optional[str] = None

    # Load based on extension using DuckDB direct queries or pandas fallback
    try:
        if ext == ".csv":
            # auto-detect headers, delimiters and types directly in DuckDB
            conn.execute(
                f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM read_csv_auto(?, header=True, sample_size=-1)",
                [file_path]
            )
        elif ext == ".tsv":
            conn.execute(
                f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM read_csv_auto(?, delim='\\t', header=True, sample_size=-1)",
                [file_path]
            )
        elif ext in [".xlsx", ".xls"]:
            available_sheets = get_excel_sheets(file_path)
            if not available_sheets:
                raise ValueError("Excel file contains no readable sheets.")
            selected_sheet = sheet_name if sheet_name in available_sheets else available_sheets[0]
            df = pd.read_excel(file_path, sheet_name=selected_sheet)
            # Register pandas DataFrame and create table
            conn.register("_temp_excel_df", df)
            conn.execute(f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM _temp_excel_df")
            conn.unregister("_temp_excel_df")
        elif ext == ".parquet":
            conn.execute(
                f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM read_parquet(?)",
                [file_path]
            )
        elif ext == ".json":
            # DuckDB read_json_auto handles records, line-delimited or structured arrays
            conn.execute(
                f"CREATE OR REPLACE TABLE \"{table_name}\" AS SELECT * FROM read_json_auto(?)",
                [file_path]
            )
    except Exception as e:
        # Graceful fallback or clear error explanation
        raise RuntimeError(f"Failed to load {ext} file into DuckDB: {str(e)}") from e

    # Extract schema details
    schema_info = get_table_schema(table_name)
    row_count = conn.execute(f"SELECT COUNT(*) FROM \"{table_name}\"").fetchone()[0]

    metadata = {
        "table_id": table_id,
        "table_name": table_name,
        "original_filename": os.path.basename(file_path),
        "file_size_bytes": file_size,
        "format": ext.replace(".", ""),
        "row_count": row_count,
        "column_count": len(schema_info),
        "schema": schema_info,
        "available_sheets": available_sheets,
        "selected_sheet": selected_sheet
    }

    _tables_registry[table_id] = metadata
    return table_id, metadata


def get_table_schema(table_name: str) -> List[Dict[str, Any]]:
    """
    Extracts column names, types, and up to 3 sample non-null values for each column.
    """
    conn = get_connection()
    # DESCRIBE returns column_name, column_type, null, key, default, extra
    describe_rows = conn.execute(f"DESCRIBE \"{table_name}\"").fetchall()
    
    schema = []
    for row in describe_rows:
        col_name = row[0]
        col_type = row[1]

        # Fetch up to 3 sample values
        try:
            samples_query = (
                f"SELECT DISTINCT \"{col_name}\" "
                f"FROM \"{table_name}\" "
                f"WHERE \"{col_name}\" IS NOT NULL "
                f"LIMIT 3"
            )
            sample_rows = conn.execute(samples_query).fetchall()
            samples = [r[0] for r in sample_rows]
        except Exception:
            samples = []

        schema.append({
            "column_name": col_name,
            "column_type": str(col_type),
            "sample_values": samples
        })

    return schema


def get_table_metadata(table_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves metadata for a registered table id."""
    return _tables_registry.get(table_id)


def execute_query(query: str, params: Optional[list] = None) -> Tuple[List[str], List[List[Any]]]:
    """
    Executes a SQL query on DuckDB and returns (column_names, rows).
    """
    conn = get_connection()
    res = conn.execute(query, params or []) if params else conn.execute(query)
    columns = [col[0] for col in res.description] if res.description else []
    rows = res.fetchall()
    return columns, rows
