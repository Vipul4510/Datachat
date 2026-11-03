from core.duckdb_engine import (
    get_connection,
    reset_engine,
    get_table_metadata,
    list_tables,
    get_table_schema,
    execute_analytical_query,
    query_to_dataframe
)
from core.sql_validation import validate_and_format_sql
from core.ingestion import ingest_file, ingest_dataframe, inspect_excel_sheets, replace_table_with_df
from core.profiling import profile_dataset
from core.data_quality import (
    evaluate_data_health,
    preview_cleaning_operation,
    apply_cleaning_operation,
    undo_last_operation,
    revert_to_original,
    export_cleaned_dataset,
    can_undo
)
from core.analytics import discover_auto_insights

__all__ = [
    "get_connection",
    "reset_engine",
    "get_table_metadata",
    "list_tables",
    "get_table_schema",
    "execute_analytical_query",
    "query_to_dataframe",
    "validate_and_format_sql",
    "ingest_file",
    "ingest_dataframe",
    "inspect_excel_sheets",
    "replace_table_with_df",
    "profile_dataset",
    "evaluate_data_health",
    "preview_cleaning_operation",
    "apply_cleaning_operation",
    "undo_last_operation",
    "revert_to_original",
    "export_cleaned_dataset",
    "can_undo",
    "discover_auto_insights"
]
