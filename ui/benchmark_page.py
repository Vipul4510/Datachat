"""
Research Benchmark and Academic Evaluation Dashboard.
Runs controlled evaluations across representative analytical question categories,
computes empirical accuracy against ground-truth reference SQL, measures latency,
and exports benchmark findings.
"""

import streamlit as st
import pandas as pd
import json

from research.benchmark_questions import BENCHMARK_QUESTIONS
from research.evaluation import run_benchmark_evaluation
from ai.provider_factory import get_available_providers, get_active_provider_name
from ui.components import render_kpi_card


def render_benchmark_page():
    st.markdown("## 🔬 Academic Evaluation & SQL Generation Benchmark")
    st.markdown(
        "*Empirical evaluation of LLM NL-to-SQL performance against verified DuckDB reference queries.*"
    )

    st.markdown("""
        <div class="dc-card">
            <h4 style="margin-top: 0; color: #38bdf8;">📐 Evaluation Methodology & Rigor</h4>
            <div style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.6;">
                This benchmark evaluates NL-to-SQL models on 20 curated analytical questions across 8 distinct categories:
                <strong>Filtering & Sorting, Aggregation & Grouping, Top-N Queries, Date-Based Analysis, Conditional Aggregations, Null-Value Handling, Multi-Metric Calculations,</strong> and <strong>Ambiguous / Complex Reasoning</strong>.
                <br/><br/>
                Unlike superficial tests that merely check if SQL syntax looks plausible, DataChat executes both the candidate query and the verified reference query against the identical DuckDB table, comparing actual result DataFrames with numerical tolerances.
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Provider and Question limit selectors
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        prov_options = ["Auto (Active Provider)", "fallback", "groq", "gemini", "grok", "ollama"]
        chosen_prov = st.selectbox(
            "Select Evaluation Target:",
            prov_options,
            format_func=lambda x: f"Provider: {x.title()}"
        )
        prov_arg = None if "Auto" in chosen_prov else chosen_prov
    with c2:
        q_limit = st.selectbox("Sample Size:", [20, 10, 5], format_func=lambda x: f"{x} Questions")
    with c3:
        st.write("")
        st.write("")
        run_btn = st.button("🚀 Run Live Benchmark", type="primary", use_container_width=True)

    # State storage for evaluation results
    if run_btn:
        with st.spinner("Executing benchmark suite against DuckDB in-process engine..."):
            res = run_benchmark_evaluation(
                provider_name=prov_arg,
                questions_limit=q_limit
            )
            st.session_state["benchmark_results"] = res
            st.success(f"Completed evaluation of {res['total_questions']} questions!")

    # Display results
    eval_data = st.session_state.get("benchmark_results")
    if eval_data:
        st.markdown("---")
        st.markdown(f"### 📊 Benchmark Scorecard: `{eval_data['provider_evaluated'].upper()}`")

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            render_kpi_card(
                title="Execution Accuracy",
                value=f"{eval_data['accuracy_percentage']}%",
                subtitle="Exact match with reference query"
            )
        with k2:
            render_kpi_card(
                title="Execution Success",
                value=f"{eval_data['execution_success_percentage']}%",
                subtitle="Ran on DuckDB without syntax error"
            )
        with k3:
            render_kpi_card(
                title="Median Latency",
                value=f"{eval_data['median_latency_seconds']:.3f}s",
                subtitle=f"Mean: {eval_data['mean_latency_seconds']:.3f}s"
            )
        with k4:
            render_kpi_card(
                title="Self-Correction Recoveries",
                value=f"{eval_data['recovery_count']}",
                subtitle=f"Total retries: {eval_data['total_retries']}"
            )

        # Performance by Category Table
        st.markdown("##### 📈 Performance Breakdown by Question Category")
        cat_rows = []
        for cat, stats in eval_data["category_performance"].items():
            tot = stats["total"]
            acc = stats["accurate"]
            acc_p = round((acc / tot * 100), 1) if tot > 0 else 0.0
            cat_rows.append({
                "Category": cat,
                "Questions": tot,
                "Executed Successfully": stats["executed"],
                "Accurate vs Ground Truth": acc,
                "Accuracy Rate": f"{acc_p}%"
            })
        st.dataframe(pd.DataFrame(cat_rows), use_container_width=True)

        # Detailed Question-Level Results
        with st.expander("🔍 Detailed Question-Level Log & SQL Inspection", expanded=True):
            det_df = pd.DataFrame(eval_data["detailed_results"])
            st.dataframe(
                det_df[["id", "category", "question", "accurate", "executed", "latency_s", "retries"]],
                use_container_width=True
            )

        # Export Report
        st.markdown("##### 📥 Export Research Benchmark Results")
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            json_str = json.dumps(eval_data, indent=2)
            st.download_button(
                label="Download Full Benchmark JSON",
                data=json_str,
                file_name=f"datachat_benchmark_{eval_data['provider_evaluated']}.json",
                mime="application/json",
                use_container_width=True
            )
        with exp_col2:
            csv_str = pd.DataFrame(eval_data["detailed_results"]).to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Detailed CSV Log",
                data=csv_str,
                file_name=f"datachat_benchmark_{eval_data['provider_evaluated']}.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.info("Click **Run Live Benchmark** to execute the evaluation suite and compute real empirical performance metrics.")
