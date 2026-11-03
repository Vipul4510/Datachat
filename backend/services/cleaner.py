"""
Data Cleaning Service for DataChat.
Handles:
1. Automated & targeted data cleaning operations:
   - Duplicate removal
   - Missing value imputation (mean, median, mode, constant, or smart auto)
   - Missing value dropping (rows or columns)
   - Outlier handling (IQR clipping/winsorizing or dropping)
   - Text standardization (whitespace stripping)
2. History stack per table for undo/revert capability.
3. Natural language cleaning intent detection & LLM parameter extraction.
4. Exporting cleaned data directly to Excel (.xlsx) or CSV format.
"""

import io
import os
import re
import json
import duckdb
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from backend.services.loader import (
    get_connection,
    get_table_metadata,
    update_table_from_df,
    get_table_schema
)
from backend.services.quality import generate_quality_report, detect_outliers_iqr

# In-memory history of DataFrames per table_id for undo capability: {table_id: [df_initial, df_clean_1, ...]}
_table_history: Dict[str, List[pd.DataFrame]] = {}


def get_current_df(table_id: str) -> pd.DataFrame:
    """Reads current DuckDB table into a pandas DataFrame."""
    meta = get_table_metadata(table_id)
    if not meta:
        raise ValueError(f"Table '{table_id}' not found.")
    conn = get_connection()
    return conn.execute(f"SELECT * FROM \"{meta['table_name']}\"").df()


def record_history_step(table_id: str, df: pd.DataFrame) -> None:
    """Appends a new DataFrame snapshot to the history stack."""
    if table_id not in _table_history:
        _table_history[table_id] = []
    _table_history[table_id].append(df.copy())
    if len(_table_history[table_id]) > 10:
        _table_history[table_id].pop(0)


def can_undo(table_id: str) -> bool:
    """Checks if there is a previous state to revert to."""
    return table_id in _table_history and len(_table_history[table_id]) > 1


def undo_cleaning(table_id: str) -> Tuple[Dict[str, Any], str]:
    """Reverts table to the previous snapshot."""
    if not can_undo(table_id):
        raise ValueError("No previous state available to undo.")

    # Pop current snapshot
    _table_history[table_id].pop()
    previous_df = _table_history[table_id][-1]

    # Overwrite DuckDB table
    update_table_from_df(table_id, previous_df.copy())
    new_report = generate_quality_report(table_id, run_isolation_forest=False)

    return new_report, "Reverted last cleaning operation to previous state."


def apply_cleaning_actions(
    table_id: str,
    action: str,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes a cleaning action on the dataset:
    - 'auto_clean': One-click comprehensive data cleaning (removes duplicates, fills nulls, trims text)
    - 'remove_duplicates': Drops duplicate rows
    - 'fill_missing': Fills null values with mean, median, mode, or constant
    - 'drop_missing': Drops rows with null values
    - 'handle_outliers': Clamps or drops IQR outliers
    - 'strip_text': Strips whitespace from string columns
    """
    params = params or {}
    meta = get_table_metadata(table_id)
    if not meta:
        raise ValueError(f"Table '{table_id}' not found.")

    original_df = get_current_df(table_id)
    if table_id not in _table_history or not _table_history[table_id]:
        record_history_step(table_id, original_df)

    initial_report = generate_quality_report(table_id, run_isolation_forest=False)
    initial_score = initial_report["health_score"]
    initial_rows = len(original_df)
    initial_nulls = initial_report["missing_cells"]
    initial_dups = initial_report["duplicate_rows"]
    initial_outliers = initial_report["total_iqr_outliers"]

    cleaned_df = original_df.copy()
    changes_applied: List[str] = []

    # 1. Action: Remove Duplicates
    if action in ["remove_duplicates", "auto_clean"]:
        dup_count = int(cleaned_df.duplicated().sum())
        if dup_count > 0:
            cleaned_df = cleaned_df.drop_duplicates().reset_index(drop=True)
            changes_applied.append(f"Removed {dup_count} duplicate row(s)")

    # 2. Action: Fill Missing Values
    if action == "fill_missing":
        cols = params.get("columns") or list(cleaned_df.columns)
        strategy = params.get("strategy", "auto")  # 'auto', 'mean', 'median', 'mode', 'constant'
        custom_value = params.get("value")

        filled_count = 0
        for col in cols:
            if col not in cleaned_df.columns:
                continue
            col_nulls = int(cleaned_df[col].isnull().sum())
            if col_nulls == 0:
                continue

            is_numeric = bool(pd.api.types.is_numeric_dtype(cleaned_df[col]))
            if strategy == "constant" and custom_value is not None:
                cleaned_df[col] = cleaned_df[col].fillna(custom_value)
                filled_count += col_nulls
            elif is_numeric:
                if strategy in ["mean", "auto"]:
                    val = round(float(cleaned_df[col].mean()), 2)
                elif strategy == "median":
                    val = round(float(cleaned_df[col].median()), 2)
                else:
                    mode_val = cleaned_df[col].mode()
                    val = mode_val[0] if not mode_val.empty else 0
                cleaned_df[col] = cleaned_df[col].fillna(val)
                filled_count += col_nulls
            else:
                mode_val = cleaned_df[col].mode()
                val = mode_val[0] if not mode_val.empty else "Unknown"
                cleaned_df[col] = cleaned_df[col].fillna(val)
                filled_count += col_nulls

        if filled_count > 0:
            changes_applied.append(f"Filled {filled_count} missing value(s) across selected column(s)")

    # 3. Action: Drop Missing Values
    elif action == "drop_missing":
        cols = params.get("columns")
        how = params.get("how", "any")
        before_drop = len(cleaned_df)
        if cols:
            valid_cols = [c for c in cols if c in cleaned_df.columns]
            if valid_cols:
                cleaned_df = cleaned_df.dropna(subset=valid_cols, how=how).reset_index(drop=True)
        else:
            cleaned_df = cleaned_df.dropna(how=how).reset_index(drop=True)
        dropped_count = before_drop - len(cleaned_df)
        if dropped_count > 0:
            changes_applied.append(f"Dropped {dropped_count} row(s) containing missing values")

    # 4. Action: Auto Clean (All in one)
    elif action == "auto_clean":
        # Missing values imputation
        filled_count = 0
        for col in cleaned_df.columns:
            col_nulls = int(cleaned_df[col].isnull().sum())
            if col_nulls == 0:
                continue

            if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                median_val = cleaned_df[col].median()
                if pd.notnull(median_val):
                    cleaned_df[col] = cleaned_df[col].fillna(median_val)
                    filled_count += col_nulls
            else:
                mode_val = cleaned_df[col].mode()
                fill_val = mode_val[0] if not mode_val.empty else "Unknown"
                cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                filled_count += col_nulls

        if filled_count > 0:
            changes_applied.append(f"Imputed {filled_count} missing value(s) with column medians/modes")

        # Strip extra whitespace from text columns
        for col in cleaned_df.select_dtypes(include=["object", "string"]).columns:
            cleaned_df[col] = cleaned_df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    # 5. Action: Handle Outliers
    if action in ["handle_outliers", "auto_clean"]:
        outlier_method = params.get("method", "clamp")  # 'clamp' (winsorize) or 'drop'
        outlier_cols = params.get("columns") or [
            c for c in cleaned_df.columns if pd.api.types.is_numeric_dtype(cleaned_df[c])
        ]
        iqr_stats = detect_outliers_iqr(cleaned_df, outlier_cols)
        total_handled = 0

        for col, stats in iqr_stats.items():
            if stats["outlier_count"] == 0 or stats["lower_bound"] is None:
                continue
            lb, ub = stats["lower_bound"], stats["upper_bound"]

            if outlier_method == "clamp" or action == "auto_clean":
                # Winsorize / clamp within IQR limits
                mask = (cleaned_df[col] < lb) | (cleaned_df[col] > ub)
                count = int(mask.sum())
                if count > 0:
                    cleaned_df[col] = cleaned_df[col].clip(lower=lb, upper=ub)
                    total_handled += count
            elif outlier_method == "drop":
                before_len = len(cleaned_df)
                cleaned_df = cleaned_df[(cleaned_df[col] >= lb) & (cleaned_df[col] <= ub)].reset_index(drop=True)
                total_handled += (before_len - len(cleaned_df))

        if total_handled > 0:
            action_desc = "Clipped (winsorized)" if (outlier_method == "clamp" or action == "auto_clean") else "Removed"
            changes_applied.append(f"{action_desc} {total_handled} statistical outlier(s)")

    if not changes_applied:
        changes_applied.append("No changes were needed; dataset is already clean for this criteria.")

    # Overwrite DuckDB table with cleaned data
    new_meta = update_table_from_df(table_id, cleaned_df)
    record_history_step(table_id, cleaned_df)

    # Recalculate fresh quality report
    new_report = generate_quality_report(table_id, run_isolation_forest=False)
    final_score = new_report["health_score"]
    score_diff = final_score - initial_score

    return {
        "success": True,
        "action": action,
        "table_id": table_id,
        "changes": changes_applied,
        "rows_before": initial_rows,
        "rows_after": len(cleaned_df),
        "columns_count": len(cleaned_df.columns),
        "initial_health_score": initial_score,
        "final_health_score": final_score,
        "score_improvement": score_diff,
        "missing_cells_remaining": new_report["missing_cells"],
        "duplicate_rows_remaining": new_report["duplicate_rows"],
        "outliers_remaining": new_report["total_iqr_outliers"],
        "quality_report": new_report,
        "metadata": new_meta,
        "can_undo": can_undo(table_id)
    }


def is_cleaning_request(question: str) -> bool:
    """
    Checks if a user query is asking for data cleaning rather than standard SQL analysis.
    """
    q = question.lower().strip()
    cleaning_keywords = [
        "clean data", "clean dataset", "clean the data", "auto clean", "autoclean",
        "remove duplicate", "remove duplicates", "drop duplicate", "drop duplicates",
        "delete duplicate", "delete duplicates", "deduplicate", "dedup",
        "fill missing", "impute missing", "handle missing", "fix missing", "replace missing",
        "drop missing", "remove missing", "drop null", "remove null", "delete null", "fix nulls",
        "handle outlier", "handle outliers", "remove outlier", "remove outliers", "clip outlier",
        "clean up", "clean file", "improve health score", "boost health score",
        "make health score 100", "clean this"
    ]
    for kw in cleaning_keywords:
        if kw in q:
            return True
    return False


def parse_cleaning_intent(question: str, schema: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """
    Parses user natural language request into specific action and parameters.
    """
    q = question.lower().strip()
    col_names = [c["column_name"] for c in schema]

    # Check for duplicate removal
    if any(k in q for k in ["duplicate", "dedup"]):
        return "remove_duplicates", {}

    # Check for outlier handling
    if "outlier" in q:
        method = "drop" if ("drop" in q or "delete" in q or "remove" in q) else "clamp"
        # Match mentioned columns
        matched_cols = [c for c in col_names if c.lower() in q]
        return "handle_outliers", {"method": method, "columns": matched_cols or None}

    # Check for missing values dropping
    if any(k in q for k in ["drop missing", "drop null", "remove missing", "remove null", "delete null"]):
        matched_cols = [c for c in col_names if c.lower() in q]
        return "drop_missing", {"columns": matched_cols or None}

    # Check for missing values filling / imputing
    if any(k in q for k in ["fill missing", "impute", "replace missing", "fix null", "fill null"]):
        strategy = "median" if "median" in q else ("mean" if "mean" in q or "average" in q else ("mode" if "mode" in q else "auto"))
        matched_cols = [c for c in col_names if c.lower() in q]
        return "fill_missing", {"strategy": strategy, "columns": matched_cols or None}

    # Default to auto-clean
    return "auto_clean", {}


def export_cleaned_dataset(table_id: str, format: str = "xlsx") -> Tuple[bytes, str, str]:
    """
    Exports the current in-memory DuckDB table as an Excel (.xlsx), CSV, or JSON file.
    Returns: (bytes_content, media_type, filename)
    """
    meta = get_table_metadata(table_id)
    if not meta:
        raise ValueError(f"Table '{table_id}' not found.")

    df = get_current_df(table_id)
    orig_name = os.path.splitext(meta.get("original_filename", "dataset"))[0]

    fmt = format.lower()
    if fmt in ["xlsx", "excel"]:
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Cleaned Data", index=False)
        content = out.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"cleaned_{orig_name}.xlsx"
    elif fmt == "csv":
        content = df.to_csv(index=False).encode("utf-8")
        media_type = "text/csv; charset=utf-8"
        filename = f"cleaned_{orig_name}.csv"
    elif fmt == "json":
        content = df.to_json(orient="records", indent=2).encode("utf-8")
        media_type = "application/json"
        filename = f"cleaned_{orig_name}.json"
    else:
        raise ValueError(f"Unsupported export format: {format}")

    return content, media_type, filename
