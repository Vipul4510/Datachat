"""Unit tests for Phase 2 - Data Quality Service."""

import os
import pytest
import pandas as pd
from backend.services.loader import load_file_into_duckdb, reset_connection
from backend.services.quality import (
    generate_quality_report,
    detect_outliers_iqr,
    detect_outliers_isolation_forest,
    calculate_health_score
)

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sample_data")

@pytest.fixture(autouse=True)
def setup_teardown():
    reset_connection()
    yield
    reset_connection()


def test_sales_quality_report():
    csv_path = os.path.join(SAMPLE_DIR, "sales_data.csv")
    table_id, _ = load_file_into_duckdb(csv_path)

    report = generate_quality_report(table_id, run_isolation_forest=True)

    # 101 rows originally, 8 columns
    assert report["row_count"] == 101
    assert report["column_count"] == 8
    assert report["duplicate_rows"] == 1  # 1 duplicate row added
    assert report["duplicate_percentage"] > 0

    # Missing values checks: profit has 1 missing, region has 1 missing
    assert report["missing_cells"] == 2
    profit_col = next(c for c in report["columns"] if c["column_name"] == "profit")
    assert profit_col["null_count"] == 1
    assert profit_col["is_numeric"] is True

    # IQR Outliers check: revenue has an intentional outlier (999999.0)
    assert "revenue" in report["iqr_outliers"]
    assert report["iqr_outliers"]["revenue"]["outlier_count"] >= 1
    assert report["total_iqr_outliers"] >= 1

    # Isolation Forest check
    if_out = report["isolation_forest_outliers"]
    assert "anomaly_count" in if_out
    assert if_out["anomaly_count"] > 0

    # Health score between 0 and 100
    assert 0 <= report["health_score"] <= 100
    assert report["health_status"] in ["Excellent", "Good", "Moderate", "Poor"]

    # Preview rows
    assert len(report["preview_rows"]) == 5


def test_clean_data_quality_report():
    # Expenses dataset is complete with 0 nulls and 0 duplicates
    json_path = os.path.join(SAMPLE_DIR, "expenses.json")
    table_id, _ = load_file_into_duckdb(json_path)

    report = generate_quality_report(table_id, run_isolation_forest=False)
    assert report["row_count"] == 20
    assert report["missing_cells"] == 0
    assert report["duplicate_rows"] == 0
    assert report["health_score"] >= 90
    assert report["health_status"] == "Excellent"


def test_health_score_bounds():
    # Perfect dataset
    perfect = calculate_health_score(100, 0, 10, 0, 50, 0)
    assert perfect == 100

    # Highly degraded dataset
    poor = calculate_health_score(100, 50, 10, 5, 50, 20)
    assert poor < 50
    assert poor >= 0


def test_invalid_table_id():
    with pytest.raises(ValueError, match="not found"):
        generate_quality_report("invalid-uuid-12345")
