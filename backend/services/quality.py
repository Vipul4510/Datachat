"""
Data Quality Module for DataChat.
Computes comprehensive quality metrics on tables loaded in DuckDB:
1. Row & column counts
2. Column types & schema
3. Missing values count & percentages per column
4. Duplicate row counts
5. Outlier detection:
   - IQR (Interquartile Range) method per numeric column
   - Isolation Forest option (multivariate anomaly detection via scikit-learn)
6. Data health score: 0 to 100 based on weighted penalties for missing values, duplicates, and anomalies
"""

import duckdb
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from sklearn.ensemble import IsolationForest
from backend.services.loader import get_connection, get_table_metadata


def detect_outliers_iqr(df: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Computes outliers for each numeric column using the Interquartile Range (IQR) rule:
    Q1 - 1.5 * IQR, Q3 + 1.5 * IQR.
    """
    outlier_stats: Dict[str, Dict[str, Any]] = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 4:
            outlier_stats[col] = {
                "outlier_count": 0,
                "outlier_percentage": 0.0,
                "lower_bound": None,
                "upper_bound": None
            }
            continue

        q1 = float(np.percentile(series, 25))
        q3 = float(np.percentile(series, 75))
        iqr = q3 - q1
        lower_bound = round(q1 - 1.5 * iqr, 4)
        upper_bound = round(q3 + 1.5 * iqr, 4)

        outlier_mask = (series < lower_bound) | (series > upper_bound)
        count = int(outlier_mask.sum())
        percentage = round((count / len(series)) * 100, 2)

        outlier_stats[col] = {
            "outlier_count": count,
            "outlier_percentage": percentage,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound
        }

    return outlier_stats


def detect_outliers_isolation_forest(
    df: pd.DataFrame,
    numeric_cols: List[str],
    contamination: float = 0.05
) -> Dict[str, Any]:
    """
    Detects multivariate anomalies using scikit-learn's Isolation Forest.
    """
    if len(numeric_cols) == 0 or len(df) < 10:
        return {
            "anomaly_count": 0,
            "anomaly_percentage": 0.0,
            "anomalous_indices": []
        }

    # Prepare numeric data, filling missing values with column median
    data = df[numeric_cols].copy()
    for col in numeric_cols:
        data[col] = data[col].fillna(data[col].median())

    try:
        clf = IsolationForest(contamination=contamination, random_state=42, n_estimators=50)
        preds = clf.fit_predict(data)
        # -1 indicates anomaly
        anomaly_mask = preds == -1
        anomaly_count = int(np.sum(anomaly_mask))
        indices = [int(idx) for idx in np.where(anomaly_mask)[0]]
        percentage = round((anomaly_count / len(df)) * 100, 2)
        return {
            "anomaly_count": anomaly_count,
            "anomaly_percentage": percentage,
            "anomalous_indices": indices[:100]  # Return top 100 indices to keep payload reasonable
        }
    except Exception as e:
        return {
            "anomaly_count": 0,
            "anomaly_percentage": 0.0,
            "error": str(e),
            "anomalous_indices": []
        }


def calculate_health_score(
    total_cells: int,
    missing_cells: int,
    total_rows: int,
    duplicate_rows: int,
    total_numeric_values: int,
    outlier_count_iqr: int
) -> int:
    """
    Calculates overall data health score from 0 to 100.
    Deductions:
    - Missingness: up to 45 points based on % of null cells
    - Duplicates: up to 25 points based on % of duplicate rows
    - Outliers: up to 30 points based on % of outlier values
    """
    score = 100.0

    # Missing values penalty (0-45 pts)
    if total_cells > 0:
        missing_ratio = missing_cells / total_cells
        score -= min(45.0, missing_ratio * 100.0 * 1.5)

    # Duplicates penalty (0-25 pts)
    if total_rows > 0:
        dup_ratio = duplicate_rows / total_rows
        score -= min(25.0, dup_ratio * 100.0 * 1.25)

    # Outliers penalty (0-30 pts)
    if total_numeric_values > 0:
        outlier_ratio = outlier_count_iqr / total_numeric_values
        score -= min(30.0, outlier_ratio * 100.0 * 1.5)

    score = max(0, min(100, int(round(score))))
    return score


def generate_quality_report(table_id: str, run_isolation_forest: bool = True) -> Dict[str, Any]:
    """
    Analyzes table and returns a full data quality report.
    """
    meta = get_table_metadata(table_id)
    if not meta:
        raise ValueError(f"Table id '{table_id}' not found in registry.")

    table_name = meta["table_name"]
    conn = get_connection()

    # Read table into pandas DataFrame for advanced statistical checks
    df: pd.DataFrame = conn.execute(f"SELECT * FROM \"{table_name}\"").df()
    row_count = len(df)
    column_count = len(df.columns)
    total_cells = row_count * column_count

    # 1. Column analysis (types, nulls, distinct counts)
    columns_report: List[Dict[str, Any]] = []
    missing_cells = 0
    numeric_cols: List[str] = []

    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        missing_cells += null_count
        null_pct = round((null_count / row_count) * 100, 2) if row_count > 0 else 0.0
        distinct_count = int(df[col].nunique(dropna=True))

        dtype_str = str(df[col].dtype)
        is_numeric = bool(pd.api.types.is_numeric_dtype(df[col]))
        if is_numeric:
            numeric_cols.append(col)

        col_info: Dict[str, Any] = {
            "column_name": col,
            "data_type": dtype_str,
            "is_numeric": is_numeric,
            "null_count": null_count,
            "null_percentage": null_pct,
            "distinct_count": distinct_count,
        }

        if is_numeric and df[col].notnull().sum() > 0:
            col_info["min"] = float(df[col].min())
            col_info["max"] = float(df[col].max())
            col_info["mean"] = round(float(df[col].mean()), 2)
            col_info["median"] = round(float(df[col].median()), 2)

        columns_report.append(col_info)

    # 2. Duplicate rows count
    duplicate_rows = int(df.duplicated().sum())
    duplicate_percentage = round((duplicate_rows / row_count) * 100, 2) if row_count > 0 else 0.0

    # 3. Outlier detection (IQR)
    iqr_outliers = detect_outliers_iqr(df, numeric_cols)
    total_iqr_outliers = sum(info["outlier_count"] for info in iqr_outliers.values())
    total_numeric_values = sum(len(df[col].dropna()) for col in numeric_cols)

    # 4. Outlier detection (Isolation Forest)
    if_outliers = {}
    if run_isolation_forest:
        if_outliers = detect_outliers_isolation_forest(df, numeric_cols)

    # 5. Overall Data Health Score (0 - 100)
    health_score = calculate_health_score(
        total_cells=total_cells,
        missing_cells=missing_cells,
        total_rows=row_count,
        duplicate_rows=duplicate_rows,
        total_numeric_values=total_numeric_values,
        outlier_count_iqr=total_iqr_outliers
    )

    # Health status rating
    if health_score >= 85:
        health_status = "Excellent"
    elif health_score >= 70:
        health_status = "Good"
    elif health_score >= 50:
        health_status = "Moderate"
    else:
        health_status = "Poor"

    # Sample preview rows (top 5 for UI table preview)
    preview_rows = df.head(5).replace({np.nan: None}).to_dict(orient="records")

    report = {
        "table_id": table_id,
        "table_name": table_name,
        "row_count": row_count,
        "column_count": column_count,
        "total_cells": total_cells,
        "missing_cells": missing_cells,
        "missing_cells_percentage": round((missing_cells / total_cells) * 100, 2) if total_cells > 0 else 0.0,
        "duplicate_rows": duplicate_rows,
        "duplicate_percentage": duplicate_percentage,
        "health_score": health_score,
        "health_status": health_status,
        "numeric_columns": numeric_cols,
        "columns": columns_report,
        "iqr_outliers": iqr_outliers,
        "total_iqr_outliers": total_iqr_outliers,
        "isolation_forest_outliers": if_outliers,
        "preview_rows": preview_rows
    }

    return report
