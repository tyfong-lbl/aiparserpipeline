import pandas as pd
import random

from pathlib import Path

def random_sample_excel_columns(input_file, output_file, num_columns, sheet_name=0):
    """
   Opens an Excel file, creates a random sample of columns without replacement,
   and writes the output to a new Excel file.

   Args:
   input_file (str or Path): Path to the input Excel file.
   output_file (str or Path): Path to the output Excel file.
   num_columns (int): Number of columns to sample from the input file.
   sheet_name (str or int, optional): Name or index of the sheet to read. Defaults to 0 (first sheet).

   Returns:
   None
   """
    # Read the input Excel file
    df = pd.read_excel(input_file, sheet_name=sheet_name)

    # Check if num_columns is valid
    if num_columns <= 0 or num_columns > len(df.columns):
       breakpoint()
       raise ValueError("Number of columns must be between 1 and the total number of columns in the input file.")

    # Create a random sample of columns without replacement
    sampled_columns = random.sample(list(df.columns), num_columns)
    sampled_df = df[sampled_columns]

    # Write the sampled data to a new Excel file
    sampled_df.to_excel(output_file, index=False)

    print(f"Random sample of {num_columns} columns has been written to {output_file}")


if __name__ == "__main__":
    # Example usage
    excel_path = Path("/Users/TYFong/Desktop/worklogs/project_logs/ai_parser/Solar_Project_Tracker_ITexamples_2022.xlsx")
    input_file = excel_path 
    storage_path = excel_path.parent
    num_columns = 25  # Change this to the desired number of columns
    output_file = Path(storage_path, f'{num_columns}_sample_columns.xlsx')
    sheet_name = "urls"  # Replace with the actual sheet name or index

    random_sample_excel_columns(input_file, output_file, num_columns, sheet_name)
