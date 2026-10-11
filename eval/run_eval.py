"""
Evaluation Script for DataChat.
CLI tool that loads a JSON test suite of natural language analytical questions,
evaluates SQL generation accuracy, self-correction retry rate, and query latency.

Usage:
    python eval/run_eval.py [--file eval/questions.json] [--mock-llm]
"""

import os
import sys
import time
import json
import argparse
from typing import Dict, Any, List

# Add project root to python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from backend.services.loader import load_file_into_duckdb, reset_connection
from backend.services.llm import run_nl_query_with_self_correction
from backend.services.sql_guard import validate_sql
from backend.services.loader import execute_query


def run_evaluation(test_file: str, mock_llm: bool = False):
    print("=" * 65)
    print("           DATACHAT EVALUATION SUITE            ")
    print("=" * 65)
    print(f"Loading test definitions from: {test_file}")

    if not os.path.exists(test_file):
        print(f"Error: Test file '{test_file}' not found.")
        sys.exit(1)

    with open(test_file, "r", encoding="utf-8") as f:
        tests: List[Dict[str, Any]] = json.load(f)

    print(f"Loaded {len(tests)} test questions.\n")

    # Group tests by dataset to avoid reloading repeatedly
    dataset_cache: Dict[str, Dict[str, Any]] = {}
    sample_dir = os.path.join(ROOT_DIR, "sample_data")

    total_tests = len(tests)
    passed_tests = 0
    total_retries = 0
    total_latency = 0.0
    results_summary = []

    for test in tests:
        q_id = test.get("id")
        dataset_name = test.get("dataset")
        question = test.get("question")
        sheet_name = test.get("sheet_name")
        expected_keywords = test.get("expected_sql_keywords", [])
        expected_min_rows = test.get("expected_min_rows", 0)

        cache_key = f"{dataset_name}:{sheet_name or 'default'}"
        if cache_key not in dataset_cache:
            dataset_path = os.path.join(sample_dir, dataset_name)
            table_id, metadata = load_file_into_duckdb(dataset_path, sheet_name=sheet_name)
            dataset_cache[cache_key] = metadata

        meta = dataset_cache[cache_key]

        start_time = time.time()
        retries = 0
        success = False
        error = None
        sql = ""
        row_count = 0

        if mock_llm:
            # Deterministic evaluation using standard DuckDB SQL for latency & execution benchmarking
            t_name = meta["table_name"]
            if "total number" in question.lower():
                sql = f"SELECT COUNT(*) as total_orders FROM \"{t_name}\""
            elif "total revenue" in question.lower() and "region" not in question.lower():
                sql = f"SELECT SUM(revenue) as total_revenue FROM \"{t_name}\""
            elif "region" in question.lower():
                sql = f"SELECT region, SUM(revenue) as total_revenue FROM \"{t_name}\" GROUP BY region ORDER BY total_revenue DESC"
            elif "average profit" in question.lower():
                sql = f"SELECT category, AVG(profit) as avg_profit FROM \"{t_name}\" GROUP BY category ORDER BY avg_profit DESC LIMIT 1"
            elif "top 5" in question.lower():
                sql = f"SELECT * FROM \"{t_name}\" ORDER BY revenue DESC LIMIT 5"
            elif "compare" in question.lower() or ("budget" in question.lower() and "spend" in question.lower()):
                sql = f"SELECT department, SUM(budget) as total_budget, SUM(actual_spend) as total_spend FROM \"{t_name}\" GROUP BY department"
            elif "budget" in question.lower() and "total" in question.lower():
                sql = f"SELECT SUM(budget) as total_budget FROM \"{t_name}\""
            elif "subject" in question.lower():
                sql = f"SELECT subject, AVG(score) as avg_score FROM \"{t_name}\" GROUP BY subject"
            else:
                sql = f"SELECT * FROM \"{t_name}\" LIMIT 10"

            is_valid, g_err, clean_sql = validate_sql(sql)
            if is_valid:
                cols, rows = execute_query(clean_sql)
                success = True
                sql = clean_sql
                row_count = len(rows)
            else:
                error = g_err
        else:
            # Run actual LLM query with self-correction
            res = run_nl_query_with_self_correction(
                table_id=meta["table_id"],
                question=question,
                table_metadata=meta
            )
            success = res.get("success", False)
            sql = res.get("sql", "")
            retries = res.get("retries", 0)
            row_count = res.get("row_count", 0)
            error = res.get("error")

        elapsed = time.time() - start_time
        total_latency += elapsed
        total_retries += retries

        # Validate against test expectations
        passed = success and (row_count >= expected_min_rows)
        if passed:
            passed_tests += 1
            status_badge = "[PASS]"
        else:
            status_badge = "[FAIL]"

        print(f"Test #{q_id:02d} {status_badge} | Latency: {elapsed:.3f}s | Retries: {retries} | Rows: {row_count}")
        print(f"        Q: {question}")
        print(f"      SQL: {sql[:80]}..." if len(sql) > 80 else f"      SQL: {sql}")
        if error:
            print(f"    ERROR: {error}")
        print("-" * 65)

        results_summary.append({
            "id": q_id,
            "passed": passed,
            "latency": elapsed,
            "retries": retries,
            "sql": sql
        })

    # Summary Metrics
    accuracy = (passed_tests / total_tests) * 100
    avg_latency = total_latency / total_tests
    retry_rate = (total_retries / total_tests)

    print("\n" + "=" * 65)
    print("                    FINAL RESULTS                        ")
    print("=" * 65)
    print(f"Total Questions Evaluated:  {total_tests}")
    print(f"Passed:                     {passed_tests} / {total_tests}")
    print(f"Accuracy Rate:              {accuracy:.1f}%")
    print(f"Average Latency:            {avg_latency:.3f}s per query")
    print(f"Average Retries per Query:  {retry_rate:.2f}")
    print("=" * 65 + "\n")

    return accuracy, avg_latency, retry_rate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DataChat Evaluation Runner")
    parser.add_argument("--file", default="eval/questions.json", help="Path to evaluation JSON")
    parser.add_argument("--mock-llm", action="store_true", help="Run benchmark with built-in query mapping")
    args = parser.parse_args()

    run_evaluation(test_file=args.file, mock_llm=args.mock_llm)
