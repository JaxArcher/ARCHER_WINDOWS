import pandas as pd
import sys

# Set encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Read the Cross-Agent Guidelines sheet
df = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Cross-Agent Guidelines')

print('='*80)
print('CROSS-AGENT GUIDELINES - FULL DETAILS')
print('='*80)

for idx, row in df.iterrows():
    print(f'\n{idx+1}. {row["Category"]}')
    print('-' * 40)
    print(row["Summary"])
    print()
