# src/aufs/user_tools/packaging/string_mapping_setup_uppercase.py

import os
import sys
import re
import pandas as pd
import shutil
from glob import glob  # Import the glob module
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QDialog, 
                               QMessageBox, QLineEdit, QLabel, QFileDialog, QMenu, QCheckBox, 
                               QApplication, QListWidget, QListWidgetItem, QToolButton, QInputDialog, QTabWidget)
from PySide6.QtCore import Qt

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')
sys.path.insert(0, src_path)

from src.aufs.user_tools.packaging.string_mapping_manager import StringMappingManager
from src.aufs.user_tools.packaging.string_mapping_snagging import StringRemappingSnaggingWidget
from src.aufs.user_tools.editable_pandas_model import EditablePandasModel
from src.aufs.user_tools.fs_meta.update_fs_info import DirectoryLoaderUI
from aufs.user_tools.packaging.uppercase_template_manager import UppercaseTemplateManager
from aufs.user_tools.packaging.data_provisioning_widget import DataProvisioningWidget
from src.aufs.user_tools.deep_editor import DeepEditor

def QVBoxLayoutWrapper(label_text, widget, add_new_callback=None, fixed_width=None, min_width=None):
    """
    Wraps a widget with a QLabel and optionally adds an "Add New" button below it.
    Allows setting fixed or minimum width for the widget.
    """
    if fixed_width is None:
        fixed_width = 300
        
    layout = QVBoxLayout()

    # Add label and the main widget
    layout.addWidget(QLabel(label_text))

    # Apply width constraints to the widget
    if fixed_width:
        widget.setFixedWidth(fixed_width)
    elif min_width:
        widget.setMinimumWidth(min_width)

    layout.addWidget(widget)

    # Add "Add New" button if a callback is provided
    if add_new_callback:
        add_new_button = QPushButton(f"Add New {label_text[:-1]}")
        add_new_button.setMaximumWidth(200)  # Restrict button width
        add_new_button.clicked.connect(add_new_callback)
        layout.addWidget(add_new_button)

    return layout

class RequestorUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("String Mapping Workflow")
        self.resize(3000, 1500)

        # Initialize class variables
        self.file_io = FileIO()
        self.payload_handler = PayloadHandler()
        self.mapping_requestor = MappingRequestor()
        self.manager = StringMappingManager()
        self.manager.selected_rows_updated.connect(self.update_preview_table)
        self.output_manager = OutputManager()
        self.session_manager = SessionManager("~/.aufs/config/jobs/active")

        # Default paths and settings
        self.client = ''
        self.project = ''
        self.recipient = ''
        self.session_name = None
        self.request_name = None
        self.template_data = ''
        self.root_output_dir = ''

        # Main layout setup using tabs
        self.tabs = QTabWidget(self)
        self.requestor_tab = QWidget()
        self.manager_tab = QWidget()
        self.manager_layout = QVBoxLayout(self.manager_tab)
        self.manager_layout.addWidget(self.manager)

        # Add manager and requestor tabs
        self.tabs.addTab(self.requestor_tab, "Requestor Interface")
        # self.tabs.addTab(self.manager_tab, "String Mapping Manager")

        # Setup the requestor UI within the `requestor_tab`
        self.setup_requestor_ui()

        # Set layout and add tabs
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def setup_button_area(self, panes_layout):
        """Adds a button area to the far right side of panes_layout."""
        button_area_layout = QHBoxLayout()
        button_area_layout.setAlignment(Qt.AlignTop)

        # Create a left-side layout
        button_area_leftside_layout = QVBoxLayout()

        # Add other left-side buttons
        edit_source_button = QPushButton("Edit Source CSV")
        edit_source_button.clicked.connect(self.edit_source_csv)
        button_area_leftside_layout.addWidget(edit_source_button)

        edit_template_button = QPushButton("Edit Template")
        edit_template_button.clicked.connect(self.edit_template_csv)
        button_area_leftside_layout.addWidget(edit_template_button)

        retire_button = QPushButton("Retire Request")
        retire_button.clicked.connect(self.retire_request)
        button_area_leftside_layout.addWidget(retire_button)

        locate_request_files_button = QPushButton("Locate Files")
        locate_request_files_button.clicked.connect(self.locate_request_files)
        button_area_leftside_layout.addWidget(locate_request_files_button)

        # Add to the main button area
        button_area_leftside_layout.addStretch()
        button_area_layout.addLayout(button_area_leftside_layout)

        # Add the right-side buttons (unchanged)
        button_area_rightside_layout = QVBoxLayout()

        # Add "Replace Source" button
        replace_source_button = QPushButton("Replace Source")
        replace_source_button.clicked.connect(self.replace_source_file)
        button_area_rightside_layout.addWidget(replace_source_button)

        # Add "Replace Template" button
        replace_template_button = QPushButton("Replace Template")
        replace_template_button.clicked.connect(self.replace_template_file)
        button_area_rightside_layout.addWidget(replace_template_button)

        button_area_rightside_layout.addStretch()

        button_area_layout.addLayout(button_area_rightside_layout)
        button_area_layout.addStretch()

        button_area_widget = QWidget()
        button_area_widget.setFixedWidth(340)
        button_area_widget.setLayout(button_area_layout)
        panes_layout.addWidget(button_area_widget)
        panes_layout.addStretch()

    def setup_requestor_ui(self):
        """Sets up both the session setup and file processing UI components."""
        layout = QVBoxLayout(self.requestor_tab)

        # === Session Setup Section ===
        session_setup_layout = QVBoxLayout()

        # Expand/collapse button for session setup
        self.expand_button = QPushButton("Session Setup")
        self.expand_button.setCheckable(True)
        self.expand_button.setChecked(True)
        self.expand_button.toggled.connect(self.toggle_session_setup)
        session_setup_layout.addWidget(self.expand_button)

        # Collapsible widget for session setup
        self.session_setup_widget = QWidget()
        self.session_setup_widget.setVisible(True)
        session_layout = QVBoxLayout(self.session_setup_widget)

        jobs_directory_layout = QHBoxLayout()
        # Jobs Directory setup
        self.jobs_directory_input = QLineEdit(os.path.expanduser("~/.aufs/config/jobs/active"))
        # self.jobs_directory_input.setMaximumWidth(500)
        self.browse_jobs_dir_button = QPushButton("Browse")
        self.browse_jobs_dir_button.clicked.connect(self.on_jobs_dir_change)

        jobs_directory_layout.addWidget(QLabel("Jobs Directory:"))
        jobs_directory_layout.addWidget(self.browse_jobs_dir_button)
        jobs_directory_layout.addWidget(self.jobs_directory_input)

        jobs_directory_layout.addStretch()

        session_layout.addLayout(jobs_directory_layout)

        # === Cascading Panes Section ===
        panes_layout = QHBoxLayout()

        # Client List
        self.client_selector = QListWidget()
        self.populate_clients()
        self.client_selector.itemClicked.connect(self.on_client_selected)

        # Add "Add New" button for clients
        client_callback = lambda: self.session_manager.handle_new_item(
            self, self.client_selector, "Client", self.session_manager.add_new_client
        )
        panes_layout.addLayout(QVBoxLayoutWrapper("Client:", self.client_selector, add_new_callback=client_callback))

        # Project List
        self.project_selector = QListWidget()
        self.project_selector.itemClicked.connect(self.on_project_selected)

        # Add "Add New" button for projects
        project_callback = lambda: self.session_manager.handle_new_item(
            self,
            self.project_selector,
            "Project",
            lambda project_name: self.session_manager.add_new_project(self.client, project_name)
        )
        panes_layout.addLayout(QVBoxLayoutWrapper("Project:", self.project_selector, add_new_callback=project_callback))

        # Recipient List
        self.recipient_selector = QListWidget()
        self.recipient_selector.itemClicked.connect(self.on_recipient_selected)

        # Add "Add New" button for recipients
        recipient_callback = lambda: self.handle_new_recipient()
        panes_layout.addLayout(QVBoxLayoutWrapper("Recipient:", self.recipient_selector, add_new_callback=recipient_callback))

        # Session List
        self.session_selector = QListWidget()
        self.session_selector.itemClicked.connect(self.on_session_selected)

        # Add "Add New" button for sessions
        session_callback = lambda: self.handle_new_session()
        panes_layout.addLayout(QVBoxLayoutWrapper("Session:", self.session_selector, add_new_callback=session_callback))

        # Request List
        self.request_selector = QListWidget()
        self.request_selector.itemClicked.connect(self.on_request_selected)

        # Add "Add New" button for requests
        request_callback = lambda: self.handle_new_request()
        panes_layout.addLayout(QVBoxLayoutWrapper("Request:", self.request_selector, add_new_callback=request_callback))

        # Add cascading panes to layout
        session_layout.addLayout(panes_layout)

        self.setup_button_area(panes_layout)

        session_setup_layout.addWidget(self.session_setup_widget)

        # === Source File Loader Section ===
        source_file_layout = QHBoxLayout()
        self.source_file_input = QLineEdit()
        self.load_source_button = QPushButton("Load Source Files CSV")
        self.load_source_button.clicked.connect(self.load_source_csv)
        source_file_layout.addWidget(QLabel("Source Files CSV:"))
        source_file_layout.addWidget(self.source_file_input)
        source_file_layout.addWidget(self.load_source_button)
        # session_layout.addLayout(source_file_layout)

        # === File Processing Section ===
        file_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.load_button = QPushButton("Load Provisioning Template")
        self.load_button.clicked.connect(self.load_file)
        file_layout.addWidget(QLabel("Provisioning template path:"))
        file_layout.addWidget(self.file_path_input)
        file_layout.addWidget(self.load_button)
        # session_layout.addLayout(file_layout)

        layout.addLayout(session_setup_layout)

        self.selected_rows_buttons_layout = QHBoxLayout()

        # Add a button to collapse/expand the Selected Rows Pane
        self.toggle_selected_rows_button = QPushButton("Show Selected Rows Pane")
        self.toggle_selected_rows_button.setCheckable(True)
        self.toggle_selected_rows_button.setChecked(False)  # Default to collapsed
        self.toggle_selected_rows_button.toggled.connect(self.toggle_selected_rows_pane)
        self.selected_rows_buttons_layout.addWidget(self.toggle_selected_rows_button)

        # Add a button to open the column selector
        self.column_selector_button = QPushButton("Selected Rows's Columns for Preview")
        self.column_selector_button.clicked.connect(self.show_column_selector_popup)
        self.selected_rows_buttons_layout.addWidget(self.column_selector_button)

        self.selected_rows_buttons_layout.addStretch()

        layout.addLayout(self.selected_rows_buttons_layout)

        # Add a placeholder for the selected columns
        self.selected_columns = []

        # === Selected Rows Pane ===
        layout.addWidget(QLabel("Selected Rows Pane:"))
        self.selected_rows_pane_table = QTableView()
        self.selected_rows_pane_model = None  # Placeholder for EditablePandasModel
        self.selected_rows_pane_table.setAlternatingRowColors(True)
        self.selected_rows_pane_table.setSelectionBehavior(QTableView.SelectRows)
        layout.addWidget(self.selected_rows_pane_table)

        self.selected_rows_pane_table.setVisible(False)  # Initially hidden

        self.preview_request_buttons_layout = QHBoxLayout()

        # Add a button to collapse/expand the Preview Pane
        self.toggle_preview_button = QPushButton("Show Preview Table")
        self.toggle_preview_button.setCheckable(True)
        self.toggle_preview_button.setChecked(False)
        self.toggle_preview_button.toggled.connect(self.toggle_preview_table)
        self.preview_request_buttons_layout.addWidget(self.toggle_preview_button)

        # === Add Checkbox for Versioning Dialog ===
        self.use_versioning_dialog_request_checkbox = QCheckBox("Use Versioning Dialog")
        self.use_versioning_dialog_request_checkbox.setChecked(False)  # Default to unchecked
        self.preview_request_buttons_layout.addWidget(self.use_versioning_dialog_request_checkbox)

        # === Process Button ===
        self.remap_button = QPushButton("Process and Preview Remap")
        self.remap_button.clicked.connect(lambda: self.process_remap(filter_parsed=True))
        self.preview_request_buttons_layout.addWidget(self.remap_button)

        # Add a checkbox for "Process Directories"
        self.process_directories_checkbox = QCheckBox("Process Directories")
        self.process_directories_checkbox.setChecked(False)  # Default to unchecked
        self.preview_request_buttons_layout.addWidget(self.process_directories_checkbox)

        self.preview_request_buttons_layout.addStretch()

        layout.addLayout(self.preview_request_buttons_layout)

        # === Request Preview Section ===
        layout.addWidget(QLabel("Request preview:"))
        self.preview_table = QTableView()
        self.preview_model = None
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setSelectionBehavior(QTableView.SelectRows)
        layout.addWidget(self.preview_table)

        self.preview_table.setVisible(True)

        # === Save Button with Dropdown Menu ===
        save_button_layout = QHBoxLayout()
        self.save_button = QToolButton(self)
        self.save_button.setText("Save with Timestamp")
        self.save_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.save_button.setPopupMode(QToolButton.MenuButtonPopup)
        self.save_button.setFixedWidth(150)

        # Create a dropdown menu for additional save options
        save_menu = QMenu(self)
        save_as_action = save_menu.addAction("Save As")
        save_original_action = save_menu.addAction("Save")
        self.save_button.setMenu(save_menu)

        # Connect save button and menu actions
        self.save_button.clicked.connect(lambda: self.save_remapped_file("timestamped"))
        save_as_action.triggered.connect(lambda: self.save_remapped_file("save_as"))
        save_original_action.triggered.connect(lambda: self.save_remapped_file("original"))

        save_button_layout.addWidget(self.save_button)
        layout.addLayout(save_button_layout)

        # === Session Preview Section ===
        session_preview_layout = QHBoxLayout()

        self.session_preview_label = QLabel("Session Data Preview:")
        session_preview_layout.addWidget(self.session_preview_label)

        # Add "Load Latest Saved" button
        self.load_latest_button = QPushButton("Load Latest Saved")
        self.load_latest_button.clicked.connect(self.load_latest_session_file)
        session_preview_layout.addWidget(self.load_latest_button)

        # Add "Load Previous Saved" button
        self.load_previous_button = QPushButton("Load Previous Saved")
        self.load_previous_button.clicked.connect(self.load_previous_session_file)
        session_preview_layout.addWidget(self.load_previous_button)

        # Add "Load latest Requests" button
        self.load_latest_requests_button = QPushButton("Load latest Requests")
        self.load_latest_requests_button.clicked.connect(self.create_session_df_from_latest_requests)
        session_preview_layout.addWidget(self.load_latest_requests_button)

        # Add "Snag Rows" button
        self.snag_rows_button = QPushButton("Snag Rows")
        self.snag_rows_button.clicked.connect(self.launch_snag_popup)
        session_preview_layout.addWidget(self.snag_rows_button)

        # Add "Process Package" button
        self.process_package_button = QPushButton("Process Package")
        self.process_package_button.clicked.connect(self.remap_session_data)
        session_preview_layout.addWidget(self.process_package_button)

        # === Add Checkbox for Versioning Dialog ===
        self.use_versioning_dialog_session_checkbox = QCheckBox("Use Versioning Dialog")
        self.use_versioning_dialog_session_checkbox.setChecked(False)  # Default to unchecked
        self.use_versioning_dialog_session_checkbox.setMaximumWidth(200)
        session_preview_layout.addWidget(self.use_versioning_dialog_session_checkbox)

        session_preview_layout.addStretch()

        layout.addLayout(session_preview_layout)

        self.session_table = QTableView()
        self.session_model = None
        self.session_table.setAlternatingRowColors(True)
        self.session_table.setSelectionBehavior(QTableView.SelectRows)
        layout.addWidget(self.session_table)

        # === Provision Data Button ===
        self.provision_data_button = QPushButton("Make Package")
        self.provision_data_button.clicked.connect(lambda: self.provision_the_data())
        layout.addWidget(self.provision_data_button)

        # === Save Session Button ===
        self.save_session_button = QPushButton("Save Session")
        self.save_session_button.clicked.connect(lambda: self.save_remapped_file("timestamped", data_source="session"))
        layout.addWidget(self.save_session_button)

        # Set the final layout
        self.requestor_tab.setLayout(layout)

    def process_remap(self, filter_parsed=True, filter_list=None, filter_mode="exclude", add_source="prepend"):
        """
        Process remapping based on selected rows and display results in preview pane.
        """
        if self.manager.selected_rows_df.empty:
            QMessageBox.warning(self, "Warning", "Please select rows in the manager before remapping.")
            return

        remapped_data = []  # Store remapped rows for DataFrame creation

        use_dialog = self.use_versioning_dialog_request_checkbox.isChecked()

        # Default filter list for process_remap
        if filter_list is None:
            filter_list = ["YYYYMMDD", "PKGVERSION3PADDED"]

        for _, selected_row in self.manager.selected_rows_df.iterrows():
            selected_row_dict = selected_row.to_dict()  # Convert row to dictionary

            # Handle additional columns
            if add_source in ["prepend", "append"]:
                if self.selected_columns:
                    source_columns = {col: selected_row_dict[col] for col in self.selected_columns if col in selected_row_dict}
                else:
                    source_columns = selected_row_dict
            else:
                source_columns = {}

            # Filter template data for matching DOTEXTENSION
            dotextension_value = selected_row_dict.get("DOTEXTENSION")
            if dotextension_value and "DOTEXTENSION" in self.template_data.columns:
                matching_template_rows = self.template_data[self.template_data["DOTEXTENSION"] == dotextension_value]
            else:
                matching_template_rows = self.template_data

            if matching_template_rows.empty:
                continue

            # Remap matching template rows
            for _, template_row in matching_template_rows.iterrows():
                template_row_dict = template_row.to_dict()  # Convert template row to dict

                # Collect all uppercase variables across all columns
                parsed_variables = []
                for key, value in template_row_dict.items():
                    if isinstance(value, str):  # Parse only string columns
                        parsed_variables.extend(self.payload_handler.parse(value, "uppercase"))

                # Filter variables based on filter_parsed, filter_list, and filter_mode
                if filter_parsed:
                    if filter_mode == "exclude":
                        parsed_variables = [var for var in parsed_variables if var not in filter_list]
                    elif filter_mode == "include":
                        parsed_variables = [var for var in parsed_variables if var in filter_list]

                # Use the helper function to remap variables
                # print(selected_row_dict, parsed_variables)
                mappings = self._remap_variables(
                    parsed_variables=parsed_variables,
                    row_data=selected_row_dict,
                    root_job_path=self.root_job_path,
                    remap_type="uppercase",
                    use_dialog=use_dialog
                )

                # Apply mappings
                if mappings:
                    for col, value in template_row_dict.items():
                        if isinstance(value, str):
                            template_row_dict[col] = self.reintegrate_using_parser(value, parsed_variables, mappings)

                # Combine source and remapped rows
                if add_source == "prepend":
                    remapped_row_with_context = {**source_columns, **template_row_dict}
                elif add_source == "append":
                    remapped_row_with_context = {**template_row_dict, **source_columns}
                else:
                    remapped_row_with_context = template_row_dict

                remapped_data.append(remapped_row_with_context)

        # Create DataFrame and update the preview table
        self.selected_rows_remapped_df = pd.DataFrame(remapped_data)
        if self.selected_rows_remapped_df.empty:
            QMessageBox.warning(self, "No Data", "No remapped results to display.")
        else:
            self.update_preview_table(self.selected_rows_remapped_df)

    def remap_session_data(self):
        """
        Remap every row in session_df for remaining uppercase variables.
        Display the remapped session data in the session preview pane.
        """
        if self.session_df is None or self.session_df.empty:
            QMessageBox.warning(self, "No Data", "No session data available to process.")
            return
        
        use_dialog = self.use_versioning_dialog_session_checkbox.isChecked()

        try:
            remapped_data = []  # Store remapped rows as dictionaries

            for _, row in self.session_df.iterrows():
                row_as_dict = row.to_dict()  # Convert row to dictionary

                # Collect all uppercase variables across all columns
                parsed_variables = []
                for col_name, value in row_as_dict.items():
                    if isinstance(value, str):  # Parse only string columns
                        parsed_variables.extend(self.payload_handler.parse(value, "uppercase"))

                # Deduplicate parsed variables
                parsed_variables = list(set(parsed_variables))

                # Use the helper function to remap variables
                # print("Session data remapping: ", row_as_dict, parsed_variables)
                mappings = self._remap_variables(
                    parsed_variables=parsed_variables,
                    row_data=row_as_dict,
                    root_job_path=self.root_job_path,
                    remap_type="uppercase",
                    use_dialog=use_dialog
                )

                # Apply mappings
                if mappings:
                    for col_name, value in row_as_dict.items():
                        if isinstance(value, str):
                            row_as_dict[col_name] = self.reintegrate_using_parser(value, parsed_variables, mappings)

                remapped_data.append(row_as_dict)

            # Update session DataFrame and preview
            self.remapped_session_df = pd.DataFrame(remapped_data)
            self.session_df = self.remapped_session_df

            if self.remapped_session_df.empty:
                print("No remapped session data to display.")
            else:
                self.update_session_table(self.remapped_session_df)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to remap session data: {str(e)}")

    def _remap_variables(self, parsed_variables, row_data, root_job_path, remap_type="uppercase", use_dialog=False):
        """
        Helper function to remap parsed variables using the manager.

        Args:
            parsed_variables (list): List of parsed variables to be remapped.
            row_data (dict or DataFrame): Data for the row being processed.
            root_job_path (str): Root job path for remapping operations.
            remap_type (str): Type of remapping to be performed (default: "uppercase").
            use_dialog (bool): Whether to show a dialog for versioning type selection.

        Returns:
            dict: Mapped variables.
        """

        return self.manager.map_requested_values(
            id_header=None,
            id_value=None,
            target_columns=parsed_variables,
            virtual_headers=None,
            ignore_columns='',
            root_job_path=root_job_path,
            row_data=pd.DataFrame([row_data]) if isinstance(row_data, dict) else row_data,
            use_dialog=use_dialog,
            remap_type=remap_type,
        )

    def replace_source_file(self):
        """Replace the source file for the current request using the prompt."""
        source_file_path = self.prompt_source_file_path()
        if source_file_path:
            destination_path = os.path.join(self.requests_dir, f"{self.request_name}_source_files.csv")
            self.replace_file(source_file_path, destination_path)
            QMessageBox.information(self, "Success", "Source file replaced successfully.")
        else:
            QMessageBox.warning(self, "Operation Canceled", "Source file replacement was canceled.")

    def replace_template_file(self):
        """Replace the template file for the current request."""
        template_file_path = self.prompt_provisioning_template_path()
        if template_file_path:
            destination_path = os.path.join(self.requests_dir, f"{self.request_name}_provisioning_template.csv")
            self.replace_file(template_file_path, destination_path)
            QMessageBox.information(self, "Success", "Template file replaced successfully.")

    def replace_file(self, source_path, destination_path, timestamp_backup=True):
        """
        Replace a file at `destination_path` with `source_path`.
        Optionally creates a timestamped backup of the existing destination file.

        Args:
            source_path (str): The file to copy from.
            destination_path (str): The file to copy to.
            timestamp_backup (bool): Whether to create a timestamped backup of the destination file if it exists.
        """
        if os.path.exists(destination_path) and timestamp_backup:
            # Create a timestamped backup of the existing file
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            backup_path = f"{destination_path}-{timestamp}"
            shutil.copyfile(destination_path, backup_path)
            print(f"Backup created: {backup_path}")

        # Replace the destination file with the source file
        shutil.copyfile(source_path, destination_path)
        print(f"Replaced {destination_path} with {source_path}")

    def open_csv_in_deepeditor(self, file_path, description):
        """
        Opens the given CSV file in the DeepEditor for editing.
        
        Args:
            file_path (str): The path to the CSV file.
            description (str): A description of the file for error messages and logging.
        """
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, f"{description} File Not Found", f"The {description} CSV file is missing or invalid.")
            return

        # Wrap DeepEditor in a QDialog
        dialog = QDialog(self)
        layout = QVBoxLayout(dialog)
        button_flags = {
            'add_row': True,
            'delete_row': True,
            'move_row_up': True,
            'move_row_down': True,
            'add_column': True,
            'delete_column': True,
            'move_column_left': True,
            'move_column_right': True,
            'sort_column': True,
            'clear_selection': True,
            'set_column_type': True,
            'dtype_dropdown': True,
            'reload': True,
            'save': True,
            'exit': False
        }
        editor = DeepEditor(file_path=file_path, button_flags=button_flags, file_type="csv")
        layout.addWidget(editor)

        # Set dialog properties
        dialog.setWindowTitle(f"Edit {description} CSV")
        dialog.resize(3000, 800)

        # Open the dialog modally
        result = dialog.exec()

        # Check for changes after the dialog closes
        if not editor.changes_made:
            # QMessageBox.information(self, "No Changes", f"No changes were made to the {description} CSV.")
            return
        else:
            if description.lower() == "source":
                self.load_source_csv(file_path)
            elif description.lower() == "template":
                self.load_provisioning_template(file_path)

    def edit_source_csv(self):
        """Opens the source CSV file in the DeepEditor."""
        source_file_path = self.source_file_input.text()
        self.open_csv_in_deepeditor(source_file_path, "Source")

    def edit_template_csv(self):
        """Opens the template CSV file in the DeepEditor."""
        template_file_path = self.file_path_input.text()
        self.open_csv_in_deepeditor(template_file_path, "Template")

    def provision_the_data(self):
        # Open path confirmation dialog
        dialog = PathConfirmationDialog(self.recipient_out)
        if dialog.exec() == QDialog.Accepted:  # If the user confirms
            self.recipient_out = dialog.selected_path  # Update the path

            # Filter session_df to include only rows where STATUS == "valid"
            provisioning_df = self.session_df.loc[self.session_df["STATUS"] == "valid"]

            # Pass the filtered DataFrame to the provisioner
            self.provisioner = DataProvisioningWidget(provisioning_df, self.recipient_out)
            self.provisioner.show()

    def locate_request_files(self):
        """
        Open the parent folder of the source and template files for the currently selected request.
        """
        if not self.request_name or not self.requests_dir:
            QMessageBox.warning(self, "No Request Selected", "Please select a request to locate its files.")
            return

        # Define file paths
        source_file_path = os.path.join(self.requests_dir, f"{self.request_name}_source_files.csv")
        template_file_path = os.path.join(self.requests_dir, f"{self.request_name}_provisioning_template.csv")

        # Determine the folder to open
        folder_to_open = None
        if os.path.exists(source_file_path):
            folder_to_open = os.path.dirname(source_file_path)
        elif os.path.exists(template_file_path):
            folder_to_open = os.path.dirname(template_file_path)

        if not folder_to_open or not os.path.exists(folder_to_open):
            QMessageBox.warning(self, "Folder Not Found", "The parent folder for the selected request's files could not be located.")
            return

        # Open the folder in the system's file browser
        try:
            system_platform = platform.system()
            if system_platform == "Windows":
                os.startfile(folder_to_open)
            elif system_platform == "Darwin":  # macOS
                subprocess.run(["open", folder_to_open])
            else:  # Linux
                subprocess.run(["xdg-open", folder_to_open])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open the folder: {str(e)}")

    def load_latest_session_file(self):
        """Load the latest saved session file into session_df and update the session table."""
        if self.session_manager.saved_session_files_df.empty:
            QMessageBox.warning(self, "No Files", "No latest session file available.")
            return

        try:
            self.saved_session_files_df = self.session_manager.saved_session_files_df
            latest_file_row = self.saved_session_files_df[self.saved_session_files_df['is_latest']].iloc[0]
            latest_file_path = latest_file_row['file_path']
            
            # Use dtype mapping to ensure proper column types
            dtype_mapping = {
                'PADDING': str,
                'FIRSTFRAME': str,
                'LASTFRAME': str,
            }
            session_df = pd.read_csv(latest_file_path, dtype=dtype_mapping)

            # Validate or filter session_df as in create_session_df_from_latest_requests
            self.session_df = self.filter_session_data(session_df)
            self.update_session_table(self.session_df)  # Refresh the session table
            QMessageBox.information(self, "File Loaded", f"Loaded latest session file:\n{latest_file_row['file_name']}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load the latest session file: {str(e)}")

    def load_previous_session_file(self):
        """Load a previously saved session file from a list of available files."""
        if self.session_manager.saved_session_files_df.empty:
            QMessageBox.warning(self, "No Files", "No session files available.")
            return

        # Show a list of available files
        dialog = QDialog(self)
        dialog.setWindowTitle("Select a Previous Session File")
        layout = QVBoxLayout(dialog)

        file_list_widget = QListWidget()
        # Add file names from the saved session files DataFrame
        for _, row in self.session_manager.saved_session_files_df.iterrows():
            file_list_widget.addItem(row['file_name'])
        layout.addWidget(file_list_widget)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def select_file():
            selected_item = file_list_widget.currentItem()
            if selected_item:
                selected_file = selected_item.text()
                dialog.accept()
                self.load_specific_session_file(selected_file)
            else:
                QMessageBox.warning(self, "No Selection", "Please select a file.")

        ok_button.clicked.connect(select_file)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def load_specific_session_file(self, file_name):
        """Load the specified session file into session_df and update the session table."""
        try:
            # Find the file path in the DataFrame
            file_row = self.session_manager.saved_session_files_df[self.session_manager.saved_session_files_df['file_name'] == file_name]
            if file_row.empty:
                QMessageBox.warning(self, "File Not Found", f"File '{file_name}' not found in the session files.")
                return

            session_file_path = file_row.iloc[0]['file_path']
            
            dtype_mapping = {
                'PADDING': str,
                'FIRSTFRAME': str,
                'LASTFRAME': str,
            }  # , dtype=dtype_mapping
            # Load the file into the session DataFrame
            self.session_df = pd.read_csv(session_file_path, dtype=dtype_mapping)
            self.update_session_table(self.session_df)  # Refresh the session table
            QMessageBox.information(self, "File Loaded", f"Loaded session file:\n{file_name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load the session file: {str(e)}")

    def retire_request(self):
        """Retire the selected request by delegating to SessionManager."""
        if not self.request_name:
            QMessageBox.warning(self, "No Request Selected", "Please select a request to retire.")
            return

        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Confirm Retire",
            f"Are you sure you want to retire the request '{self.request_name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            # Delegate retiring logic to SessionManager
            files_moved = self.session_manager.retire_request(
                client=self.client,
                project=self.project,
                recipient=self.recipient,
                session_name=self.session_name,
                request_name=self.request_name
            )

            if files_moved == 0:
                QMessageBox.warning(
                    self, "No Files Found",
                    f"No files found matching '{self.request_name}*' in the requests folder."
                )
            else:
                QMessageBox.information(
                    self, "Request Retired",
                    f"The request '{self.request_name}' has been retired successfully.\n"
                    f"{files_moved} file(s) moved to 'retired'."
                )
            self.populate_requests()  # Refresh the requests list

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to retire the request: {str(e)}")

    def apply_resizing_to_views(self):
        """
        Iterates over all models and views in the application, applying column resizing where enabled.
        """
        model_view_pairs = [
            (self.session_model, self.session_table),
            (self.preview_model, self.preview_table),
            (self.selected_rows_pane_model, self.selected_rows_pane_table),
        ]

        for model, view in model_view_pairs:
            if isinstance(model, EditablePandasModel):
                model.apply_column_widths(view)

    def show_column_selector_popup(self, use_selection_order=False):
        """
        Show a popup to select columns from selected_rows for preview, with an option
        to use either the DataFrame column order or the selection order.

        Args:
            use_selection_order (bool): If True, the order of selected columns will be based on selection order.
                                        If False, it will follow the DataFrame column order.
        """
        if self.manager.selected_rows_df is None or self.manager.selected_rows_df.empty:
            QMessageBox.warning(self, "No Data", "No selected rows available for column selection.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Columns for Preview")

        layout = QVBoxLayout(dialog)

        # Multi-select list of columns
        column_list = QListWidget()
        column_list.setSelectionMode(QListWidget.MultiSelection)

        # List of columns currently selected
        active_columns = set(self.selected_columns)
        # print("Active columns are: ", active_columns)

        # Populate the column list
        for column in self.manager.selected_rows_df.columns:
            item = QListWidgetItem(column)
            column_list.addItem(item)  # Add the item first
            if column in active_columns:  # Highlight the active columns
                item.setSelected(True)  # Set it as selected

        layout.addWidget(column_list)

        # Add OK and Cancel buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def apply_selection():
            selected_items = column_list.selectedItems()
            if use_selection_order:
                # Use the order of selection
                self.selected_columns = [item.text() for item in selected_items]
            else:
                # Use the order from the DataFrame
                self.selected_columns = [
                    column for column in self.manager.selected_rows_df.columns
                    if column in {item.text() for item in selected_items}
                ]
            dialog.accept()
            self.update_selected_rows_columns()  # Update the preview pane table

        ok_button.clicked.connect(apply_selection)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def update_selected_rows_columns(self, clear=False):
        """
        Update the preview pane table to show filtered data based on the selected columns.
        Uses the selected_rows data instead of session_df.

        Args:
            clear (bool): If True, clears the default columns and displays no columns.
        """
        if self.manager.selected_rows_df is None or self.manager.selected_rows_df.empty:
            # QMessageBox.warning(self, "No Data", "No selected rows available for preview.")
            return

        # Use whitelist for default column selection unless `clear` is True
        default_columns = [] if clear else ["FILE", "FIRSTFRAME", "LASTFRAME", "PADDING"]
        if not self.selected_columns:
            self.selected_columns = [col for col in default_columns if col in self.manager.selected_rows_df.columns]

        # Filter selected_rows_df by selected columns
        if self.selected_columns:
            filtered_df = self.manager.selected_rows_df[self.selected_columns]
        else:
            filtered_df = self.manager.selected_rows_df.iloc[:, :0]  # Show no columns if selection is empty

        # Update the table model
        self.selected_rows_pane_model = EditablePandasModel(filtered_df, auto_fit_columns=False)
        self.selected_rows_pane_table.setModel(self.selected_rows_pane_model)

        # Apply column resizing after updating the model
        self.apply_resizing_to_views()
        # self.process_remap()

    def update_preview_table(self, dataframe: pd.DataFrame):
        """Updates the preview table with the provided DataFrame."""
        if dataframe is None or dataframe.empty:
            QMessageBox.warning(self, "No Data", "No data available for preview.")
            return

        self.preview_model = EditablePandasModel(dataframe, auto_fit_columns=True)
        self.preview_table.setModel(self.preview_model)

        # Apply column resizing after updating the model
        self.apply_resizing_to_views()

    def update_session_table(self, dataframe: pd.DataFrame):
        """Updates the session table with the remapped session data."""
        if dataframe is None or dataframe.empty:
            QMessageBox.warning(self, "No Data", "No session data available to preview.")
            return

        self.session_model = EditablePandasModel(dataframe, auto_fit_columns=True)
        self.session_table.setModel(self.session_model)

        # Apply column resizing after updating the model
        self.apply_resizing_to_views()

    def launch_snag_popup(self):
        """Launch the StringRemappingSnaggingWidget for snagging rows."""
        if self.session_df is None or self.session_df.empty:
            QMessageBox.warning(self, "No Data", "No session data available for snagging.")
            return

        try:
            # Create a QDialog to wrap the StringRemappingSnaggingWidget
            dialog = QDialog(self)
            dialog.setWindowTitle("Snag Rows")
            dialog.resize(2200, 600)

            # Initialize the StringRemappingSnaggingWidget
            # print("Before snagging: ")
            # print(self.session_df)
            widget = StringRemappingSnaggingWidget(
                dataframe=self.session_df.copy(),
                # dropdown_column="PROVISIONEDLINK",
                # dedupe_column="FILE",
                dedupe_column="PROVISIONEDLINK",
                dropdown_column="FILE",
                parent=dialog
            )

            # Set the widget inside the dialog layout
            layout = QVBoxLayout(dialog)
            layout.addWidget(widget)

            # Add dialog buttons (OK/Cancel)
            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")
            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            # Connect buttons to dialog actions
            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)

            # Execute the dialog modally
            if dialog.exec() == QDialog.Accepted:
                # Get the updated DataFrame from the widget
                updated_df = widget.get_result()
                if updated_df is not None:
                    self.session_df = updated_df  # Update session_df with the modified data
                    # print("After snagging: ")
                    # print(self.session_df)
                    self.update_session_table(self.session_df)  # Refresh the session table
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to snag rows: {str(e)}")

    def load_source_csv(self, source_file_path=None):
        """Load a Source Files CSV into the manager with contextual data."""
        if source_file_path:
            self.source_file_input.setText(source_file_path)
        else:
            source_file_path, _ = QFileDialog.getOpenFileName(
                self, "Open Source Files CSV", "", "CSV Files (*.csv);;All Files (*)"
            )
            self.source_file_input.setText(source_file_path)

        # Extract context from dropdowns
        # root_path = self.jobs_directory_input.text()
        # recipient = self.recipient_selector.currentText()
        user = os.getenv("USER", "default_user")  # Use system user as default

        # Reinitialize manager with contextual information
        self.manager.initialize_manager_with_csv(
            csv_path=source_file_path,
            root_path=self.root_path,
            recipient=self.recipient,
            user=user,
            load_all=True
        )

    def load_provisioning_template(self, file_path):
        """Load a provisioning template into the requestor."""
        self.file_path_input.setText(file_path)
        self.load_file(file_path)

    def clear_clients(self):
        """Clears the clients dropdown and all dependent dropdowns."""
        self.client_selector.clear()
        self.clear_projects()

    def clear_projects(self):
        self.project_selector.clear()
        self.clear_recipients()  # Clear subsequent dependent dropdowns

    def clear_recipients(self):
        self.recipient_selector.clear()
        self.clear_sessions()

    def clear_sessions(self):
        self.session_selector.clear()
        self.clear_requests()

    def clear_requests(self):
        self.request_selector.clear()

    def on_client_selected(self, item):
        """Handles client selection and populates projects."""
        self.client = item.text()
        self.clear_list(self.project_selector)
        self.clear_list(self.recipient_selector)
        self.clear_list(self.session_selector)
        self.clear_list(self.request_selector)
        self.clear_session_table()
        self.populate_projects()

    def on_project_selected(self, item):
        """Handles project selection and populates recipients."""
        self.project = item.text()
        self.root_path = os.path.join(self.session_manager.root_directory, self.client, self.project, "packaging")
        self.root_job_path = os.path.join(self.session_manager.root_directory, self.client, self.project)
        self.clear_list(self.recipient_selector)
        self.clear_list(self.session_selector)
        self.clear_list(self.request_selector)
        self.clear_session_table()
        self.populate_recipients()

    def on_recipient_selected(self, item):
        """Handles recipient selection and populates sessions."""
        self.recipient = item.text()
        self.clear_list(self.session_selector)
        self.clear_list(self.request_selector)
        self.clear_session_table()
        self.populate_sessions()
        self.on_recipient_change()

    def on_session_selected(self, item):
        """Handles session selection and populates requests."""
        self.session_name = item.text()
        self.clear_list(self.request_selector)
        self.clear_session_table()
        self.populate_requests()
        self.on_session_change()

    def on_request_selected(self, item):
        """Handles request selection."""
        self.request_name = item.text()
        self.on_request_change()

    def clear_list(self, list_widget):
        """Clears all items from a QListWidget."""
        list_widget.clear()

    def clear_session_table(self):
        data = {
        "Name": ["No Data"],
        }
        self.empty_df = pd.DataFrame(data)
        self.update_session_table(self.empty_df)
        self.clear_preview_table()

    def clear_preview_table(self):
        self.update_preview_table(self.empty_df)
        self.clear_selected_rows_pane()

    def clear_selected_rows_pane(self):
        # print("Clearing selected rows pane explicitly...")
        self.selected_rows_pane_model = EditablePandasModel(pd.DataFrame())  # Explicitly use an empty DataFrame
        self.selected_rows_pane_table.setModel(self.selected_rows_pane_model)
        # print("Selected rows pane cleared.")

    def populate_clients(self):
        self.clear_list(self.client_selector)
        self.root_directory = self.session_manager.root_directory
        self.client = ''
        self.project = ''
        self.recipient = ''
        self.session_name = ''
        self.request_name = ''
        not_clients = ["vendors", "OUT", "packaging", "IN"]
        for client in self.session_manager.get_clients():
            if client in not_clients:
                continue

            # Add "New Client" or other client
            if client == "New Client":
                self.client_selector.addItem("New Client")
            else:
                # print("Client again: ", client)
                self.client_selector.addItem(client)

    def populate_projects(self):
        self.clear_list(self.project_selector)
        self.project = ''
        self.recipient = ''
        self.session_name = ''
        self.request_name = ''
        for project in self.session_manager.get_projects(self.client):
            self.project_selector.addItem("New project") if project == "New project" else self.project_selector.addItem(project)

    def populate_recipients(self):
        self.clear_list(self.recipient_selector)
        self.recipient = ''
        self.session_name = ''
        self.request_name = ''
        for recipient in self.session_manager.get_recipients(self.client, self.project):
            self.recipient_selector.addItem("New recipient") if recipient == "New recipient" else self.recipient_selector.addItem(recipient)

    def populate_sessions(self):
        self.clear_list(self.session_selector)
        self.session_name = ''
        self.request_name = ''
        for session in self.session_manager.get_sessions(self.client, self.project, self.recipient):
            self.session_selector.addItem("New session") if session == "New session" else self.session_selector.addItem(session)

    def populate_requests(self):
        self.clear_list(self.request_selector)
        self.request_name = ''
        for request in self.session_manager.get_requests(self.client, self.project, self.recipient, self.session_name):
            self.request_selector.addItem("New request") if request == "New request" else self.request_selector.addItem(request)

    def on_jobs_dir_change(self):
        """Handles changes to the jobs directory."""
        new_jobs_dir = QFileDialog.getExistingDirectory(self, "Select Jobs Directory", self.jobs_directory_input.text())
        if new_jobs_dir:  # If a valid directory was selected
            self.jobs_directory_input.setText(new_jobs_dir)
            # self.clear_clients()  # Clear existing dropdowns
            self.populate_clients()  # Repopulate with the new jobs directory

    def on_client_change(self):
        selected_client = self.client_selector.currentItem()
        self.client = selected_client
        if selected_client == "New Client":
            self.session_manager.handle_new_item(
                self,
                self.client_selector,
                "Client",
                self.session_manager.add_new_client
            )
        elif selected_client == "":
            return  # Skip further processing if the blank item is selected
        else:
            # self.clear_projects()
            self.populate_projects()

    def on_project_change(self):
        selected_project = self.project_selector.currentItem()
        self.project = selected_project
        self.root_path = os.path.join(self.session_manager.root_directory, self.client, self.project, "packaging")
        if selected_project == "New Project":
            selected_client = self.client_selector.currentItem()
            if selected_client:
                self.session_manager.handle_new_item(
                    self,
                    self.project_selector,
                    "Project",
                    lambda project: self.session_manager.add_new_project(selected_client, project),
                )
        elif selected_project == "":
            return
        else:
            # self.clear_recipients()
            self.populate_recipients()

    def on_recipient_change(self):
        selected_recipient_item = self.recipient_selector.currentItem()
        if selected_recipient_item:
            selected_recipient = selected_recipient_item.text()  # Extract text
            self.recipient = selected_recipient
        else:
            self.recipient = None  # Handle cases where no item is selected

        if not self.root_output_dir:
            self.root_output_dir = self.session_manager.root_directory

        if self.recipient == "client":
            self.recipient_out = os.path.join(self.root_output_dir, "OUT", "client", self.client, self.project)
        else:
            self.recipient_out = os.path.join(self.root_output_dir, "OUT", "vendor", self.recipient, self.client, self.project)

        if selected_recipient == "New Recipient":
            selected_client = self.client_selector.currentItem()
            selected_project = self.project_selector.currentItem()
            if selected_client and selected_project:
                self.session_manager.handle_new_item(
                    self,
                    self.recipient_selector,
                    "Recipient",
                    lambda recipient: self.session_manager.add_new_recipient(
                        selected_client.text(),  # Extract text for `selected_client`
                        selected_project.text(),  # Extract text for `selected_project`
                        recipient,
                    ),
                )
        elif selected_recipient == "":
            return
        else:
            # self.clear_sessions()
            self.populate_sessions()

    def on_session_change(self):
        """Handle changes in the Session dropdown."""
        selected_session = self.session_name
        self.requests_file = os.path.join(self.session_manager.root_directory, self.recipient, "sessions", self.session_name, f"{self.session_name}_requests.csv")

        if selected_session == "New Session":
            selected_client = self.client_selector.currentItem()
            selected_project = self.project_selector.currentItem()
            selected_recipient = self.recipient_selector.currentItem()
            if selected_client and selected_project and selected_recipient:
                self.session_manager.handle_new_item(
                    self,
                    self.session_selector,
                    "Session",
                    lambda session: self.session_manager.add_new_session(
                        selected_client, selected_project, selected_recipient, session
                    ),
                )
        elif selected_session == "":
            return
        else:
            self.populate_requests()
            self.create_session_df_from_latest_requests()  # Use the helper method

    def create_session_df_from_latest_requests(self):
        """
        Initialize session_df from the latest CSV files in the session directory.
        Filters and combines request files into a single DataFrame.
        """
        try:
            session_dir = os.path.join(
                self.jobs_directory_input.text(), self.client, self.project, "packaging", 
                self.recipient, "sessions", self.session_name
            )
            requests_dir = os.path.join(session_dir, "requests")
            os.makedirs(requests_dir, exist_ok=True)  # Ensure the requests directory exists

            session_df = pd.DataFrame()  # Placeholder for the combined DataFrame

            # Find request files with a timestamp in their name
            request_files = [
                file for file in os.listdir(requests_dir)
                if re.match(r".+-\d{14}\.csv", file)
            ]
            if not request_files:
                # QMessageBox.warning(self, "No Request Files", "No timestamped request files found.")
                return

            latest_requests = {}
            # Find the latest request file for each unique request name
            for file in request_files:
                request_name = file.split("-")[0]  # Extract the base request name
                if request_name not in latest_requests or file > latest_requests[request_name]:
                    latest_requests[request_name] = file

            # Load and combine the latest request files into a single DataFrame
            for request_file in latest_requests.values():
                request_file_path = os.path.join(requests_dir, request_file)
            
                dtype_mapping = {
                    'PADDING': str,
                    'FIRSTFRAME': str,
                    'LASTFRAME': str,
                }  # , dtype=dtype_mapping Default to an empty dictionary if no mapping is provided
                # self.dataframe = pd.read_csv(self.file_path, dtype=dtype_mapping)

                request_df = pd.read_csv(request_file_path, dtype=dtype_mapping)
                session_df = pd.concat([session_df, request_df], ignore_index=True)

            # self.session_df = self.filter_session_data(session_df)
            self.session_df = session_df
            self.update_session_table(self.session_df)  # Refresh the session table
            # QMessageBox.information(self, "Requests Loaded", "Latest request files have been loaded.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load requests: {str(e)}")

    def filter_session_data(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Filter the given DataFrame to remove duplicates based on specific criteria.

        Args:
            dataframe (pd.DataFrame): The session DataFrame to filter.

        Returns:
            pd.DataFrame: The filtered DataFrame.
        """
        if dataframe.empty:
            print("DataFrame is empty.")
            return dataframe

        print(f"Initial DataFrame shape: {dataframe.shape}")

        if "RAWITEMNAME" in dataframe.columns:
            initial_rows = len(dataframe)
            dataframe = dataframe.drop_duplicates(subset=["RAWITEMNAME"], keep="first")
            print(f"Removed {initial_rows - len(dataframe)} duplicate rows based on 'RAWITEMNAME'.")
        else:
            print("'RAWITEMNAME' column not found. No deduplication applied.")

        print(f"Final DataFrame shape: {dataframe.shape}")
        return dataframe

    def on_request_change(self):
        """Handle changes in the Request dropdown."""
        selected_request = self.request_name
        jobs_dir = self.jobs_directory_input.text()
        session_dir = os.path.join(
            jobs_dir, self.client, self.project, "packaging", self.recipient, "sessions", self.session_name
        )
        requests_dir = os.path.join(session_dir, "requests")
        self.requests_dir = requests_dir

        if selected_request == "New Request":
            # Handle new request creation
            self.handle_new_request()
        elif selected_request == "":
            # Do nothing on blank selection
            return
        else:
            # Handle an existing request
            source_file_path = os.path.join(self.requests_dir, f"{selected_request}_source_files.csv")
            provisioning_template_path = os.path.join(self.requests_dir, f"{selected_request}_provisioning_template.csv")
            self.file_path = os.path.join(self.requests_dir, f"{selected_request}.csv")
            # print(source_file_path)
            # print(provisioning_template_path)
            # print(self.file_path)

            missing_files = []
            if not os.path.exists(source_file_path):
                missing_files.append("Source Files CSV")
            if not os.path.exists(provisioning_template_path):
                missing_files.append("Provisioning Template CSV")

            if missing_files:
                # Inform the user about missing files and offer to create them
                reply = QMessageBox.question(
                    self,
                    "Missing Files",
                    f"The following required files are missing for the selected request:\n\n"
                    f"{', '.join(missing_files)}\n\n"
                    "Would you like to provide these files now?",
                    QMessageBox.Yes | QMessageBox.No,
                )

                if reply == QMessageBox.Yes:
                    # Use handle_new_request but pass the existing request name
                    self.handle_new_request(request_name=selected_request)
                else:
                    QMessageBox.warning(self, "Request Not Loaded", "Request setup was canceled due to missing files.")
            else:
                try:
                    # Load existing files into manager and requestor
                    self.load_source_csv(source_file_path=source_file_path)
                    self.load_provisioning_template(provisioning_template_path)

                    # Update `selected_rows_columns` only after successful loading
                    self.update_selected_rows_columns()

                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load the request: {str(e)}")

                # Add functionality to load the latest {request}-{timestamp}.csv file
                try:
                    # Search for remapped files matching the {request}-{timestamp}.csv pattern
                    remapped_files = [
                        file for file in os.listdir(self.requests_dir)
                        if re.match(rf"{re.escape(selected_request)}-\d{{14}}\.csv", file)
                    ]

                    if remapped_files:
                        # Find the latest remapped file by timestamp
                        latest_file = max(
                            remapped_files,
                            key=lambda f: datetime.strptime(f.split("-")[-1].split(".")[0], "%Y%m%d%H%M%S")
                        )
                        latest_file_path = os.path.join(self.requests_dir, latest_file)

                        # Load the latest remapped file into `selected_rows_remapped_df`
                    
                        dtype_mapping = {
                            'PADDING': str,
                            'FIRSTFRAME': str,
                            'LASTFRAME': str,
                        }  # , dtype=dtype_mapping Default to an empty dictionary if no mapping is provided
                        self.selected_rows_remapped_df = pd.read_csv(latest_file_path, dtype=dtype_mapping)

                except Exception as e:
                    print(f"Failed to load remapped file: {e}")  # Log failure, no disruptive messaging

    def handle_new_recipient(self):
        """Handle the creation or selection of a new recipient."""
        vendor_dir = os.path.join(self.session_manager.root_directory, "vendors")
        if not os.path.exists(vendor_dir):
            os.makedirs(vendor_dir)

        # List of directories in `vendors`
        recipient_options = [d for d in os.listdir(vendor_dir) if os.path.isdir(os.path.join(vendor_dir, d))]
        
        # Show the selection dialog
        dialog = ListInputDialog(self, "Select or Create New Recipient", recipient_options)
        if dialog.exec() == QDialog.Accepted:
            result = dialog.get_result()
            if result == "New...":
                # Show the dual-input dialog for a new recipient
                input_dialog = DualInputDialog(self, "New Recipient", blacklist=['>', '<', '|', ';'])
                if input_dialog.exec() == QDialog.Accepted:
                    full_name, working_name = input_dialog.get_results()

                    # Create the new recipient
                    self.session_manager.add_new_recipient(self.client, self.project, working_name)

                    # Refresh the recipients and select the newly created one
                    self.populate_recipients()
                    self.select_list_item(self.recipient_selector, working_name)
            else:
                # Existing recipient case
                self.session_manager.add_new_recipient(self.client, self.project, result)
                self.populate_recipients()
                self.select_list_item(self.recipient_selector, result)

    def handle_new_session(self):
        """Handle the creation or selection of a new session."""
        session_csv_path = os.path.join(self.session_manager.root_directory, self.client, self.project, "sessions.csv")
        session_options = []
        # Get the correct session directory path
        session_path = os.path.join(self.session_manager.root_directory, self.client, self.project, "packaging", self.recipient, "sessions")

        if os.path.exists(session_csv_path):
            try:
                session_df = pd.read_csv(session_csv_path)
                session_options = session_df.iloc[:, 0].tolist()  # Use the first column
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to read sessions.csv: {e}")
        else:
            # Use default whitelist if sessions.csv doesn't exist
            session_options = ["Roto", "Prep", "Matchmove"]
            
        # Show the selection dialog
        dialog = ListInputDialog(self, "Select or Create New Session", session_options)
        if dialog.exec() == QDialog.Accepted:
            result = dialog.get_result()
            if result == "New...":
                # Show the dual-input dialog for a new session
                input_dialog = DualInputDialog(self, "New Session", blacklist=['>', '<', '|', ';'])
                if input_dialog.exec() == QDialog.Accepted:
                    full_name, working_name = input_dialog.get_results()

                    # Add padded appendage to ensure a unique name
                    working_name = self.add_padded_appendage(working_name, session_path, source_type="directory")
                    print("What name did i go for?", working_name)

                    # Create the new session
                    self.session_manager.add_new_session(self.client, self.project, self.recipient, working_name)

                    # Refresh the sessions and select the newly created one
                    self.populate_sessions()
                    self.select_list_item(self.session_selector, working_name)
            else:
                # Existing session case
                working_name = self.add_padded_appendage(result, session_path, source_type="directory")
                self.session_manager.add_new_session(self.client, self.project, self.recipient, working_name)
                self.populate_sessions()
                self.select_list_item(self.session_selector, result)

    def handle_new_request(self, request_name=None):
        """Handle the creation of a new request or missing files for an existing request."""
        # Load existing request names or use defaults
        requests_csv_path = os.path.join(self.root_path, f"{self.session_name}_requests.csv")
        request_options = []

        if os.path.exists(requests_csv_path):
            try:
                requests_df = pd.read_csv(requests_csv_path)
                request_options = requests_df.iloc[:, 0].tolist()  # Use the first column
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to read requests.csv: {e}")
        else:
            # Default whitelist if no requests.csv exists
            request_options = ["bidRequest", "turnover", "reference", "editorial"]

        # Show the selection dialog
        dialog = ListInputDialog(self, "Select or Create New Request", request_options)
        if dialog.exec() == QDialog.Accepted:
            result = dialog.get_result()

            if result == "New...":  # Handle the "New..." option
                # Show the dual-input dialog
                input_dialog = DualInputDialog(self, "New Request", blacklist=['>', '<', '|', ';'])
                if input_dialog.exec() == QDialog.Accepted:
                    full_name, working_name = input_dialog.get_results()

                    # Ensure the working name is unique with a padded appendage
                    requests_dir = os.path.join(self.root_path, self.recipient, "sessions", self.session_name)
                    working_name = self.add_padded_appendage(working_name, requests_dir, source_type="csv")
                    

                    # Prompt for source_files_csv
                    source_file_path = self.prompt_source_file_path()
                    if not source_file_path:
                        QMessageBox.warning(self, "Request Not Created", "Source Files CSV is required.")
                        return

                    # Prompt for provisioning_template_csv
                    provisioning_template_path = self.prompt_provisioning_template_path()
                    if not provisioning_template_path:
                        QMessageBox.warning(self, "Request Not Created", "Provisioning Template CSV is required.")
                        return

                    # Create the request by copying the provided files
                    try:
                        self.session_manager.add_new_request(
                            client=self.client,
                            project=self.project,
                            recipient=self.recipient,
                            session_name=self.session_name,
                            request_name=working_name,
                            source_csv_path=source_file_path,
                            provisioning_template_path=provisioning_template_path,
                        )
                        QMessageBox.information(
                            self, "Request Created",
                            f"Request '{working_name}' setup has been completed."
                        )
                        self.populate_requests()  # Refresh the requests dropdown
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to create the request: {str(e)}")
            else:  # Handle existing request selection
                request_name = result

        if not request_name:  # Ensure a name was set
            QMessageBox.warning(self, "Request Not Created", "No request name provided.")
            return

        # Add padded appendage (for existing requests)
        # print("this is the requests_dir debug: ", self.root_path, self.recipient, self.session_name)
        requests_dir = os.path.join(self.root_path, self.recipient, "sessions", self.session_name)
        request_name = self.add_padded_appendage(request_name, requests_dir, source_type="csv")
        # Prompt for source_files_csv (if not provided yet)
        source_file_path = self.prompt_source_file_path()
        if not source_file_path:
            QMessageBox.warning(self, "Request Not Created", "Source Files CSV is required.")
            return

        # Prompt for provisioning_template_csv (if not provided yet)
        provisioning_template_path = self.prompt_provisioning_template_path()
        if not provisioning_template_path:
            QMessageBox.warning(self, "Request Not Created", "Provisioning Template CSV is required.")
            return

        # Create the request (for existing requests)
        try:
            self.session_manager.add_new_request(
                client=self.client,
                project=self.project,
                recipient=self.recipient,
                session_name=self.session_name,
                request_name=request_name,
                source_csv_path=source_file_path,
                provisioning_template_path=provisioning_template_path,
            )
            QMessageBox.information(
                self, "Request Created",
                f"Request '{request_name}' setup has been completed."
            )
            self.populate_requests()  # Refresh the requests dropdown
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create the request: {str(e)}")

    def prompt_source_file_path(self) -> str:
        """Prompt the user to select or create a source file path."""
        source_dir = os.path.join(self.root_job_path, "fs_updates")
        # Ensure the directory exists
        os.makedirs(source_dir, exist_ok=True)

        # Get the list of CSV files in the directory
        options = sorted([f for f in os.listdir(source_dir) if f.endswith(".csv")])
        # options.append("New Scrape")  # Add the "New Scrape" option

        # Show the selection dialog
        dialog = ListInputDialog(self, "Select Source Files CSV", options)
        if dialog.exec() == QDialog.Accepted:
            selected = dialog.get_result()

            # Handle "New Scrape" option
            if selected == "New...":
                # Wrap DirectoryLoaderUI in a QDialog
                loader_dialog = QDialog(self)
                loader_dialog.setWindowTitle("Directory Loader")
                loader_dialog.resize(800, 1200)

                loader = DirectoryLoaderUI(self.session_manager.root_directory, self.client, self.project)
                layout = QVBoxLayout(loader_dialog)
                layout.addWidget(loader)
                loader_dialog.setLayout(layout)

                # Launch the DirectoryLoaderUI
                if loader_dialog.exec() == QDialog.Accepted:
                    # Rebuild the options list and re-show the dialog if a new file was added
                    return self.prompt_source_file_path()
                else:
                    # User canceled the loader
                    print("User canceled 'New Scrape' operation.")
                    return self.prompt_source_file_path()

            # Handle regular file selection
            else:
                full_path = os.path.join(source_dir, selected)
                if os.path.exists(full_path):  # Ensure the file exists
                    print(f"Selected file path: {full_path}")
                    return full_path
                else:
                    print(f"Selected file does not exist: {full_path}")
                    QMessageBox.warning(
                        self, "File Not Found", f"The selected file could not be found:\n{full_path}"
                    )
                    return self.prompt_source_file_path()

        # User canceled the dialog
        print("User canceled file selection dialog.")
        return None

    def prompt_provisioning_template_path(self) -> str:
        """Prompt the user to select or import a provisioning template."""
        global_templates_dir = os.path.join(self.root_directory, "packaging", "global")
        vendor_templates_dir = os.path.join(self.root_directory, "packaging", "vendor", self.recipient)
        client_templates_dir = os.path.join(self.root_directory, "packaging", "client", self.client)
        project_templates_dir = os.path.join(self.root_directory, "packaging", "client", self.client, self.project)
        template_dir = os.path.join(self.root_job_path, "templates")
        custom_templates_dir = ''
        print("templates are in this directory: ", template_dir)
        if not os.path.exists(template_dir):
            os.makedirs(template_dir)  # Create the directory if it doesn't exist

        # Get the list of CSV files in the directory
        global_options = [f.name for f in Path(global_templates_dir).rglob("*.csv")]
        options = [f for f in os.listdir(template_dir) if f.endswith(".csv")]
        options = options + global_options
        options.append("Import Template")

        # Show the selection dialog
        dialog = ListInputDialog(self, "Select Provisioning Template CSV", options)
        if dialog.exec() == QDialog.Accepted:
            selected = dialog.get_result()
            if selected == "Import Template":
                # Open a file dialog to import the template
                file_path, _ = QFileDialog.getOpenFileName(
                    self, "Import Template", "", "CSV Files (*.csv);;All Files (*)"
                )
                if file_path:
                    # Copy the selected file to the templates directory
                    new_file_path = os.path.join(template_dir, os.path.basename(file_path))
                    shutil.copyfile(file_path, new_file_path)
                    print("copied: ", file_path, "  - to -  ", new_file_path)
                    return self.prompt_provisioning_template_path()  # Refresh and re-prompt
            else:
                return os.path.join(template_dir, selected)

        return None  # User canceled the dialog

    def add_padded_appendage(self, name: str, path: str, source_type: str = "directory") -> str:
        """
        Add a 3-padded numeric suffix to the name to ensure uniqueness.

        Args:
            name (str): The base name to append the padded suffix to.
            path (str): The directory or CSV file path to check for existing names.
            source_type (str): Determines the source type to check for names:
                            - 'directory': Check for existing items in the directory.
                            - 'csv': Check for existing items in a CSV file.

        Returns:
            str: The unique name with a padded suffix.
        """
        print(f"Preparing to add appendage for: {name} in {path} using {source_type}")

        max_suffix = 0  # Start with 0 to handle empty cases

        if source_type == "directory":
            # Ensure the directory exists
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)

            # List all items in the directory
            existing_items = os.listdir(path)
            print(f"Existing items: {existing_items}")

            # Filter items starting with the name and having a numeric suffix
            matching_items = [
                item for item in existing_items if item.startswith(name) and '-' in item
            ]
            for item in matching_items:
                try:
                    suffix = int(item.rsplit('-', 1)[-1])
                    max_suffix = max(max_suffix, suffix)
                except ValueError:
                    continue  # Skip items that don't end with a numeric suffix

        elif source_type == "csv":
            # Construct the path to the expected `_requests.csv` file
            requests_csv = os.path.join(path, f"{self.session_name}_requests.csv")
            if os.path.exists(requests_csv):
                try:
                    requests_df = pd.read_csv(requests_csv)
                    if not requests_df.empty:
                        # Extract the last entry and increment its numeric suffix
                        last_item = requests_df.iloc[-1, 0]
                        print(f"Last item in CSV: {last_item}")
                        if '-' in last_item:
                            suffix = int(last_item.rsplit('-', 1)[-1])
                            max_suffix = max(max_suffix, suffix)
                except Exception as e:
                    print(f"Failed to read requests CSV: {e}")
            else:
                print(f"No requests CSV found at: {requests_csv}")

        else:
            raise ValueError(f"Invalid source_type: {source_type}. Must be 'directory' or 'csv'.")

        # Increment and format the suffix
        new_suffix = max_suffix + 1
        unique_name = f"{name}-{new_suffix:03d}"
        print(f"Unique name generated: {unique_name}")

        return unique_name

    def select_list_item(self, list_widget, item_text):
        """Select an item in a QListWidget by its text."""
        matching_items = list_widget.findItems(item_text, Qt.MatchExactly)
        if matching_items:
            list_widget.setCurrentItem(matching_items[0])

    def toggle_session_setup(self, checked):
        """Toggle the visibility of the session setup widget."""
        self.session_setup_widget.setVisible(checked)

    def toggle_selected_rows_pane(self, checked):
        """
        Toggle the visibility of the selected_rows_pane_table.
        """
        self.selected_rows_pane_table.setVisible(checked)
        if checked:
            self.toggle_selected_rows_button.setText("Hide Selected Rows Pane")
        else:
            self.toggle_selected_rows_button.setText("Show Selected Rows Pane")

    def toggle_preview_table(self, checked):
        """
        Toggle the visibility of the preview_table.
        """
        self.preview_table.setVisible(checked)
        if checked:
            self.toggle_preview_button.setText("Hide Preview Table")
        else:
            self.toggle_preview_button.setText("Show Preview Table")

    def load_file(self, file_path):
        
        if file_path:
            self.file_path_input.setText(file_path)
            self.file_type = 'csv' if file_path.endswith('.csv') else 'txt'
            if self.file_type == 'csv':
                self.template_data = pd.read_csv(file_path)
                self.preview_data = self.template_data
                # self.column_list_widget.clear()
                # self.column_list_widget.setVisible(True)
                all_cols_item = QListWidgetItem("all-cols")
                all_cols_item.setCheckState(Qt.Unchecked)
                # self.column_list_widget.addItem(all_cols_item)
                for col in self.preview_data.columns:
                    item = QListWidgetItem(col)
                    item.setCheckState(Qt.Unchecked)
                    # self.column_list_widget.addItem(item)
            else:
                with open(file_path, 'r') as file:
                    text = file.read()
                self.preview_data = pd.DataFrame([[text]], columns=['text'])
                # self.column_list_widget.setVisible(False)
            # self.preview_display.setText(str(self.preview_data))

    def reintegrate_using_parser(self, text, parsed_variables, mapping_dict):
        """
        Reintegrate text using parser insights and a mapping dictionary.

        Parameters:
        - text (str): The original text chunk to modify.
        - parsed_variables (list): Variables extracted by the parser.
        - mapping_dict (dict): Mappings of variables to replacements.

        Returns:
        - str: Text with replacements applied intelligently.
        """
        # Tokenize the text into components split by common delimiters
        delimiters = self.payload_handler.delimiters
        pattern = f"([{''.join(map(re.escape, delimiters))}])"
        tokens = re.split(pattern, text)

        # Replace tokens only if they exactly match a parsed variable
        for i, token in enumerate(tokens):
            if token in parsed_variables and token in mapping_dict:
                tokens[i] = mapping_dict[token]  # Replace token using mapping

        # Reconstruct the text from tokens
        return "".join(tokens)

    def save_remapped_file(self, save_option, data_source="request"):
        """
        Save the remapped data (request or session) to a file.

        Args:
            save_option (str): One of ["original", "save_as", "timestamped"].
            data_source (str): Either "request" (default) or "session" to specify the data source to save.
        """
        # Determine the DataFrame and default file path to save
        if data_source == "request":
            remapped_data = self.selected_rows_remapped_df
            file_path = self.file_path  # Request file path
        elif data_source == "session":
            remapped_data = self.session_df
            if remapped_data is None or remapped_data.empty:
                QMessageBox.warning(self, "No Data", "No session data to save.")
                return
            # Generate the default session file path
            session_dir = os.path.join(
                self.jobs_directory_input.text(), self.client, self.project,
                "packaging", self.recipient, "sessions", self.session_name
            )
            file_path = os.path.join(session_dir, f"{self.session_name}.csv")
        else:
            raise ValueError("Invalid data_source specified. Use 'request' or 'session'.")

        if remapped_data is None or remapped_data.empty:
            QMessageBox.warning(self, "No Data", "No data available to save.")
            return

        # Use OutputManager to handle saving
        try:
            self.output_manager.save(remapped_data, file_path, "csv", save_option)
            # Trigger final version logging in StringMappingManager
            self.manager.finalize_logging()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

class SessionManager:
    def __init__(self, root_directory):
        self.root_directory = os.path.expanduser(root_directory)
        self.session_csv = os.path.join(self.root_directory, "sessions.csv")
        print(self.session_csv)

        # Ensure the session CSV exists
        if not os.path.exists(self.session_csv):
            pd.DataFrame(columns=["session_name"]).to_csv(self.session_csv, index=False)

    def get_clients(self):
        return [d for d in os.listdir(self.root_directory) if os.path.isdir(os.path.join(self.root_directory, d))]

    def get_projects(self, client):
        self.client_path = os.path.join(self.root_directory, client)
        return [d for d in os.listdir(self.client_path) if os.path.isdir(os.path.join(self.client_path, d))]

    def get_recipients(self, client, project):
        project_path = os.path.join(self.root_directory, client, project, "packaging")
        os.makedirs(project_path, exist_ok=True)  # Ensure the "packaging" directory exists
        return [d for d in os.listdir(project_path) if os.path.isdir(os.path.join(project_path, d))]

    def get_sessions(self, client, project, recipient):
        recipient_path = os.path.join(self.root_directory, client, project, "packaging", recipient, "sessions")
        os.makedirs(recipient_path, exist_ok=True)  # Ensure the "sessions" directory exists
        return [d for d in os.listdir(recipient_path) if os.path.isdir(os.path.join(recipient_path, d))]

    def get_requests(self, client, project, recipient, session_name):
        """
        Get the list of requests and also prepare a DataFrame for saved session files.

        Parameters:
            client (str): Client name.
            project (str): Project name.
            recipient (str): Recipient name.
            session_name (str): Session name.

        Returns:
            List[str]: List of request names from the CSV file.
        """
        session_dir = os.path.join(self.root_directory, client, project, "packaging", recipient, "sessions", session_name)
        requests_file = os.path.join(session_dir, f"{session_name}_requests.csv")

        # Initialize storage for session files and latest session file
        self.session_files = []  # Store all session CSV files
        self.latest_session_file = None  # Store the latest session file

        # Step 1: Get timestamped session files
        if os.path.exists(session_dir):
            session_files = [
                file for file in os.listdir(session_dir)
                if re.match(r".+-\d{14}\.csv", file)  # Match timestamped session files
            ]
            self.session_files = sorted(session_files)  # Store sorted list of session files

            if self.session_files:
                self.latest_session_file = self.session_files[-1]  # The latest session file (last in sorted order)

            # Create a DataFrame for saved session files
            file_data = [
                {
                    "file_name": file,
                    "file_path": os.path.join(session_dir, file),
                    "is_latest": file == self.latest_session_file
                }
                for file in self.session_files
            ]
            self.saved_session_files_df = pd.DataFrame(file_data, columns=["file_name", "file_path", "is_latest"])
        else:
            # Initialize an empty DataFrame if no session files exist
            self.saved_session_files_df = pd.DataFrame(columns=["file_name", "file_path", "is_latest"])

        # Step 2: Get requests from the CSV
        if not os.path.exists(requests_file):
            return []  # Return an empty list if the requests file does not exist

        try:
            requests_df = pd.read_csv(requests_file)
            return requests_df['request_name'].tolist()  # Return request names from the CSV
        except Exception as e:
            raise IOError(f"Failed to read requests file: {str(e)}")

    def create_directory_structure(self, client, project, recipient, session_name):
        """Ensure directory structure is in place for a new session."""
        path = os.path.join(self.root_directory, client, project, "packaging", recipient, "sessions", session_name)
        os.makedirs(path, exist_ok=True)
        return path

    def handle_new_item(self, parent_widget, dropdown, type_label, create_func):
        """Handles the creation of a new item for a dropdown."""
        new_item_text, ok = QInputDialog.getText(
            parent_widget, f"New {type_label}", f"Enter a new {type_label}:"
        )
        if not ok or not new_item_text.strip():  # Ensure the dialog wasn't canceled and input is not empty
            print(f"No action taken for {type_label}.")  # Debug log
            return  # Do nothing if canceled
        new_item_text = new_item_text.strip()

        # Create the new item in the session manager
        create_func(new_item_text)

        # Add the new item to the dropdown
        new_item = QListWidgetItem(new_item_text)
        dropdown.addItem(new_item.text())  # Add the item as text
        matching_items = dropdown.findItems(new_item_text, Qt.MatchExactly)

        if matching_items:  # Ensure we match the new item
            dropdown.setCurrentItem(matching_items[0])  # Set the new item as selected

    def add_new_client(self, client):
        self.client = client
        client_path = os.path.join(self.root_directory, client)
        client_in_path = os.path.join(self.root_directory, "IN", "client", self.client)
        client_out_path = os.path.join(self.root_directory, "OUT", "client", self.client)
        os.makedirs(client_path, exist_ok=True)
        os.makedirs(client_in_path, exist_ok=True)
        os.makedirs(client_out_path, exist_ok=True)

    def add_new_project(self, client, project):
        self.project = project
        job_path = os.path.join(self.root_directory, client, project)
        
        project_path = os.path.join(self.root_directory, client, project, "packaging", "client")
        os.makedirs(project_path, exist_ok=True)

        shots_file = os.path.join(job_path, "shots.csv")
        if not os.path.exists(shots_file):
            df = pd.DataFrame(columns=["SHOTNAME", "ALTSHOTNAME", "FIRSTFRAME", "LASTFRAME"])
            df.to_csv(shots_file, index=False)
        
        io_path = os.path.join(job_path, "IO")
        os.makedirs(io_path, exist_ok=True)

        client_in = os.path.join(self.root_directory, "IN", "client", client, project)
        client_out = os.path.join(self.root_directory, "OUT", "client", client, project)
        os.makedirs(client_in, exist_ok=True)
        os.makedirs(client_out, exist_ok=True)

        from_client_path = os.path.join(io_path, "from_client")
        to_client_path = os.path.join(io_path, "to_client")
        rel_client_in = os.path.join("../../../IN/client", client, project)
        rel_client_out = os.path.join("../../../OUT/client", client, project)
        # Create symlinks
        try:
            os.symlink(rel_client_in, from_client_path)
            print(f"Created symlink: {from_client_path} -> {rel_client_in}")
        except FileExistsError:
            print(f"Symlink already exists: {from_client_path}")

        try:
            os.symlink(rel_client_out, to_client_path)
            print(f"Created symlink: {to_client_path} -> {rel_client_out}")
        except FileExistsError:
            print(f"Symlink already exists: {to_client_path}")

    def add_new_recipient(self, client, project, recipient_name):
        self.recipient = recipient_name
        self.job_root_dir = os.path.join(self.root_directory, client, project)
        vendor_path = os.path.join(self.job_root_dir, "packaging", self.recipient)
        recipient_path = os.path.join(self.root_directory, "vendors", self.recipient, client, project)
        recipient_in = os.path.join(self.root_directory, "IN", "vendor", self.recipient, client, project)
        recipient_out = os.path.join(self.root_directory, "OUT", "vendor", self.recipient, client, project)
        from_recipient = os.path.join(self.job_root_dir, "IO", f"from_{self.recipient}")
        to_recipient = os.path.join(self.job_root_dir, "IO", f"to_{self.recipient}")
        os.makedirs(recipient_path, exist_ok=True)
        os.makedirs(recipient_in, exist_ok=True)
        os.makedirs(recipient_out, exist_ok=True)
        self.create_relative_symlink(recipient_path, vendor_path)
        self.create_relative_symlink(recipient_in, from_recipient)
        self.create_relative_symlink(recipient_out, to_recipient)

    def add_new_session(self, client, project, recipient, session_name):
        self.session_name = session_name
        session_path = os.path.join(self.root_directory, client, project, "packaging", recipient, "sessions", session_name)
        session_requests_path = os.path.join(session_path, "requests")
        os.makedirs(session_path, exist_ok=True)
        os.makedirs(session_requests_path, exist_ok=True)

    def add_new_request(self, client, project, recipient, session_name, request_name, source_csv_path, provisioning_template_path):
        """
        Create a new request directory and populate it with the necessary files.

        Parameters:
        - client (str): Client name.
        - project (str): Project name.
        - recipient (str): Recipient name.
        - session_name (str): Session name.
        - request_name (str): Request name.
        - source_csv_path (str): Path to the source files CSV.
        - provisioning_template_path (str): Path to the provisioning template CSV.
        """
        session_dir = os.path.join(
            self.root_directory, client, project, "packaging", recipient, "sessions", session_name
        )
        requests_dir = os.path.join(session_dir, "requests")
        os.makedirs(requests_dir, exist_ok=True)

        # Copy and rename the source files CSV
        source_file_target = os.path.join(requests_dir, f"{request_name}_source_files.csv")
        try:
            shutil.copyfile(source_csv_path, source_file_target)
        except Exception as e:
            raise IOError(f"Failed to copy Source Files CSV: {str(e)}")

        # Copy and rename the provisioning template
        provisioning_file_target = os.path.join(requests_dir, f"{request_name}_provisioning_template.csv")
        try:
            shutil.copyfile(provisioning_template_path, provisioning_file_target)
        except Exception as e:
            raise IOError(f"Failed to copy Provisioning Template CSV: {str(e)}")

        # Append the request_name to the {session_name}_requests.csv file
        requests_file = os.path.join(session_dir, f"{session_name}_requests.csv")
        try:
            if os.path.exists(requests_file):
                # If the file exists, read it
                requests_df = pd.read_csv(requests_file)
            else:
                # If the file does not exist, create a new DataFrame
                requests_df = pd.DataFrame(columns=["request_name"])
            
            # Append the new request_name
            requests_df = pd.concat([requests_df, pd.DataFrame({"request_name": [request_name]})], ignore_index=True)
            
            # Filter for unique entries
            requests_df = requests_df.drop_duplicates(subset=["request_name"], keep="first")

            # Save the updated DataFrame back to the CSV
            requests_df.to_csv(requests_file, index=False)
        except Exception as e:
            raise IOError(f"Failed to update requests file: {str(e)}")

        print(f"New request, {request_name}, created for {session_name} session")

    def retire_request(self, client, project, recipient, session_name, request_name):
        """
        Retires all files matching `{request_name}*` by moving them to a 'retired' subdirectory
        and removes the request entry from `{session_name}_requests.csv`.

        Parameters:
            client (str): Client name.
            project (str): Project name.
            recipient (str): Recipient name.
            session_name (str): Session name.
            request_name (str): Request name to retire.

        Returns:
            int: Number of files moved.
        """
        # Get the current requests directory
        requests_dir = os.path.join(
            self.root_directory, client, project, "packaging", recipient, "sessions", session_name, "requests"
        )
        retired_dir = os.path.join(requests_dir, "retired")
        os.makedirs(retired_dir, exist_ok=True)  # Create the retired directory if it doesn't exist

        # Use glob to find all files matching the pattern `{request_name}*`
        pattern = os.path.join(requests_dir, f"{request_name}*")
        matching_files = glob(pattern)

        # Move each matching file to the 'retired' subdirectory
        for file_path in matching_files:
            shutil.move(file_path, os.path.join(retired_dir, os.path.basename(file_path)))

        # Remove the request entry from `{session_name}_requests.csv`
        session_dir = os.path.join(
            self.root_directory, client, project, "packaging", recipient, "sessions", session_name
        )
        requests_file = os.path.join(session_dir, f"{session_name}_requests.csv")

        try:
            # Load the CSV file
            if os.path.exists(requests_file):
                requests_df = pd.read_csv(requests_file)

                # Remove the row corresponding to `request_name`
                filtered_df = requests_df[requests_df['request_name'] != request_name]

                # Save the updated DataFrame back to the CSV
                filtered_df.to_csv(requests_file, index=False)
            else:
                raise FileNotFoundError(f"{requests_file} does not exist.")
        except Exception as e:
            raise IOError(f"Failed to update {requests_file}: {str(e)}")

        return len(matching_files)

    def create_relative_symlink(self, target, link_name):
        """
        Create a relative symbolic link pointing to 'target' named 'link_name'.
        """
        # Resolve the absolute paths
        target_path = Path(target).resolve()
        link_path = Path(link_name).resolve()

        # Compute the relative path from the link to the target
        relative_target = os.path.relpath(target_path, link_path.parent)

        # Create the symbolic link
        os.symlink(relative_target, link_path)
        print(f"Created symlink: {link_path} -> {relative_target}")

class ListInputDialog(QDialog):
    def __init__(self, parent, title, options, key_value_mode=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.selected_item = None

        # Main layout
        layout = QVBoxLayout(self)

        # List of items
        self.list_widget = QListWidget()
        for option in options:
            if isinstance(option, dict):
                display_text = f"{option['key']}, {option['value']}"
            else:
                display_text = option
            self.list_widget.addItem(display_text)

        if "New..." not in options:  # Ensure "New..." is added once
            self.list_widget.addItem("New...")

        layout.addWidget(self.list_widget)

        # New input fields (hidden initially)
        self.new_input_widget = QWidget()
        new_input_layout = QHBoxLayout(self.new_input_widget)

        self.new_key_input = QLineEdit()
        self.new_key_input.setPlaceholderText("Key (e.g., Roto)")
        self.new_value_input = QLineEdit()
        self.new_value_input.setPlaceholderText("Value (e.g., roto)")
        new_input_layout.addWidget(self.new_key_input)

        if key_value_mode:
            new_input_layout.addWidget(QLabel(":"))
            new_input_layout.addWidget(self.new_value_input)

        # layout.addWidget(self.new_input_widget)
        # self.new_input_widget.setVisible(False)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Connections
        self.list_widget.itemClicked.connect(self.on_item_selected)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def on_item_selected(self, item):
        """Show or hide the new input fields based on the selected item."""
        if item.text() == "New...":
            # self.new_input_widget.setVisible(True)
            self.new_key_input.setFocus()
        else:
            self.new_input_widget.setVisible(False)

    def get_result(self):
        """Return the selected or inputted item."""
        if self.new_input_widget.isVisible():
            key = self.new_key_input.text().strip()
            value = self.new_value_input.text().strip()
            if key:
                return {"key": key, "value": value} if value else key
        else:
            selected_item = self.list_widget.currentItem()
            if selected_item:
                return selected_item.text()
        return None

class DualInputDialog(QDialog):
    """A dialog to capture both Full Name and Working Name."""

    def __init__(self, parent, title, blacklist=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.blacklist = blacklist or []

        # Main layout
        layout = QVBoxLayout(self)

        # Full Name input
        layout.addWidget(QLabel("Full Name:"))
        self.full_name_input = QLineEdit(self)
        self.full_name_input.setPlaceholderText("Enter Full Name (e.g., 'New Recipient')")
        layout.addWidget(self.full_name_input)

        # Working Name input
        layout.addWidget(QLabel("Working Name:"))
        self.working_name_input = QLineEdit(self)
        self.working_name_input.setPlaceholderText("Enter Working Name (e.g., 'new_recipient')")
        layout.addWidget(self.working_name_input)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Connections
        self.ok_button.clicked.connect(self.validate_and_accept)
        self.cancel_button.clicked.connect(self.reject)

    def validate_and_accept(self):
        """Validate input and close the dialog if valid."""
        full_name = self.full_name_input.text().strip()
        working_name = self.working_name_input.text().strip()

        if not full_name or not working_name:
            QMessageBox.warning(self, "Invalid Input", "Both Full Name and Working Name are required.")
            return

        if any(char in full_name for char in self.blacklist):
            QMessageBox.warning(self, "Invalid Input", "Full Name contains invalid characters.")
            return

        if not re.match(r'^[a-z0-9_]+$', working_name):
            QMessageBox.warning(self, "Invalid Input", "Working Name must only contain lowercase letters, numbers, and underscores.")
            return

        self.accept()  # Close the dialog

    def get_results(self):
        """Return the Full Name and Working Name."""
        return self.full_name_input.text().strip(), self.working_name_input.text().strip()

class PathConfirmationDialog(QDialog):
    def __init__(self, initial_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Recipient Path")
        self.selected_path = initial_path  # Initialize with the given path
        self.resize(800, 150)

        # Layouts
        main_layout = QVBoxLayout(self)
        input_layout = QHBoxLayout()

        # Widgets
        self.label = QLabel("Confirm or edit the recipient path:")
        self.path_edit = QLineEdit(self.selected_path)
        self.browse_button = QPushButton("Browse...")
        self.confirm_button = QPushButton("Confirm")
        self.cancel_button = QPushButton("Cancel")

        # Add widgets to layouts
        input_layout.addWidget(self.path_edit)
        input_layout.addWidget(self.browse_button)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addWidget(self.label)
        main_layout.addLayout(input_layout)
        main_layout.addLayout(button_layout)

        # Connect signals
        self.browse_button.clicked.connect(self.open_file_browser)
        self.confirm_button.clicked.connect(self.confirm_path)
        self.cancel_button.clicked.connect(self.reject)

    def open_file_browser(self):
        """Open a file browser to select a directory."""
        new_path = QFileDialog.getExistingDirectory(self, "Select Directory", self.selected_path)
        if new_path:  # If a valid directory is selected, update the path
            self.path_edit.setText(new_path)

    def confirm_path(self):
        """Confirm the selected path and close the dialog."""
        self.selected_path = self.path_edit.text().strip()
        if not self.selected_path:
            QMessageBox.warning(self, "Invalid Path", "The path cannot be empty.")
            return
        self.accept()  # Close the dialog with QDialog.Accepted

class OutputManager:
    def __init__(self):
        self.format_handlers = {
            'csv': self._write_csv,
            'txt': self._write_txt,
        }
        self.naming_conventions = {
            'original': self._original_name,
            'save_as': self._save_as_name,
            'timestamped': self._timestamped_name,
        }

    def save(self, data, file_path, format_type, naming_option):
        # Get the correct file path based on the naming option
        save_path = self.naming_conventions[naming_option](file_path)

        # Check if the save path is empty (indicating cancel)
        if not save_path:
            QMessageBox.information(None, "Canceled", "Save operation was canceled.")
            return

        # Call the appropriate format handler method
        if format_type in self.format_handlers:
            self.format_handlers[format_type](data, save_path)
            QMessageBox.information(None, "Success", f"File saved successfully as:\n{save_path}")
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

    def _original_name(self, file_path):
        return file_path

    def _save_as_name(self, file_path):
        save_path, _ = QFileDialog.getSaveFileName(None, "Save As", file_path, "All Files (*)")
        return save_path  # Directly return the selected or empty path (if canceled)

    def _timestamped_name(self, file_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base, ext = os.path.splitext(file_path)
        return f"{base}-{timestamp}{ext}"

    def _write_csv(self, data, save_path):
        """Write DataFrame or string data to a CSV file."""
        if isinstance(data, pd.DataFrame):  # Save DataFrame directly
            data.to_csv(save_path, index=False)
        elif isinstance(data, str):  # Save string data as a single column CSV
            pd.DataFrame({'Remapped_Text': data.split("\n")}).to_csv(save_path, index=False)
        else:
            raise ValueError("Unsupported data type for CSV export.")

    def _write_txt(self, data, save_path):
        with open(save_path, 'w') as f:
            f.write(data)

class FileIO:
    def read(self, file_path):
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        else:
            with open(file_path, 'r') as f:
                text = f.read()
            return pd.DataFrame([[text]], columns=['text'])

    def write(self, data, save_path):
        if isinstance(data, pd.DataFrame):
            data.to_csv(save_path, index=False)
        else:
            with open(save_path, 'w') as f:
                f.write(data)

class PayloadHandler:
    def __init__(self):
        self.delimiters = ['-', '_', '.', '/', ':', '\\']

    def chunk_data(self, data, columns=None):
        """
        Iterates over rows in a DataFrame or plain text, limiting processing to specified columns.

        Args:
            data (DataFrame or str): The data to process.
            columns (list, optional): The columns to process if the data is a DataFrame.

        Yields:
            str: Processed row or text chunk as a single string.
        """
        if isinstance(data, pd.DataFrame):
            # Use specified columns, or default to all columns
            data = data[columns] if columns else data
            for _, row in data.iterrows():
                yield " ".join(str(value) for value in row.values)
        else:
            # Handle plain text input
            yield data

    def parse(self, data, parse_type, columns=None):
        """
        Routes data chunks to the appropriate parser based on the parse_type.

        Args:
            data: The data to parse (DataFrame or string).
            parse_type (str): The type of parsing to perform.
            columns (list, optional): Specific columns to process if the data is a DataFrame.

        Returns:
            list: The parsed results.
        """
        chunks = self.chunk_data(data, columns=columns)
        results = []

        for chunk in chunks:
            if parse_type == "uppercase":
                results.extend(Parsers.extract_uppercase(chunk, self.delimiters))
            elif parse_type == "path":
                results.extend(Parsers.extract_paths(chunk))
            elif parse_type == "raw_item_name":
                results.extend(Parsers.extract_raw_item_names(chunk))
            else:
                raise ValueError(f"Unknown parse_type: {parse_type}")

        return results

    def reintegrate(self, processed_chunks, original_data):
        """
        Reintegrates the processed chunks into the original structure.
        
        Args:
            processed_chunks (list of dict): List of rows with processed replacements.
            original_data (DataFrame): Original template data.

        Returns:
            DataFrame: Reintegrated DataFrame with replacements applied.
        """
        # Initialize a list to store rows with reintegrated values
        reintegrated_rows = []

        # Iterate through each processed chunk and the corresponding original row
        for original_row, processed_row in zip(original_data.iterrows(), processed_chunks):
            # Unpack original row
            index, original_values = original_row
            reintegrated_row = {}

            # Iterate through columns to replace only the matched values
            for col_name, original_value in original_values.items():
                # Replace only if the column exists in the processed row
                if col_name in processed_row and processed_row[col_name] is not None:
                    reintegrated_row[col_name] = processed_row[col_name]
                else:
                    reintegrated_row[col_name] = original_value

            # Add the reintegrated row to the list
            reintegrated_rows.append(reintegrated_row)

        # Convert the reintegrated rows back into a DataFrame
        return pd.DataFrame(reintegrated_rows)

class Parsers:
    @staticmethod
    def filter_blacklist_chars(parsed_list, blacklist_chars=None):
        """Filter out elements from parsed_list that contain any blacklisted character.
        
        If no blacklist_chars list is provided, a default set of characters will be used.
        """
        if blacklist_chars is None:
            blacklist_chars = ['>', '<', '|', ';']  # Default characters

        # Filter out items containing any blacklisted character
        filtered_list = [
            item for item in parsed_list
            if not any(char in item for char in blacklist_chars)
        ]
        
        return filtered_list

    @staticmethod
    def extract_paths(chunk, blacklist_chars=None):
        """Extracts potential path strings from the provided chunk and filters them
        using the blacklist if provided.
        """
        path_suspects = []
        i = 0
        while i < len(chunk):
            if chunk[i] in ('/', '\\'):
                start = i - 2 if i >= 2 and re.match(r'[A-Za-z]:', chunk[i-2:i]) else i
                end = i
                while end < len(chunk) and chunk[end] not in (' ', '\n', '\t', ';', ',', '|'):
                    end += 1
                path_suspect = chunk[start:end]
                path_suspects.append(path_suspect)
                i = end
            else:
                i += 1
        
        # Apply blacklist filtering if any suspects were found
        return Parsers.filter_blacklist_chars(path_suspects, blacklist_chars)

    @staticmethod
    def extract_uppercase(chunk, delimiters=None):
        # print("CHUNK provided by the PayloadHandler is:", chunk)
        delimiters = delimiters or ['-', '_', '.', '/', ':', '\\']
        parts = re.split(f"[{''.join(map(re.escape, delimiters))}]", chunk)
        parsed_strings = [part for part in parts if part.isupper() and len(part) > 1]
        parsed_strings = list(dict.fromkeys(parsed_strings))
        # print("PARSED STRINGS are:", parsed_strings)
        return parsed_strings

    @staticmethod
    def extract_raw_item_names(chunk):
        """Extract paths that end with a file extension."""
        path_suspects = Parsers.extract_paths(chunk)
        filtered_suspects = [
            path for path in path_suspects if re.search(r'\.\w+$', path)  # Basic check for file extension
        ]
        # print("raw filenames with file extensions:", filtered_suspects)
        raw_items = [(path, path.split('/')[-1]) for path in filtered_suspects]
        # print("RAWITEMNAMES are: ", raw_items)
        return raw_items

class MappingRequestor:
    def __init__(self):
        self.string_mapper = StringMappingManager()

    def map(self, parsed_strings, id_header, id_value, target_columns):
        self.string_mapper.set_mapping_context(id_header, id_value, target_columns)
        return [self.string_mapper.map_requested_values(string) for string in parsed_strings]

if __name__ == "__main__":

    app = QApplication(sys.argv)
    coordinator = RequestorUI()
    coordinator.show()
    sys.exit(app.exec())