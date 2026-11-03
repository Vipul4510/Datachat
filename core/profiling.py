"""
Automated Dataset Intelligence and Profiling Service.
Generates comprehensive structural and statistical profiles of loaded datasets:
- Schema and inferred semantic data types
- Missing values and completeness rates
- Duplicate rows detection
- Distinct cardinality and potential primary key candidates
- Detailed numeric distributions (five-number summary, mean, std, IQR outliers)
- Categorical distributions and top value frequencies
- Date range spans
- Actionable quality warnings
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from core.duckdb_engine import get_connection, get_table_metadata, query_to_dataframe


def infer_semantic_type(series: pd.Series, duckdb_type: str) -> str:
    """Infers high-level semantic type: Numeric, Datetime, Categorical, Boolean, or Text."""
    dt = str(series.dtype).lower()
    duck_lower = duckdb_type.lower()

    if "bool" in dt or "boolean" in duck_lower:
        return "Boolean"
    if "date" in dt or "time" in dt or "date" in duck_lower or "timestamp" in duck_lower:
        return "Datetime"
    if pd.api.types.is_numeric_dtype(series):
        # If integer with very low cardinality, might be categorical flag
        if series.nunique() <= 2 and len(series) > 10:
            return "Boolean"
        return "Numeric"
    # Check if string series can be parsed as dates
    if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
        valid = series.dropna()
        if len(valid) > 0 and len(valid) <= 1000:
            try:
                pd.to_datetime(valid.iloc[:50], format="mixed")
                return "Datetime"
            except Exception:
                pass
        unique_ratio = valid.nunique() / len(valid) if len(valid) > 0 else 0
        if unique_ratio < 0.2 or valid.nunique() <= 20:
            return "Categorical"
        return "Text"
    return "Categorical"


def profile_dataset(table_id: str, max_sample_rows: int = 100000) -> Dict[str, Any]:
    """
    Produces an exhaustive profile of the dataset.
    
    Args:
        table_id: ID of the loaded table.
        max_sample_rows: Maximum sample to evaluate for expensive statistical operations.
        
    Returns:
        Comprehensive dictionary of profile metrics and observations.
    """
    meta = get_table_metadata(table_id)
    if not meta:
        raise ValueError(f"Table '{table_id}' not found.")

    table_name = meta["table_name"]
    conn = get_connection()

    total_rows = int(conn.execute(f"SELECT COUNT(*) FROM \"{table_name}\"").fetchone()[0])
    col_info = conn.execute(f"DESCRIBE \"{table_name}\"").fetchall()

    # Load dataframe for statistical analysis
    if total_rows > max_sample_rows:
        df = conn.execute(f"SELECT * FROM \"{table_name}\" USING SAMPLE {max_sample_rows}").df()
        is_sampled = True
    else:
        df = conn.execute(f"SELECT * FROM \"{table_name}\"").df()
        is_sampled = False

    total_cols = len(df.columns)
    total_cells = total_rows * total_cols
    total_missing_cells = int(df.isna().sum().sum())
    overall_completeness_pct = round(((total_cells - total_missing_cells) / total_cells * 100), 2) if total_cells > 0 else 100.0

    # Duplicate rows
    duplicate_rows_count = int(df.duplicated().sum())

    column_profiles: Dict[str, Dict[str, Any]] = {}
    numeric_columns: List[str] = []
    categorical_columns: List[str] = []
    datetime_columns: List[str] = []
    actionable_warnings: List[Dict[str, str]] = []

    duck_types = {str(c[0]): str(c[1]) for c in col_info}

    for col in df.columns:
        series = df[col]
        d_type = duck_types.get(col, str(series.dtype))
        semantic_type = infer_semantic_type(series, d_type)

        null_count = int(series.isna().sum())
        null_pct = round((null_count / len(series) * 100), 2)
        distinct_count = int(series.nunique(dropna=True))

        col_prof: Dict[str, Any] = {
            "name": col,
            "duckdb_type": d_type,
            "semantic_type": semantic_type,
            "null_count": null_count,
            "null_percentage": null_pct,
            "distinct_count": distinct_count,
            "is_unique": (distinct_count == len(series.dropna()) and len(series.dropna()) > 0),
            "sample_values": series.dropna().head(3).tolist(),
        }

        # Numeric Statistics
        if semantic_type == "Numeric":
            numeric_columns.append(col)
            clean_num = series.dropna()
            if len(clean_num) > 0:
                q1 = float(clean_num.quantile(0.25))
                q3 = float(clean_num.quantile(0.75))
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers_count = int(((clean_num < lower_bound) | (clean_num > upper_bound)).sum())

                col_prof["statistics"] = {
                    "min": float(clean_num.min()),
                    "max": float(clean_num.max()),
                    "mean": round(float(clean_num.mean()), 3),
                    "median": round(float(clean_num.median()), 3),
                    "std": round(float(clean_num.std()), 3) if len(clean_num) > 1 else 0.0,
                    "q25": round(q1, 3),
                    "q75": round(q3, 3),
                    "iqr": round(iqr, 3),
                    "outliers_count": outliers_count,
                    "skewness": round(float(clean_num.skew()), 3) if len(clean_num) > 2 else 0.0
                }

                if outliers_count > 0:
                    actionable_warnings.append({
                        "column": col,
                        "type": "outlier",
                        "severity": "medium",
                        "message": f"Found {outliers_count} potential outlier values outside 1.5x IQR bounds [{lower_bound:.2f}, {upper_bound:.2f}]."
                    })
            else:
                col_prof["statistics"] = None

        # Categorical Statistics
        elif semantic_type in ["Categorical", "Text", "Boolean"]:
            categorical_columns.append(col)
            top_counts = series.value_counts(dropna=True).head(5).to_dict()
            col_prof["top_frequencies"] = {str(k): int(v) for k, v in top_counts.items()}

        # Datetime Statistics
        elif semantic_type == "Datetime":
            datetime_columns.append(col)
            try:
                dt_series = pd.to_datetime(series.dropna(), errors="coerce")
                dt_clean = dt_series.dropna()
                if len(dt_clean) > 0:
                    col_prof["datetime_range"] = {
                        "min_date": str(dt_clean.min()),
                        "max_date": str(dt_clean.max()),
                        "days_span": int((dt_clean.max() - dt_clean.min()).days)
                    }
            except Exception:
                pass

        # Warning checks
        if null_pct > 30.0:
            actionable_warnings.append({
                "column": col,
                "type": "missing_values",
                "severity": "high" if null_pct > 50 else "medium",
                "message": f"{null_pct}% of entries are missing ({null_count} null rows)."
            })
        if distinct_count == 1 and total_rows > 1:
            actionable_warnings.append({
                "column": col,
                "type": "constant_column",
                "severity": "low",
                "message": f"Column has only 1 distinct constant value across all rows."
            })

        column_profiles[col] = col_prof

    if duplicate_rows_count > 0:
        actionable_warnings.insert(0, {
            "column": "Dataset",
            "type": "duplicate_rows",
            "severity": "high",
            "message": f"Detected {duplicate_rows_count} exact duplicate rows."
        })

    return {
        "table_id": table_id,
        "table_name": table_name,
        "row_count": total_rows,
        "column_count": total_cols,
        "total_cells": total_cells,
        "missing_cells": total_missing_cells,
        "completeness_percentage": overall_completeness_pct,
        "duplicate_rows": duplicate_rows_count,
        "columns": column_profiles,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "datetime_columns": datetime_columns,
        "actionable_warnings": actionable_warnings,
        "is_sampled": is_sampled,
    }
