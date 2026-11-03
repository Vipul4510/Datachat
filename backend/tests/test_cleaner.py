"""Unit tests for Data Cleaning Service & Endpoints."""

import os
import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.loader import load_file_into_duckdb, reset_connection, get_table_metadata
from backend.services.cleaner import (
    apply_cleaning_actions,
    undo_cleaning,
    is_cleaning_request,
    parse_cleaning_intent,
    export_cleaned_dataset,
    can_undo
)

client = TestClient(app)
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sample_data")


@pytest.fixture(autouse=True)
def setup_teardown():
    reset_connection()
    yield
    reset_connection()


def test_clean_duplicates_and_health_score_increase():
    # Load dataset
    csv_path = os.path.join(SAMPLE_DIR, "sales_data.csv")
    table_id, meta = load_file_into_duckdb(csv_path)

    # sales_data.csv has 1 duplicate row and 10 missing cells
    res = apply_cleaning_actions(table_id, "remove_duplicates")
    assert res["success"] is True
    assert res["duplicate_rows_remaining"] == 0
    assert res["rows_after"] < res["rows_before"]
    assert res["final_health_score"] >= res["initial_health_score"]


def test_auto_clean_maximizes_health():
    csv_path = os.path.join(SAMPLE_DIR, "sales_data.csv")
    table_id, meta = load_file_into_duckdb(csv_path)

    res = apply_cleaning_actions(table_id, "auto_clean")
    assert res["success"] is True
    assert res["duplicate_rows_remaining"] == 0
    assert res["missing_cells_remaining"] == 0
    assert res["final_health_score"] > res["initial_health_score"]
    assert res["final_health_score"] >= 95


def test_undo_cleaning():
    csv_path = os.path.join(SAMPLE_DIR, "sales_data.csv")
    table_id, meta = load_file_into_duckdb(csv_path)

    initial_rows = meta["row_count"]
    # Clean duplicates
    apply_cleaning_actions(table_id, "remove_duplicates")
    assert can_undo(table_id) is True

    # Undo
    restored_report, msg = undo_cleaning(table_id)
    assert restored_report["row_count"] == initial_rows
    assert restored_report["duplicate_rows"] > 0


def test_export_cleaned_files():
    csv_path = os.path.join(SAMPLE_DIR, "sales_data.csv")
    table_id, meta = load_file_into_duckdb(csv_path)

    apply_cleaning_actions(table_id, "auto_clean")

    # Export CSV
    csv_bytes, media, filename = export_cleaned_dataset(table_id, format="csv")
    assert media.startswith("text/csv")
    assert filename.endswith(".csv")
    assert len(csv_bytes) > 0

    # Export Excel
    xlsx_bytes, media, filename = export_cleaned_dataset(table_id, format="xlsx")
    assert "openxmlformats" in media
    assert filename.endswith(".xlsx")
    assert len(xlsx_bytes) > 0


def test_api_clean_endpoint():
    with open(os.path.join(SAMPLE_DIR, "sales_data.csv"), "rb") as f:
        upload_resp = client.post("/upload", files={"file": ("sales_data.csv", f, "text/csv")})
    assert upload_resp.status_code == 200
    table_id = upload_resp.json()["table_id"]
    orig_score = upload_resp.json()["quality_report"]["health_score"]

    # Trigger clean
    clean_resp = client.post("/clean", json={"table_id": table_id, "action": "auto_clean"})
    assert clean_resp.status_code == 200
    data = clean_resp.json()
    assert data["is_cleaning"] is True
    assert data["quality_report"]["health_score"] >= orig_score

    # Check export cleaned endpoint
    dl_resp = client.get(f"/export/cleaned/{table_id}?format=xlsx")
    assert dl_resp.status_code == 200
    assert "spreadsheet" in dl_resp.headers["content-type"]


def test_api_ask_cleaning_intent():
    with open(os.path.join(SAMPLE_DIR, "sales_data.csv"), "rb") as f:
        upload_resp = client.post("/upload", files={"file": ("sales_data.csv", f, "text/csv")})
    table_id = upload_resp.json()["table_id"]

    # Send natural language cleaning question
    ask_resp = client.post("/ask", json={"table_id": table_id, "question": "Please clean this dataset and remove duplicates"})
    assert ask_resp.status_code == 200
    data = ask_resp.json()
    assert data["is_cleaning"] is True
    assert "cleaning_details" in data
    assert "Data Cleaning" in data["summary"]
