"""
Tests for Benchmark Evaluation and Ground Truth Comparison.
"""

import pytest
import pandas as pd
from research.benchmark_questions import BENCHMARK_QUESTIONS
from research.evaluation import results_match, run_benchmark_evaluation


def test_benchmark_questions_schema():
    assert len(BENCHMARK_QUESTIONS) == 20
    categories = set(q["category"] for q in BENCHMARK_QUESTIONS)
    assert len(categories) == 8
    for q in BENCHMARK_QUESTIONS:
        assert "id" in q
        assert "question" in q
        assert "reference_sql" in q
        assert "dataset" in q


def test_results_match_scalar_numbers():
    df1 = pd.DataFrame([{"total": 12500.50}])
    df2 = pd.DataFrame([{"total_rev": 12500.51}])
    assert results_match(df1, df2) is True


def test_results_match_mismatched_rows():
    df1 = pd.DataFrame([{"val": 10}, {"val": 20}])
    df2 = pd.DataFrame([{"val": 10}])
    assert results_match(df1, df2) is False


def test_results_match_sorted_alignment():
    df1 = pd.DataFrame({"cat": ["A", "B"], "sum": [100, 200]})
    df2 = pd.DataFrame({"cat": ["B", "A"], "sum": [200, 100]})
    assert results_match(df1, df2) is True


def test_run_benchmark_evaluation_fallback_mode():
    res = run_benchmark_evaluation(provider_name="fallback", questions_limit=3)
    assert res["total_questions"] == 3
    assert res["valid_sql_percentage"] == 100.0
    assert res["execution_success_percentage"] == 100.0
    assert res["median_latency_seconds"] >= 0.0
    assert len(res["detailed_results"]) == 3
