import pyarrow.parquet as pq
import pandas as pd

def build_metadata_df(parquet_file_path):
    # Load the parquet file metadata
    parquet_file = pq.ParquetFile(parquet_file_path)
    
    # Create an empty list to hold the metadata objects
    metadata_objects = []
    
    # 1. Add file-level (schema) metadata object
    metadata_objects.append({
        "Type": "schema",
        "ID": 0,
        "Description": "File-level metadata"
    })
    
    # 2. Add column-level metadata objects
    for col_id, schema_field in enumerate(parquet_file.schema):
        metadata_objects.append({
            "Type": "column",
            "ID": col_id,
            "Description": f"Column: {schema_field.name}"
        })
    
    # 3. Add row group-level metadata objects
    for row_group_id in range(parquet_file.num_row_groups):
        row_group_meta = parquet_file.metadata.row_group(row_group_id)
        metadata_objects.append({
            "Type": "rowgroup",
            "ID": row_group_id,
            "Description": f"Row Group {row_group_id} (rows {row_group_meta.num_rows})"
        })
    
    # Convert the metadata objects list into a DataFrame
    metadata_df = pd.DataFrame(metadata_objects)
    return metadata_df

# Usage
parquet_file_path = "your_parquet_file.parquet"
metadata_df = build_metadata_df(parquet_file_path)
print(metadata_df)
