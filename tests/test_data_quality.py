"""
Tests for Data Quality Doctor and Cleaning Stack.
"""

import pytest
import pandas as pd
from core.duckdb_engine import reset_engine
from core.ingestion import ingest_dataframe
from core.data_quality import (
    evaluate_data_health,
    preview_cleaning_operation,
    apply_cleaning_operation,
    undo_last_operation,
    revert_to_original,
    export_cleaned_dataset,
    can_undo
)


@pytest.fixture(autouse=True)
def setup_dirty_dataset():
    reset_engine()
    df = pd.DataFrame({
        "id": [1, 2, 2, 3, 4, 5, 6, 7],
        "name": [" Alice ", "Bob", "Bob", "Charlie", None, "Eva", "Frank", "Grace"],
        "score": [85.0, 90.0, 90.0, None, 75.0, 300.0, 82.0, 88.0]  # 300 is outlier, duplicate row id=2
    })
    table_id, meta = ingest_dataframe(df, source_name="students")
    yield table_id, meta
    reset_engine()


def test_evaluate_health_score(setup_dirty_dataset):
    table_id, _ = setup_dirty_dataset
    report = evaluate_data_health(table_id, run_isolation_forest=False)
    assert 0 <= report["health_score"] <= 100
    assert report["duplicate_rows"] == 1
    assert report["missing_cells"] == 2


def test_remove_duplicates_preview_and_apply(setup_dirty_dataset):
    table_id, _ = setup_dirty_dataset

    # Preview
    preview = preview_cleaning_operation(table_id, "remove_duplicates")
    assert preview["affected_records"] == 1
    assert preview["rows_before"] == 8
    assert preview["rows_after"] == 7

    # Apply
    report, desc = apply_cleaning_operation(table_id, "remove_duplicates")
    assert report["total_rows"] == 7
    assert report["duplicate_rows"] == 0
    assert can_undo(table_id) is True

    # Undo
    undone_rep, undo_desc = undo_last_operation(table_id)
    assert undone_rep["total_rows"] == 8
    assert undone_rep["duplicate_rows"] == 1


def test_fill_missing_operation(setup_dirty_dataset):
    table_id, _ = setup_dirty_dataset
    report, desc = apply_cleaning_operation(
        table_id, "fill_missing", params={"column": "score", "strategy": "mean"}
    )
    score_col = [c for c in report["column_metrics"] if c["name"] == "score"][0]
    assert score_col["null_count"] == 0


def test_export_cleaned_dataset(setup_dirty_dataset):
    table_id, _ = setup_dirty_dataset
    csv_bytes, mime, name = export_cleaned_dataset(table_id, "csv")
    assert len(csv_bytes) > 0
    assert "text/csv" in mime
    assert name.endswith(".csv")
