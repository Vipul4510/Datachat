"""
Auto-Insights and Hypothesis Discovery UI Page.
Renders automated descriptive statistics, correlation heatmaps with non-causation caveats,
time-series growth trends, and research hypothesis cards.
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from core.duckdb_engine import get_table_metadata
from core.analytics import discover_auto_insights
from ui.components import render_kpi_card


def render_auto_insights_page():
    st.markdown("## 💡 Auto-Insights & Hypothesis Discovery")
    st.markdown("*Autonomous exploratory analytics and research hypotheses generated directly from data.*")

    active_id = st.session_state.get("active_table_id")
    if not active_id:
        st.warning("⚠️ No dataset loaded. Please upload or select a dataset in the **Overview** page.")
        return

    meta = get_table_metadata(active_id)
    if not meta:
        st.error("Active dataset could not be resolved.")
        return

    insights = discover_auto_insights(active_id)

    # 1. Primary Metric Cards
    if insights["summary_cards"]:
        st.markdown("### 📌 Primary Metric Summaries")
        card_cols = st.columns(len(insights["summary_cards"]))
        for i, card in enumerate(insights["summary_cards"]):
            with card_cols[i]:
                render_kpi_card(
                    title=f"Total {card['metric']}",
                    value=f"{card['total']:,.2f}",
                    subtitle=f"Avg: {card['average']:,.2f} | Max: {card['max']:,.2f}"
                )

    st.markdown("---")

    # 2. Category Insights & Time Trends
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("### 🏆 Top Category Leaders")
        if insights["category_insights"]:
            for cat in insights["category_insights"]:
                st.markdown(f"**{cat['title']}**")
                st.caption(cat["description"])
                breakdown_df = pd.DataFrame(cat["breakdown"])
                if not breakdown_df.empty:
                    fig = px.bar(
                        breakdown_df,
                        x=cat["category_column"],
                        y=cat["metric_column"],
                        template="plotly_dark",
                        color_discrete_sequence=["#06b6d4"]
                    )
                    fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No categorical volume breakdowns found in this dataset.")

    with col_right:
        st.markdown("### 📈 Time-Series Trends")
        if insights["temporal_insights"]:
            for temp in insights["temporal_insights"]:
                st.markdown(f"**Trend in {temp['metric_column']}**")
                st.caption(temp["description"])
                trend_df = pd.DataFrame(temp["trend_data"])
                if not trend_df.empty:
                    fig = px.line(
                        trend_df,
                        x="period",
                        y=temp["metric_column"],
                        markers=True,
                        template="plotly_dark"
                    )
                    fig.update_traces(line=dict(color="#10b981", width=3))
                    fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No temporal date columns detected for time-series aggregation.")

    st.markdown("---")

    # 3. Numeric Correlations with Academic Non-Causation Caveat
    st.markdown("### 🔗 Statistical Associations & Correlations")
    st.info(f"🎓 **{insights['correlation_caveat']}**")

    if insights["correlations"]:
        corr_df = pd.DataFrame(insights["correlations"])
        corr_df.columns = ["Variable 1", "Variable 2", "Pearson r", "Strength", "Direction"]
        st.dataframe(corr_df, use_container_width=True)
    else:
        st.info("Fewer than 2 continuous numeric variables found to compute correlations.")

    st.markdown("---")

    # 4. Formulated Research Hypotheses
    st.markdown("### 🔬 Formulated Research Hypotheses")
    if insights["hypotheses"]:
        for idx, h in enumerate(insights["hypotheses"]):
            st.markdown(f"""
                <div class="dc-card">
                    <div style="font-weight: 700; color: #a855f7; font-size: 1.05rem; margin-bottom: 0.25rem;">
                        Hypothesis #{idx+1}: {h['title']}
                    </div>
                    <div style="font-size: 0.9rem; color: #cbd5e1; margin-bottom: 0.5rem;">
                        <strong>Observation:</strong> {h['observation']}
                    </div>
                    <div style="font-size: 0.9rem; color: #38bdf8; margin-bottom: 0.5rem;">
                        <strong>Candidate Hypothesis:</strong> {h['hypothesis']}
                    </div>
                    <div style="font-size: 0.85rem; color: #94a3b8;">
                        <strong>Research Guidance:</strong> {h['recommendation']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Upload a dataset with numeric and categorical dimensions to generate research hypotheses.")
