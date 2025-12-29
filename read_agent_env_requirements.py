#!/usr/bin/env python

import pandas as pd

# Read the Excel file and extract Agent_ENV requirements
try:
    # Read "Dev Agents Plan Detailed" sheet
    df_detailed = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan Detailed')
    
    # Find the row for Environmental Interaction Developer (Agent_ENV)
    agent_env_row = df_detailed[df_detailed['Agent Name'] == 'Environmental Interaction Developer (Agent_ENV)']
    
    if not agent_env_row.empty:
        print("Found Agent_ENV in 'Dev Agents Plan Detailed':")
        print("="*80)
        
        # Save to a text file for reference
        with open('agent_env_requirements.txt', 'w', encoding='utf-8') as f:
            f.write("AGENT_ENV REQUIREMENTS FROM EXCEL\n")
            f.write("="*80 + "\n\n")
            
            # Write each column
            for column in df_detailed.columns:
                f.write(f"\n{column.upper()}:\n")
                f.write("-" * len(column) + "\n")
                value = agent_env_row[column].iloc[0]
                f.write(str(value) + "\n\n")
                
                # Also print to console
                print(f"\n{column.upper()}:\n")
                print("-" * len(column))
                print(str(value))
                print()
    else:
        print("Agent_ENV row not found in 'Dev Agents Plan Detailed'")
        
    # Read "Dev Agents Plan" sheet
    print("\n" + "="*80)
    print("AGENT_ENV IN 'Dev Agents Plan':")
    print("="*80)
    
    df_plan = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan')
    agent_env_plan_row = df_plan[df_plan['Agent Name'] == 'Environmental Interaction Developer']
    
    if not agent_env_plan_row.empty:
        with open('agent_env_requirements.txt', 'a', encoding='utf-8') as f:
            f.write("\n" + "="*80 + "\n")
            f.write("DEV AGENTS PLAN:\n")
            f.write("="*80 + "\n\n")
            
            for column in df_plan.columns:
                f.write(f"\n{column.upper()}:\n")
                f.write("-" * len(column) + "\n")
                value = agent_env_plan_row[column].iloc[0]
                f.write(str(value) + "\n\n")
                
                # Print to console
                print(f"\n{column.upper()}:\n")
                print("-" * len(column))
                print(str(value))
                print()
    else:
        print("Agent_ENV not found in 'Dev Agents Plan'")
        
    # Read "Cross-Agent Guidelines" sheet
    print("\n" + "="*80)
    print("CROSS-AGENT GUIDELINES:")
    print("="*80)
    
    df_guidelines = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Cross-Agent Guidelines')
    
    with open('agent_env_requirements.txt', 'a', encoding='utf-8') as f:
        f.write("\n" + "="*80 + "\n")
        f.write("CROSS-AGENT GUIDELINES:\n")
        f.write("="*80 + "\n\n")
        
        for _, row in df_guidelines.iterrows():
            category = row['Category']
            summary = row['Summary']
            f.write(f"\n{category.upper()}:\n")
            f.write("-" * len(category) + "\n")
            f.write(str(summary) + "\n\n")
            
            # Print to console
            print(f"\n{category.upper()}:\n")
            print("-" * len(category))
            print(str(summary))
            print()
    
    print("\n" + "="*80)
    print("Saved all requirements to agent_env_requirements.txt")
    print("="*80)
    
except Exception as e:
    print(f"Error reading Excel file: {e}")
    import traceback
    traceback.print_exc()