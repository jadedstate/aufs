import os
import pyarrow.parquet as pq
import tempfile
import subprocess

def extract_script_from_parquet(parquet_file):
    """
    Extracts the script embedded in the first column (chunk 0) of the Parquet file.
    :param parquet_file: Path to the Parquet file.
    :return: The extracted script as a string.
    """
    try:
        # Step 1: Read the Parquet file
        table = pq.read_table(parquet_file)

        # Step 2: Extract the script from the first column, chunk 0
        script = table.column(0)[0].as_py()  # First row of the first column
        print("Extracted Script:\n", script)
        return script
    except Exception as e:
        print(f"Failed to extract script from Parquet file: {e}")
        return None

def execute_extracted_script(script_content, parquet_file, base_dir):
    """
    Executes the extracted script by writing it to a temp file and running it.
    :param script_content: The extracted script content as a string.
    :param parquet_file: Path to the Parquet file (passed to the script).
    :param base_dir: Base directory where the script should create directories and symlinks.
    """
    try:
        # Step 1: Create a temporary file to hold the script
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_script_file:
            script_path = temp_script_file.name

            # Append a function call to execute the extracted script with the correct arguments
            script_content_with_call = f"""
{script_content}

# Automatically call the function after extraction
create_dirs_and_symlinks("{parquet_file}", "{base_dir}")
"""

            temp_script_file.write(script_content_with_call.encode())  # Write the script to the file
        
        print(f"Temporary script written to: {script_path}")

        # Step 2: Execute the script using subprocess, passing the necessary arguments
        result = subprocess.run(['python', script_path], capture_output=True, text=True)

        # Step 3: Log the output and any errors from the subprocess
        print(f"Subprocess Output:\n{result.stdout}")
        print(f"Subprocess Error (if any):\n{result.stderr}")

        # Clean up: Remove the temporary script file after execution
        os.remove(script_path)
        print(f"Temporary script {script_path} removed.")
        
    except Exception as e:
        print(f"Failed to execute the script: {e}")


if __name__ == "__main__":
    # Example usage:
    parquet_file = "/Users/uel/Downloads/steviebabes.parquet"
    base_dir = "/Users/uel/Desktop/aufs"

    # Step 1: Extract the script from the Parquet file
    script = extract_script_from_parquet(parquet_file)

    if script:
        # Step 2: Execute the script
        execute_extracted_script(script, parquet_file, base_dir)
    else:
        print("No script extracted from the Parquet file.")
