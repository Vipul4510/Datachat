"""
DataChat API Routers.
Endpoints:
- POST /upload: Upload file (CSV, TSV, Excel, JSON, Parquet), get table id, schema, and quality report
- POST /ask: Query with natural language, get SQL, tabular rows, plain-English summary, and suggested chart
- GET /report/{id}?format=pdf|xlsx: Export quality report and Q&A history
- GET /health: Health check endpoint
"""

import os
import shutil
import tempfile
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Response
from pydantic import BaseModel

from backend.services.loader import (
    load_file_into_duckdb,
    get_table_metadata,
    get_excel_sheets,
    MAX_FILE_SIZE_BYTES
)
from backend.services.quality import generate_quality_report
from backend.services.llm import (
    run_nl_query_with_self_correction,
    generate_suggested_questions
)
from backend.services.charts import suggest_chart
from backend.services.export import generate_excel_export, generate_pdf_export
from backend.services.cleaner import (
    apply_cleaning_actions,
    undo_cleaning,
    is_cleaning_request,
    parse_cleaning_intent,
    export_cleaned_dataset,
    can_undo
)

router = APIRouter()

# In-memory session store for chat histories per table: {table_id: [chat_item, ...]}
_table_chat_histories: Dict[str, List[Dict[str, Any]]] = {}
_table_quality_reports: Dict[str, Dict[str, Any]] = {}


class AskRequest(BaseModel):
    table_id: str
    question: str
    chat_history: Optional[List[Dict[str, str]]] = None


class CleanRequest(BaseModel):
    table_id: str
    action: str = "auto_clean"
    params: Optional[Dict[str, Any]] = None


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "DataChat API", "duckdb": "in-process"}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None)
):
    """
    Accepts file upload (CSV, TSV, XLSX, XLS, JSON, Parquet), creates in-memory DuckDB table,
    computes auto data-quality report and 4 starter question suggestions.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file has no filename.")

    ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = [".csv", ".tsv", ".xlsx", ".xls", ".json", ".parquet"]
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(allowed_exts)}"
        )

    # Save to temp file securely to process with DuckDB
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        temp_path = temp_file.name
        content = await file.read()
        if len(content) == 0:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")
        if len(content) > MAX_FILE_SIZE_BYTES:
            os.remove(temp_path)
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum allowed size of 200 MB."
            )
        temp_file.write(content)

    try:
        # Load into DuckDB
        table_id, metadata = load_file_into_duckdb(
            file_path=temp_path,
            sheet_name=sheet_name
        )
        metadata["original_filename"] = file.filename

        # Generate data quality report
        quality_report = generate_quality_report(table_id, run_isolation_forest=True)
        _table_quality_reports[table_id] = quality_report
        _table_chat_histories[table_id] = []

        # Generate suggested questions via LLM
        suggested_questions = generate_suggested_questions(
            table_name=metadata["table_name"],
            schema=metadata["schema"]
        )

        return {
            "status": "success",
            "table_id": table_id,
            "metadata": metadata,
            "quality_report": quality_report,
            "suggested_questions": suggested_questions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@router.post("/ask")
async def ask_question(request: AskRequest):
    """
    Processes natural language question:
    1. If cleaning request: executes data cleaning, updates DuckDB table, recomputes health score,
       and provides download link for cleaned dataset.
    2. If analytical query: enforces SQL safety guard, executes on DuckDB, handles self-correction,
       and returns conversational answer + table + chart.
    """
    table_meta = get_table_metadata(request.table_id)
    if not table_meta:
        raise HTTPException(status_code=404, detail=f"Table ID '{request.table_id}' not found.")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Check if the user is asking to clean data
    if is_cleaning_request(request.question):
        action, params = parse_cleaning_intent(request.question, table_meta["schema"])
        clean_result = apply_cleaning_actions(request.table_id, action, params)
        _table_quality_reports[request.table_id] = clean_result["quality_report"]

        score_before = clean_result["initial_health_score"]
        score_after = clean_result["final_health_score"]
        diff = clean_result["score_improvement"]
        diff_str = f"(+{diff} pts 🎉)" if diff > 0 else ("(no score change)" if diff == 0 else f"({diff} pts)")
        changes_bullets = "\n".join([f"• {c}" for c in clean_result["changes"]])

        summary = (
            f"🧹 **Data Cleaning Applied Successfully!**\n\n"
            f"{changes_bullets}\n\n"
            f"📈 **Data Health Score:** {score_before}/100 ➔ **{score_after}/100** {diff_str}\n"
            f"• Rows: {clean_result['rows_before']} ➔ {clean_result['rows_after']}\n"
            f"• Missing cells remaining: {clean_result['missing_cells_remaining']}\n"
            f"• Duplicates remaining: {clean_result['duplicate_rows_remaining']}\n"
            f"• Outliers remaining: {clean_result['outliers_remaining']}\n\n"
            f"Your in-memory dataset is now updated! You can download the cleaned file below or continue chatting."
        )

        history_entry = {
            "question": request.question,
            "sql": f"-- Cleaned data using action '{action}'",
            "summary": summary,
            "columns": [c["column_name"] for c in clean_result["metadata"]["schema"]],
            "row_count": clean_result["rows_after"],
            "success": True,
            "chart": {"type": "none"}
        }
        if request.table_id not in _table_chat_histories:
            _table_chat_histories[request.table_id] = []
        _table_chat_histories[request.table_id].append(history_entry)

        return {
            "status": "success",
            "question": request.question,
            "sql": f"-- Cleaned dataset via {action.replace('_', ' ').title()}",
            "summary": summary,
            "columns": [c["column_name"] for c in clean_result["metadata"]["schema"]],
            "rows": [],
            "row_count": clean_result["rows_after"],
            "chart": {"type": "none"},
            "retries": 0,
            "is_cleaning": True,
            "cleaning_details": clean_result,
            "quality_report": clean_result["quality_report"],
            "metadata": clean_result["metadata"]
        }

    # Retrieve existing chat history for conversational follow-ups
    session_history = _table_chat_histories.get(request.table_id, [])
    # Merge client passed history if available
    combined_history = request.chat_history or [
        {"role": "user", "content": h["question"]} for h in session_history
    ]

    # Execute NL to SQL with self-correction
    result = run_nl_query_with_self_correction(
        table_id=request.table_id,
        question=request.question,
        chat_history=combined_history,
        table_metadata=table_meta
    )

    chart_info = {"type": "none"}
    if result.get("success") and result.get("columns") and result.get("rows"):
        chart_info = suggest_chart(result["columns"], result["rows"])

    # Record in history
    history_entry = {
        "question": request.question,
        "sql": result.get("sql", ""),
        "summary": result.get("summary", ""),
        "columns": result.get("columns", []),
        "row_count": result.get("row_count", 0),
        "success": result.get("success", False),
        "chart": chart_info
    }
    if request.table_id not in _table_chat_histories:
        _table_chat_histories[request.table_id] = []
    _table_chat_histories[request.table_id].append(history_entry)

    return {
        "status": "success" if result.get("success") else "error",
        "question": request.question,
        "sql": result.get("sql"),
        "summary": result.get("summary"),
        "columns": result.get("columns", []),
        "rows": result.get("rows", []),
        "row_count": result.get("row_count", 0),
        "chart": chart_info,
        "retries": result.get("retries", 0),
        "error": result.get("error")
    }


@router.post("/clean")
async def clean_data(request: CleanRequest):
    """
    Executes a specific cleaning action (auto_clean, remove_duplicates, fill_missing, drop_missing, handle_outliers),
    updates the in-process DuckDB table, recomputes health metrics, and returns the updated report.
    """
    table_meta = get_table_metadata(request.table_id)
    if not table_meta:
        raise HTTPException(status_code=404, detail=f"Table ID '{request.table_id}' not found.")

    clean_result = apply_cleaning_actions(request.table_id, request.action, request.params)
    _table_quality_reports[request.table_id] = clean_result["quality_report"]

    score_before = clean_result["initial_health_score"]
    score_after = clean_result["final_health_score"]
    diff = clean_result["score_improvement"]
    diff_str = f"(+{diff} pts 🎉)" if diff > 0 else ("(no change)" if diff == 0 else f"({diff} pts)")
    changes_bullets = "\n".join([f"• {c}" for c in clean_result["changes"]])

    summary = (
        f"🧹 **Data Cleaning Applied ({request.action.replace('_', ' ').title()})**\n\n"
        f"{changes_bullets}\n\n"
        f"📈 **Data Health Score:** {score_before}/100 ➔ **{score_after}/100** {diff_str}"
    )

    history_entry = {
        "question": f"Clean dataset ({request.action})",
        "sql": f"-- Cleaned data using action '{request.action}'",
        "summary": summary,
        "columns": [c["column_name"] for c in clean_result["metadata"]["schema"]],
        "row_count": clean_result["rows_after"],
        "success": True,
        "chart": {"type": "none"}
    }
    if request.table_id not in _table_chat_histories:
        _table_chat_histories[request.table_id] = []
    _table_chat_histories[request.table_id].append(history_entry)

    return {
        "status": "success",
        "is_cleaning": True,
        "cleaning_details": clean_result,
        "quality_report": clean_result["quality_report"],
        "metadata": clean_result["metadata"],
        "summary": summary
    }


@router.post("/clean/undo")
async def undo_clean(request: Dict[str, str]):
    """Undoes the previous cleaning action, restoring previous snapshot."""
    table_id = request.get("table_id")
    if not table_id:
        raise HTTPException(status_code=400, detail="table_id is required")
    try:
        new_report, message = undo_cleaning(table_id)
        _table_quality_reports[table_id] = new_report
        new_meta = get_table_metadata(table_id)
        return {
            "status": "success",
            "message": message,
            "quality_report": new_report,
            "metadata": new_meta,
            "can_undo": can_undo(table_id)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export/cleaned/{table_id}")
def export_cleaned(
    table_id: str,
    format: str = Query("xlsx", pattern="^(xlsx|csv|json)$")
):
    """Downloads cleaned dataset file as Excel (.xlsx), CSV, or JSON."""
    try:
        content, media_type, filename = export_cleaned_dataset(table_id, format)
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/report/{table_id}")
def export_report(
    table_id: str,
    format: str = Query("xlsx", pattern="^(pdf|xlsx)$")
):
    """
    Exports data-quality report and full Q&A conversational history as PDF or Excel.
    """
    table_meta = get_table_metadata(table_id)
    if not table_meta:
        raise HTTPException(status_code=404, detail=f"Table ID '{table_id}' not found.")

    quality_report = _table_quality_reports.get(table_id)
    if not quality_report:
        quality_report = generate_quality_report(table_id)
        _table_quality_reports[table_id] = quality_report

    chat_history = _table_chat_histories.get(table_id, [])

    if format.lower() == "xlsx":
        content = generate_excel_export(table_meta, quality_report, chat_history)
        filename = f"datachat_report_{table_meta['original_filename']}.xlsx"
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
    else:
        content = generate_pdf_export(table_meta, quality_report, chat_history)
        filename = f"datachat_report_{table_meta['original_filename']}.pdf"
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
