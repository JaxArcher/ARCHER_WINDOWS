import pandas as pd
import sys

# Set encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Read the Excel file
df = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan Detailed')

# Get the Voice Interaction Developer row
voice_row = df.iloc[0]

print('='*80)
print('VOICE INTERACTION DEVELOPER (Agent_V) - FULL DETAILS')
print('='*80)

for column in df.columns:
    print(f'\n{column}:')
    print('-' * 40)
    value = str(voice_row[column]).strip()
    print(value)
    print()

# Also check the Dev Agents Plan sheet
print('\n' + '='*80)
print('CHECKING Dev Agents Plan SHEET')
print('='*80)

df_plan = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan')
print('Columns:', df_plan.columns.tolist())

# Search for Voice Interaction Developer in this sheet
for idx, row in df_plan.iterrows():
    for col in df_plan.columns:
        cell_value = str(row[col])
        if 'Voice Interaction Developer' in cell_value or 'Agent_V' in cell_value:
            print(f'\nFound at row {idx}:')
            print(row.to_string())

# Also check Cross-Agent Guidelines
print('\n' + '='*80)
print('CHECKING Cross-Agent Guidelines SHEET')
print('='*80)

df_cross = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Cross-Agent Guidelines')
print('Columns:', df_cross.columns.tolist())
print('\nFirst few rows:')
print(df_cross.head())
