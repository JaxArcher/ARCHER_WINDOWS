#!/usr/bin/env python

import sys
import os

# Add the venv_windows Scripts directory to PATH
venv_python = r"D:\ARCHER_WINDOWS\venv_windows\Scripts\python.exe"

# Try to import pandas, if not available, install it
try:
    import pandas as pd
    print("Pandas is available")
except ImportError:
    print("Pandas not available, trying to install...")
    # Try to install pandas using pip from the venv
    import subprocess
    try:
        subprocess.run([venv_python, "-m", "pip", "install", "pandas", "openpyxl"], 
                      check=True, capture_output=True, text=True)
        print("Pandas installed successfully")
        # Now try to import again
        import pandas as pd
    except Exception as e:
        print(f"Failed to install pandas: {e}")
        sys.exit(1)

# Now read the Excel file
try:
    df = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan Detailed')
    
    # Find the row for Environmental Interaction Developer (Agent_ENV)
    agent_env_row = df[df['Agent'] == 'Environmental Interaction Developer (Agent_ENV)']
    
    if not agent_env_row.empty:
        print("Found Agent_ENV row:")
        print(agent_env_row.to_string())
        
        # Save to a text file for reference
        with open('agent_env_requirements.txt', 'w') as f:
            f.write("Agent_ENV Requirements:\n\n")
            f.write(agent_env_row.to_string())
            f.write("\n\n")
    else:
        print("Agent_ENV row not found")
        
    # Also check the "Dev Agents Plan" sheet
    df_plan = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan')
    agent_env_plan_row = df_plan[df_plan['Agent'] == 'Environmental Interaction Developer (Agent_ENV)']
    
    if not agent_env_plan_row.empty:
        print("\nFound Agent_ENV in Dev Agents Plan:")
        print(agent_env_plan_row.to_string())
        
        with open('agent_env_requirements.txt', 'a') as f:
            f.write("\nDev Agents Plan:\n\n")
            f.write(agent_env_plan_row.to_string())
            f.write("\n\n")
    else:
        print("Agent_ENV not found in Dev Agents Plan")
        
    # Check "Cross-Agent Guidelines" sheet
    df_guidelines = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Cross-Agent Guidelines')
    
    with open('agent_env_requirements.txt', 'a') as f:
        f.write("\nCross-Agent Guidelines:\n\n")
        f.write(df_guidelines.to_string())
        
    print("\nSaved requirements to agent_env_requirements.txt")
    
except Exception as e:
    print(f"Error reading Excel file: {e}")
    import traceback
    traceback.print_exc()