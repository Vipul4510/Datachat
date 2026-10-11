"""
Export Service for DataChat.
Generates:
1. Excel (.xlsx) workbook with Data-Quality summary, Preview data, and full Q&A chat history.
2. PDF executive report with Data-Quality score, issues table, and query history using ReportLab.
"""

import io
import pandas as pd
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch


def generate_excel_export(
    metadata: Dict[str, Any],
    quality_report: Dict[str, Any],
    chat_history: List[Dict[str, Any]]
) -> bytes:
    """Exports dataset metadata, quality analysis, and chat Q&A history to Excel."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Data Health & Summary
        summary_rows = [
            {"Metric": "Filename", "Value": metadata.get("original_filename")},
            {"Metric": "Format", "Value": metadata.get("format")},
            {"Metric": "Total Rows", "Value": quality_report.get("row_count")},
            {"Metric": "Total Columns", "Value": quality_report.get("column_count")},
            {"Metric": "Missing Cells", "Value": f"{quality_report.get('missing_cells')} ({quality_report.get('missing_cells_percentage')}%)"},
            {"Metric": "Duplicate Rows", "Value": f"{quality_report.get('duplicate_rows')} ({quality_report.get('duplicate_percentage')}%)"},
            {"Metric": "Total IQR Outliers", "Value": quality_report.get("total_iqr_outliers")},
            {"Metric": "Data Health Score", "Value": f"{quality_report.get('health_score')} / 100 ({quality_report.get('health_status')})"}
        ]
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Health Summary", index=False)

        # Sheet 2: Columns Breakdown
        if quality_report.get("columns"):
            col_df = pd.DataFrame(quality_report["columns"])
            col_df.to_excel(writer, sheet_name="Column Quality", index=False)

        # Sheet 3: Q&A History
        if chat_history:
            qa_rows = []
            for item in chat_history:
                qa_rows.append({
                    "Timestamp": item.get("timestamp", ""),
                    "Question": item.get("question", ""),
                    "Answer Summary": item.get("summary", ""),
                    "Generated SQL": item.get("sql", ""),
                    "Result Rows Count": item.get("row_count", 0)
                })
            pd.DataFrame(qa_rows).to_excel(writer, sheet_name="Q&A History", index=False)

    return output.getvalue()


def generate_pdf_export(
    metadata: Dict[str, Any],
    quality_report: Dict[str, Any],
    chat_history: List[Dict[str, Any]]
) -> bytes:
    """Exports executive report to PDF using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1e293b")
    )
    subtitle_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#64748b")
    )
    h2_style = ParagraphStyle(
        "Heading2",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )
    code_style = ParagraphStyle(
        "CodeText",
        parent=styles["Code"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0369a1")
    )

    story = []

    # Title & Header
    story.append(Paragraph("DataChat Executive Analytics Report", title_style))
    story.append(Paragraph(f"File: {metadata.get('original_filename')} | In-Process DuckDB Engine", subtitle_style))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=14))

    # Health Overview Table
    story.append(Paragraph("Data Quality & Health Overview", h2_style))
    health_data = [
        ["Metric", "Value", "Metric", "Value"],
        ["Health Score", f"{quality_report.get('health_score')}/100 ({quality_report.get('health_status')})", "Total Rows", str(quality_report.get("row_count"))],
        ["Missing Cells", f"{quality_report.get('missing_cells')} ({quality_report.get('missing_cells_percentage')}%)", "Total Columns", str(quality_report.get("column_count"))],
        ["Duplicate Rows", f"{quality_report.get('duplicate_rows')} ({quality_report.get('duplicate_percentage')}%)", "IQR Outliers", str(quality_report.get("total_iqr_outliers"))],
    ]
    t = Table(health_data, colWidths=[110, 150, 110, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0284c7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    # Column Breakdown Table
    story.append(Paragraph("Columns Specification", h2_style))
    col_table_data = [["Column Name", "Type", "Null Count", "Distinct"]]
    for c in quality_report.get("columns", [])[:12]:
        col_table_data.append([
            c["column_name"][:20],
            c["data_type"][:12],
            f"{c['null_count']} ({c['null_percentage']}%)",
            str(c["distinct_count"])
        ])
    col_t = Table(col_table_data, colWidths=[150, 120, 130, 120])
    col_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    story.append(col_t)
    story.append(Spacer(1, 16))

    # Chat Q&A History
    if chat_history:
        story.append(Paragraph("Conversational Analytics History", h2_style))
        for idx, chat in enumerate(chat_history):
            q_text = f"<b>Q{idx+1}: {chat.get('question', '')}</b>"
            a_text = f"<b>Insight:</b> {chat.get('summary', '')}"
            sql_text = f"SQL: {chat.get('sql', '')}"
            
            story.append(Paragraph(q_text, body_style))
            story.append(Spacer(1, 3))
            story.append(Paragraph(a_text, body_style))
            story.append(Spacer(1, 3))
            story.append(Paragraph(sql_text, code_style))
            story.append(Spacer(1, 8))

    doc.build(story)
    return buffer.getvalue()
