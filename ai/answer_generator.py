"""
Answer Generation and Smart Visualization Selector.
Generates plain-English analytical summaries, transparent methodology explanations,
and automatically recommends optimal charts (Bar, Line, Pie, Scatter, KPI, or Table).
"""

from typing import Dict, Any, List, Optional
from ai.provider_factory import resolve_provider, BaseAIProvider
from ai.fallback_provider import DeterministicFallbackProvider


def recommend_visualization(
    columns: List[str],
    rows: List[List[Any]],
    question: str
) -> Dict[str, Any]:
    """
    Intelligently determines the best visualization based on query results:
    - KPI Card: single scalar value
    - Line Chart: time series with ordered dates
    - Bar Chart: categorical aggregation
    - Horizontal Bar Chart: many categorical bars (>7 items)
    - Scatter Plot: two continuous numerical dimensions
    - Pie Chart: proportion across <= 5 categories
    - Table: multi-column tabular results
    """
    row_count = len(rows)
    col_count = len(columns)

    if row_count == 0 or col_count == 0:
        return {"chart_type": "table", "title": "No Data", "x": None, "y": None}

    # 1. Single scalar value -> KPI Card
    if row_count == 1 and col_count == 1:
        val = rows[0][0]
        return {
            "chart_type": "kpi",
            "title": columns[0],
            "value": val,
            "x": None,
            "y": None
        }

    # Helper: inspect column values
    def is_numeric_col(idx: int) -> bool:
        vals = [r[idx] for r in rows if r[idx] is not None]
        return len(vals) > 0 and all(isinstance(v, (int, float)) for v in vals)

    def is_date_col(idx: int) -> bool:
        col_name = columns[idx].lower()
        if "date" in col_name or "time" in col_name or "month" in col_name or "year" in col_name:
            return True
        return False

    # 2. Two columns: Category / Date + Metric
    if col_count == 2:
        c0_num = is_numeric_col(0)
        c1_num = is_numeric_col(1)

        # One categorical/date and one numeric
        if (not c0_num and c1_num) or (c0_num and not c1_num):
            cat_idx = 0 if not c0_num else 1
            num_idx = 1 if not c0_num else 0

            # Time series -> Line Chart
            if is_date_col(cat_idx):
                return {
                    "chart_type": "line",
                    "title": f"{columns[num_idx]} over Time",
                    "x": columns[cat_idx],
                    "y": columns[num_idx]
                }

            # Few categories with share/proportion -> Pie Chart
            q_low = question.lower()
            if row_count <= 5 and ("share" in q_low or "percentage" in q_low or "proportion" in q_low or "breakdown" in q_low):
                return {
                    "chart_type": "pie",
                    "title": f"Proportional Distribution of {columns[num_idx]} by {columns[cat_idx]}",
                    "x": columns[cat_idx],
                    "y": columns[num_idx]
                }

            # Many categories -> Horizontal Bar
            if row_count > 7:
                return {
                    "chart_type": "horizontal_bar",
                    "title": f"{columns[num_idx]} by {columns[cat_idx]}",
                    "x": columns[num_idx],
                    "y": columns[cat_idx]
                }

            # Standard Bar
            return {
                "chart_type": "bar",
                "title": f"{columns[num_idx]} by {columns[cat_idx]}",
                "x": columns[cat_idx],
                "y": columns[num_idx]
            }

        # Two numeric columns -> Scatter Plot
        if c0_num and c1_num and row_count >= 5:
            return {
                "chart_type": "scatter",
                "title": f"Relationship: {columns[0]} vs {columns[1]}",
                "x": columns[0],
                "y": columns[1]
            }

    # 3. Default to Table for complex multi-column results
    return {
        "chart_type": "table",
        "title": "Tabular Result",
        "x": None,
        "y": None
    }


def generate_transparent_answer(
    question: str,
    sql: str,
    columns: List[str],
    rows: List[List[Any]],
    latency_ms: float,
    is_fallback: bool = False,
    provider_name: str = "AI Engine"
) -> Dict[str, Any]:
    """
    Generates a transparent analytical answer package:
    - Plain-English executive summary
    - Explanation of SQL query construction
    - Visualization recommendation
    - Latency and data integrity metadata
    """
    row_count = len(rows)

    # Empty result
    if row_count == 0:
        return {
            "summary": "The query executed successfully but matched zero records in the dataset.",
            "sql": sql,
            "latency_ms": latency_ms,
            "row_count": 0,
            "visualization": {"chart_type": "table", "title": "Empty Result"},
            "explanation": "No records satisfied the filtering conditions in the SQL query.",
            "assumptions": ["Ensure spelling and casing of filter values match the dataset values."]
        }

    # Deterministic summary builder
    if row_count == 1 and len(columns) == 1:
        val = rows[0][0]
        formatted_val = f"{val:,.2f}" if isinstance(val, (int, float)) else str(val)
        summary = f"The computed {columns[0]} is **{formatted_val}**."
    elif row_count <= 5 and len(columns) == 2:
        items = [f"**{r[0]}**: {r[1]:,.2f}" if isinstance(r[1], (int, float)) else f"**{r[0]}**: {r[1]}" for r in rows]
        summary = f"Found {row_count} records. Top results: {', '.join(items)}."
    else:
        summary = f"Executed analytical query successfully, returning {row_count} records across {len(columns)} columns."

    # Analyze SQL for explainability
    sql_upper = sql.upper()
    aggregations = []
    if "COUNT(" in sql_upper: aggregations.append("counted occurrences")
    if "SUM(" in sql_upper: aggregations.append("aggregated totals")
    if "AVG(" in sql_upper: aggregations.append("calculated averages")
    if "MIN(" in sql_upper or "MAX(" in sql_upper: aggregations.append("computed boundary extremes (min/max)")

    filters = []
    if "WHERE" in sql_upper: filters.append("applied row-level WHERE conditions")
    if "GROUP BY" in sql_upper: filters.append("grouped observations by category")
    if "ORDER BY" in sql_upper: filters.append("sorted results for ranking")
    if "LIMIT" in sql_upper: filters.append("bounded maximum result rows")

    explanation_parts = []
    if aggregations:
        explanation_parts.append(f"The query {', '.join(aggregations)}.")
    if filters:
        explanation_parts.append(f"It {', '.join(filters)}.")
    explanation = " ".join(explanation_parts) if explanation_parts else "Queried raw dataset observations."

    assumptions = [
        "Results reflect current dataset state in DuckDB in-memory engine.",
        "Missing or null values were handled according to standard SQL semantics (ignored in aggregations)."
    ]

    visualization = recommend_visualization(columns, rows, question)

    return {
        "summary": summary,
        "sql": sql,
        "latency_ms": latency_ms,
        "row_count": row_count,
        "visualization": visualization,
        "explanation": explanation,
        "assumptions": assumptions,
        "is_fallback": is_fallback,
        "provider_name": provider_name
    }
