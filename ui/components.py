"""
UI Theme and Shared Reusable Components for Streamlit.
Provides professional modern styling, glassmorphic metric cards,
status indicators, and Plotly visualization wrappers.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, List, Optional


def inject_custom_styles():
    """Injects custom CSS for sleek, professional dark aesthetics."""
    st.markdown("""
        <style>
        /* Import Inter Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        code, pre {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* Glassmorphic Cards */
        .dc-card {
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid rgba(51, 65, 85, 0.6);
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
            backdrop-filter: blur(12px);
            box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4);
        }

        .dc-card-highlight {
            background: linear-gradient(135deg, rgba(14, 165, 233, 0.1) 0%, rgba(30, 41, 59, 0.7) 100%);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }

        /* Metric Badges */
        .dc-badge {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .dc-badge-emerald {
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
        }
        .dc-badge-cyan {
            background: rgba(6, 182, 212, 0.2);
            color: #22d3ee;
            border: 1px solid rgba(6, 182, 212, 0.4);
        }
        .dc-badge-amber {
            background: rgba(245, 158, 11, 0.2);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.4);
        }
        .dc-badge-rose {
            background: rgba(244, 63, 94, 0.2);
            color: #fb7185;
            border: 1px solid rgba(244, 63, 94, 0.4);
        }

        /* Chip Buttons */
        .stButton>button {
            border-radius: 8px;
            transition: all 0.15s ease-in-out;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(51, 65, 85, 0.5);
            background-color: #0b0f19;
        }
        </style>
    """, unsafe_allow_html=True)


def render_kpi_card(title: str, value: Any, subtitle: str = "", delta: Optional[str] = None):
    """Renders a styled KPI metric box."""
    delta_html = f"<span style='color: #34d399; font-size: 0.8rem; margin-left: 0.5rem;'>{delta}</span>" if delta else ""
    st.markdown(f"""
        <div class="dc-card">
            <div style="font-size: 0.75rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em;">{title}</div>
            <div style="font-size: 1.75rem; font-weight: 800; color: #f8fafc; margin-top: 0.25rem;">
                {value} {delta_html}
            </div>
            {f'<div style="font-size: 0.75rem; color: #64748b; margin-top: 0.25rem;">{subtitle}</div>' if subtitle else ''}
        </div>
    """, unsafe_allow_html=True)


def render_chart(viz_config: Dict[str, Any], columns: List[str], rows: List[List[Any]]):
    """Renders dynamic interactive Plotly chart according to recommendation."""
    chart_type = viz_config.get("chart_type", "table")
    title = viz_config.get("title", "")
    x_col = viz_config.get("x")
    y_col = viz_config.get("y")

    if not rows or not columns:
        st.info("No data available to plot.")
        return

    df = pd.DataFrame(rows, columns=columns)

    # 1. KPI Card
    if chart_type == "kpi":
        val = viz_config.get("value", df.iloc[0, 0])
        fmt = f"{val:,.2f}" if isinstance(val, (int, float)) else str(val)
        render_kpi_card(title=title, value=fmt, subtitle="Single Query Metric")
        return

    # 2. Bar Chart
    if chart_type == "bar" and x_col and y_col:
        fig = px.bar(
            df, x=x_col, y=y_col,
            title=title,
            color=y_col,
            color_continuous_scale="Viridis",
            template="plotly_dark"
        )
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        return

    # 3. Horizontal Bar Chart
    if chart_type == "horizontal_bar" and x_col and y_col:
        fig = px.bar(
            df, x=x_col, y=y_col,
            orientation="h",
            title=title,
            color=x_col,
            color_continuous_scale="Blues",
            template="plotly_dark"
        )
        fig.update_layout(height=max(400, len(df) * 28), margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        return

    # 4. Line Chart
    if chart_type == "line" and x_col and y_col:
        fig = px.line(
            df, x=x_col, y=y_col,
            markers=True,
            title=title,
            template="plotly_dark"
        )
        fig.update_traces(line=dict(width=3, color="#06b6d4"))
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        return

    # 5. Pie Chart
    if chart_type == "pie" and x_col and y_col:
        fig = px.pie(
            df, names=x_col, values=y_col,
            title=title,
            hole=0.4,
            template="plotly_dark"
        )
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        return

    # 6. Scatter Plot
    if chart_type == "scatter" and x_col and y_col:
        fig = px.scatter(
            df, x=x_col, y=y_col,
            title=title,
            trendline="ols",
            template="plotly_dark"
        )
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
        return

    # 7. Fallback Table
    st.dataframe(df, use_container_width=True, height=350)
