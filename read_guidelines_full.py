import pandas as pd
import sys

# Set encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Read the Cross-Agent Guidelines sheet
sheets = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name=['Cross-Agent Guidelines'])
df_guidelines = sheets['Cross-Agent Guidelines']

print('=== CROSS-AGENT GUIDELINES (FULL) ===')
print()

for i, row in df_guidelines.iterrows():
    category = row['Category']
    summary = row['Summary']
    
    print(f'{category}')
    print('=' * 80)
    print(summary)
    print()
    print('-' * 80)
    print()
