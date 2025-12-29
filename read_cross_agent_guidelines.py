import pandas as pd
import sys

# Set encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Read the Cross-Agent Guidelines sheet
df = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Cross-Agent Guidelines')

print("Cross-Agent Guidelines:")
print("="*80)

# Print all rows
for idx, row in df.iterrows():
    print(f"\nRow {idx}:")
    for col_name, value in row.items():
        try:
            print(f"  {col_name}: {str(value)[:300]}...")
        except Exception as e:
            print(f"  {col_name}: [Could not display]")
    print("-" * 60)