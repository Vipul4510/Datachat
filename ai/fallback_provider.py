"""
Deterministic Rule-Based Analytics Provider (No-API Fallback Mode).
Provides genuine offline analytical querying capabilities when no LLM API is configured.
Translates common natural language analytical patterns directly into valid DuckDB SQL
using the active dataset schema, without pretending to be an LLM.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from ai.base_provider import BaseAIProvider


class DeterministicFallbackProvider(BaseAIProvider):
    def __init__(self):
        super().__init__(
            name="Deterministic Fallback",
            model="Rule-Based Analytical Parser",
            api_key="none",
            timeout=5.0
        )

    def is_configured(self) -> bool:
        return True

    def health_check(self) -> Tuple[bool, str]:
        return True, "Deterministic offline analytics engine is active and ready."

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
        # Not typically called directly; fallback uses synthesize_sql
        return "Deterministic Fallback Active."

    def synthesize_sql(
        self,
        question: str,
        table_name: str,
        schema: List[Dict[str, Any]]
    ) -> Tuple[str, str]:
        """
        Synthesizes safe, schema-aware DuckDB SQL for common analytical intents.
        Returns: (sql_query, reasoning_explanation)
        """
        q = question.lower()
        col_names = [c["column_name"] for c in schema]
        col_lower_map = {c.lower(): c for c in col_names}

        # Identify numeric and categorical columns
        numeric_cols = []
        categorical_cols = []
        for c in schema:
            t = c.get("column_type", "").lower()
            if any(n in t for n in ["int", "double", "float", "decimal", "numeric", "hugeint"]):
                numeric_cols.append(c["column_name"])
            else:
                categorical_cols.append(c["column_name"])

        # Match columns mentioned in question
        mentioned_cols = [orig for low, orig in col_lower_map.items() if low in q]

        # 1. Total row count / order count
        if any(kw in q for kw in ["how many", "count", "total number", "number of rows"]):
            # Check if filtered by category (e.g. "in Technology category")
            filter_clause = ""
            for c in schema:
                for sample in c.get("sample_values", []):
                    if sample and str(sample).lower() in q:
                        filter_clause = f" WHERE \"{c['column_name']}\" = '{sample}'"
                        break
                if filter_clause:
                    break

            sql = f"SELECT COUNT(*) as total_count FROM \"{table_name}\"{filter_clause}"
            reason = "Count total occurrences matching analytical criteria."
            return sql, reason

        # 2. Top N rows by metric
        top_match = re.search(r"top\s+(\d+)", q)
        if top_match or "highest" in q or "top" in q:
            n = int(top_match.group(1)) if top_match else 5
            # Target metric
            target_metric = None
            for m in numeric_cols:
                if m.lower() in q:
                    target_metric = m
                    break
            if not target_metric and numeric_cols:
                target_metric = numeric_cols[0]

            # Target category if grouping
            target_cat = None
            for cat in categorical_cols:
                if cat.lower() in q:
                    target_cat = cat
                    break

            if target_cat and target_metric:
                sql = (
                    f"SELECT \"{target_cat}\", SUM(\"{target_metric}\") as total_{target_metric} "
                    f"FROM \"{table_name}\" "
                    f"GROUP BY \"{target_cat}\" "
                    f"ORDER BY total_{target_metric} DESC LIMIT {n}"
                )
                reason = f"Rank top {n} {target_cat} categories by aggregated {target_metric} in descending order."
            elif target_metric:
                sql = f"SELECT * FROM \"{table_name}\" ORDER BY \"{target_metric}\" DESC LIMIT {n}"
                reason = f"Select top {n} individual records ordered by {target_metric} descending."
            else:
                sql = f"SELECT * FROM \"{table_name}\" LIMIT {n}"
                reason = f"Select first {n} records from dataset."
            return sql, reason

        # 3. Sum / Total
        if "total" in q or "sum" in q:
            target_metric = None
            for m in numeric_cols:
                if m.lower() in q:
                    target_metric = m
                    break
            if not target_metric and numeric_cols:
                target_metric = numeric_cols[0]

            # Check if group by category exists
            target_cat = None
            for cat in categorical_cols:
                if cat.lower() in q:
                    target_cat = cat
                    break

            if target_cat and target_metric:
                sql = (
                    f"SELECT \"{target_cat}\", SUM(\"{target_metric}\") as total_{target_metric} "
                    f"FROM \"{table_name}\" "
                    f"GROUP BY \"{target_cat}\" "
                    f"ORDER BY total_{target_metric} DESC"
                )
                reason = f"Aggregate total {target_metric} grouped by {target_cat}."
            elif target_metric:
                sql = f"SELECT SUM(\"{target_metric}\") as total_{target_metric} FROM \"{table_name}\""
                reason = f"Compute total sum of {target_metric} across all records."
            else:
                sql = f"SELECT COUNT(*) FROM \"{table_name}\""
                reason = "Count total records."
            return sql, reason

        # 4. Average / Mean
        if "average" in q or "avg" in q or "mean" in q:
            target_metric = None
            for m in numeric_cols:
                if m.lower() in q:
                    target_metric = m
                    break
            if not target_metric and numeric_cols:
                target_metric = numeric_cols[0]

            target_cat = None
            for cat in categorical_cols:
                if cat.lower() in q:
                    target_cat = cat
                    break

            if target_cat and target_metric:
                sql = (
                    f"SELECT \"{target_cat}\", AVG(\"{target_metric}\") as avg_{target_metric} "
                    f"FROM \"{table_name}\" "
                    f"GROUP BY \"{target_cat}\" "
                    f"ORDER BY avg_{target_metric} DESC"
                )
                reason = f"Calculate mean {target_metric} grouped by {target_cat}."
            elif target_metric:
                sql = f"SELECT AVG(\"{target_metric}\") as avg_{target_metric} FROM \"{table_name}\""
                reason = f"Compute mean value of {target_metric} across dataset."
            else:
                sql = f"SELECT * FROM \"{table_name}\" LIMIT 10"
                reason = "Default preview."
            return sql, reason

        # 5. Min and Max
        if "minimum" in q or "maximum" in q or "min" in q or "max" in q:
            target_metric = None
            for m in numeric_cols:
                if m.lower() in q:
                    target_metric = m
                    break
            if not target_metric and numeric_cols:
                target_metric = numeric_cols[0]

            sql = f"SELECT MIN(\"{target_metric}\") as min_val, MAX(\"{target_metric}\") as max_val, AVG(\"{target_metric}\") as avg_val FROM \"{table_name}\""
            reason = f"Extract boundary extremes (MIN, MAX) and central average for {target_metric}."
            return sql, reason

        # 6. Inequality / numerical comparison filter (e.g. "profit > 500", "revenue above 1000")
        filter_match = re.search(r"(\w+)\s*(?:>|>=|greater than|above|more than)\s*(\d+(?:\.\d+)?)", q)
        if filter_match:
            cand_col = filter_match.group(1).lower()
            val = filter_match.group(2)
            matched_c = col_lower_map.get(cand_col)
            if matched_c:
                sql = f"SELECT * FROM \"{table_name}\" WHERE \"{matched_c}\" > {val} LIMIT 50"
                reason = f"Filter rows where {matched_c} exceeds {val}."
                return sql, reason

        # 7. Exact categorical filter (e.g. "in West region", "records from Technology")
        for c in schema:
            for sample in c.get("sample_values", []):
                if sample and str(sample).lower() in q:
                    sql = f"SELECT * FROM \"{table_name}\" WHERE \"{c['column_name']}\" = '{sample}' LIMIT 50"
                    reason = f"Filter records where {c['column_name']} equals '{sample}'."
                    return sql, reason

        # 8. Default inspection preview
        selected_cols = ", ".join([f'"{c}"' for c in (mentioned_cols if mentioned_cols else col_names[:6])])
        sql = f"SELECT {selected_cols} FROM \"{table_name}\" LIMIT 20"
        reason = "Rule-based schema projection and sample preview."
        return sql, reason
