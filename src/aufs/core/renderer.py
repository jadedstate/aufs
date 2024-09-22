# core/writing/renderer.py
import pyarrow.parquet as pq
import os

def render_table(table, file_path, schema=None, compression='SNAPPY', create_dirs=False):
    """
    Renders a PyArrow table to a Parquet file, with options to create directories if needed.
    
    :param table: PyArrow Table to be rendered (written).
    :param file_path: The path where the Parquet file will be rendered.
    :param schema: Optional schema for the Parquet file.
    :param compression: Compression type (default is SNAPPY).
    :param create_dirs: Whether to create the directory if it doesn't exist (default False).
    """
    
    # Add '.parquet' if it's not already there
    if not file_path.endswith('.parquet'):
        file_path += '.parquet'
    
    # Check if the file already exists
    if os.path.exists(file_path):
        raise FileExistsError(f"File already exists at: {file_path}")
    
    # Handle directory creation
    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        if create_dirs:
            os.makedirs(dir_path)
        else:
            user_input = input(f"Path '{dir_path}' doesn't exist. Create it? (yes/no): ").strip().lower()
            if user_input == 'yes':
                os.makedirs(dir_path)
            else:
                print("Operation cancelled.")
                return
    
    try:
        # Write the PyArrow table to Parquet file
        pq.write_table(table, file_path, compression=compression)
        print(f"Successfully rendered Parquet file: {file_path}")
    except Exception as e:
        print(f"Failed to render Parquet file: {file_path}. Error: {e}")
