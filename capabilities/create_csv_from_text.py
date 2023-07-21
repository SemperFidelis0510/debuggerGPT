import pandas as pd
import sys

# Function to convert text to DataFrame
def text_to_df(text):
    lines = text.split('\n')
    data = []
    for line in lines:
        if line.strip():
            data.append([x.strip() for x in line.split('|')[1:-1]])
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

# Read the text from the first command line argument
input_text = sys.argv[1]

# Convert the text to a DataFrame
df = text_to_df(input_text)

# Save the DataFrame to a CSV file
df.to_csv('S:\\OneDrive - Technion\\Documents\\School\\Pakals\\infi 1\\schedule.csv', index=False)
