"""
Ask DataChat - Conversational Multi-Turn Analytics Page.
Features conversational memory, starter prompt chips, explainable answer drawers,
interactive SQL execution, and automatic visualization rendering.
"""

import streamlit as st
import pandas as pd

from core.duckdb_engine import get_table_metadata, execute_analytical_query
from core.analytics import discover_auto_insights
from ai.sql_generator import generate_and_execute_sql
from ai.answer_generator import generate_transparent_answer
from ai.provider_factory import get_active_provider_name, resolve_provider
from ui.components import render_chart, render_kpi_card


def render_chat_page():
    st.markdown("## 💬 Ask DataChat")
    st.markdown("*Ask analytical questions in plain English. Queries execute directly on DuckDB.*")

    active_id = st.session_state.get("active_table_id")
    if not active_id:
        st.warning("⚠️ No dataset currently loaded. Please load a sample or upload a file in the **Overview** page first.")
        return

    meta = get_table_metadata(active_id)
    if not meta:
        st.error("Active dataset metadata could not be resolved.")
        return

    provider, prov_status = resolve_provider()

    # Active provider banner
    st.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(71, 85, 105, 0.4); border-radius: 8px; padding: 0.5rem 1rem; margin-bottom: 1rem; font-size: 0.8rem; display: flex; justify-content: space-between; align-items: center;">
            <span>Dataset: <strong>{meta['file_name']}</strong> ({meta['row_count']:,} rows)</span>
            <span>Active Engine: <strong style="color: #38bdf8;">{provider.name} ({provider.model})</strong></span>
        </div>
    """, unsafe_allow_html=True)

    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Starter question chips if chat is empty
    if not st.session_state["chat_history"]:
        insights = discover_auto_insights(active_id)
        suggested = insights.get("suggested_questions", [])
        if suggested:
            st.markdown("##### 💡 Suggested Analytical Questions (Click to Ask):")
            chip_cols = st.columns(len(suggested))
            for i, q_text in enumerate(suggested):
                with chip_cols[i]:
                    if st.button(q_text, key=f"chip_{i}", use_container_width=True):
                        st.session_state["pending_question"] = q_text
                        st.rerun()

    # Render previous messages
    for idx, msg in enumerate(st.session_state["chat_history"]):
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.write(msg["content"])
            else:
                st.markdown(msg["summary"])

                # Render Chart
                if "visualization" in msg and "columns" in msg and "rows" in msg:
                    render_chart(msg["visualization"], msg["columns"], msg["rows"])

                # Render Table if multiple rows
                if len(msg.get("rows", [])) > 1:
                    df = pd.DataFrame(msg["rows"], columns=msg["columns"])
                    with st.expander(f"📋 View Tabular Data ({len(df)} rows)", expanded=False):
                        st.dataframe(df, use_container_width=True, height=250)
                        csv = df.to_csv(index=False).encode("utf-8")
                        st.download_button("📥 Download CSV", csv, f"result_{idx}.csv", "text/csv", key=f"dl_{idx}")

                # Explainability Drawer: "How did DataChat get this answer?"
                with st.expander("🔍 How did DataChat get this answer?", expanded=False):
                    st.markdown(f"**Query Logic:** {msg.get('explanation', 'N/A')}")
                    st.code(msg.get("sql", "-- No SQL"), language="sql")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.caption(f"⚡ Latency: **{msg.get('latency_ms', 0):.2f} ms**")
                    with c2:
                        st.caption(f"📊 Rows Returned: **{msg.get('row_count', 0)}**")
                    with c3:
                        st.caption(f"🤖 Provider: **{msg.get('provider_name', 'AI Engine')}**")

                    if msg.get("assumptions"):
                        st.markdown("**Assumptions & Caveats:**")
                        for a in msg["assumptions"]:
                            st.caption(f"- {a}")

    # Chat Input
    prompt = st.chat_input("Ask a question about your data (e.g. 'What is the total revenue by region?')...")
    pending = st.session_state.pop("pending_question", None)
    user_query = pending or prompt

    if user_query:
        # Append user message
        st.session_state["chat_history"].append({"role": "user", "content": user_query})

        with st.chat_message("assistant"):
            with st.spinner("Analyzing schema, generating DuckDB SQL, and executing..."):
                # Execute NL to SQL
                res = generate_and_execute_sql(
                    table_id=active_id,
                    table_name=meta["table_name"],
                    question=user_query,
                    chat_history=st.session_state["chat_history"]
                )

                if not res["success"]:
                    st.error(f"❌ Could not execute analytical query: {res['error']}")
                    if res.get("sql"):
                        st.code(res["sql"], language="sql")
                    st.session_state["chat_history"].append({
                        "role": "assistant",
                        "summary": f"Query execution failed: {res['error']}",
                        "sql": res.get("sql", ""),
                        "explanation": "Query validation or execution error.",
                        "latency_ms": 0.0,
                        "row_count": 0,
                        "columns": [],
                        "rows": []
                    })
                else:
                    ans = generate_transparent_answer(
                        question=user_query,
                        sql=res["sql"],
                        columns=res["columns"],
                        rows=res["rows"],
                        latency_ms=res["latency_ms"],
                        is_fallback=res.get("is_fallback", False),
                        provider_name=res.get("provider_name", "AI Engine")
                    )

                    st.markdown(ans["summary"])
                    render_chart(ans["visualization"], res["columns"], res["rows"])

                    # Store in chat history
                    st.session_state["chat_history"].append({
                        "role": "assistant",
                        "summary": ans["summary"],
                        "sql": res["sql"],
                        "visualization": ans["visualization"],
                        "columns": res["columns"],
                        "rows": res["rows"],
                        "latency_ms": res["latency_ms"],
                        "row_count": res["row_count"],
                        "explanation": ans["explanation"],
                        "assumptions": ans["assumptions"],
                        "provider_name": res.get("provider_name", "AI Engine")
                    })
                    st.rerun()

    # Clear chat option
    if st.session_state["chat_history"]:
        if st.button("🗑️ Clear Conversation History"):
            st.session_state["chat_history"] = []
            st.rerun()
