import pandas as pd
import matplotlib.pyplot as plt
from pandas.plotting import table
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

# Check if DataFrame is not empty
if not df.empty:
    # Create a figure and a single subplot
    fig, ax = plt.subplots(figsize=(12, 4))

    # Hide axes
    ax.xaxis.set_visible(False) 
    ax.yaxis.set_visible(False) 

    # Table from DataFrame
    tab = table(ax, df, loc='center', cellLoc = 'center')

    # Autoresize the columns
    plt.gcf().tight_layout()

    # Save the figure as a PDF
    plt.savefig('P:\Scripts\debuggerGPT\capabilities\schedule.pdf')
else:
    print('The input text could not be converted to a DataFrame.')
