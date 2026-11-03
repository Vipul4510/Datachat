"""
Curated Benchmark Question Suite for Academic Evaluation.
Contains 20 rigorously categorized natural language questions with verified
reference SQL queries and expected ground truth results.
"""

from typing import Dict, Any, List

BENCHMARK_QUESTIONS: List[Dict[str, Any]] = [
    # Category 1: Aggregation & Grouping
    {
        "id": 1,
        "category": "Aggregation & Grouping",
        "question": "What is the total revenue across all sales orders?",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT SUM(revenue) as total_revenue FROM {table}",
        "description": "Tests basic scalar aggregation (SUM) without grouping."
    },
    {
        "id": 2,
        "category": "Aggregation & Grouping",
        "question": "Show total revenue by region sorted from highest to lowest",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT region, SUM(revenue) as total_revenue FROM {table} GROUP BY region ORDER BY total_revenue DESC",
        "description": "Tests categorical GROUP BY and descending sort."
    },
    {
        "id": 3,
        "category": "Aggregation & Grouping",
        "question": "What is the average profit for each product category?",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT category, AVG(profit) as avg_profit FROM {table} GROUP BY category",
        "description": "Tests categorical grouping with AVG aggregation."
    },

    # Category 2: Filtering & Sorting
    {
        "id": 4,
        "category": "Filtering & Sorting",
        "question": "Find all orders where profit is greater than 500",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT * FROM {table} WHERE profit > 500",
        "description": "Tests numeric inequality filter in WHERE clause."
    },
    {
        "id": 5,
        "category": "Filtering & Sorting",
        "question": "How many orders were placed in the Technology category?",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT COUNT(*) as count FROM {table} WHERE category = 'Technology'",
        "description": "Tests exact string literal equality filter with COUNT."
    },
    {
        "id": 6,
        "category": "Filtering & Sorting",
        "question": "List all orders from the West region sorted by order date",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT * FROM {table} WHERE region = 'West' ORDER BY order_date ASC",
        "description": "Tests string filtering combined with chronological sorting."
    },

    # Category 3: Top-N Queries
    {
        "id": 7,
        "category": "Top-N Queries",
        "question": "List the top 5 orders by revenue",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT * FROM {table} ORDER BY revenue DESC LIMIT 5",
        "description": "Tests ORDER BY DESC with LIMIT 5."
    },
    {
        "id": 8,
        "category": "Top-N Queries",
        "question": "Which product category has the highest average profit?",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT category, AVG(profit) as avg_profit FROM {table} GROUP BY category ORDER BY avg_profit DESC LIMIT 1",
        "description": "Tests GROUP BY, ORDER BY aggregated alias, and LIMIT 1."
    },

    # Category 4: Date-Based Analysis
    {
        "id": 9,
        "category": "Date-Based Analysis",
        "question": "Show monthly revenue breakdown",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT strftime(CAST(order_date AS DATE), '%Y-%m') as month, SUM(revenue) as total_rev FROM {table} GROUP BY month ORDER BY month",
        "description": "Tests date parsing, monthly truncation, and chronological grouping."
    },
    {
        "id": 10,
        "category": "Date-Based Analysis",
        "question": "How many orders occurred in the first quarter of 2023?",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT COUNT(*) FROM {table} WHERE CAST(order_date AS DATE) >= '2023-01-01' AND CAST(order_date AS DATE) <= '2023-03-31'",
        "description": "Tests date range boundary filtering."
    },

    # Category 5: Conditional Aggregations
    {
        "id": 11,
        "category": "Conditional Aggregations",
        "question": "Compare total revenue of orders with profit above 200 versus profit below or equal to 200",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT CASE WHEN profit > 200 THEN 'High Profit' ELSE 'Normal Profit' END as profit_tier, SUM(revenue) as total_rev FROM {table} GROUP BY profit_tier",
        "description": "Tests CASE WHEN conditional grouping."
    },
    {
        "id": 12,
        "category": "Conditional Aggregations",
        "question": "Count how many high-value orders (revenue > 1000) each region generated",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT region, COUNT(CASE WHEN revenue > 1000 THEN 1 END) as high_val_orders FROM {table} GROUP BY region",
        "description": "Tests conditional aggregation within COUNT."
    },

    # Category 6: Null-Value Handling
    {
        "id": 13,
        "category": "Null-Value Handling",
        "question": "Find all records that have missing customer names or missing dates",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT * FROM {table} WHERE customer_name IS NULL OR order_date IS NULL",
        "description": "Tests IS NULL predicate and OR logic."
    },
    {
        "id": 14,
        "category": "Null-Value Handling",
        "question": "What is the average revenue considering only non-null discount records?",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT AVG(revenue) as avg_rev FROM {table} WHERE discount IS NOT NULL",
        "description": "Tests explicit IS NOT NULL filtering before aggregation."
    },

    # Category 7: Multi-Metric Calculations
    {
        "id": 15,
        "category": "Multi-Metric Calculations",
        "question": "What is the minimum, maximum, and average unit price?",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT MIN(unit_price) as min_p, MAX(unit_price) as max_p, AVG(unit_price) as avg_p FROM {table}",
        "description": "Tests multi-metric scalar aggregations in a single query."
    },
    {
        "id": 16,
        "category": "Multi-Metric Calculations",
        "question": "What is the overall profit margin percentage across the entire dataset?",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT (SUM(profit) / SUM(revenue)) * 100.0 as profit_margin_pct FROM {table}",
        "description": "Tests arithmetic ratio between two aggregated sums."
    },

    # Category 8: Ambiguous & Complex Reasoning
    {
        "id": 17,
        "category": "Ambiguous / Complex",
        "question": "Which region is the most profitable in terms of total profit?",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT region, SUM(profit) as total_profit FROM {table} GROUP BY region ORDER BY total_profit DESC LIMIT 1",
        "description": "Tests natural language understanding of 'most profitable' mapped to SUM(profit)."
    },
    {
        "id": 18,
        "category": "Ambiguous / Complex",
        "question": "List orders where unit price exceeds average unit price",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT * FROM {table} WHERE unit_price > (SELECT AVG(unit_price) FROM {table})",
        "description": "Tests nested subquery aggregation."
    },
    {
        "id": 19,
        "category": "Ambiguous / Complex",
        "question": "What is the total number of orders in the dataset?",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT COUNT(*) as total_orders FROM {table}",
        "description": "Tests universal record count cardinality."
    },
    {
        "id": 20,
        "category": "Ambiguous / Complex",
        "question": "What is the total units sold in the West region?",
        "dataset": "sales_data.csv",
        "reference_sql": "SELECT SUM(quantity) as total_units FROM {table} WHERE region = 'West'",
        "description": "Tests domain terminology mapping ('units sold' -> quantity column)."
    }
]
