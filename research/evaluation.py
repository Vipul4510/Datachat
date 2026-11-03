"""
Academic Evaluation Engine for NL-to-SQL Analytics.
Executes candidate queries against ground-truth reference SQL on DuckDB,
compares execution accuracy, AST validity, median latency, and repair recovery rates.
"""

import os
import time
import json
import statistics
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from core.duckdb_engine import (
    get_connection,
    execute_analytical_query,
    query_to_dataframe
)
from core.ingestion import ingest_file
from core.sql_validation import validate_and_format_sql
from ai.sql_generator import generate_and_execute_sql
from research.benchmark_questions import BENCHMARK_QUESTIONS


def results_match(ref_df: pd.DataFrame, cand_df: pd.DataFrame, tolerance: float = 0.05) -> bool:
    """
    Rigorously compares ground truth reference DataFrame with candidate DataFrame.
    Accounts for column alias differences, ordering variations, and float rounding.
    """
    if ref_df.empty and cand_df.empty:
        return True
    if ref_df.empty or cand_df.empty:
        return False

    # Check shape
    if len(ref_df) != len(cand_df):
        return False

    # If single scalar value (1x1)
    if ref_df.shape == (1, 1) and cand_df.shape == (1, 1):
        v1 = ref_df.iloc[0, 0]
        v2 = cand_df.iloc[0, 0]
        try:
            f1, f2 = float(v1), float(v2)
            return abs(f1 - f2) <= tolerance or (f1 != 0 and abs((f1 - f2) / f1) <= 0.02)
        except Exception:
            return str(v1).strip().lower() == str(v2).strip().lower()

    # Compare sorted values ignoring column names if column count matches
    if ref_df.shape[1] == cand_df.shape[1]:
        try:
            # Sort both DataFrames by first column for alignment
            sorted_ref = ref_df.sort_values(by=ref_df.columns[0]).reset_index(drop=True)
            sorted_cand = cand_df.sort_values(by=cand_df.columns[0]).reset_index(drop=True)

            for i in range(len(sorted_ref)):
                for j in range(sorted_ref.shape[1]):
                    val1 = sorted_ref.iloc[i, j]
                    val2 = sorted_cand.iloc[i, j]
                    if pd.isna(val1) and pd.isna(val2):
                        continue
                    try:
                        n1, n2 = float(val1), float(val2)
                        if abs(n1 - n2) > tolerance and (n1 != 0 and abs((n1 - n2) / n1) > 0.02):
                            return False
                    except Exception:
                        if str(val1).strip().lower() != str(val2).strip().lower():
                            return False
            return True
        except Exception:
            pass

    return False


def run_benchmark_evaluation(
    provider_name: Optional[str] = None,
    dataset_dir: str = "sample_data",
    questions_limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Executes the benchmark evaluation harness.
    
    Returns:
        Comprehensive evaluation report with accuracy, latency, and category breakdown.
    """
    questions = BENCHMARK_QUESTIONS[:questions_limit] if questions_limit else BENCHMARK_QUESTIONS
    dataset_cache: Dict[str, Tuple[str, Dict[str, Any]]] = {}

    detailed_results = []
    latencies = []
    valid_count = 0
    executed_count = 0
    accurate_count = 0
    retries_count = 0
    recovered_count = 0

    category_stats: Dict[str, Dict[str, int]] = {}

    for item in questions:
        q_id = item["id"]
        category = item["category"]
        question = item["question"]
        dataset_name = item["dataset"]
        ref_sql_template = item["reference_sql"]

        if category not in category_stats:
            category_stats[category] = {"total": 0, "accurate": 0, "executed": 0}
        category_stats[category]["total"] += 1

        # Load dataset if not cached
        if dataset_name not in dataset_cache:
            file_path = os.path.join(dataset_dir, dataset_name)
            if not os.path.exists(file_path):
                # Search up one level if needed
                file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data", dataset_name)
            t_id, meta = ingest_file(file_path)
            dataset_cache[dataset_name] = (t_id, meta)

        table_id, metadata = dataset_cache[dataset_name]
        table_name = metadata["table_name"]

        # 1. Execute ground truth reference SQL
        ref_sql = ref_sql_template.replace("{table}", f'"{table_name}"')
        ref_df = pd.DataFrame()
        try:
            ref_df = query_to_dataframe(ref_sql)
        except Exception as e:
            ref_err = str(e)

        # 2. Candidate model execution
        start_t = time.perf_counter()
        cand_res = generate_and_execute_sql(
            table_id=table_id,
            table_name=table_name,
            question=question,
            preferred_provider=provider_name
        )
        elapsed_s = round(time.perf_counter() - start_t, 4)
        latencies.append(elapsed_s)

        is_valid = bool(cand_res["sql"])
        is_executed = cand_res["success"]
        retries = cand_res.get("retries", 0)
        retries_count += retries

        is_accurate = False
        cand_df = pd.DataFrame()

        if is_executed:
            executed_count += 1
            category_stats[category]["executed"] += 1
            try:
                cand_df = query_to_dataframe(cand_res["sql"])
                is_accurate = results_match(ref_df, cand_df)
            except Exception:
                is_accurate = False

        if is_valid:
            valid_count += 1
        if is_accurate:
            accurate_count += 1
            category_stats[category]["accurate"] += 1

        if retries > 0 and is_executed:
            recovered_count += 1

        detailed_results.append({
            "id": q_id,
            "category": category,
            "question": question,
            "reference_sql": ref_sql,
            "generated_sql": cand_res["sql"],
            "sql_valid": is_valid,
            "executed": is_executed,
            "accurate": is_accurate,
            "retries": retries,
            "latency_s": elapsed_s,
            "error": cand_res.get("error")
        })

    total_q = len(questions)
    valid_pct = round((valid_count / total_q) * 100, 1) if total_q > 0 else 0.0
    exec_pct = round((executed_count / total_q) * 100, 1) if total_q > 0 else 0.0
    acc_pct = round((accurate_count / total_q) * 100, 1) if total_q > 0 else 0.0
    med_latency = round(statistics.median(latencies), 4) if latencies else 0.0
    mean_latency = round(statistics.mean(latencies), 4) if latencies else 0.0

    return {
        "provider_evaluated": provider_name or "Auto (Active)",
        "total_questions": total_q,
        "valid_sql_percentage": valid_pct,
        "execution_success_percentage": exec_pct,
        "accuracy_percentage": acc_pct,
        "median_latency_seconds": med_latency,
        "mean_latency_seconds": mean_latency,
        "total_retries": retries_count,
        "recovery_count": recovered_count,
        "category_performance": category_stats,
        "detailed_results": detailed_results
    }
