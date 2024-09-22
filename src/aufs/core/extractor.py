# core/writing/extractor.py

import pyarrow.parquet as pq

def extract_table(file_path):
    """
    Extracts the data from a Parquet file and returns it as an Arrow table.
    
    :param file_path: The path to the Parquet file.
    :return: Arrow table containing the data.
    """
    try:
        table = pq.read_table(file_path)
        print(f"Successfully extracted Parquet file: {file_path}")
        return table
    except Exception as e:
        print(f"Failed to extract Parquet file: {file_path}. Error: {e}")
        return None
