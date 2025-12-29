import pandas as pd
import sys

# Set encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Read the Excel file
df = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan Detailed')

# Find the Specialized Agents Developer (Agent_SPEC) row
spec_row = df[df['Agent Name'].str.contains('Specialized Agents Developer|Agent_SPEC', case=False, na=False)].iloc[0]

print('=== SPECIALIZED AGENTS DEVELOPER (Agent_SPEC) ===')
print()

for column in df.columns:
    print(f'\n{column}:')
    print('=' * 50)
    value = spec_row[column]
    if pd.notna(value):
        print(str(value))
    else:
        print('N/A')
    print()
