import sys
import os
import subprocess
import zipfile
import shutil
import random
import string
import csv
from pathlib import PureWindowsPath, PurePosixPath
import pandas as pd
from pathlib import Path
import hashlib
import json
import tempfile
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QCheckBox, QComboBox,
                               QDialog, QListWidget, QListWidgetItem, QDockWidget, QMessageBox,QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QPushButton, QDialog)
import pandas as pd

from PySide6.QtCore import Qt
import pyarrow as pa

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.core.rendering.render_processor import InputManager
from src.aufs.utils import validate_schema
from src.aufs.core.rendering.the_third_embedder import TheThirdEmbedder
from user_adder_smb import SMBUserAdder
import src_dest_linking_01

def get_platform_dictionary():
    return {
        "win_script": "0",
        "darwin_script": "1",
        "linux_script": "2"
    }

class SchemaWidget(QDialog):
    def __init__(self, schema, source_df, parent=None):
        super().__init__(parent)
        self.schema = schema
        self.source_df = source_df
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Create a table widget to display schema columns and source data
        self.table_widget = QTableWidget(self)
        self.table_widget.setColumnCount(len(self.schema.names))
        self.table_widget.setRowCount(len(self.source_df))

        # Set table headers to schema names
        self.table_widget.setHorizontalHeaderLabels(self.schema.names)

        # Populate the table with source data
        for row_idx in range(len(self.source_df)):
            for col_idx, col_name in enumerate(self.schema.names):
                if col_name == 'DEST':
                    # Place DEST column in the second position
                    value = self.source_df['DEST'].iloc[row_idx]
                else:
                    value = self.source_df.iloc[row_idx, col_idx]
                self.table_widget.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

        layout.addWidget(self.table_widget)

        # Add a button to confirm or submit the table
        submit_button = QPushButton("Submit", self)
        submit_button.clicked.connect(self.submit_data)
        layout.addWidget(submit_button)

        self.setLayout(layout)

    def submit_data(self):
        # Process the data and close the dialog
        self.accept()

    def get_updated_dataframe(self):
        # Collect the modified data from the table widget back into a DataFrame
        updated_data = []
        for row_idx in range(self.table_widget.rowCount()):
            row_data = {}
            for col_idx, col_name in enumerate(self.schema.names):
                item = self.table_widget.item(row_idx, col_idx)
                row_data[col_name] = item.text() if item else None
            updated_data.append(row_data)
        return pd.DataFrame(updated_data)

class WranglerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Setup directories (from OSFSToSchemaApp)
        self.setup_aufs_directories()

        # Initialize schema, data, path, name, and metadata status
        self.path_status = "Not Set"
        self.name_status = "Not Set"
        self.schema_status = "Not Set"
        self.data_status = "Not Set"
        self.metadata_status = "Not Set"

        # Set up the correct base path for the scripts directory
        # Adjust the path below to match where the core/net directory resides relative to this file
        self.scripts_base_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'net')

        # Initialize TheThirdEmbedder with the correct base path
        self.embedder = TheThirdEmbedder(base_path=self.scripts_base_path)
        self.input_manager = InputManager()
        self.schema = None
        self.data = None
        self.metadata = False

        self.setWindowTitle("Parquet Wrangler")
        self.setGeometry(100, 100, 1000, 1200)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)

        # Parquet name and output path input
        self.name_label = QLabel("Parquet Name:")
        self.name_input = QLineEdit()

        self.path_label = QLabel("Output Path:")
        self.path_input = QLineEdit()
        self.path_input.setText('~/.aufs/parquet/dev')

        # Add buttons to set path and filename in summary
        self.set_path_button = QPushButton("Set Path", self)
        self.set_path_button.clicked.connect(lambda: self.update_summary(item_name='path', status='Set'))
        self.main_layout.addWidget(self.set_path_button)

        self.set_name_button = QPushButton("Set Filename", self)
        self.set_name_button.clicked.connect(lambda: self.update_summary(item_name='name', status='Set'))
        self.main_layout.addWidget(self.set_name_button)

        # Add Reset Summary button above the filename input box
        self.reset_summary_button = QPushButton("Reset Summary", self)
        self.reset_summary_button.clicked.connect(self.reset_all)
        self.main_layout.addWidget(self.reset_summary_button)

        self.main_layout.addWidget(self.name_label)
        self.main_layout.addWidget(self.name_input)
        self.main_layout.addWidget(self.path_label)
        self.main_layout.addWidget(self.path_input)

        # Add schema driver
        self.add_schema_driver()

        # Add data and metadata drivers
        self.add_data_driver()
        self.add_metadata_driver()

        # Render Button
        self.render_button = QPushButton("Render Parquet", self)
        self.render_button.clicked.connect(self.render_parquet)
        self.main_layout.addWidget(self.render_button)

        # Summary display
        self.summary_label = QLabel("Current State Summary:")
        self.summary_output = QLabel()
        self.main_layout.addWidget(self.summary_label)
        self.main_layout.addWidget(self.summary_output)

        # Initialize the summary
        self.update_summary()

    def add_schema_driver(self):
        """Add schema driver as a dock widget."""
        schema_driver = QDockWidget("Schema Driver", self)
        schema_driver.setAllowedAreas(Qt.LeftDockWidgetArea)

        # Schema handling UI
        self.schema_tool = QWidget()
        schema_layout = QVBoxLayout(self.schema_tool)

        self.schema_open_button = QPushButton("Open", self)
        self.schema_validate_button = QPushButton("Validate", self)
        self.schema_pass_to_wrangler_button = QPushButton("Pass to Wrangler", self)

        schema_layout.addWidget(self.schema_open_button)
        schema_layout.addWidget(self.schema_validate_button)
        schema_layout.addWidget(self.schema_pass_to_wrangler_button)

        self.schema_open_button.clicked.connect(self.open_existing)
        self.schema_validate_button.clicked.connect(self.validate_schema)
        self.schema_pass_to_wrangler_button.clicked.connect(self.pass_to_wrangler)

        self.schema_list = QListWidget(self)
        schema_layout.addWidget(self.schema_list, stretch=1)

        self.refresh_button = QPushButton("Refresh List", self)
        schema_layout.addWidget(self.refresh_button)
        self.refresh_button.clicked.connect(self.refresh_schema_list)

        self.zip_as_dir_checkbox = QCheckBox("Include zip name as parent directory", self)
        schema_layout.addWidget(self.zip_as_dir_checkbox)
        self.zip_as_dir_checkbox.stateChanged.connect(self.toggle_zip_as_dir)

        schema_driver.setWidget(self.schema_tool)
        self.addDockWidget(Qt.LeftDockWidgetArea, schema_driver)

        # Populate schema list on startup
        self.refresh_schema_list()

    def toggle_zip_as_dir(self, state):
        self.include_zip_as_dir = (state == Qt.Checked)
        print(f"Include zip file name as directory: {self.include_zip_as_dir}")

    def setup_aufs_directories(self):
        """Ensure that the ~/.aufs/osfsdirstoschema directory structure is in place."""
        home_dir = str(Path.home())
        self.aufs_root = os.path.join(home_dir, '.aufs', 'osfsdirstoschema')
        self.working_dir = os.path.join(self.aufs_root, 'working')
        self.saved_dir = os.path.join(self.aufs_root, 'saved')

        os.makedirs(self.working_dir, exist_ok=True)
        os.makedirs(self.saved_dir, exist_ok=True)

    def refresh_schema_list(self):
        """Refresh the list of schemas, greying out the ones that are currently open."""
        self.schema_list.clear()

        for schema_file in os.listdir(self.saved_dir):
            if schema_file.endswith('.zip'):
                item_text = schema_file
                working_path = os.path.join(self.working_dir, schema_file.replace('.zip', ''))

                item = QListWidgetItem(item_text)

                if os.path.exists(working_path):
                    item.setFlags(Qt.NoItemFlags)  # Grey out the item
                    item.setText(f"{item_text} (In Progress)")

                self.schema_list.addItem(item)

    def open_existing(self):
        """Open an existing schema from the ~/.aufs/osfsdirstoschema/saved directory."""
        selected_item = self.schema_list.currentItem()
        if selected_item:
            zip_file = selected_item.text().replace(" (In Progress)", "")
            self.start_subprocess(os.path.join(self.saved_dir, zip_file))

    def generate_id(self, parent_name, dir_name):
        return hashlib.sha256(f"{parent_name}-{dir_name}".encode()).hexdigest()

    def build_directory_tree_metadata(self, dir_ids, parent_ids, dir_names):
        tree = {}
        for dir_id, parent_id, dir_name in zip(dir_ids, parent_ids, dir_names):
            if parent_id not in tree:
                tree[parent_id] = []
            tree[parent_id].append({"id": dir_id, "name": dir_name})
        return tree

    def dynamic_schema_field_maker(self, package_full_df):
        """
        Creates a list of tuples representing field names and types for a dynamic schema.
        This method checks for the HASHEDFILE column in package_full_df and adds it if necessary.
        """
        fields = []

        # Check if HASHEDFILE column exists, if not, generate one
        if 'HASHEDFILE' not in package_full_df.columns:
            package_full_df['HASHEDFILE'] = package_full_df.apply(
                lambda row: self.generate_id(row['DEST'], row['SRC']), axis=1)

        # Go through each file link in the DEST field and create fields for it
        for idx, row in package_full_df.iterrows():
            dest = row['DEST']
            hashed_file = row['HASHEDFILE']

            # Create column name (following directory naming convention, but with '-file')
            file_column_name = f"{dest}-file"

            # Create a field with the column name, add HASHEDFILE as metadata
            fields.append(
                pa.field(file_column_name, pa.string(), metadata={
                    'HASHEDFILE': hashed_file.encode('utf-8')
                })
            )

        return fields

    def generate_schema_for_link_packaging(self, package_full_df, use_dynamic_schema=False):
        """
        Generates a PyArrow schema for packaging links (DEST field) based on the provided package_full_df.
        This method creates fields for both directories and files, adds metadata for links, and includes the
        original schema functionalities like platform scripts and directory UUID metadata.
        """
        try:
            fields = []  # Holds PyArrow fields for each directory and file (column)
            dir_ids = []  # List of UUIDs for each directory
            parent_ids = []  # List of UUIDs for parent directories
            dir_names = []  # List of directory names
            uuid_dirname_mapping = {}  # UUID to directory name mapping
            directory_tree = {}  # Directory tree to store parent-child relationships

            # Iterate over each DEST value (file path) in the package_full_df
            for dest in package_full_df['DEST']:
                directories = dest.split(os.sep)[:-1]  # Split the DEST path into directories, exclude the file
                file_name = os.path.basename(dest)

                parent_uuid = None
                for i, directory in enumerate(directories):
                    # Full path of the directory up to this level
                    dir_path = os.sep.join(directories[:i + 1])
                    # Generate UUID for this directory level
                    dir_uuid = self.generate_id(directory, dir_path)

                    # Map UUID to directory name if not already mapped
                    if dir_uuid not in uuid_dirname_mapping:
                        uuid_dirname_mapping[dir_uuid] = directory

                        # Link parent to child in the directory tree if there's a parent
                        if parent_uuid:
                            if parent_uuid not in directory_tree:
                                directory_tree[parent_uuid] = []
                            directory_tree[parent_uuid].append({"id": dir_uuid, "name": directory})

                    parent_uuid = dir_uuid  # Update parent for the next level

                    # Add field for the directory if we haven't done it yet
                    if i == len(directories) - 1:  # Only create field for the final directory in the path
                        dir_field_name = f"{directory}-dir"
                        if dir_field_name not in [f.name for f in fields]:
                            fields.append(pa.field(dir_field_name, pa.string()))

                # Now handle the file part of the DEST
                file_uuid = self.generate_id(directories[-1], file_name)
                uuid_dirname_mapping[file_uuid] = file_name
                file_field_name = f"{file_name}-file"
                fields.append(pa.field(file_field_name, pa.string(), metadata={'HASHEDFILE': file_uuid.encode('utf-8')}))

            # Create the PyArrow schema with the fields
            schema = pa.schema(fields)

            # Add metadata for directory tree and UUID mapping
            metadata = schema.metadata or {}
            metadata[b'directory_tree'] = json.dumps(directory_tree).encode('utf-8')
            metadata[b'uuid_dirname_mapping'] = json.dumps(uuid_dirname_mapping).encode('utf-8')

            # Retrieve platform scripts and add to metadata
            platform_dictionary = get_platform_dictionary()
            metadata[b'platform_scripts'] = json.dumps(platform_dictionary).encode('utf-8')

            # Update schema with metadata
            schema = schema.with_metadata(metadata)

            # Set schema to self and return it
            self.schema = schema
            return schema

        except Exception as e:
            print(f"Error in generate_schema_for_link_packaging: {e}")
            raise

    def source_destination_linking(self, zip_file_path):
        """
        This method reads the CSV equivalent of the package file, scrapes the files from the unzipped directory,
        and invokes the new widget.
        """
        try:
            # Replace .zip with .csv and read the CSV into a Pandas DataFrame
            csv_file_path = zip_file_path.replace(".zip", ".csv")
            package_full_df = pd.read_csv(csv_file_path)

            # Unzip the file and scrape for files (used as the 'template schema' for the dialog)
            temp_dir = self.unzip_to_temp(zip_file_path)
            template_schema = self.scrape_for_files(temp_dir)

            # Invoke the new widget for user interaction (SourceDestinationLinkingDialog)
            dialog = src_dest_linking_01.SourceDestinationLinkingDialog(package_full_df, template_schema)
            
            # Show the dialog and wait for the user to finish the interaction
            if dialog.exec() == QDialog.Accepted:
                # Retrieve the modified DataFrame after user interaction
                modified_package_df = dialog.get_updated_dataframe()

                # Call the generate_schema_for_link_packaging with use_dynamic_schema=True
                schema = self.generate_schema_for_link_packaging(modified_package_df)

                # Set the schema directly on WranglerApp
                self.schema = schema

                # Update the summary to show that the schema is "Set"
                self.update_summary(item_name='schema', status='Set')

                print("Schema for package links set and summary updated.")
                QMessageBox.information(self, "Wrangler", "Schema for package links has been set successfully!")

            else:
                print("Source-Destination linking dialog was canceled or closed.")

        except Exception as e:
            print(f"Error in source_destination_linking: {e}")
            QMessageBox.critical(self, "Error", f"Failed to process package file: {e}")

        finally:
            # Ensure the temporary directory is cleaned up after processing
            self.cleanup_temp_dir(temp_dir)

    def generate_schema(self, zip_file, use_dynamic_schema=False):
        temp_dir = self.unzip_to_temp(zip_file)

        try:
            root_path = temp_dir
            scraped_dirs = self.scrape_directories(root_path)

            fields = []  # Holds PyArrow fields for each directory (column)
            dir_ids = []  # List of UUIDs for each directory
            parent_ids = []  # List of UUIDs for parent directories
            dir_names = []  # List of directory names
            uuid_dirname_mapping = {}  # UUID to directory name mapping

            # Iterate over each scraped directory to generate fields and UUIDs
            for dir_path in scraped_dirs:
                dir_name = os.path.basename(dir_path)
                parent_path = os.path.dirname(dir_path)
                parent_name = os.path.basename(parent_path) if parent_path != root_path else 'tree_root'  # Set 'tree_root' for the parent of root directories

                # Generate UUID (unique ID) for current directory and parent directory
                dir_id = self.generate_id(parent_name, dir_name)
                parent_id = self.generate_id('tree_root', parent_name) if parent_name == 'tree_root' else self.generate_id(os.path.basename(os.path.dirname(parent_path)), parent_name)

                # Store directory names and their corresponding UUIDs
                dir_ids.append(dir_id)
                parent_ids.append(parent_id)
                dir_names.append(dir_name)
                uuid_dirname_mapping[dir_id] = dir_name  # UUID to directory name mapping

                # Create column name as parent-name-dir and add as a field
                column_name = f"{parent_name}-{dir_name}-dir"
                fields.append(pa.field(column_name, pa.string()))

            # Optionally add dynamic fields (if required in future)
            if use_dynamic_schema:
                dynamic_fields = self.dynamic_schema_field_maker()  # Adds extra fields dynamically
                for name, dtype in dynamic_fields:
                    fields.append(pa.field(name, dtype))

            # Create a PyArrow schema with the generated fields
            schema = pa.schema(fields)

            # Build directory tree metadata using UUIDs
            tree_metadata = self.build_directory_tree_metadata(dir_ids, parent_ids, dir_names)

            # Add metadata to the schema
            metadata = schema.metadata or {}
            metadata[b'directory_tree'] = json.dumps(tree_metadata).encode('utf-8')  # Encode the full directory tree
            metadata[b'uuid_dirname_mapping'] = json.dumps(uuid_dirname_mapping).encode('utf-8')  # Add UUID mapping
            platform_dictionary = get_platform_dictionary()
            metadata[b'platform_scripts'] = json.dumps(platform_dictionary).encode('utf-8')  # Add platform scripts

            # Update schema with metadata
            schema = schema.with_metadata(metadata)

            # Set schema to self
            self.schema = schema
            return schema

        finally:
            # Cleanup the temporary directory
            self.cleanup_temp_dir(temp_dir)

    def unzip_to_temp(self, zip_file):
        working_dir = tempfile.mkdtemp()

        if self.zip_as_dir_checkbox.isChecked():
            zip_dir_name = os.path.splitext(os.path.basename(zip_file))[0]
            zip_dir = os.path.join(working_dir, zip_dir_name)
            os.makedirs(zip_dir, exist_ok=True)
            temp_dir = zip_dir
        else:
            temp_dir = working_dir

        print(f"Unzipping to temporary directory: {temp_dir}")

        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        return working_dir

    def scrape_for_files(self, root_path, clean_root=True):
        """
        Scrape all files from the given root_path and return absolute paths to each file.
        Optionally clean the root path from the file paths if clean_root is True.
        """
        scraped_files = []
        for root, _, files in os.walk(root_path, followlinks=False):
            for file in files:
                file_path = os.path.join(root, file)
                if clean_root:
                    file_path = file_path.replace(root_path, '').lstrip(os.sep)
                scraped_files.append(file_path)
        print(f"Scraped files from {root_path}: {scraped_files}")
        return scraped_files

    def remove_temp_dir_from_schema(self, template_schema, temp_dir):
        """
        Removes the temp_dir path prefix from each entry in the template_schema.
        """
        return [path.replace(temp_dir, '').lstrip(os.sep) for path in template_schema]

    def scrape_directories(self, root_path):
        scraped_dirs = []
        for root, dirs, _ in os.walk(root_path, followlinks=False):
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                scraped_dirs.append(dir_path)
        print(f"Scraped directories from {root_path}: {scraped_dirs}")
        return scraped_dirs

    def cleanup_temp_dir(self, temp_dir):
        print(f"Cleaning up temporary directory: {temp_dir}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    def validate_schema(self):
        selected_item = self.schema_list.currentItem()
        if selected_item:
            zip_file = selected_item.text().replace(" (In Progress)", "")
            zip_file_path = os.path.join(self.saved_dir, zip_file)
            schema = self.generate_schema(zip_file_path)
            schema_valid = validate_schema(schema)

            if schema_valid:
                print("Schema validated successfully.")
                QMessageBox.information(self, "Validation", "Schema validated successfully!")
            else:
                print("Schema validation failed.")
                QMessageBox.warning(self, "Validation Failed", "Schema validation failed.")

            return schema_valid
        else:
            print("No schema selected for validation.")
            return False

    def pass_to_wrangler(self):
        selected_item = self.schema_list.currentItem()
        if selected_item:
            zip_file = selected_item.text().replace(" (In Progress)", "")
            zip_file_path = os.path.join(self.saved_dir, zip_file)

            if zip_file.startswith("packaging"):
                # If the selected item starts with 'packaging', invoke source_destination_linking
                self.source_destination_linking(zip_file_path)
            else:
                # Otherwise, use the regular generate_schema method
                schema = self.generate_schema(zip_file_path)

                # Set the schema directly on WranglerApp
                self.schema = schema

                # Update the summary to show that the schema is "Set"
                self.update_summary(item_name='schema', status='Set')

                print("Schema set and summary updated.")
                print(self.schema)
                QMessageBox.information(self, "Wrangler", "Schema has been set successfully!")

    def start_subprocess(self, zip_file):
        current_dir = os.path.dirname(__file__)
        sp_script_path = os.path.join(current_dir, 'os_fs_dirs_to_schema_sp.py')
        python_interpreter = sys.executable
        subprocess.Popen([python_interpreter, sp_script_path, zip_file], start_new_session=True)

####

    def add_data_driver(self):
        """Add data driver"""
        data_driver = QDockWidget("Data Driver", self)
        data_driver.setAllowedAreas(Qt.LeftDockWidgetArea)

        data_widget = QWidget()
        data_layout = QVBoxLayout()
        # Protocol list in the data driver
        protocol_label = QLabel("Available Protocols:")
        self.protocol_list = QListWidget()
        self.populate_protocol_list()  # Populate the protocol list
        # In the add_data_driver method, connect the selection event to the on_protocol_selected method
        self.protocol_list.itemSelectionChanged.connect(self.on_protocol_selected)


        data_layout.addWidget(protocol_label)
        data_layout.addWidget(self.protocol_list)
        # Text input for specifying the data's location (e.g., smb_server/share)
        data_location_label = QLabel("Data Location:")
        self.data_location_input = QLineEdit()
        self.data_location_input.setText("18.134.142.64/XXX_data")
        data_layout.addWidget(data_location_label)
        data_layout.addWidget(self.data_location_input)

        # Dropdown list for selecting users
        user_label = QLabel("Select User:")
        self.user_dropdown = QComboBox()
        self.load_user_data()  # Load the CSV into a DataFrame and populate the dropdown
        data_layout.addWidget(user_label)
        data_layout.addWidget(self.user_dropdown)

        # Button for adding a user
        add_user_button = QPushButton("Add User")
        add_user_button.clicked.connect(self.add_user_dialog)  # Opens a dialog for user input
        data_layout.addWidget(add_user_button)

        # Checkboxes with associated input fields
        self.username_password_checkbox = QCheckBox("Include Username & Password")
        self.mount_point_checkbox = QCheckBox("Specify Mount Point")
        self.encrypt_checkbox = QCheckBox("Encrypt Data")

        data_layout.addWidget(self.username_password_checkbox)
        data_layout.addWidget(self.mount_point_checkbox)
        data_layout.addWidget(self.encrypt_checkbox)

        # Mount Point Inputs (initially disabled)
        self.mount_point_windows = QLineEdit("Z:")
        self.mount_point_mac = QLineEdit("$HOME/Desktop/aufs")
        self.mount_point_linux = QLineEdit("$HOME/Desktop/aufs")

        data_layout.addWidget(QLabel("Windows Mount Point:"))
        data_layout.addWidget(self.mount_point_windows)
        data_layout.addWidget(QLabel("MacOS Mount Point:"))
        data_layout.addWidget(self.mount_point_mac)
        data_layout.addWidget(QLabel("Linux Mount Point:"))
        data_layout.addWidget(self.mount_point_linux)

        # Disable mount point inputs until the checkbox is selected
        self.mount_point_windows.setEnabled(False)
        self.mount_point_mac.setEnabled(False)
        self.mount_point_linux.setEnabled(False)

        # Checkbox toggles for mount points
        self.mount_point_checkbox.toggled.connect(self.toggle_mount_points)

        # Button to set data for the schema
        set_data_button = QPushButton("Set Data for schema")
        set_data_button.clicked.connect(self.set_data_for_schema)
        data_layout.addWidget(set_data_button)

        data_widget.setLayout(data_layout)
        data_driver.setWidget(data_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, data_driver)

    def toggle_mount_points(self, checked):
        """Enable or disable mount point inputs based on the checkbox status."""
        self.mount_point_windows.setEnabled(checked)
        self.mount_point_mac.setEnabled(checked)
        self.mount_point_linux.setEnabled(checked)

    def on_protocol_selected(self):
        """
        Called when the user selects a protocol from the protocol list.
        """
        selected_item = self.protocol_list.currentItem()
        if selected_item:
            self.selected_protocol = selected_item.text()  # Store the selected protocol
            self.load_user_data()
            print(f"Protocol selected: {self.selected_protocol}")
        else:
            QMessageBox.warning(self, "Warning", "Please select a protocol.")

    def load_user_data(self):
        """
        Load user data from a CSV file and populate the dropdown list.
        If the CSV file is empty or missing, populate the dropdown with a friendly message.
        """
        try:
            # Define the path to the user CSV based on the selected protocol
            protocol = self.selected_protocol if hasattr(self, 'selected_protocol') else "smb"  # Default to smb if not set
            print('Protocol being used to load user data: ', protocol)
            csv_location = os.path.expanduser(f"~/.aufs/provisioning/users/{protocol}/aufs_{protocol}_users.csv")

            # Attempt to read CSV into a DataFrame
            user_df = pd.read_csv(csv_location, header=None)

            # Clear the dropdown in case of old data
            self.user_dropdown.clear()

            # Check if the CSV is empty, and handle it gracefully
            if user_df.empty:
                self.user_dropdown.addItem(f"No {protocol} Users")
            else:
                # Populate the dropdown with usernames from the first row
                for user in user_df.iloc[0]:
                    self.user_dropdown.addItem(user)

        except FileNotFoundError:
            # If the file is not found, treat it as having no users
            self.user_dropdown.clear()
            self.user_dropdown.addItem(f"No {protocol} Users")

        except Exception as e:
            # Handle other errors with a user-friendly message
            print(f"Error loading CSV: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load user data: {e}")

    def populate_user_dropdown(self):
        """
        Populate the user dropdown list from the loaded DataFrame.
        """
        self.user_dropdown.clear()
        
        if not hasattr(self, 'user_data_df'):
            return

        # Assuming the first row of CSV contains usernames
        users = self.user_data_df.columns
        self.user_dropdown.addItems(users)

    def add_user_dialog(self):
        """ Opens the SMBUserAdder widget when the 'Add User' button is pressed. """
        self.smb_user_adder_window = SMBUserAdder()  # Create an instance of SMBUserAdder
        self.smb_user_adder_window.show()  # Show the SMBUserAdder window

    def set_data_for_schema(self):
        """
        Embed selected protocol's scripts into the first column of a Pandas DataFrame using the schema for headers.
        If the selected protocol is 'links', populate the columns based on HASHEDFILE.
        """
        try:
            # Ensure that a protocol has been selected
            if not hasattr(self, 'selected_protocol'):
                QMessageBox.warning(self, "Warning", "Please select a protocol from the list.")
                return

            selected_protocol = self.selected_protocol  # Use the user-selected protocol
            print(f"Selected Protocol: {selected_protocol}")

            if selected_protocol == 'links':
                # Special case for 'links' protocol
                self.dataloc_handler_links(self.package_full_df)
                QMessageBox.information(self, "Data", "Links have been set for the schema!")
                return

            # Fetch scripts for the selected protocol using TheThirdEmbedder
            smb_scripts = self.embedder.get_scripts_for_all_platforms(selected_protocol)
            print(f"Scripts for {selected_protocol}: {smb_scripts}")

            if not smb_scripts:
                print(f"No scripts found for {selected_protocol}. Please ensure they are present in /core/net/{selected_protocol}/")
                QMessageBox.critical(self, "Error", f"No scripts found for {selected_protocol}")
                return

            # Handle replacement variables
            uname = None
            psswd = None

            if self.username_password_checkbox.isChecked():
                # Fetch the selected user's credentials
                selected_user = self.user_dropdown.currentText()
                user_index = self.user_dropdown.currentIndex()
                
                # Assuming user_df holds usernames and passwords as columns
                user_credentials = pd.read_csv(os.path.expanduser(f"~/.aufs/provisioning/users/{selected_protocol}/aufs_{selected_protocol}_users.csv"), header=None)
                
                uname, psswd = user_credentials.iloc[1, user_index].split(':')  # Assuming the second row holds credentials in 'username:password' format

            # Prepare platform-specific script data
            platform_dictionary = get_platform_dictionary()
            platform_order = [key.split('_')[0] for key, value in sorted(platform_dictionary.items(), key=lambda item: item[1])]

            script_data = []
            for platform in platform_order:
                script_content = smb_scripts.get(platform)
                if script_content:
                    print(f"Embedding script for {platform}: {script_content[:100]}...")

                    # Use the data location handler for the selected protocol
                    dataloc_linux_mac, dataloc_win = self.dataloc_handler(selected_protocol)

                    # Replace placeholders with actual values
                    script_content = script_content.replace("DATALOC", dataloc_win if platform == "win" else dataloc_linux_mac)
                    
                    if uname and psswd:
                        script_content = script_content.replace("UNAME", uname)
                        script_content = script_content.replace("PSSWD", psswd)

                    script_data.append(script_content)
                else:
                    print(f"No script found for platform {platform}")
                    script_data.append(None)

            # Create a Pandas DataFrame with the schema's column names
            df = pd.DataFrame(columns=self.schema.names)

            # Fill the first column with the script data
            first_column_name = self.schema.names[0]
            df[first_column_name] = pd.Series(script_data, dtype='object')

            # Ensure the DataFrame columns match the schema's data types
            for column_name, field in zip(self.schema.names, self.schema.types):
                if column_name != first_column_name:  # Skip the first column (already filled)
                    if pa.types.is_string(field):
                        df[column_name] = pd.Series([None] * len(script_data), dtype='object')
                    elif pa.types.is_int64(field):
                        df[column_name] = pd.Series([None] * len(script_data), dtype='Int64')
                    elif pa.types.is_float64(field):
                        df[column_name] = pd.Series([None] * len(script_data), dtype='float64')
                    else:
                        df[column_name] = pd.Series([None] * len(script_data), dtype='object')

            # Convert the DataFrame to a PyArrow Table using the schema
            table = pa.Table.from_pandas(df, schema=self.schema, preserve_index=False)

            # Set the table in self for rendering into Parquet
            self.data = table

            # Update the summary to show that the data has been set
            self.update_summary(item_name='data', status='Set')

            # Notify the user that data is ready
            print(f"Data for {selected_protocol} scripts has been embedded in the first column of the DataFrame.")
            QMessageBox.information(self, "Data", f"{selected_protocol} scripts have been embedded and set for the schema!")

        except Exception as e:
            print(f"Error while embedding data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to embed script data for {selected_protocol}: {str(e)}")

    def dataloc_handler(self, protocol):
        """
        Dispatch to the appropriate protocol-specific data location handler, or bypass handling if none found.
        """
        handler_method = getattr(self, f'dataloc_handler_{protocol}', None)
        
        if handler_method:
            return handler_method()
        else:
            print(f"No specific data location handler for protocol: {protocol}. Bypassing.")
            # If no handler is found, return the raw value from the data location input
            data_loc = self.data_location_input.text().strip()
            return data_loc, data_loc  # Return the same value for both Linux/Mac and Windows

    def dataloc_handler_links(self, package_full_df):
        """
        Match HASHEDFILE in schema metadata with the package_full_df and insert row data
        into the first row for corresponding '-file' columns.
        """
        for column in self.schema:
            # Check if the column has HASHEDFILE metadata
            if 'HASHEDFILE' in column.metadata:
                hashedfile_value = column.metadata['HASHEDFILE'].decode('utf-8')

                # Find the matching row in package_full_df based on HASHEDFILE
                matching_row = package_full_df[package_full_df['HASHEDFILE'] == hashedfile_value]

                if not matching_row.empty:
                    # Insert the full row data into the first chunk for this column
                    row_data = matching_row.iloc[0].to_dict()  # Convert the row to a dictionary
                    print(f"Inserting data for HASHEDFILE {hashedfile_value}: {row_data}")

                    # For each field in the row, insert into the first row of the column
                    self.data[column.name] = row_data  # Assuming `self.data` is your dataframe to populate

    def dataloc_handler_smb(self):
        """
        Handle SMB data location parsing and formatting.
        - Split the input by both "\" and "/" in two steps.
        - Rebuild for Linux/Mac using "/" and for Windows manually with "\\".
        - Ensure Windows paths start with "\\" for network paths.
        """
        smb_server_share = self.data_location_input.text().strip()

        # Step 1: Remove "smb:" prefix if present
        if ":" in smb_server_share:
            smb_server_share = smb_server_share.split(":", 1)[1].strip()

        # Step 2: Split the path by backslashes and forward slashes
        path_elements = smb_server_share.split("\\")  # Split by backslashes first
        path_elements = [sub_element for element in path_elements for sub_element in element.split("/")]  # Then split by forward slashes

        # Remove any empty elements caused by leading slashes
        path_elements = [element for element in path_elements if element]

        # Step 3: Rebuild for Linux/Mac using "/"
        smb_linux_mac = "/".join(path_elements)

        # Step 4: Manually build the Windows path using backslashes
        smb_win = "\\".join(path_elements)

        # Ensure the Windows path starts with "\\" for network paths
        smb_win = f"\\\\{smb_win}"

        # Debugging: print the formatted paths
        print(f"Formatted SMB paths: Linux/Mac: {smb_linux_mac}, Windows: {smb_win}")

        return smb_linux_mac, smb_win

    def dataloc_handler_nfs(self):
        """
        Handle NFS data location parsing and formatting.
        - Normalize input for NFS server:/share.
        """
        nfs_server_share = self.data_location_input.text().strip()

        # Normalize the NFS format (server:/share)
        if ":" not in nfs_server_share:
            nfs_server_share = nfs_server_share.replace("/", ":/")  # Ensure server:/share format

        return nfs_server_share

    def populate_protocol_list(self):
        """
        Populates the protocol list in the Data Driver with non-empty directories from '/core/net'.
        """
        # Check if the directory exists
        if os.path.exists(self.scripts_base_path):
            # Iterate over the subdirectories in '/core/net'
            for protocol_dir in os.listdir(self.scripts_base_path):
                full_path = os.path.join(self.scripts_base_path, protocol_dir)

                # Add to the list only if it's a non-empty directory
                if os.path.isdir(full_path) and os.listdir(full_path):  # Check if it's a directory and not empty
                    self.protocol_list.addItem(QListWidgetItem(protocol_dir))  # Add to the list
        else:
            print(f"Directory '{self.scripts_base_path}' not found.")

    def add_metadata_driver(self):
        """Add metadata driver"""
        metadata_driver = QDockWidget("Metadata Driver", self)
        metadata_driver.setAllowedAreas(Qt.LeftDockWidgetArea)
        metadata_widget = QWidget()
        metadata_layout = QVBoxLayout()
        metadata_label = QLabel("Metadata Driver Placeholder (Flag Off)")
        metadata_layout.addWidget(metadata_label)
        metadata_widget.setLayout(metadata_layout)
        metadata_driver.setWidget(metadata_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, metadata_driver)

    def update_summary(self, item_name=None, status=None):
        """Update the summary output based on the item name and its status, no checks on current state."""
        if item_name and status:
            if item_name == "path":
                self.path_status = status
            elif item_name == "name":
                self.name_status = status
            elif item_name == "schema":
                self.schema_status = status
            elif item_name == "data":
                self.data_status = status
            elif item_name == "metadata":
                self.metadata_status = status

        summary = (f"Filepath: {self.path_status}\n"
                   f"Filename: {self.name_status}\n"
                   f"Schema: {self.schema_status}\n"
                   f"Data: {self.data_status}\n"
                   f"Metadata: {self.metadata_status}")
        self.summary_output.setText(summary)
        print(f"Summary updated: {summary}")

    def reset_all(self):
        """Reset all summary fields to 'Not Set'."""
        self.path_status = "Not Set"
        self.name_status = "Not Set"
        self.schema_status = "Not Set"
        self.data_status = "Not Set"
        self.metadata_status = "Not Set"
        self.update_summary()

    def render_parquet(self):
        """Render parquet file"""
        if not self.schema:
            QMessageBox.warning(self, "Warning", "Schema is missing. Cannot render Parquet file.")
            return

        if not self.data:
            QMessageBox.warning(self, "Warning", "Data is missing. Cannot render Parquet file.")
            return

        output_path = os.path.join(self.path_input.text(), self.name_input.text())
        if not output_path:
            QMessageBox.warning(self, "Warning", "Output path or filename is missing.")
            return

        metadata = self.metadata if self.metadata else None

        try:
            self.input_manager.process_render(self.schema, self.data, metadata, output_path)
            QMessageBox.information(self, "Success", f"Parquet file successfully written to {output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Render failed: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WranglerApp()
    window.show()
    sys.exit(app.exec())
