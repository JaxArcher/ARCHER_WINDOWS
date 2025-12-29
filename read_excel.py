#!/usr/bin/env python
import pandas as pd
import sys
import io

# Set stdout to handle UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    df = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan Detailed')
    print('Successfully read the file')
    print('Shape:', df.shape)
    print('Columns:', df.columns.tolist())
    
    # Look for Orchestration & Memory Developer
    for index, row in df.iterrows():
        if 'Orchestration' in str(row.get('Agent Name', '')) or 'Memory' in str(row.get('Agent Name', '')):
            print(f'\nFound relevant row at index {index}:')
            for col, value in row.items():
                print(f'  {col}: {value}')
            
except Exception as e:
    print('Error:', str(e))
    import traceback
    traceback.print_exc()