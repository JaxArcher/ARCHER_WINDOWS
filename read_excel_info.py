import pandas as pd
import sys

# Set encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Read the Excel file
df_detailed = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan Detailed')
df_plan = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan')
df_cross = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Cross-Agent Guidelines')

print("=== Dev Agents Plan Detailed ===")
print("Columns:", df_detailed.columns.tolist())
print("\nUI & Visualization Developer row:")
for idx, row in df_detailed.iterrows():
    if 'UI & Visualization Developer' in str(row.values) or 'Agent_UI' in str(row.values):
        print(f"\nRow {idx}:")
        for col, val in row.items():
            print(f"  {col}: {val}")

print("\n\n=== Dev Agents Plan ===")
print("Columns:", df_plan.columns.tolist())
print("\nUI & Visualization Developer row:")
for idx, row in df_plan.iterrows():
    if 'UI & Visualization Developer' in str(row.values) or 'Agent_UI' in str(row.values):
        print(f"\nRow {idx}:")
        for col, val in row.items():
            print(f"  {col}: {val}")

print("\n\n=== Cross-Agent Guidelines ===")
print("Columns:", df_cross.columns.tolist())
print("\nFirst few rows:")
print(df_cross.head(10).to_string())
