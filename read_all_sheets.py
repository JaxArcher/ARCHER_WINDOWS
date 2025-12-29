#!/usr/bin/env python
import pandas as pd
import sys
import io

# Set stdout to handle UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    # Read all relevant sheets
    sheets_to_read = ['Dev Agents Plan', 'Cross-Agent Guidelines']
    
    for sheet_name in sheets_to_read:
        print(f'\n=== {sheet_name} ===')
        df = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name=sheet_name)
        print(f'Shape: {df.shape}')
        print(f'Columns: {df.columns.tolist()}')
        
        # Look for Orchestration & Memory Developer related content
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            if any('Orchestration' in str(v) or 'Memory' in str(v) or 'Agent_ORCH' in str(v) 
                   for v in row_dict.values()):
                print(f'\nRelevant row {index}:')
                for col, value in row.items():
                    print(f'  {col}: {value}')
        
except Exception as e:
    print('Error:', str(e))
    import traceback
    traceback.print_exc()