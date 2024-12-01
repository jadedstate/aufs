# src/aufs/user_tools/packaging/version_controller.py

import pandas as pd
from PySide6.QtWidgets import QVBoxLayout, QLabel, QRadioButton, QLineEdit, QDialogButtonBox, QDialog
from PySide6.QtGui import QIntValidator

import os
import csv
from datetime import datetime

class VersionController:
    def __init__(self, root_path, recipient, user=None, v_format="v", padding=4, working_versions=None):
        self.root_path = root_path
        self.recipient = recipient
        self.user = user or "system"
        self.v_format = v_format
        self.padding = padding
        self.working_versions = working_versions if working_versions is not None else {}

    def get_item_version_path(self, item):
        """Define path to the item’s versioning directory."""
        # print("ROOT PATH: ",self.root_path)
        # print("RECIPIENT: ", self.recipient)
        # print("ITEM: ", item)
        version_dir = os.path.join(self.root_path, self.recipient, "versioning", item)
        os.makedirs(version_dir, exist_ok=True)
        return version_dir

    def retrieve_working_version(self, item, use_dialog=False):
        """
        Retrieve or initialize the working version for an item, based on existing version files.
        If `use_dialog` is True, prompt the user for versioning type selection.

        Returns:
            tuple: Formatted version ID and updated working_versions dictionary.
        """
        # Check if the item already exists in working_versions
        if item in self.working_versions:
            return self._format_version_id(self.working_versions[item]), self.working_versions

        # Initialize version if not in working_versions
        version_path = self.get_item_version_path(item)
        version_files = [os.path.join(version_path, f) for f in os.listdir(version_path) if f.endswith('.csv')]

        if "YYYYMMDD_PKGVERSION3PADDED" in item:
            # Filter files by current date
            current_date = datetime.utcnow().strftime('%Y%m%d')
            date_filtered_files = [
                file for file in version_files if current_date in os.path.basename(file)
            ]
            print(f"Filtered files for date {current_date}: {date_filtered_files}")
            previous_version = self._get_highest_version(date_filtered_files)
        else:
            previous_version = self._get_highest_version(version_files)

        # Prompt the user with the dialog if use_dialog is True
        if use_dialog:
            dialog = VersioningTypeDialog(item_name=item, parent=None)
            if dialog.exec_() == QDialog.Accepted:
                versioning_type = dialog.get_versioning_type()
            else:
                raise ValueError("Versioning type selection was cancelled.")
        else:
            versioning_type = "iterate"

        # Determine the working version based on versioning_type
        if isinstance(versioning_type, (int, str)) and str(versioning_type).isdigit():
            self.working_versions[item] = int(versioning_type)
        elif versioning_type == "iterate":
            self.working_versions[item] = previous_version + 1
        elif versioning_type == "current":
            self.working_versions[item] = previous_version
        else:
            raise ValueError(f"Unsupported versioning_type: {versioning_type}")

        return self._format_version_id(self.working_versions[item]), self.working_versions

    def _get_highest_version(self, files):
        """
        Get the highest version number from a list of CSV files.

        Args:
            files (list): List of file paths to scan for version numbers.

        Returns:
            int: The highest version number found, or 0 if no valid versions are found.
        """
        highest_version = 0
        print("Scanning files for highest version...")
        print(files)

        for file in files:
            print(f"Processing file: {file}")
            try:
                # Read the file into a DataFrame
                df = pd.read_csv(file, header=None)
                print(f"DataFrame loaded:\n{df}")

                # Check for VERSION header
                if "VERSION" in df.iloc[0].values:
                    version_index = list(df.iloc[0]).index("VERSION")
                    print(f"'VERSION' header found at index {version_index}.")
                    df = df.iloc[1:]  # Exclude the header row
                else:
                    version_index = 1  # Assume version is in the second column
                    print("No 'VERSION' header, using column index 1.")

                # Iterate over rows to find the highest version
                for _, row in df.iterrows():
                    try:
                        version = int(row[version_index])
                        print(f"Found version: {version}")
                        highest_version = max(highest_version, version)
                    except (ValueError, IndexError) as e:
                        print(f"Skipping invalid row: {row}. Error: {e}")
            except Exception as e:
                print(f"Error reading file {file}: {e}")
        
        print(f"Highest Version Found: {highest_version}")
        return highest_version

    def _get_latest_version_file(self, path):
        """Retrieve the latest timestamped CSV file in a given directory."""
        try:
            files = [f for f in os.listdir(path) if f.endswith('.csv')]
            if not files:
                return None
            # Sort files by timestamp embedded in filename and return the latest
            return os.path.join(path, sorted(files, key=lambda x: int(x.split('-')[-1].split('.')[0]))[-1])
        except Exception as e:
            print(f"Error retrieving latest version file: {e}")
            return None

    def _format_version_id(self, version_number):
        """Format the version ID based on the v_format and padding settings."""
        prefix = "v" if self.v_format == "v" else ("V" if self.v_format == "V" else "")
        return f"{prefix}{version_number:0{self.padding}d}"

    def log_version(self, item):
        """
        Log the version information for an item in a timestamped CSV file.
        If sub-items are associated, their versions are also updated.
        """
        version_path = self.get_item_version_path(item)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        log_path = os.path.join(version_path, f"{item}-{timestamp}.csv")
        
        version_id = self.working_versions[item]

        # Write the new version entry to a timestamped log file
        with open(log_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([datetime.utcnow().strftime('%Y%m%d'), version_id, self.user, item])

    def check_and_initialize_sub_items(self, item):
        """
        Load sub-items from thisitemsitems.csv. If empty, alert the user to populate it.
        Otherwise, load the list and ensure all sub-items are tracked.
        """
        sub_items_path = os.path.join(self.get_item_version_path(item), "thisitemsitems.csv")
        
        # Check if thisitemsitems.csv exists and is populated
        if not os.path.exists(sub_items_path):
            raise ValueError(f"No sub-items file found for '{item}'. Please populate 'thisitemsitems.csv'.")
        
        # Read and validate sub-items
        with open(sub_items_path, 'r') as csvfile:
            sub_items = [row[0] for row in csv.reader(csvfile) if row]
        
        if not sub_items:
            raise ValueError(f"Sub-items list for '{item}' is empty. Populate 'thisitemsitems.csv' to proceed.")
        
        return sub_items

class VersioningTypeDialog(QDialog):
    def __init__(self, item_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Versioning Type")
        self.setModal(True)
        self.selected_versioning_type = "iterate"  # Default
        self.selected_version = None

        # Layout for the dialog
        layout = QVBoxLayout(self)

        # Display the item name
        layout.addWidget(QLabel(f"Set versioning type for item: {item_name}"))

        # Add radio buttons for versioning type
        self.iterate_radio = QRadioButton("Iterate")
        self.iterate_radio.setChecked(True)  # Default selection
        self.current_radio = QRadioButton("Current")
        self.set_version_radio = QRadioButton("Set Version")

        layout.addWidget(self.iterate_radio)
        layout.addWidget(self.current_radio)
        layout.addWidget(self.set_version_radio)

        # Add input for version number (only visible for "Set Version")
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText("Enter version number")
        self.version_input.setValidator(QIntValidator(0, 9999))  # Allow only integers
        self.version_input.setVisible(False)
        self.version_input.setText("101")  # Default value
        self.set_version_radio.toggled.connect(lambda checked: self.version_input.setVisible(checked))
        layout.addWidget(self.version_input)

        # Add dialog buttons (OK/Cancel)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_versioning_type(self):
        """Return the selected versioning type and version (if applicable)."""
        if self.iterate_radio.isChecked():
            self.selected_versioning_type = "iterate"
        elif self.current_radio.isChecked():
            self.selected_versioning_type = "current"
        elif self.set_version_radio.isChecked():
            self.selected_versioning_type = int(self.version_input.text())
        return self.selected_versioning_type
