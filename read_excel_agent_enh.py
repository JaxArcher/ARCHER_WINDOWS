import pandas as pd
import sys

# Set encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Read the Excel file
df = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan Detailed')

print("Available columns:")
for i, col in enumerate(df.columns):
    print(f"{i}: {col}")

print("\n" + "="*80)
print("Searching for Agent_ENH or Enhancements & Integration Developer...")
print("="*80)

# Search in all cells
for idx, row in df.iterrows():
    row_str = ' '.join(str(cell) for cell in row)
    if 'Enhancements' in row_str or 'Agent_ENH' in row_str or 'Integration' in row_str:
        print(f"\nRow {idx}:")
        for col_name, value in row.items():
            # Handle potential encoding issues
            try:
                print(f"  {col_name}: {str(value)[:200]}...")  # Truncate long values
            except Exception as e:
                print(f"  {col_name}: [Could not display: {e}]")
        print("-" * 60)

print("\n" + "="*80)
print("First 3 rows for context:")
print("="*80)
# Print first 3 rows with truncation
for idx, row in df.head(3).iterrows():
    print(f"\nRow {idx}:")
    for col_name, value in row.items():
        try:
            print(f"  {col_name}: {str(value)[:100]}...")
        except Exception as e:
            print(f"  {col_name}: [Could not display]")

# Also check other sheets
print("\n" + "="*80)
print("Available sheets:")
print("="*80)
all_sheets = pd.ExcelFile('ARCHER_Enhanced_Features_FINAL.xlsx').sheet_names
for sheet in all_sheets:
    print(f"- {sheet}")

# Check Dev Agents Plan sheet specifically
print("\n" + "="*80)
print("Checking 'Dev Agents Plan' sheet:")
print("="*80)
df_plan = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan')
for idx, row in df_plan.iterrows():
    row_str = ' '.join(str(cell) for cell in row)
    if 'Enhancements' in row_str or 'Agent_ENH' in row_str or 'Integration' in row_str:
        print(f"\nFound in Dev Agents Plan - Row {idx}:")
        for col_name, value in row.items():
            try:
                print(f"  {col_name}: {str(value)[:200]}...")
            except Exception as e:
                print(f"  {col_name}: [Could not display]")