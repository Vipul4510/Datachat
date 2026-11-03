"""
Overview and Ingestion Page.
Provides dataset loading, file drag-and-drop, sample dataset loader,
and automated intelligence quick-start cards.
"""

import os
import streamlit as st
import pandas as pd

from core.ingestion import ingest_file, inspect_excel_sheets
from core.duckdb_engine import list_tables, get_table_metadata
from core.profiling import profile_dataset
from ui.components import render_kpi_card


def render_overview_page():
    st.markdown("## 📊 Welcome to DataChat")
    st.markdown(
        "*Trustworthy Conversational Data Analytics & Research Platform powered by in-process DuckDB.*"
    )

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("""
        <div class="dc-card">
            <h4 style="margin-top: 0; color: #38bdf8;">⚡ Research Highlights & Engine Capabilities</h4>
            <ul style="color: #cbd5e1; font-size: 0.9rem; line-height: 1.6;">
                <li><strong>Zero-Server DuckDB Engine:</strong> High-performance columnar SQL execution directly in-process.</li>
                <li><strong>SQLGlot AST Safety Guard:</strong> Rejects mutations (DDL/DML), blocks injection attacks, and bounds row limits.</li>
                <li><strong>One-Shot Self-Correction:</strong> Catches syntax and runtime errors and repairs SQL with bounded retry.</li>
                <li><strong>Provider Abstraction:</strong> Hot-swap between Groq, Google Gemini, xAI Grok, local Ollama, or Offline Fallback.</li>
                <li><strong>Transparent Analytics:</strong> Inspect exact SQL queries, execution latency, and logical justifications for every answer.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="dc-card">
            <h4 style="margin-top: 0; color: #a855f7;">📁 Load Sample Benchmark Datasets</h4>
            <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.75rem;">
                Select a verified dataset to explore immediately:
            </div>
        </div>
        """, unsafe_allow_html=True)

        samples = [
            ("Sales Orders (CSV)", "sample_data/sales_data.csv"),
            ("Department Expenses (JSON)", "sample_data/expenses.json"),
            ("Student Exam Scores (Excel)", "sample_data/student_marks.xlsx"),
            ("Sales Parquet (Parquet)", "sample_data/sales_data.parquet"),
        ]

        for label, path in samples:
            if os.path.exists(path):
                if st.button(f"Load {label}", use_container_width=True):
                    with st.spinner(f"Ingesting {label}..."):
                        try:
                            table_id, meta = ingest_file(path)
                            st.session_state["active_table_id"] = table_id
                            st.success(f"Loaded '{meta['file_name']}' successfully ({meta['row_count']} rows, {meta['column_count']} columns)!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to load sample: {str(e)}")

    st.markdown("---")
    st.markdown("### 📤 Upload Your Own Dataset")

    uploaded_file = st.file_uploader(
        "Upload CSV, TSV, Excel (.xlsx/.xls), JSON, or Parquet dataset (up to 200MB):",
        type=["csv", "tsv", "xlsx", "xls", "json", "parquet"]
    )

    if uploaded_file is not None:
        # Save temp file
        temp_dir = os.path.join(os.getcwd(), "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Handle Excel sheet selector
        sheet_to_load = None
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext in [".xlsx", ".xls"]:
            sheets = inspect_excel_sheets(temp_path)
            if len(sheets) > 1:
                sheet_to_load = st.selectbox("Select workbook sheet to analyze:", sheets)

        if st.button("🚀 Ingest & Profile Dataset", type="primary"):
            with st.spinner("Parsing format and loading into DuckDB..."):
                try:
                    table_id, meta = ingest_file(temp_path, sheet_name=sheet_to_load)
                    st.session_state["active_table_id"] = table_id
                    st.success(f"Dataset '{meta['file_name']}' loaded into DuckDB ({meta['row_count']} rows)!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ingestion error: {str(e)}")

    # Display Active Dataset Quick Profile if loaded
    active_id = st.session_state.get("active_table_id")
    if active_id:
        meta = get_table_metadata(active_id)
        if meta:
            st.markdown("---")
            st.markdown(f"### 📈 Active Dataset Profile: `{meta['file_name']}`")
            prof = profile_dataset(active_id)

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                render_kpi_card("Total Rows", f"{prof['row_count']:,}")
            with k2:
                render_kpi_card("Total Columns", f"{prof['column_count']}")
            with k3:
                render_kpi_card("Completeness", f"{prof['completeness_percentage']}%")
            with k4:
                render_kpi_card("Duplicates", f"{prof['duplicate_rows']}")

            if prof["actionable_warnings"]:
                st.markdown("##### ⚠️ Actionable Quality Observations")
                for w in prof["actionable_warnings"][:3]:
                    st.warning(f"**{w['column']}** ({w['type'].replace('_', ' ').title()}): {w['message']}")
