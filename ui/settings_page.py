"""
Settings and AI Provider Diagnostics Page.
Allows dynamic configuration of LLM providers, model selection,
live API health probes, and timeout/retry parameters.
"""

import os
import streamlit as st
from config.settings import settings
from ai.provider_factory import (
    get_provider_diagnostics,
    set_active_provider,
    get_active_provider_name,
    get_available_providers
)


def render_settings_page():
    st.markdown("## ⚙️ Settings & Model Provider Configuration")
    st.markdown("*Configure AI model backends, test live API connectivity, and tune query constraints.*")

    tab1, tab2, tab3 = st.tabs(["🔌 Provider Connectivity & Diagnostics", "🔑 Credentials & Model Selection", "🛡️ Execution Safeguards"])

    # TAB 1: Diagnostics
    with tab1:
        st.markdown("### 📡 Live Provider Status")
        st.caption("Probe each provider to verify API keys, endpoints, and model availability:")

        current_active = get_active_provider_name()
        active_choice = st.selectbox(
            "Default Active Provider Mode:",
            ["auto", "groq", "gemini", "grok", "ollama", "fallback"],
            index=["auto", "groq", "gemini", "grok", "ollama", "fallback"].index(current_active) if current_active in ["auto", "groq", "gemini", "grok", "ollama", "fallback"] else 0,
            help="In 'auto' mode, DataChat automatically uses the first configured and healthy model backend."
        )
        if active_choice != current_active:
            set_active_provider(active_choice)
            st.success(f"Active provider updated to: **{active_choice.upper()}**")

        if st.button("🔄 Run Live Health Diagnostics"):
            with st.spinner("Probing provider endpoints..."):
                st.session_state["diag_results"] = get_provider_diagnostics()

        diagnostics = st.session_state.get("diag_results", get_provider_diagnostics())

        for diag in diagnostics:
            color = "#10b981" if diag["healthy"] else ("#f59e0b" if diag["configured"] else "#ef4444")
            icon = "🟢" if diag["healthy"] else ("🟡" if diag["configured"] else "🔴")

            st.markdown(f"""
                <div class="dc-card" style="border-left: 4px solid {color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 1.1rem; font-weight: 700; color: #f8fafc;">{icon} {diag['name']}</span>
                            <span style="font-size: 0.8rem; color: #94a3b8; margin-left: 0.75rem;">Model: <code>{diag['model']}</code></span>
                        </div>
                        <div class="dc-badge {'dc-badge-emerald' if diag['healthy'] else ('dc-badge-amber' if diag['configured'] else 'dc-badge-rose')}">
                            {'Healthy' if diag['healthy'] else ('Misconfigured / Unreachable' if diag['configured'] else 'Not Configured')}
                        </div>
                    </div>
                    <div style="font-size: 0.85rem; color: #cbd5e1; margin-top: 0.5rem;">
                        <strong>Diagnostic Status:</strong> {diag['status_message']}
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # TAB 2: Credentials and Model Selection
    with tab2:
        st.markdown("### 🔑 API Keys and Model Identifiers")
        st.caption("Update keys in runtime memory or save them to local configuration:")

        with st.form("api_keys_form"):
            st.markdown("##### 🚀 Groq (LPU Inference)")
            groq_key = st.text_input("GROQ_API_KEY", value=settings.groq_api_key, type="password")
            groq_model = st.selectbox(
                "Groq Model",
                ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
                index=0
            )

            st.markdown("---")
            st.markdown("##### ✨ Google Gemini")
            gemini_key = st.text_input("GEMINI_API_KEY", value=settings.gemini_api_key, type="password")
            gemini_model = st.selectbox(
                "Gemini Model",
                ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
                index=0
            )

            st.markdown("---")
            st.markdown("##### 🤖 xAI Grok")
            grok_key = st.text_input("XAI_API_KEY (xAI Grok)", value=settings.xai_api_key, type="password")
            grok_model = st.selectbox(
                "xAI Grok Model",
                ["grok-2-latest", "grok-beta", "grok-2-1212"],
                index=0
            )

            st.markdown("---")
            st.markdown("##### 💻 Ollama (Local Daemon)")
            ollama_url = st.text_input("OLLAMA_BASE_URL", value=settings.ollama_base_url)
            ollama_model = st.text_input("Ollama Model", value=settings.ollama_model)

            save_btn = st.form_submit_button("💾 Save Credentials & Reload")

            if save_btn:
                # Update environment variables
                if groq_key: os.environ["GROQ_API_KEY"] = groq_key.strip()
                if groq_model: os.environ["GROQ_MODEL"] = groq_model.strip()
                if gemini_key: os.environ["GEMINI_API_KEY"] = gemini_key.strip()
                if gemini_model: os.environ["GEMINI_MODEL"] = gemini_model.strip()
                if grok_key: os.environ["XAI_API_KEY"] = grok_key.strip()
                if grok_model: os.environ["XAI_MODEL"] = grok_model.strip()
                if ollama_url: os.environ["OLLAMA_BASE_URL"] = ollama_url.strip()
                if ollama_model: os.environ["OLLAMA_MODEL"] = ollama_model.strip()

                settings.reload()
                st.session_state["diag_results"] = get_provider_diagnostics()
                st.success("Credentials saved to environment. Providers refreshed!")
                st.rerun()

    # TAB 3: Execution Safeguards
    with tab3:
        st.markdown("### 🛡️ Analytical Safeguards & Resource Limits")
        st.caption("Configure query execution bounding rules enforced by SQLGlot and DuckDB:")

        max_rows = st.slider("Maximum Query Result Rows (LIMIT)", min_value=50, max_value=2000, value=settings.max_row_limit, step=50)
        max_retries = st.slider("Self-Correction Retries (Bounded Loop)", min_value=0, max_value=3, value=settings.max_retries, step=1)
        timeout_sec = st.slider("Execution Timeout (Seconds)", min_value=5.0, max_value=60.0, value=settings.query_timeout_seconds, step=5.0)

        if st.button("Apply Guardrail Settings"):
            os.environ["MAX_ROW_LIMIT"] = str(max_rows)
            os.environ["MAX_RETRIES"] = str(max_retries)
            os.environ["QUERY_TIMEOUT_SECONDS"] = str(timeout_sec)
            settings.reload()
            st.success("Guardrail parameters updated.")
