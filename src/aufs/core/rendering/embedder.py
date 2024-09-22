import os
import pyarrow as pa
import pandas as pd

class TheFirstEmbedder:
    """
    A class for embedding Python scripts into the first column of a Parquet schema.
    (This is currently used for macOS/Linux)
    """

    @staticmethod
    def create_dirs_and_symlinks():
        """
        Generates a Python script that creates directories and symlinks (used for macOS/Linux).
        This script will be embedded into chunk 0 of the first column.
        """
        script = f"""
import os
import pyarrow.parquet as pq

def create_dirs_and_symlinks(parquet_file, base_dir):
    table = pq.read_table(parquet_file)
    schema = table.schema

    # Step 1: Create the base directory (if it doesn't exist)
    os.makedirs(base_dir, exist_ok=True)

    # Step 2: Create a symlink (only if it doesn't exist)
    symlink_target = '../../Downloads'
    symlink_path = os.path.join(base_dir, 'steve')
    
    if not os.path.islink(symlink_path):
        try:
            os.symlink(symlink_target, symlink_path)
            print(f"Created symlink at {{symlink_path}} -> {{symlink_target}}")
        except OSError as e:
            print(f"Failed to create symlink: {{e}}")
    else:
        print(f"Symlink already exists: {{symlink_path}}")

    # Step 3: Process schema fields (without affecting the symlink creation)
    for field in schema:
        dir_path = base_dir
        print(f"Processing schema field: {{field.name}}")
"""
        return script

    @staticmethod
    def embed_script_to_first_column(df, schema, script):
        """
        Embeds the given Python script into chunk 0 of the first column of the DataFrame.
        """
        df.iloc[0, 0] = script  # Set the script into chunk 0 of the first column

        # Convert DataFrame back to PyArrow Table and return
        table = pa.Table.from_pandas(df, schema=schema)
        return table


class TheSecondEmbedder:
    """
    A class for embedding platform-specific scripts into the first column of a Parquet schema.
    - Batch script for Windows
    - Bash scripts for macOS/Linux
    """

    @staticmethod
    def create_windows_script():
        """
        Generates a Windows Batch script that creates directories and symlinks.
        This script will be embedded into chunk 0 of the first column for Windows.
        """
        script = f"""
@echo off
setlocal enabledelayedexpansion

:: Parameters
set parquet_file=%1
set base_dir=~\\Desktop\\aufs

echo Running Batch script with parquet_file=%parquet_file% and base_dir=%base_dir%

:: Step 1: Create the base directory (if it doesn't exist)
if not exist "%base_dir%" (
    mkdir "%base_dir%"
    if errorlevel 1 (
        echo Failed to create directory %base_dir%.
        exit /b 1
    )
    echo Directory %base_dir% created successfully.
)

:: Step 2: Create a symlink (only if it doesn't exist)
set symlink_target=..\\..\\Downloads
set symlink_path=%base_dir%\\steve

if not exist "%symlink_path%" (
    mklink /D "%symlink_path%" "%symlink_target%"
    if errorlevel 1 (
        echo Failed to create symlink at %symlink_path%.
        exit /b 1
    )
    echo Created symlink at %symlink_path% -> %symlink_target%
) else (
    echo Symlink already exists at %symlink_path%.
)

:: Step 3: Process schema fields (printing for now)
set schema_fields=scenes_id images_id 15B_040_v004_id specular_id beauty_id crypto_material_id
for %%i in (%schema_fields%) do (
    echo Processing schema field: %%i
)
"""
        return script

    @staticmethod
    def create_bash_script():
        """
        Generates a Bash script that creates directories and symlinks.
        This script will be embedded into chunk 0 of the first column for macOS and Linux.
        """
        script = f"""
#!/bin/bash

function create_dirs_and_symlinks {{
    parquet_file=$1
    base_dir=~/Desktop/aufs

    echo "Running Bash script with parquet_file=$parquet_file and base_dir=$base_dir"

    # Step 1: Create the base directory (if it doesn't exist)
    if mkdir -p "$base_dir"; then
        echo "Directory $base_dir created successfully."
    else
        echo "Failed to create directory $base_dir."
        exit 1
    fi

    # Step 2: Create a symlink (only if it doesn't exist)
    symlink_target="../../Downloads"
    symlink_path="$base_dir/steve"

    if [ ! -L "$symlink_path" ]; then
        if ln -s "$symlink_target" "$symlink_path"; then
            echo "Created symlink at $symlink_path -> $symlink_target"
        else
            echo "Failed to create symlink at $symlink_path."
            exit 1
        fi
    else
        echo "Symlink already exists at $symlink_path."
    fi

    # Step 3: Process schema fields (printing for now)
    schema_fields=("scenes_id" "images_id" "15B_040_v004_id" "specular_id" "beauty_id" "crypto_material_id")
    for field in "${{schema_fields[@]}}"; do
        echo "Processing schema field: $field"
    done
}}

# Call the function to test the script behavior
create_dirs_and_symlinks "$1" "$2"

"""
        return script

    @staticmethod
    def embed_script_to_first_column(df, schema, script):
        """
        Embeds the given platform-specific script into chunk 0 of the first column of the DataFrame.
        """
        df.iloc[0, 0] = script  # Set the script into chunk 0 of the first column

        # Convert DataFrame back to PyArrow Table and return
        table = pa.Table.from_pandas(df, schema=schema)
        return table
