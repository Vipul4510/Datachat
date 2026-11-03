"""
Data Quality Doctor UI Page.
Comprehensive data quality auditing, calibrated health scoring,
explainable cleaning transformations with preview, undo stack, and cleaned exports.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from core.duckdb_engine import get_table_metadata
from core.data_quality import (
    evaluate_data_health,
    preview_cleaning_operation,
    apply_cleaning_operation,
    undo_last_operation,
    revert_to_original,
    export_cleaned_dataset,
    can_undo
)
from ui.components import render_kpi_card


def render_data_quality_page():
    st.markdown("## 🩺 Data Quality Doctor")
    st.markdown("*Audit dataset health, detect multivariate anomalies, and safely repair data issues.*")

    active_id = st.session_state.get("active_table_id")
    if not active_id:
        st.warning("⚠️ No dataset loaded. Please upload or select a dataset in the **Overview** page.")
        return

    meta = get_table_metadata(active_id)
    if not meta:
        st.error("Active dataset could not be resolved.")
        return

    # Evaluate current data health
    with st.spinner("Calculating calibrated health scores and anomaly distributions..."):
        report = evaluate_data_health(active_id)

    # Top KPI Bar
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_kpi_card(
            title="Health Score",
            value=f"{report['health_score']}/100",
            subtitle=f"Rating: {report['status']}"
        )
    with k2:
        render_kpi_card(
            title="Total Rows",
            value=f"{report['total_rows']:,}",
            subtitle=f"Columns: {report['total_cols']}"
        )
    with k3:
        render_kpi_card(
            title="Missing Cells",
            value=f"{report['missing_cells']:,}",
            subtitle=f"{report['missing_percentage']}% of cells"
        )
    with k4:
        render_kpi_card(
            title="Duplicate Rows",
            value=f"{report['duplicate_rows']:,}",
            subtitle=f"{report['duplicate_percentage']}% duplicates"
        )
    with k5:
        render_kpi_card(
            title="IQR Outliers",
            value=f"{report['total_iqr_outliers']:,}",
            subtitle="1.5x IQR Rule"
        )

    # Export & Undo Actions Bar
    c_act1, c_act2, c_act3 = st.columns([2, 1, 1])
    with c_act1:
        st.caption("Active Snapshot Actions:")
    with c_act2:
        if can_undo(active_id):
            if st.button("↩️ Undo Last Clean", type="secondary", use_container_width=True):
                new_rep, desc = undo_last_operation(active_id)
                st.success(desc)
                st.rerun()
    with c_act3:
        if st.button("🔄 Restore Original", use_container_width=True):
            new_rep, desc = revert_to_original(active_id)
            st.info(desc)
            st.rerun()

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["🛠️ Interactive Cleaning Lab", "📊 Missingness & Anomalies", "💾 Download Cleaned Data"])

    # TAB 1: Interactive Cleaning Lab
    with tab1:
        st.markdown("### 🧹 Safe & Explainable Transformations")
        st.markdown("Preview the exact impact before applying changes to DuckDB:")

        action_type = st.selectbox(
            "Select Cleaning Operation:",
            [
                ("remove_duplicates", "1. Remove Duplicate Rows"),
                ("fill_missing", "2. Impute Missing Values (Mean / Median / Mode / Constant)"),
                ("handle_outliers", "3. Handle IQR Outliers (Clip / Cap to Bounds)"),
                ("strip_text", "4. Trim Text Whitespace & Clean Strings"),
                ("drop_missing", "5. Drop Incomplete Rows (Strict Filtering)")
            ],
            format_func=lambda x: x[1]
        )[0]

        params = {}
        if action_type == "fill_missing":
            col_opts = ["All Columns"] + [c["name"] for c in report["column_metrics"] if c["null_count"] > 0]
            selected_c = st.selectbox("Select Target Column:", col_opts)
            if selected_c != "All Columns":
                params["column"] = selected_c
            strategy = st.radio("Imputation Strategy:", ["mean", "median", "mode", "zero"], horizontal=True)
            params["strategy"] = strategy

        elif action_type == "handle_outliers":
            method = st.radio("Outlier Strategy:", [("clip", "Clip/Clamp to IQR Bounds (Preserves rows)"), ("drop", "Drop Outlier Rows")], format_func=lambda x: x[1])
            params["method"] = method[0]

        # Calculate Preview
        preview = preview_cleaning_operation(active_id, action_type, params)

        p_col1, p_col2 = st.columns([2, 1])
        with p_col1:
            st.markdown(f"""
                <div class="dc-card">
                    <div style="font-weight: 700; color: #38bdf8; margin-bottom: 0.5rem;">Proposed Action Details</div>
                    <div style="font-size: 0.9rem; color: #cbd5e1; margin-bottom: 0.75rem;">{preview['description']}</div>
                    <div style="font-size: 0.85rem; color: #94a3b8;">
                        • Records Affected: <strong>{preview['affected_records']}</strong><br/>
                        • Row Count: <strong>{preview['rows_before']}</strong> → <strong>{preview['rows_after']}</strong><br/>
                        • Missing Cells: <strong>{preview['missing_before']}</strong> → <strong>{preview['missing_after']}</strong>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with p_col2:
            st.write("")
            st.write("")
            if preview["affected_records"] == 0:
                st.info("No records match this operation's criteria.")
            else:
                if st.button("✅ Apply Transformation", type="primary", use_container_width=True):
                    with st.spinner("Applying cleaning operation in DuckDB..."):
                        new_rep, desc = apply_cleaning_operation(active_id, action_type, params)
                        st.success(f"Successfully applied: {desc}")
                        st.rerun()

        if preview["preview_sample"]:
            st.markdown("##### 🔍 Preview of Cleaned Rows (First 5 records):")
            st.dataframe(pd.DataFrame(preview["preview_sample"]), use_container_width=True)

    # TAB 2: Missingness & Anomaly Inspection
    with tab2:
        st.markdown("### 📊 Column Health Breakdown")
        col_df = pd.DataFrame(report["column_metrics"])
        st.dataframe(col_df, use_container_width=True, height=280)

        # Missing values bar chart
        missing_cols = col_df[col_df["null_count"] > 0]
        if not missing_cols.empty:
            st.markdown("##### 📉 Missing Value Percentages by Column")
            fig = px.bar(
                missing_cols, x="name", y="null_percentage",
                title="Missing Value Percentage (%)",
                color="null_percentage",
                color_continuous_scale="Reds",
                template="plotly_dark"
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("🎉 Zero missing values detected across all columns!")

        # Isolation forest report
        iso = report.get("isolation_forest_anomalies", {})
        st.markdown("##### 🌲 Multivariate Isolation Forest Anomaly Detection")
        st.markdown(
            f"Isolation Forest identified **{iso.get('anomaly_count', 0)}** multivariate anomalies "
            f"({iso.get('anomaly_percentage', 0.0)}% contamination level across numeric dimensions)."
        )

    # TAB 3: Export Cleaned Dataset
    with tab3:
        st.markdown("### 💾 Export Cleaned Dataset")
        st.markdown("Download your cleaned, imputed, and transformed dataset for downstream analytics:")

        d_col1, d_col2 = st.columns(2)
        with d_col1:
            csv_bytes, c_mime, c_name = export_cleaned_dataset(active_id, "csv")
            st.download_button(
                label=f"📥 Download Cleaned CSV ({meta['file_name']})",
                data=csv_bytes,
                file_name=c_name,
                mime=c_mime,
                use_container_width=True
            )

        with d_col2:
            xlsx_bytes, x_mime, x_name = export_cleaned_dataset(active_id, "xlsx")
            st.download_button(
                label=f"📥 Download Cleaned Excel (.xlsx)",
                data=xlsx_bytes,
                file_name=x_name,
                mime=x_mime,
                use_container_width=True
            )
