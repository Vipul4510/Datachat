"""
Auto-Insights and Hypothesis Discovery Service.
Generates automated exploratory analytics without requiring an LLM:
- Category breakdowns and volume leaders
- Time-series trends and growth rates
- Numeric correlation matrix with explicit non-causation caveats
- Anomaly alerts and statistical summaries
- Tailored hypothesis suggestions for user inquiry
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from core.duckdb_engine import get_connection, get_table_metadata, query_to_dataframe


def discover_auto_insights(table_id: str) -> Dict[str, Any]:
    """
    Computes statistical auto-insights from the active dataset.
    Returns:
        {
            "summary_cards": List[Dict[str, Any]],
            "category_insights": List[Dict[str, Any]],
            "correlations": List[Dict[str, Any]],
            "correlation_caveat": str,
            "temporal_insights": List[Dict[str, Any]],
            "hypotheses": List[Dict[str, str]],
            "suggested_questions": List[str]
        }
    """
    meta = get_table_metadata(table_id)
    if not meta:
        raise ValueError(f"Table '{table_id}' not found.")

    conn = get_connection()
    t_name = meta["table_name"]
    df = conn.execute(f"SELECT * FROM \"{t_name}\"").df()

    if df.empty:
        return {"summary_cards": [], "category_insights": [], "correlations": [], "hypotheses": [], "suggested_questions": []}

    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in df.columns if (pd.api.types.is_string_dtype(df[c]) or pd.api.types.is_object_dtype(df[c])) and df[c].nunique() < 50]
    date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower() or pd.api.types.is_datetime64_any_dtype(df[c])]

    summary_cards = []
    category_insights = []
    correlations = []
    temporal_insights = []
    hypotheses = []
    suggested_questions = []

    # 1. Summary Cards for primary numeric metrics
    for col in num_cols[:4]:
        clean_s = df[col].dropna()
        if len(clean_s) > 0:
            total_val = float(clean_s.sum())
            mean_val = float(clean_s.mean())
            summary_cards.append({
                "metric": col,
                "total": round(total_val, 2),
                "average": round(mean_val, 2),
                "min": round(float(clean_s.min()), 2),
                "max": round(float(clean_s.max()), 2)
            })

    # 2. Category Insights (Top contributors)
    if cat_cols and num_cols:
        primary_cat = cat_cols[0]
        primary_num = num_cols[0]
        grouped = df.groupby(primary_cat)[primary_num].sum().reset_index()
        grouped = grouped.sort_values(by=primary_num, ascending=False)
        total_sum = grouped[primary_num].sum()

        top_item = grouped.iloc[0]
        top_share = round((top_item[primary_num] / total_sum * 100), 1) if total_sum > 0 else 0

        category_insights.append({
            "title": f"Top Contributor in {primary_cat}",
            "description": f"'{top_item[primary_cat]}' accounts for {top_share}% of total {primary_num} ({top_item[primary_num]:,.2f}).",
            "category_column": primary_cat,
            "metric_column": primary_num,
            "breakdown": grouped.head(6).to_dict(orient="records")
        })

    # 3. Numeric Correlations with Strict Research Caveats
    if len(num_cols) >= 2:
        clean_num_df = df[num_cols].dropna()
        if len(clean_num_df) >= 5:
            corr_matrix = clean_num_df.corr(method="pearson")
            pairs = []
            for i in range(len(num_cols)):
                for j in range(i + 1, len(num_cols)):
                    c1, c2 = num_cols[i], num_cols[j]
                    val = corr_matrix.loc[c1, c2]
                    if not pd.isna(val) and abs(val) > 0.25:
                        pairs.append({
                            "col1": c1,
                            "col2": c2,
                            "correlation": round(float(val), 3),
                            "strength": "Strong" if abs(val) >= 0.7 else ("Moderate" if abs(val) >= 0.4 else "Weak"),
                            "direction": "Positive" if val > 0 else "Negative"
                        })
            pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
            correlations = pairs[:6]

    # 4. Temporal Insights
    if date_cols and num_cols:
        d_col = date_cols[0]
        n_col = num_cols[0]
        try:
            temp_df = df.copy()
            temp_df[d_col] = pd.to_datetime(temp_df[d_col], errors="coerce")
            temp_df = temp_df.dropna(subset=[d_col, n_col])
            if len(temp_df) > 5:
                # Group by Month-Year
                temp_df["period"] = temp_df[d_col].dt.to_period("M").astype(str)
                monthly = temp_df.groupby("period")[n_col].sum().reset_index().sort_values("period")
                if len(monthly) >= 2:
                    first_val = monthly.iloc[0][n_col]
                    last_val = monthly.iloc[-1][n_col]
                    pct_change = round(((last_val - first_val) / abs(first_val) * 100), 1) if first_val != 0 else 0.0
                    temporal_insights.append({
                        "date_column": d_col,
                        "metric_column": n_col,
                        "pct_change": pct_change,
                        "periods_count": len(monthly),
                        "description": f"Over {len(monthly)} monthly periods, total {n_col} shifted by {pct_change:+.1f}%.",
                        "trend_data": monthly.to_dict(orient="records")
                    })
        except Exception:
            pass

    # 5. Formulate Hypotheses requiring investigation
    if correlations:
        top_corr = correlations[0]
        hypotheses.append({
            "title": f"Association between {top_corr['col1']} and {top_corr['col2']}",
            "observation": f"A {top_corr['strength'].lower()} {top_corr['direction'].lower()} statistical correlation (r = {top_corr['correlation']}) was observed.",
            "hypothesis": f"Higher {top_corr['col1']} values tend to accompany higher {top_corr['col2']} values. Does an underlying driver (e.g. scale, volume, or pricing tier) influence both variables?",
            "recommendation": "Investigate confounding categorical factors before drawing causal inferences."
        })

    if category_insights:
        top_cat_insight = category_insights[0]
        hypotheses.append({
            "title": f"Concentration Risk in {top_cat_insight['category_column']}",
            "observation": top_cat_insight["description"],
            "hypothesis": "Revenue or activity may be disproportionately dependent on top segments.",
            "recommendation": "Examine margin stability across lower-volume segments to assess portfolio diversification."
        })

    # 6. Starter Analytical Questions for Chips
    if num_cols and cat_cols:
        suggested_questions.append(f"What is the total {num_cols[0]} by {cat_cols[0]}?")
        suggested_questions.append(f"Show the top 5 {cat_cols[0]} ranked by {num_cols[0]}")
    if len(num_cols) >= 2:
        suggested_questions.append(f"What is the average {num_cols[0]} and {num_cols[1]}?")
        suggested_questions.append(f"Find all records where {num_cols[0]} is greater than average")
    elif num_cols:
        suggested_questions.append(f"What is the total, minimum, and maximum {num_cols[0]}?")
        suggested_questions.append(f"How many rows exist in this dataset?")

    return {
        "summary_cards": summary_cards,
        "category_insights": category_insights,
        "correlations": correlations,
        "correlation_caveat": (
            "METHODOLOGICAL NOTE: Pearson r measures linear statistical association only. "
            "Correlation does NOT imply causality, as unobserved confounding variables or common trends may be responsible."
        ),
        "temporal_insights": temporal_insights,
        "hypotheses": hypotheses,
        "suggested_questions": suggested_questions[:4]
    }
