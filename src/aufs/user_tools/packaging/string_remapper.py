import os
import sys
import pandas as pd
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, 
                               QMessageBox)

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
        self.unprocessed_target_columns = []

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

    def remap(self, id_column=None, id_value=None, target_columns=None, virtual_headers=None, use_dialog=False, row_data=None, remap_type=None, ignore_columns=None, root_job_path=None, use_custom_remapper=True, interrupt=False):
        ignore_columns = ignore_columns or []
        never_custom_cols = ["PADDING"]  # Add any other columns to exclude from custom remapping
        self.unprocessed_target_columns = [
            col for col in target_columns if col.isupper() and col not in never_custom_cols
        ]  # Initialize tracking
        
        # Set default virtual headers if not provided
        if virtual_headers is None:
            virtual_headers = ["VERSION", "YYYYMMDD", "PKGVERSION3PADDED"]
        
        result = {}
        self.job_templates_path = os.path.join(root_job_path, "templates") if root_job_path else None

        if row_data is not None:
            self.row_data = row_data.iloc[0]
        elif id_column and id_value and self.mappings_df is not None:
            row = self.mappings_df[self.mappings_df[id_column] == id_value]
            if row.empty:
                return {}
            self.row_data = row.iloc[0]
        else:
            raise ValueError("Either row_data or a valid id_column and id_value must be provided.")

        remap_type = remap_type or self.row_data.get('REMAPTYPE', 'string')

        for col in target_columns:
            if col in ignore_columns:
                continue

            value = None
            if col in self.row_data:
                value = self.row_data[col]
                if col == "PADDING":
                    value = self._format_padding(value, self.row_data.get("PADDING_STYLE", "standard"))
                elif col == "DOTEXTENSION":
                    value = self._adjust_dotextension(value, self.row_data.get("EXT_CASE", "default"))
            elif col in virtual_headers:  # Check against the dynamic `virtual_headers`
                value = self._handle_virtual_column(col, row_data=self.row_data, use_dialog=use_dialog)

            # If value is valid, add to result and mark column as processed
            if self._is_valid_value(value):
                result[col] = value
                if col in self.unprocessed_target_columns:
                    self.unprocessed_target_columns.remove(col)

        # Custom remapping for remaining variables
        if use_custom_remapper and self.unprocessed_target_columns:
            custom_remapper = CustomVariableRemapper(
                mappings_df=self.mappings_df,
                root_path=self.root_path,
                recipient=self.recipient,
                user=self.user,
                job_templates_path=self.job_templates_path
            )
            custom_results = custom_remapper.custom_remap(self.unprocessed_target_columns)
            result.update(custom_results)  # Merge custom remapping results into the final output

        return result

    def _handle_virtual_column(self, col, id_value=None, row_data=None, use_dialog=False):
        """Handles virtual columns that require versioning or date formatting."""
        # print("BooOOO from virtual columns handler, here is the row_data for reference: ")
        # print(row_data)
        if col == "VERSION" and self.version_controller:
            # Use PARENTITEM from row_data if available, otherwise fall back to id_value
            item = row_data.get("PARENTITEM") if row_data is not None else None
            if not item and id_value:
                item = os.path.basename(id_value)

            if self._is_valid_value(item):
                self.initialize_version_controller(v_format="v", padding=4)
                version, self.working_versions = self.version_controller.retrieve_working_version(item, use_dialog=use_dialog)
                return version
            else:
                return
        elif col == "YYYYMMDD":
            return datetime.utcnow().strftime('%Y%m%d')

        elif col == "PKGVERSION3PADDED":
            # Use a special item name when row_data is available
            item = "YYYYMMDD_PKGVERSION3PADDED"
            self.initialize_version_controller(v_format="no", padding=3)
            version, self.working_versions = self.version_controller.retrieve_working_version(item, use_dialog=use_dialog)
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

class CustomVariableRemapper(StringRemapper):
    TEMPLATE_FILENAME = "custom_aufs_pkg_template.csv"

    def __init__(self, job_templates_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_templates_path = job_templates_path

    def _initialize_template(self):
        """Ensure the custom template CSV exists and has the required structure."""
        template_path = os.path.join(self.job_templates_path, self.TEMPLATE_FILENAME)
        if not os.path.exists(template_path):
            df = pd.DataFrame(columns=["Variable", "Action", "Value"])
            df.to_csv(template_path, index=False)
        return pd.read_csv(template_path)

    def _update_template(self, new_entries):
        """Add new entries to the template CSV."""
        template_path = os.path.join(self.job_templates_path, self.TEMPLATE_FILENAME)
        template_df = pd.read_csv(template_path)
        updated_df = pd.concat([template_df, pd.DataFrame(new_entries)], ignore_index=True)
        updated_df.to_csv(template_path, index=False)

    def custom_remap(self, remaining_vars):
        """
        Remap remaining variables using the custom template.

        Parameters:
        - remaining_vars (list): List of unprocessed uppercase variables.

        Returns:
        - dict: A dictionary containing remapped results in the form {Variable: Value}.
        """
        # Load or initialize the custom template
        template = self._initialize_template()
        # print("This is the template content: ")
        # print(template)

        # Prepare the results dictionary
        results = {}

        # Track variables requiring user input
        user_input_needed = []
        # print("Remaining VARIABLES are: ", remaining_vars)

        for variable in remaining_vars:
            # Check if the variable exists in the template
            match = template.loc[template["Variable"] == variable]
            if not match.empty:
                action = match.iloc[0]["Action"]
                value = match.iloc[0]["Value"]

                if action == "remap":
                    # Add to results directly
                    results[variable] = value
                # If "ignore", skip this variable
            else:
                # Track for user input
                user_input_needed.append(variable)

        # Handle unmapped variables via user input
        if user_input_needed:
            user_defined_entries = self._prompt_user_for_mappings(user_input_needed)
            self._update_template(user_defined_entries)  # Update template with user input

            # Add user-defined mappings to results
            for entry in user_defined_entries:
                if entry["Action"] == "remap":
                    results[entry["Variable"]] = entry["Value"]

        return results

    def _prompt_user_for_mappings(self, variables):
        """Prompt the user for input on unmapped variables."""
        dialog = TemplateBuilderDialog(variables)
        if dialog.exec() == QDialog.Accepted:
            return dialog.get_mappings()
        return []

class TemplateBuilderDialog(QDialog):
    def __init__(self, variables, parent=None):
        super().__init__(parent)
        self.variables = variables
        self.mappings = []

        self.setWindowTitle("Custom Variable Mapping")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # Add widgets for each variable
        self.entries = []
        for var in self.variables:
            row_layout = QHBoxLayout()
            
            label = QLabel(var, self)
            dropdown = QComboBox(self)
            dropdown.addItems(["ignore", "remap"])
            text_input = QLineEdit(self)

            row_layout.addWidget(label)
            row_layout.addWidget(dropdown)
            row_layout.addWidget(text_input)
            layout.addLayout(row_layout)

            # Store entry components
            self.entries.append((var, dropdown, text_input))

        # Add Save and Cancel buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save", self)
        cancel_button = QPushButton("Cancel", self)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        save_button.clicked.connect(self.save_and_close)
        cancel_button.clicked.connect(self.close)

    def save_and_close(self):
        """Save user input and close the dialog."""
        self.mappings = []
        for var, dropdown, text_input in self.entries:
            action = dropdown.currentText()
            value = text_input.text()

            # Check if dropdown=remap and textInput=na|NaN|None
            if action == "remap" and value.strip().lower() in {"na", "nan", "none"}:
                confirmation = QMessageBox.question(
                    self,
                    "Confirm Empty Value",
                    f"The value for variable '{var}' is '{value}', which will be treated as an empty string. Do you want to proceed?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if confirmation == QMessageBox.Yes:
                    value = ""  # Treat as an empty string
                else:
                    continue  # Skip saving this entry

            # Check if textInput=<valid value> & dropdown!=remap
            elif value.strip() and action != "remap":
                confirmation = QMessageBox.question(
                    self,
                    "Confirm Action Adjustment",
                    f"The value for variable '{var}' is '{value}', but the action is set to '{action}'. Do you want to change the action to 'remap'?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if confirmation == QMessageBox.Yes:
                    action = "remap"  # Adjust action to 'remap'

            # Save the mapping
            self.mappings.append({"Variable": var, "Action": action, "Value": value})

        self.accept()

    def get_mappings(self):
        """Return the collected mappings."""
        return self.mappings
