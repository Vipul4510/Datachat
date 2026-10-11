"""Unit and integration tests for FastAPI endpoints."""

import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.loader import reset_connection

client = TestClient(app)
SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sample_data")

@pytest.fixture(autouse=True)
def setup_teardown():
    reset_connection()
    yield
    reset_connection()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["duckdb"] == "in-process"


def test_upload_csv_endpoint():
    csv_path = os.path.join(SAMPLE_DIR, "sales_data.csv")
    with open(csv_path, "rb") as f:
        response = client.post(
            "/upload",
            files={"file": ("sales_data.csv", f, "text/csv")}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "table_id" in data
    assert "quality_report" in data
    assert data["quality_report"]["row_count"] == 101
    assert "suggested_questions" in data
    assert len(data["suggested_questions"]) == 4


def test_upload_excel_endpoint():
    xlsx_path = os.path.join(SAMPLE_DIR, "student_marks.xlsx")
    with open(xlsx_path, "rb") as f:
        response = client.post(
            "/upload",
            data={"sheet_name": "ExamScores"},
            files={"file": ("student_marks.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["metadata"]["selected_sheet"] == "ExamScores"
    assert data["quality_report"]["row_count"] == 32


def test_export_report_xlsx_and_pdf():
    # First upload sales
    csv_path = os.path.join(SAMPLE_DIR, "sales_data.csv")
    with open(csv_path, "rb") as f:
        upload_resp = client.post(
            "/upload",
            files={"file": ("sales_data.csv", f, "text/csv")}
        )
    table_id = upload_resp.json()["table_id"]

    # Test xlsx export
    res_xlsx = client.get(f"/report/{table_id}?format=xlsx")
    assert res_xlsx.status_code == 200
    assert "spreadsheet" in res_xlsx.headers["content-type"]
    assert len(res_xlsx.content) > 1000

    # Test pdf export
    res_pdf = client.get(f"/report/{table_id}?format=pdf")
    assert res_pdf.status_code == 200
    assert "pdf" in res_pdf.headers["content-type"]
    assert len(res_pdf.content) > 1000
