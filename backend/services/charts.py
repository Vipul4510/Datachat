"""
Chart Suggestion Service.
Analyzes query results shape and column types to choose the most suitable chart:
- 'bar': categorical x numeric (or aggregated comparison)
- 'line': time/date or continuous sequence x numeric
- 'pie': categorical distribution with 2 to 7 distinct slices
- 'table': raw records, too many columns/rows, or text-heavy outputs
"""

import re
from typing import Dict, Any, List, Optional

DATE_PATTERNS = [r"date", r"time", r"month", r"year", r"day", r"week", r"quarter", r"period"]

def is_date_like(col_name: str, values: List[Any]) -> bool:
    """Checks if column name or values resemble time series / dates."""
    lower_col = col_name.lower()
    if any(re.search(pat, lower_col) for pat in DATE_PATTERNS):
        return True
    # Check value formats
    for val in values[:5]:
        val_str = str(val).strip()
        if re.match(r"^\d{4}-\d{2}", val_str) or re.match(r"^\d{2}/\d{2}/\d{4}", val_str):
            return True
    return False


def is_numeric_value(val: Any) -> bool:
    """Checks if a single value is numeric."""
    if val is None:
        return False
    try:
        float(val)
        return True
    except (ValueError, TypeError):
        return False


def suggest_chart(columns: List[str], rows: List[List[Any]]) -> Dict[str, Any]:
    """
    Determines optimal chart type and returns visualization configuration for Recharts.
    """
    if not columns or not rows:
        return {"type": "none", "reason": "No data returned"}

    if len(rows) == 1 and len(columns) == 1:
        # Single metric KPI card
        return {
            "type": "metric",
            "title": columns[0],
            "value": rows[0][0],
            "unit": ""
        }

    # Inspect column data types from result rows
    col_types = []
    for c_idx, col in enumerate(columns):
        sample_vals = [row[c_idx] for row in rows if row[c_idx] is not None]
        num_count = sum(1 for v in sample_vals if is_numeric_value(v))
        is_num = (num_count / len(sample_vals) > 0.8) if sample_vals else False
        col_types.append({
            "name": col,
            "is_numeric": is_num,
            "is_date": is_date_like(col, sample_vals)
        })

    num_cols = [c["name"] for c in col_types if c["is_numeric"]]
    cat_cols = [c["name"] for c in col_types if not c["is_numeric"]]
    date_cols = [c["name"] for c in col_types if c["is_date"]]

    row_count = len(rows)

    # Convert rows to list of dicts for charting libraries
    data = []
    for r in rows:
        row_dict = {}
        for c_idx, col in enumerate(columns):
            val = r[c_idx]
            # Convert numeric strings to actual float/int for charting
            if is_numeric_value(val):
                row_dict[col] = float(val) if "." in str(val) else int(val)
            else:
                row_dict[col] = val
        data.append(row_dict)

    # 1. Line Chart: 1 date/time column and at least 1 numeric column
    if date_cols and num_cols and 2 <= row_count <= 100:
        return {
            "type": "line",
            "xAxis": date_cols[0],
            "yAxis": num_cols[0],
            "series": num_cols[:3],  # support up to 3 numeric metrics
            "data": data,
            "title": f"{num_cols[0]} over {date_cols[0]}"
        }

    # 2. Pie Chart: 1 categorical column with 2-7 rows and 1 numeric column (and values are positive)
    if len(cat_cols) == 1 and len(num_cols) == 1 and 2 <= row_count <= 7:
        # Check if values are non-negative
        first_num = num_cols[0]
        all_positive = all(row.get(first_num, 0) >= 0 for row in data)
        if all_positive:
            return {
                "type": "pie",
                "nameKey": cat_cols[0],
                "dataKey": first_num,
                "data": data,
                "title": f"Distribution of {first_num} by {cat_cols[0]}"
            }

    # 3. Bar Chart: 1 categorical column and 1 or more numeric columns (up to 30 rows)
    if cat_cols and num_cols and 2 <= row_count <= 35:
        return {
            "type": "bar",
            "xAxis": cat_cols[0],
            "yAxis": num_cols[0],
            "series": num_cols[:3],
            "data": data,
            "title": f"{num_cols[0]} by {cat_cols[0]}"
        }

    # 4. Two numeric columns comparison (Scatter or Bar)
    if len(num_cols) >= 2 and row_count <= 25:
        return {
            "type": "bar",
            "xAxis": columns[0],
            "yAxis": num_cols[1],
            "series": [num_cols[1]],
            "data": data,
            "title": f"{num_cols[1]} comparison"
        }

    # Default to table representation
    return {
        "type": "table",
        "data": data,
        "title": "Tabular Results"
    }
