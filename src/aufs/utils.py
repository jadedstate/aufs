# utils.py

import pyarrow as pa
from src.aufs.core.renderer import render_table

def validate_schema(fields):
    """
    Validates the schema fields and returns detailed error information if invalid.
    :param fields: A list of fields defining the schema.
    :return: Tuple (bool, str) where bool indicates if the schema is valid, 
             and str contains error details if any.
    """
    try:
        schema = pa.schema(fields)
        return True, "Schema is valid"
    except Exception as e:
        return False, f"Schema validation failed: {str(e)}"

def validate_data(data, schema):
    """
    Validates that the data is in a valid format (pyarrow.Table) and that it matches the provided schema.
    :param data: A pyarrow.Table or a Python dictionary.
    :param schema: The schema to validate against.
    :return: Tuple (bool, str) where bool indicates if the data is valid for rendering,
             and str contains error details if any.
    """
    try:
        if isinstance(data, pa.Table):
            # If the data is already a pyarrow.Table, check that the schema matches
            if data.schema == schema:
                return True, "Data is valid and matches schema"
            else:
                return False, "Data schema does not match the provided schema"
        else:
            # If the data is a dictionary, raise an error as it's not ready for rendering
            return False, "Data is not in the correct format (pyarrow.Table)"
    except Exception as e:
        return False, f"Data validation failed: {str(e)}"
    
def validate_metadata(metadata):
    """
    Validates the metadata structure.
    :param metadata: A dictionary of metadata.
    :return: Tuple (bool, str) where bool indicates if the metadata is valid,
             and str contains error details if any.
    """
    try:
        # Example check for specific metadata keys (e.g., "compression", "version")
        required_keys = ["compression", "version"]
        for key in required_keys:
            if key not in metadata:
                raise ValueError(f"Missing required metadata key: {key}")
        
        return True, "Metadata is valid"
    except Exception as e:
        return False, f"Metadata validation failed: {str(e)}"

def invoke_renderer(package, file_path):
    """
    Invokes the renderer with the validated package.
    
    :param package: A dictionary containing schema, data, metadata, and setup info.
    :param file_path: The path where the Parquet file will be written.
    """
    # Unpack the package
    schema = package['schema']
    data = package['data']
    metadata = package['metadata']
    compression = package['compression']
    
    # Call the write_parquet_file function
    render_table(data, file_path, compression=compression)  # Schema is part of the table, no need to pass it explicitly
