import os
import sys
import pandas as pd
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')
sys.path.insert(0, src_path)

from src.aufs.user_tools.packaging.version_controller import VersionController

class StringRemapper:
    def __init__(self, mappings_df=None, root_path=None, recipient=None, user=None):
        """
        Initialize the StringRemapper with optional mappings DataFrame and versioning controls.
        
        Parameters:
        - mappings_df (pd.DataFrame): DataFrame containing remapping information.
        - root_path (str): Root path for versioning controller.
        - recipient (str): Recipient designation for versioning purposes.
        - user (str): User or process identifier for version logging.
        """
        self.mappings_df = mappings_df
        self.version_controller = None
        self.root_path = root_path # '/Users/uel/.aufs/config/jobs/active/unit/rr_mumbai/packaging'
        self.recipient = recipient # 'amolesh'
        self.user = user or "system"
        self.working_versions = {}

        self.version_controller = VersionController(
            root_path=self.root_path,
            recipient=self.recipient,
            user=self.user,
            working_versions=self.working_versions
        )

    def set_mappings(self, mappings_df):
        """Sets or updates the mappings DataFrame."""
        self.mappings_df = mappings_df

    def initialize_version_controller(self, v_format="v", padding=4):
        """
        Initialize or re-initialize the VersionController with specific settings.
        
        Parameters:
        - v_format (str): Prefix format ('v', 'V', or 'no').
        - padding (int): Number padding for version numbers.
        """
        # print("Boo from the version controller initializer....")
        self.version_controller = VersionController(
            root_path=self.root_path, 
            recipient=self.recipient, 
            user=self.user,
            v_format=v_format, 
            padding=padding,
            working_versions=self.working_versions
        )

    def _is_valid_value(self, value):
        """Check if a value is valid."""
        if value is None:
            return False
        if isinstance(value, float) and pd.isna(value):  # Handle NaN for float
            return False
        if isinstance(value, str) and not value.strip():  # Empty or whitespace-only strings
            return False
        return True  # Assume all other cases are valid

    def remap(self, id_column=None, id_value=None, target_columns=None, row_data=None, remap_type=None, ignore_columns=None):
        """
        Perform the remapping process, supporting direct row_data input.
        """
        ignore_columns = ignore_columns or []

        if row_data is not None:
            self.row_data = row_data.iloc[0]  # Convert to Series for easier access
        elif id_column and id_value and self.mappings_df is not None:
            row = self.mappings_df[self.mappings_df[id_column] == id_value]
            if row.empty:
                return {}  # No match found; return empty dictionary
            self.row_data = row.iloc[0]
        else:
            raise ValueError("Either row_data or a valid id_column and id_value must be provided.")

        # Set remap type
        self.remap_type = remap_type or self.row_data.get('REMAPTYPE', 'string')
        result = {}  # Initialize as a dictionary

        for col in target_columns:
            if col in ignore_columns:
                continue

            # Handle virtual columns
            if col in ["VERSION", "YYYYMMDD", "PKGVERSION3PADDED"]:
                if row_data is not None:
                    value = self._handle_virtual_column(col, row_data=self.row_data)
                else:
                    value = self._handle_virtual_column(col, id_value=id_value)
            else:
                # Regular columns
                if col in self.row_data:
                    value = self.row_data[col]
                    if isinstance(value, str) and value.strip():  # Check for valid non-empty strings
                        if col == "PADDING":
                            value = self._format_padding(value, self.row_data.get("PADDING_STYLE", "standard"))
                        elif col == "DOTEXTENSION":
                            value = self._adjust_dotextension(value, self.row_data.get("EXT_CASE", "default"))
                        elif self.remap_type.endswith("-findfile-rec"):
                            value = self._find_file(value, None, recursive=True)
                        elif self.remap_type.endswith("-findfile-norec"):
                            value = self._find_file(value, None, recursive=False)
                    else:
                        continue  # Skip invalid or empty values
                else:
                    continue  # Skip missing columns

            # Add valid mappings to the result dictionary
            if value:  # Ensure value is not None or empty
                result[col] = value

        return result

    def _handle_virtual_column(self, col, id_value=None, row_data=None):
        """Handles virtual columns that require versioning or date formatting."""
        # print("BooOOO from virtual columns handler, here is the row_data for reference: ")
        # print(row_data)
        if col == "VERSION" and self.version_controller:
            # Use PARENTITEM from row_data if available, otherwise fall back to id_value
            item = row_data.get("PARENTITEM") if row_data is not None else None
            if not item and id_value:
                item = os.path.basename(id_value)

            self.initialize_version_controller(v_format="v", padding=4)
            version, self.working_versions = self.version_controller.retrieve_working_version(item)
            return version

        elif col == "YYYYMMDD":
            return datetime.utcnow().strftime('%Y%m%d')

        elif col == "PKGVERSION3PADDED":
            # Use a special item name when row_data is available
            item = "YYYYMMDD_PKGVERSION3PADDED"
            self.initialize_version_controller(v_format="no", padding=3)
            version, self.working_versions = self.version_controller.retrieve_working_version(item)
            return version

        return ""

    def _format_padding(self, padding_value, style="standard"):
        """Format padding based on a specified style: standard, hashed, or dollar."""
        try:
            padding_length = len(str(int(padding_value)))
            padding_value = int(padding_value)
            # print(padding_length)
            if style == "standard":
                # Use '%0Xd' if padding_length is a single character, otherwise '%Xd'
                format_str = f"%0{padding_value}d" if padding_length == 1 else f"%{padding_value}d"
                return format_str

            elif style == "hashed":
                # Create a string of '#' characters matching the padding length
                return "#" * padding_value

            elif style == "dollar":
                # Append padding length to "$F"
                return f"$F{padding_value}"

        except ValueError:
            # Return the original value if it cannot be parsed as an integer
            return padding_value

    def _adjust_dotextension(self, extension, case_option):
        """Adjust file extension case based on the specified option."""
        if case_option == "upper":
            return extension.upper()
        elif case_option == "lower":
            return extension.lower()
        return extension  # Default: no change

    def _find_file(self, directory, filename, recursive=True):
        """Search for a file in a directory with optional recursion."""
        if recursive:
            for root, _, files in os.walk(directory):
                if filename in files:
                    return os.path.join(root, filename)
        else:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path) and os.path.basename(item_path) == filename:
                    return item_path
        return None

    def log_final_versions(self):
        """Log each final version in working_versions to the versioning directory."""
        print("THESE are the WORKING_VERSIONS: ")
        print(self.working_versions)
        for item in self.working_versions:
            self.version_controller.log_version(item)