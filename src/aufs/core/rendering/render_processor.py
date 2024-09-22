# receiver.py

import pyarrow as pa
import pyarrow.parquet as pq
from src.aufs.utils import validate_schema, validate_data, validate_metadata, invoke_renderer

class InputManager:
    def __init__(self):
        self.package = {}

    def receive_and_validate(self, schema, data=None, metadata=None, compression='SNAPPY', partitioning=None):
        """
        Receives and validates schema, data, and metadata. Halts at the first invalid component.
        If no data is provided, it creates an empty table with the provided schema.
        
        :param schema: User-provided schema.
        :param data: User-provided data.
        :param metadata: Optional metadata.
        :param compression: Compression setting for the Parquet file.
        :param partitioning: Optional partitioning information.
        :return: A dictionary with the validated components or None if validation fails.
        """
        # Validate schema
        schema_valid = validate_schema(schema)
        if not schema_valid:
            print(f"Schema validation failed")
            return None

        # Handle the case where data is None (create an empty table with the schema)
        if data is None:
            data = {field.name: [] for field in schema}  # Create an empty dictionary based on schema
            print("No data provided, creating an empty table with the provided schema.")
        
        # Validate data (only if data was provided or an empty dataset was generated)
        data_valid, data_msg = validate_data(data, schema)
        if not data_valid:
            print(f"Data validation failed: {data_msg}")
            return None

        # Validate metadata (optional)
        if metadata:
            metadata_valid, metadata_msg = validate_metadata(metadata)
            if not metadata_valid:
                print(f"Metadata validation failed: {metadata_msg}")
                return None

        # Package all validated parts into a single structure
        package = {
            'schema': schema,
            'data': data,
            'metadata': metadata,
            'compression': compression,
            'partitioning': partitioning
        }

        return package

    def process_render(self, schema, data, metadata, output_path, compression='SNAPPY', partitioning=None):
        """
        Receives the validated package, and invokes the renderer to write the Parquet file.
        
        :param schema: The schema for the Parquet file.
        :param data: The data for the Parquet file.
        :param metadata: Optional metadata for the Parquet file.
        :param output_path: The path to write the Parquet file.
        :param compression: The compression to use for the Parquet file.
        :param partitioning: Optional partitioning for the Parquet file.
        """
        # Package and validate the data
        package = self.receive_and_validate(schema, data, metadata, compression, partitioning)
        
        if package:
            # Invoke the renderer to write the Parquet file
            invoke_renderer(package, output_path)
            print(f"Rendering successful: Parquet file written to {output_path}")
        else:
            # Generic failure message
            print("Render failed. Please fix your data and try again.")
