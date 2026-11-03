"""
Dataset Explorer Page.
Allows users to inspect raw data records, explore column-level schemas,
view distributions, and execute custom ad-hoc DuckDB SQL queries.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from core.duckdb_engine import (
    get_table_metadata,
    get_table_schema,
    query_to_dataframe,
    execute_analytical_query
)
from core.sql_validation import validate_and_format_sql


def render_explorer_page():
    st.markdown("## 🔍 Dataset Explorer")
    st.markdown("*Inspect raw records, investigate schemas, and test ad-hoc DuckDB SQL.*")

    active_id = st.session_state.get("active_table_id")
    if not active_id:
        st.warning("⚠️ No dataset loaded. Please upload or select a dataset in the **Overview** page.")
        return

    meta = get_table_metadata(active_id)
    if not meta:
        st.error("Active dataset could not be resolved.")
        return

    table_name = meta["table_name"]
    df = query_to_dataframe(f"SELECT * FROM \"{table_name}\" LIMIT 500")

    tab1, tab2, tab3 = st.tabs(["📄 Data Grid Preview", "📐 Column Schema Inspector", "⚡ Ad-Hoc SQL Sandbox"])

    # TAB 1: Data Grid
    with tab1:
        st.markdown(f"**Showing first {len(df)} rows from table `{table_name}`**")
        st.dataframe(df, use_container_width=True, height=450)

        c1, c2 = st.columns([1, 4])
        with c1:
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Export Current View (CSV)", csv_data, f"{meta['file_name']}_view.csv", "text/csv")

    # TAB 2: Column Schema Inspector
    with tab2:
        schema = get_table_schema(active_id)
        schema_df = pd.DataFrame([
            {
                "Column Name": c["column_name"],
                "Data Type": c["column_type"],
                "Null Count": c["null_count"],
                "Null %": f"{c['null_percentage']}%",
                "Distinct Values": c["distinct_count"],
                "Sample Values": ", ".join([str(v) for v in c["sample_values"][:3]])
            }
            for c in schema
        ])
        st.dataframe(schema_df, use_container_width=True, height=400)

        st.markdown("##### 📊 Single Column Distribution Inspector")
        col_names = [c["column_name"] for c in schema]
        selected_col = st.selectbox("Choose a column to plot distribution:", col_names)

        if selected_col:
            series = df[selected_col].dropna()
            if pd.api.types.is_numeric_dtype(series):
                fig = px.histogram(
                    df, x=selected_col,
                    nbins=25,
                    title=f"Histogram of {selected_col}",
                    marginal="box",
                    template="plotly_dark",
                    color_discrete_sequence=["#38bdf8"]
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                top_vals = series.value_counts().head(15).reset_index()
                top_vals.columns = [selected_col, "Count"]
                fig = px.bar(
                    top_vals, x=selected_col, y="Count",
                    title=f"Top Frequencies for {selected_col}",
                    template="plotly_dark",
                    color_discrete_sequence=["#a855f7"]
                )
                st.plotly_chart(fig, use_container_width=True)

    # TAB 3: SQL Sandbox
    with tab3:
        st.markdown(f"Execute direct SQL on table `\"{table_name}\"`:")
        default_query = f"SELECT * FROM \"{table_name}\" LIMIT 10"
        user_sql = st.text_area("SQL Query Editor:", value=default_query, height=120)

        if st.button("▶️ Execute Query", type="primary"):
            is_valid, err_msg, safe_sql = validate_and_format_sql(user_sql, allowed_tables=[table_name])
            if not is_valid:
                st.error(f"🛑 Security Guard Blocked Query: {err_msg}")
            else:
                res = execute_analytical_query(safe_sql)
                if not res["success"]:
                    st.error(f"❌ DuckDB Execution Error: {res['error']}")
                else:
                    st.success(f"Executed in {res['latency_ms']:.2f} ms | Rows: {res['row_count']}")
                    res_df = pd.DataFrame(res["rows"], columns=res["columns"])
                    st.dataframe(res_df, use_container_width=True, height=350)
