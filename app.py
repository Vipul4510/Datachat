"""
DataChat — Trustworthy Conversational Data Analytics Using DuckDB.
Master Streamlit Application Entrypoint.
"""

import os
import sys
import streamlit as st

# Ensure root directory is in sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config.settings import settings
from core.duckdb_engine import list_tables, get_table_metadata, reset_engine
from core.ingestion import ingest_file
from ai.provider_factory import resolve_provider, get_active_provider_name

from ui.components import inject_custom_styles
from ui.overview_page import render_overview_page
from ui.chat_page import render_chat_page
from ui.explorer_page import render_explorer_page
from ui.data_quality_page import render_data_quality_page
from ui.auto_insights_page import render_auto_insights_page
from ui.benchmark_page import render_benchmark_page
from ui.settings_page import render_settings_page

# Page configuration
st.set_page_config(
    page_title="DataChat — Conversational DuckDB Analytics",
    page_icon="🦆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom aesthetics
inject_custom_styles()

# Auto-load default sample if no table loaded yet
if "active_table_id" not in st.session_state:
    sample_sales = os.path.join(ROOT_DIR, "sample_data", "sales_data.csv")
    if os.path.exists(sample_sales):
        try:
            tid, _ = ingest_file(sample_sales)
            st.session_state["active_table_id"] = tid
        except Exception:
            st.session_state["active_table_id"] = None
    else:
        st.session_state["active_table_id"] = None

# Sidebar Navigation
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
            <span style="font-size: 1.8rem;">🦆</span>
            <div>
                <span style="font-size: 1.3rem; font-weight: 800; color: #f8fafc; letter-spacing: -0.02em;">DataChat</span>
                <div style="font-size: 0.7rem; color: #38bdf8; font-weight: 600; text-transform: uppercase;">Research-Grade Analytics</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Active Provider Status Badge
    active_prov, prov_status = resolve_provider()
    badge_color = "#34d399" if active_prov.is_configured() and active_prov.name != "Deterministic Fallback" else "#38bdf8"
    st.markdown(f"""
        <div style="background: rgba(15, 23, 42, 0.9); border: 1px solid rgba(51, 65, 85, 0.7); border-radius: 8px; padding: 0.5rem 0.75rem; margin-bottom: 1.25rem;">
            <div style="font-size: 0.65rem; color: #94a3b8; text-transform: uppercase; font-weight: 700;">AI Engine</div>
            <div style="font-size: 0.85rem; font-weight: 700; color: {badge_color}; margin-top: 0.1rem;">
                ● {active_prov.name}
            </div>
            <div style="font-size: 0.7rem; color: #cbd5e1; font-family: monospace;">{active_prov.model}</div>
        </div>
    """, unsafe_allow_html=True)

    # Active Dataset Selector
    loaded_tables = list_tables()
    active_id = st.session_state.get("active_table_id")

    if loaded_tables:
        options = {t["table_id"]: f"{t['file_name']} ({t['row_count']:,} rows)" for t in loaded_tables}
        default_index = list(options.keys()).index(active_id) if active_id in options else 0
        selected_table_id = st.selectbox(
            "Active Dataset:",
            options=list(options.keys()),
            format_func=lambda x: options[x],
            index=default_index
        )
        st.session_state["active_table_id"] = selected_table_id

    st.markdown("---")

    # Main Navigation
    NAV_ITEMS = [
        ("📊 Overview", "overview"),
        ("💬 Ask DataChat", "chat"),
        ("🔍 Dataset Explorer", "explorer"),
        ("🩺 Data Quality Doctor", "quality"),
        ("💡 Auto-Insights", "insights"),
        ("🔬 Research Benchmark", "benchmark"),
        ("⚙️ Settings", "settings")
    ]

    current_nav = st.session_state.get("current_nav", "chat")

    for label, nav_id in NAV_ITEMS:
        is_selected = (current_nav == nav_id)
        btn_type = "primary" if is_selected else "secondary"
        if st.button(label, key=f"nav_{nav_id}", use_container_width=True, type=btn_type):
            st.session_state["current_nav"] = nav_id
            st.rerun()

    st.markdown("---")

    # Session Reset
    if st.button("🔄 Reset Connection & Cache", use_container_width=True):
        reset_engine()
        st.session_state.clear()
        st.rerun()

    st.markdown("""
        <div style="font-size: 0.7rem; color: #64748b; text-align: center; margin-top: 1rem;">
            DataChat v2.0 • In-Process DuckDB
        </div>
    """, unsafe_allow_html=True)

# Page Routing
active_page = st.session_state.get("current_nav", "chat")

if active_page == "overview":
    render_overview_page()
elif active_page == "chat":
    render_chat_page()
elif active_page == "explorer":
    render_explorer_page()
elif active_page == "quality":
    render_data_quality_page()
elif active_page == "insights":
    render_auto_insights_page()
elif active_page == "benchmark":
    render_benchmark_page()
elif active_page == "settings":
    render_settings_page()
else:
    render_chat_page()
