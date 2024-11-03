# src/aufs/user_tools/packaging/string_remapper.py

import os

class StringRemapper:
    def __init__(self, mappings_df=None):
        self.mappings_df = mappings_df

    def set_mappings(self, mappings_df):
        """Sets or updates the mappings DataFrame."""
        self.mappings_df = mappings_df

    def remap(self, id_column, id_value, target_columns):
        """
        Retrieve remap values based on an ID column, ID value, and target columns.
        Applies optional path logic based on REMAPTYPE in the mappings.
        
        Parameters:
        - id_column (str): Column to use as ID for lookup (e.g., 'FILE' or 'REMAPTHIS').
        - id_value (str): Value in the ID column to find the row.
        - target_columns (list of str): List of column names to retrieve values for remapping.
        
        Returns:
        - list of tuples: Each tuple contains (column_name, column_value), applying path logic if specified.
        """
        if self.mappings_df is None:
            raise ValueError("Mappings DataFrame is not set. Load a CSV file to initialize mappings.")

        # Locate the row based on ID column and ID value
        row = self.mappings_df[self.mappings_df[id_column] == id_value]
        if row.empty:
            raise ValueError(f"No mapping found for ID column '{id_column}' with value '{id_value}'")
        
        row_data = row.iloc[0]  # Get the first matching row
        remap_type = row_data.get('REMAPTYPE', 'string')  # Default to simple string remapping
        original_filename = os.path.basename(id_value)  # Extract filename for findfile types

        # Build and return list of tuples for each target column
        result = []
        for col in target_columns:
            map_to_path = row_data.get(col, None)
            if map_to_path and remap_type.endswith("-findfile-rec"):
                # Recursive search for file
                found_path = self._find_file(map_to_path, original_filename, recursive=True)
            elif map_to_path and remap_type.endswith("-findfile-norec"):
                # Non-recursive search for file
                found_path = self._find_file(map_to_path, original_filename, recursive=False)
            else:
                # Standard remapping without file search (for generic strings)
                found_path = map_to_path
            
            result.append((col, found_path))
        return result

    def _find_file(self, directory, filename, recursive=True):
        """Helper function to search for a file in a directory if path-specific remapping is specified."""
        if recursive:
            for root, _, files in os.walk(directory):
                if filename in files:
                    return os.path.join(root, filename)
        else:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path) and os.path.basename(item_path) == filename:
                    return item_path
        # Return None if file is not found
        return None
