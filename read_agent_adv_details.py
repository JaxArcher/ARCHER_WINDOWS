#!/usr/bin/env python
import pandas as pd
import sys
import io

# Set stdout to handle UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    # Read the main detailed plan sheet
    df_detailed = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan Detailed')
    print('=== AGENT_ADV DETAILED PLAN ===')
    print('Shape:', df_detailed.shape)
    print('Columns:', df_detailed.columns.tolist())
    
    # Look for Advanced & Experimental Features Developer
    for index, row in df_detailed.iterrows():
        if 'Advanced' in str(row.get('Agent Name', '')) or 'Experimental' in str(row.get('Agent Name', '')):
            print(f'\n=== FOUND AGENT_ADV AT INDEX {index} ===')
            for col, value in row.items():
                print(f'{col}: {value}')
            print('=' * 50)
    
    # Read the main plan sheet
    df_plan = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan')
    print('\n=== AGENT_ADV MAIN PLAN ===')
    print('Shape:', df_plan.shape)
    print('Columns:', df_plan.columns.tolist())
    
    # Look for Advanced & Experimental Features Developer in main plan
    for index, row in df_plan.iterrows():
        if 'Advanced' in str(row.get('Agent Name', '')) or 'Experimental' in str(row.get('Agent Name', '')):
            print(f'\n=== FOUND AGENT_ADV IN MAIN PLAN AT INDEX {index} ===')
            for col, value in row.items():
                print(f'{col}: {value}')
            print('=' * 50)
    
    # Read Cross-Agent Guidelines
    df_guidelines = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Cross-Agent Guidelines')
    print('\n=== CROSS-AGENT GUIDELINES ===')
    print('Shape:', df_guidelines.shape)
    print('Columns:', df_guidelines.columns.tolist())
    print('\nFirst few rows:')
    print(df_guidelines.head())
    
except Exception as e:
    print('Error:', str(e))
    import traceback
    traceback.print_exc()