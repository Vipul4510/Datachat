"""
Sample datasets generator for testing DataChat:
1. sales_data.csv (Retail sales, dates, products, regions, profits, with some nulls/outliers)
2. student_marks.xlsx (Students across subjects, with multiple sheets)
3. expenses.json (Monthly operational expenses, department categories)
4. sample.parquet & sample.tsv (Format verification files)
"""

import os
import pandas as pd
import numpy as np

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data")
os.makedirs(SAMPLE_DIR, exist_ok=True)

def generate_sample_data():
    np.random.seed(42)

    # 1. Sales Dataset (CSV)
    regions = ["North", "South", "East", "West"]
    categories = ["Technology", "Furniture", "Office Supplies"]
    sales_data = []
    for i in range(1, 101):
        region = np.random.choice(regions)
        category = np.random.choice(categories)
        units = int(np.random.randint(1, 50))
        unit_price = round(float(np.random.uniform(10.0, 500.0)), 2)
        revenue = round(units * unit_price, 2)
        profit = round(revenue * np.random.uniform(0.05, 0.35), 2)
        
        # introduce deliberate edge cases for quality testing:
        # row 15 has missing profit, row 30 has missing region, row 50 has outlier revenue
        if i == 15:
            profit = None
        if i == 30:
            region = None
        if i == 50:
            revenue = 999999.0  # obvious outlier

        sales_data.append({
            "order_id": f"ORD-{1000 + i}",
            "order_date": f"2025-0{(i % 9) + 1}-{(i % 25) + 1:02d}",
            "region": region,
            "category": category,
            "units_sold": units,
            "unit_price": unit_price,
            "revenue": revenue,
            "profit": profit
        })
    # Add a duplicate row
    sales_data.append(sales_data[0].copy())

    df_sales = pd.DataFrame(sales_data)
    sales_path = os.path.join(SAMPLE_DIR, "sales_data.csv")
    df_sales.to_csv(sales_path, index=False)
    print(f"Generated {sales_path} ({len(df_sales)} rows)")

    # 2. Student Marks (Excel with 2 sheets)
    students = [
        {"student_id": f"STU-{100 + i}", "name": name, "grade": grade}
        for i, (name, grade) in enumerate([
            ("Alice Smith", "Grade 10"), ("Bob Jones", "Grade 10"),
            ("Charlie Brown", "Grade 11"), ("Diana Prince", "Grade 11"),
            ("Ethan Hunt", "Grade 12"), ("Fiona Gallagher", "Grade 12"),
            ("George Clark", "Grade 10"), ("Hannah Abbott", "Grade 11")
        ])
    ]
    df_students = pd.DataFrame(students)

    scores = []
    subjects = ["Math", "Physics", "Chemistry", "English"]
    for s in students:
        for subj in subjects:
            score = int(np.random.randint(50, 99))
            scores.append({
                "student_id": s["student_id"],
                "subject": subj,
                "score": score,
                "term": "Term 1"
            })
    df_scores = pd.DataFrame(scores)

    excel_path = os.path.join(SAMPLE_DIR, "student_marks.xlsx")
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_students.to_excel(writer, sheet_name="Students", index=False)
        df_scores.to_excel(writer, sheet_name="ExamScores", index=False)
    print(f"Generated {excel_path} (2 sheets)")

    # 3. Expenses Dataset (JSON)
    departments = ["Engineering", "Marketing", "Sales", "HR", "Operations"]
    expenses = []
    for month in ["2025-01", "2025-02", "2025-03", "2025-04"]:
        for dept in departments:
            expenses.append({
                "expense_id": f"EXP-{len(expenses)+1:03d}",
                "month": month,
                "department": dept,
                "budget": int(np.random.randint(15000, 50000)),
                "actual_spend": int(np.random.randint(12000, 55000)),
                "approved_by": "Director"
            })
    df_expenses = pd.DataFrame(expenses)
    json_path = os.path.join(SAMPLE_DIR, "expenses.json")
    df_expenses.to_json(json_path, orient="records", indent=2)
    print(f"Generated {json_path} ({len(expenses)} records)")

    # 4. Parquet format sample
    parquet_path = os.path.join(SAMPLE_DIR, "sales_data.parquet")
    df_sales.dropna().to_parquet(parquet_path, index=False)
    print(f"Generated {parquet_path}")

    # 5. TSV format sample
    tsv_path = os.path.join(SAMPLE_DIR, "expenses.tsv")
    df_expenses.to_csv(tsv_path, sep="\t", index=False)
    print(f"Generated {tsv_path}")

if __name__ == "__main__":
    generate_sample_data()
