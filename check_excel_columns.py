#!/usr/bin/env python

import pandas as pd

# Read the Excel file and check column names
try:
    df = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan Detailed')
    
    print("Columns in 'Dev Agents Plan Detailed':")
    print(df.columns.tolist())
    print("\nFirst few rows:")
    print(df.head())
    
    # Also check other sheets
    print("\n" + "="*50)
    df_plan = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan')
    print("Columns in 'Dev Agents Plan':")
    print(df_plan.columns.tolist())
    print("\nFirst few rows:")
    print(df_plan.head())
    
    print("\n" + "="*50)
    df_guidelines = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Cross-Agent Guidelines')
    print("Columns in 'Cross-Agent Guidelines':")
    print(df_guidelines.columns.tolist())
    print("\nFirst few rows:")
    print(df_guidelines.head())
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()