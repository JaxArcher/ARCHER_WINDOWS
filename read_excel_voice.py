import pandas as pd

# Read the Excel file
df = pd.read_excel('ARCHER_Enhanced_Features_FINAL.xlsx', sheet_name='Dev Agents Plan Detailed')

print('Columns:', df.columns.tolist())
print('\nShape:', df.shape)
print('\nFirst few rows:')
print(df.head())

# Search for Voice Interaction Developer
print('\n\nSearching for Voice Interaction Developer...')
for idx, row in df.iterrows():
    for col in df.columns:
        cell_value = str(row[col])
        if 'Voice Interaction Developer' in cell_value or 'Agent_V' in cell_value:
            print(f'\nFound at row {idx}, column {col}:')
            print(row.to_string())
            print('\n' + '='*80)
