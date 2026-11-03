"""
Data Quality Doctor Service.
Computes calibrated health metrics (IQR + Isolation Forest) and provides safe,
explainable, previewable data cleaning operations with an undo/rollback history stack.
"""

import io
import copy
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from sklearn.ensemble import IsolationForest

from core.duckdb_engine import (
    get_connection,
    get_table_metadata,
    query_to_dataframe,
    register_table_metadata
)
from core.ingestion import replace_table_with_df

# Table history stack for undo support: {table_id: [df_original, df_clean1, ...]}
_cleaning_history: Dict[str, List[pd.DataFrame]] = {}
_original_dataframes: Dict[str, pd.DataFrame] = {}


def get_current_dataframe(table_id: str) -> pd.DataFrame:
    """Returns current state of table as DataFrame."""
    meta = get_table_metadata(table_id)
    if not meta:
        raise ValueError(f"Table '{table_id}' not found.")
    conn = get_connection()
    return conn.execute(f"SELECT * FROM \"{meta['table_name']}\"").df()


def init_table_history(table_id: str, df: pd.DataFrame) -> None:
    """Initializes history stack and stores untouched original dataframe."""
    if table_id not in _original_dataframes:
        _original_dataframes[table_id] = df.copy()
    if table_id not in _cleaning_history:
        _cleaning_history[table_id] = [df.copy()]


def can_undo(table_id: str) -> bool:
    """Checks whether an undo action is available."""
    return table_id in _cleaning_history and len(_cleaning_history[table_id]) > 1


def undo_last_operation(table_id: str) -> Tuple[Dict[str, Any], str]:
    """Reverts to the previous dataframe snapshot."""
    if not can_undo(table_id):
        raise ValueError("No previous state to undo.")

    # Remove current snapshot
    _cleaning_history[table_id].pop()
    previous_df = _cleaning_history[table_id][-1].copy()

    # Apply back to DuckDB
    replace_table_with_df(table_id, previous_df)
    report = evaluate_data_health(table_id)
    return report, "Reverted the last cleaning action successfully."


def revert_to_original(table_id: str) -> Tuple[Dict[str, Any], str]:
    """Restores the pristine original uploaded dataset."""
    if table_id not in _original_dataframes:
        raise ValueError("Original data backup not found.")

    original_df = _original_dataframes[table_id].copy()
    _cleaning_history[table_id] = [original_df.copy()]
    replace_table_with_df(table_id, original_df)
    report = evaluate_data_health(table_id)
    return report, "Restored dataset to original uploaded state."


def evaluate_data_health(table_id: str, run_isolation_forest: bool = True) -> Dict[str, Any]:
    """
    Computes calibrated data health score (0 to 100) and detailed diagnostic metrics.
    Penalties are weighted:
    - Missing cells: up to 40 penalty points
    - Duplicates: up to 30 penalty points
    - Outliers / Anomaly rates: up to 30 penalty points
    """
    meta = get_table_metadata(table_id)
    if not meta:
        raise ValueError(f"Table '{table_id}' not found.")

    df = get_current_dataframe(table_id)
    init_table_history(table_id, df)

    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols

    if total_cells == 0:
        return {
            "health_score": 0,
            "status": "Poor",
            "total_rows": 0,
            "total_cols": 0,
            "duplicate_rows": 0,
            "missing_cells": 0,
            "column_metrics": [],
            "iqr_outliers": {},
            "isolation_forest_anomalies": {"anomaly_count": 0, "anomaly_percentage": 0.0}
        }

    # Missing values
    missing_by_col = df.isna().sum().to_dict()
    total_missing_cells = sum(missing_by_col.values())
    overall_missing_pct = (total_missing_cells / total_cells) * 100.0

    # Duplicates
    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = (duplicate_rows / total_rows) * 100.0 if total_rows > 0 else 0.0

    # Numeric columns for outlier detection
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    # IQR Outliers
    iqr_outliers: Dict[str, Dict[str, Any]] = {}
    total_iqr_outliers = 0
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) >= 4:
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            mask = (series < lower) | (series > upper)
            cnt = int(mask.sum())
            total_iqr_outliers += cnt
            iqr_outliers[col] = {
                "outlier_count": cnt,
                "outlier_pct": round((cnt / len(series) * 100), 2) if len(series) > 0 else 0.0,
                "lower_bound": round(lower, 3),
                "upper_bound": round(upper, 3)
            }
        else:
            iqr_outliers[col] = {
                "outlier_count": 0,
                "outlier_pct": 0.0,
                "lower_bound": None,
                "upper_bound": None
            }

    # Isolation Forest
    iso_anomalies = {"anomaly_count": 0, "anomaly_percentage": 0.0}
    if run_isolation_forest and len(numeric_cols) > 0 and total_rows >= 10:
        try:
            num_df = df[numeric_cols].fillna(df[numeric_cols].median())
            clf = IsolationForest(contamination=0.05, random_state=42, n_estimators=50)
            preds = clf.fit_predict(num_df)
            anom_count = int((preds == -1).sum())
            iso_anomalies = {
                "anomaly_count": anom_count,
                "anomaly_percentage": round((anom_count / total_rows * 100), 2)
            }
        except Exception:
            pass

    # Score calculation
    # Base = 100
    missing_penalty = min(40.0, (overall_missing_pct / 50.0) * 40.0)
    dup_penalty = min(30.0, (duplicate_pct / 20.0) * 30.0)
    outlier_penalty = min(30.0, ((total_iqr_outliers / total_rows) * 100.0 / 20.0) * 30.0) if total_rows > 0 else 0.0

    raw_score = 100.0 - (missing_penalty + dup_penalty + outlier_penalty)
    health_score = int(max(0, min(100, round(raw_score))))

    if health_score >= 90:
        status = "Excellent"
        color = "emerald"
    elif health_score >= 75:
        status = "Good"
        color = "cyan"
    elif health_score >= 50:
        status = "Moderate"
        color = "amber"
    else:
        status = "Poor"
        color = "rose"

    column_metrics = []
    for col in df.columns:
        null_cnt = int(missing_by_col[col])
        null_p = round((null_cnt / total_rows * 100), 2)
        column_metrics.append({
            "name": col,
            "type": str(df[col].dtype),
            "null_count": null_cnt,
            "null_percentage": null_p,
            "distinct_count": int(df[col].nunique(dropna=True)),
            "outliers": iqr_outliers.get(col, {}).get("outlier_count", 0)
        })

    return {
        "health_score": health_score,
        "status": status,
        "status_color": color,
        "total_rows": total_rows,
        "total_cols": total_cols,
        "total_cells": total_cells,
        "missing_cells": total_missing_cells,
        "missing_percentage": round(overall_missing_pct, 2),
        "duplicate_rows": duplicate_rows,
        "duplicate_percentage": round(duplicate_pct, 2),
        "total_iqr_outliers": total_iqr_outliers,
        "column_metrics": column_metrics,
        "iqr_outliers": iqr_outliers,
        "isolation_forest_anomalies": iso_anomalies,
        "can_undo": can_undo(table_id)
    }


def preview_cleaning_operation(
    table_id: str,
    action: str,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculates the exact impact of a proposed cleaning transformation WITHOUT applying it.
    
    Supported actions:
    - 'remove_duplicates': drops duplicate rows
    - 'fill_missing': imputes nulls using strategy (mean, median, mode, constant)
    - 'drop_missing': drops rows with null values
    - 'handle_outliers': clips numeric columns to IQR bounds
    - 'strip_text': trims whitespace from all string columns
    
    Returns:
        {
            "action": str,
            "affected_records": int,
            "rows_before": int,
            "rows_after": int,
            "missing_before": int,
            "missing_after": int,
            "preview_diff": List[Dict[str, Any]],
            "description": str
        }
    """
    params = params or {}
    df = get_current_dataframe(table_id)
    target_df = df.copy()

    rows_before = len(df)
    missing_before = int(df.isna().sum().sum())
    description = ""
    affected = 0

    if action == "remove_duplicates":
        affected = int(target_df.duplicated().sum())
        target_df = target_df.drop_duplicates()
        description = f"Remove {affected} duplicate rows from the dataset."

    elif action == "fill_missing":
        strategy = params.get("strategy", "mean")
        col = params.get("column")
        cols_to_fill = [col] if col else target_df.columns

        for c in cols_to_fill:
            if c not in target_df.columns:
                continue
            null_count = int(target_df[c].isna().sum())
            if null_count == 0:
                continue
            affected += null_count
            if pd.api.types.is_numeric_dtype(target_df[c]):
                if strategy == "mean":
                    val = target_df[c].mean()
                elif strategy == "median":
                    val = target_df[c].median()
                elif strategy == "zero":
                    val = 0
                else:
                    val = params.get("constant", 0)
                target_df[c] = target_df[c].fillna(val)
            else:
                mode_vals = target_df[c].mode()
                val = mode_vals.iloc[0] if len(mode_vals) > 0 else "Unknown"
                target_df[c] = target_df[c].fillna(val)

        description = f"Impute missing values using '{strategy}' strategy across target columns."

    elif action == "drop_missing":
        affected = int(target_df.isna().any(axis=1).sum())
        target_df = target_df.dropna()
        description = f"Drop {affected} rows containing one or more null values."

    elif action == "handle_outliers":
        method = params.get("method", "clip")  # 'clip' or 'drop'
        col = params.get("column")
        num_cols = [col] if col else [c for c in target_df.columns if pd.api.types.is_numeric_dtype(target_df[c])]

        for c in num_cols:
            series = target_df[c].dropna()
            if len(series) >= 4:
                q1 = float(series.quantile(0.25))
                q3 = float(series.quantile(0.75))
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                outliers = ((series < lower) | (series > upper)).sum()
                affected += int(outliers)
                if method == "clip":
                    target_df[c] = target_df[c].clip(lower=lower, upper=upper)
                elif method == "drop":
                    target_df = target_df[(target_df[c] >= lower) & (target_df[c] <= upper) | target_df[c].isna()]

        description = f"Handle IQR outliers by {method}ping to 1.5x IQR bounds."

    elif action == "strip_text":
        str_cols = [c for c in target_df.columns if pd.api.types.is_string_dtype(target_df[c]) or pd.api.types.is_object_dtype(target_df[c])]
        for c in str_cols:
            clean = target_df[c].astype(str).str.strip()
            diff = (target_df[c].astype(str) != clean).sum()
            affected += int(diff)
            target_df[c] = clean
        description = f"Strip leading and trailing whitespace from text columns."

    rows_after = len(target_df)
    missing_after = int(target_df.isna().sum().sum())

    return {
        "action": action,
        "affected_records": affected,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "missing_before": missing_before,
        "missing_after": missing_after,
        "description": description,
        "preview_sample": target_df.head(5).to_dict(orient="records")
    }


def apply_cleaning_operation(
    table_id: str,
    action: str,
    params: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], str]:
    """
    Applies the cleaning transformation to DuckDB and records the snapshot in history.
    """
    preview = preview_cleaning_operation(table_id, action, params)
    df = get_current_dataframe(table_id)

    # Perform action on df
    target_df = df.copy()
    if action == "remove_duplicates":
        target_df = target_df.drop_duplicates()
    elif action == "fill_missing":
        strategy = (params or {}).get("strategy", "mean")
        col = (params or {}).get("column")
        cols_to_fill = [col] if col else target_df.columns
        for c in cols_to_fill:
            if c not in target_df.columns:
                continue
            if pd.api.types.is_numeric_dtype(target_df[c]):
                val = target_df[c].mean() if strategy == "mean" else target_df[c].median()
                target_df[c] = target_df[c].fillna(val)
            else:
                m = target_df[c].mode()
                val = m.iloc[0] if len(m) > 0 else "Unknown"
                target_df[c] = target_df[c].fillna(val)
    elif action == "drop_missing":
        target_df = target_df.dropna()
    elif action == "handle_outliers":
        method = (params or {}).get("method", "clip")
        col = (params or {}).get("column")
        num_cols = [col] if col else [c for c in target_df.columns if pd.api.types.is_numeric_dtype(target_df[c])]
        for c in num_cols:
            s = target_df[c].dropna()
            if len(s) >= 4:
                q1 = float(s.quantile(0.25))
                q3 = float(s.quantile(0.75))
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                if method == "clip":
                    target_df[c] = target_df[c].clip(lower=lower, upper=upper)
                elif method == "drop":
                    target_df = target_df[(target_df[c] >= lower) & (target_df[c] <= upper) | target_df[c].isna()]
    elif action == "strip_text":
        str_cols = [c for c in target_df.columns if pd.api.types.is_string_dtype(target_df[c]) or pd.api.types.is_object_dtype(target_df[c])]
        for c in str_cols:
            target_df[c] = target_df[c].astype(str).str.strip()

    # Record to history stack
    if table_id not in _cleaning_history:
        _cleaning_history[table_id] = [df.copy()]
    _cleaning_history[table_id].append(target_df.copy())
    if len(_cleaning_history[table_id]) > 10:
        _cleaning_history[table_id].pop(0)

    # Overwrite DuckDB table
    replace_table_with_df(table_id, target_df)
    report = evaluate_data_health(table_id)
    return report, preview["description"]


def export_cleaned_dataset(table_id: str, format_type: str = "csv") -> Tuple[bytes, str, str]:
    """
    Exports the current (cleaned) dataset to bytes.
    Returns: (file_bytes, mime_type, file_name)
    """
    df = get_current_dataframe(table_id)
    meta = get_table_metadata(table_id)
    base_name = meta.get("file_name", "dataset").rsplit(".", 1)[0]

    if format_type.lower() == "xlsx":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="CleanedData")
        file_bytes = output.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        file_name = f"{base_name}_cleaned.xlsx"
    else:
        file_bytes = df.to_csv(index=False).encode("utf-8")
        mime = "text/csv"
        file_name = f"{base_name}_cleaned.csv"

    return file_bytes, mime, file_name
