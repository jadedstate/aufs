# src/aufs/user_tools/packaging/string_mapping_setup_uppercase.py

import os
import sys
import re
import pandas as pd
import shutil
from glob import glob
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QDialog, QProgressDialog, 
                               QMessageBox, QLineEdit, QComboBox, QLabel, QFileDialog, QMenu, QCheckBox, 
                               QApplication, QListWidget, QListWidgetItem, QMainWindow, QInputDialog, QTabWidget)
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

class JobDataIngestor(QWidget):
    def __init__(self, session_manager, ingest_widget, parent=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.ingest_widget = ingest_widget  # Explicit reference to IngestWidget

        self.client = ''
        self.project = ''
        self.recipient = ''
        self.root_output_dir = ''

        layout = QVBoxLayout()

        # === Setup Session ===
        self.session_setup_widget = QWidget()
        self.session_setup_widget.setVisible(True)
        session_layout = QVBoxLayout(self.session_setup_widget)

        # Jobs directory
        jobs_directory_layout = QHBoxLayout()
        self.jobs_directory_input = QLineEdit(os.path.expanduser("~/.aufs/config/jobs/active"))
        self.browse_jobs_dir_button = QPushButton("Browse")
        self.browse_jobs_dir_button.clicked.connect(self.on_jobs_dir_change)

        jobs_directory_layout.addWidget(QLabel("Jobs Directory:"))
        jobs_directory_layout.addWidget(self.browse_jobs_dir_button)
        jobs_directory_layout.addWidget(self.jobs_directory_input)

        jobs_directory_layout.addStretch()
        session_layout.addLayout(jobs_directory_layout)

        # === Panes ===
        panes_layout = QHBoxLayout()

        # Clients
        self.client_selector = QListWidget()
        self.populate_clients()
        self.client_selector.itemClicked.connect(self.on_client_selected)

        client_callback = lambda: self.session_manager.handle_new_item(
            self, self.client_selector, "Client", self.session_manager.add_new_client
        )

        client_widget = QWidget()
        client_layout = QVBoxLayout(client_widget)
        client_layout.addLayout(QVBoxLayoutWrapper("Client:", self.client_selector, add_new_callback=client_callback))
        panes_layout.addWidget(client_widget)

        # Projects
        self.project_selector = QListWidget()
        self.project_selector.itemClicked.connect(self.on_project_selected)

        project_callback = lambda: self.session_manager.handle_new_item(
            self, self.project_selector, "Project", lambda project_name: self.session_manager.add_new_project(self.client, project_name)
        )

        project_widget = QWidget()
        project_layout = QVBoxLayout(project_widget)
        project_layout.addLayout(QVBoxLayoutWrapper("Project:", self.project_selector, add_new_callback=project_callback))
        panes_layout.addWidget(project_widget)

        # Recipients
        self.recipient_selector = QListWidget()
        self.recipient_selector.itemClicked.connect(self.on_recipient_selected)

        recipient_callback = lambda: self.handle_new_recipient()

        recipient_widget = QWidget()
        recipient_layout = QVBoxLayout(recipient_widget)
        recipient_layout.addLayout(QVBoxLayoutWrapper("Recipient:", self.recipient_selector, add_new_callback=recipient_callback))
        panes_layout.addWidget(recipient_widget)

        # Add panes layout
        session_layout.addLayout(panes_layout)

        # Add session widget instead of layout
        layout.addWidget(self.session_setup_widget)
        self.setLayout(layout)  # Finalize layout

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

    def on_client_selected(self, item):
        """Handles client selection and populates projects."""
        self.client = item.text()
        self.clear_list(self.project_selector)
        self.clear_list(self.recipient_selector)

        # Populate projects
        self.populate_projects()

        # Clear IngestWidget destinations
        if self.ingest_widget:  # Use explicit reference
            self.ingest_widget.clear_destination_dropdown()

    def on_project_selected(self, item):
        """Handles project selection and populates recipients."""
        self.project = item.text()
        self.root_path = os.path.join(self.session_manager.root_directory, self.client, self.project, "packaging")
        self.root_job_path = os.path.join(self.session_manager.root_directory, self.client, self.project)
        self.clear_list(self.recipient_selector)

        # Populate recipients
        self.populate_recipients()

        # Clear IngestWidget destinations
        if self.ingest_widget:  # Use explicit reference
            self.ingest_widget.clear_destination_dropdown()

    def on_recipient_selected(self, item):
        """Handles recipient selection and updates the ingest widget."""
        self.recipient = item.text()

        # Trigger recipient change updates
        self.on_recipient_change()

        # Refresh IngestWidget destinations
        if self.ingest_widget:  # Use explicit reference
            self.ingest_widget.populate_destinations()

    def clear_list(self, list_widget):
        """Clears all items from a QListWidget."""
        list_widget.clear()

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
        # else:
        #     # self.clear_sessions()
        #     self.populate_sessions()

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

    def select_list_item(self, list_widget, item_text):
        """Select an item in a QListWidget by its text."""
        matching_items = list_widget.findItems(item_text, Qt.MatchExactly)
        if matching_items:
            list_widget.setCurrentItem(matching_items[0])

class IngestSessionManager:
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
            shutil.copy2file(source_csv_path, source_file_target)
        except Exception as e:
            raise IOError(f"Failed to copy Source Files CSV: {str(e)}")

        # Copy and rename the provisioning template
        provisioning_file_target = os.path.join(requests_dir, f"{request_name}_provisioning_template.csv")
        try:
            shutil.copy2file(provisioning_template_path, provisioning_file_target)
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

class IngestWidget(QWidget):
    def __init__(self, session_manager, parent=None, job_data_ingestor=None):
        super().__init__(parent)
        self.session_manager = session_manager

        # Store the reference to JobDataIngestor
        self.job_data_ingestor = job_data_ingestor

        # Initialize paths, UI components, etc.
        self.client = ''
        self.project = ''
        self.recipient = ''
        # self.setup_ui()

        # === Layouts ===
        main_layout = QVBoxLayout(self)

        # === Add Files/Folders Section ===
        add_buttons_layout = QHBoxLayout()
        self.add_files_button = QPushButton("Add Files")
        self.add_files_button.clicked.connect(self.add_files)
        add_buttons_layout.addWidget(self.add_files_button)

        self.add_folders_button = QPushButton("Add Folders")
        self.add_folders_button.clicked.connect(self.add_folders)
        add_buttons_layout.addWidget(self.add_folders_button)

        self.remove_selected_button = QPushButton("Remove Selected")
        self.remove_selected_button.clicked.connect(self.remove_selected_paths)  # Hook the function
        add_buttons_layout.addWidget(self.remove_selected_button)  # Add delete button

        main_layout.addLayout(add_buttons_layout)

        # === ListView for Paths ===
        self.paths_list = QListWidget()
        self.paths_list.setSelectionMode(QListWidget.MultiSelection)  # Enable multi-select
        main_layout.addWidget(self.paths_list)

        # === Total Size Label ===
        self.total_size_label = QLabel("Total Size: 0 B")
        main_layout.addWidget(self.total_size_label)

        self.options_layout = QHBoxLayout()
        self.options_layout.addWidget(QLabel("Destination:"))
        # === Destination Dropdown ===
        self.destination_dropdown = QComboBox()
        # self.populate_destinations()
        self.options_layout.addWidget(self.destination_dropdown)

        # === Merge Strategy Dropdown ===
        self.options_layout.addWidget(QLabel("Merge Strategy:"))
        self.merge_dropdown = QComboBox()
        self.merge_dropdown.addItems(["Replace", "Keep Newest"])
        self.options_layout.addWidget(self.merge_dropdown)

        self.options_layout.addStretch()

        main_layout.addLayout(self.options_layout)

        # === Action Buttons ===
        actions_layout = QHBoxLayout()
        self.move_button = QPushButton("Ingest-MOVE")
        self.move_button.clicked.connect(self.move_data)
        actions_layout.addWidget(self.move_button)

        self.copy_button = QPushButton("Ingest-COPY")
        self.copy_button.clicked.connect(self.copy_data)
        actions_layout.addWidget(self.copy_button)

        # self.cancel_button = QPushButton("Cancel")
        # self.cancel_button.clicked.connect(self.cancel_move)
        # actions_layout.addWidget(self.cancel_button)

        actions_layout.addStretch()

        main_layout.addLayout(actions_layout)

        # === Data Storage ===
        self.paths_df = pd.DataFrame(columns=["PATH", "PATHTYPE", "SIZE", "HRSIZE", "ISDUPLICATE"])  # Updated DataFrame

        self.setLayout(main_layout)

    def add_files(self):
        """Continuously prompt to add files until the user clicks Cancel."""
        # if not self.validate_selection():
        #     return
        while True:
            files, _ = QFileDialog.getOpenFileNames(self, "Select Files")
            if not files:  # User clicked Cancel
                break
            self.add_paths(files)

    def add_folders(self):
        """Continuously prompt to add folders until the user clicks Cancel."""
        # if not self.validate_selection():
        #     return
        while True:
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            if not folder:  # User clicked Cancel
                break
            self.add_paths([folder])

    def validate_selection(self):
        """Validate and pull the latest selection from JobDataIngestor."""
        # Pull fresh values from JobDataIngestor
        self.client = self.job_data_ingestor.client
        self.project = self.job_data_ingestor.project
        self.recipient = self.job_data_ingestor.recipient

        # Validate the selections
        if not self.client:
            QMessageBox.critical(self, "Error", "Please select a valid client.")
            return False
        if not self.project:
            QMessageBox.critical(self, "Error", "Please select a valid project.")
            return False
        if not self.recipient:
            QMessageBox.critical(self, "Error", "Please select a valid recipient.")
            return False

        return True

    def add_paths(self, new_paths):
        """Add new paths and update the UI."""
        for path in new_paths:
            if path not in self.paths_df['PATH'].values:  # Avoid duplicates
                self.add_to_dataframe(path)

        # Update duplicates, sizes, and UI
        self.update_duplicates()
        self.update_total_size()
        self.update_listview()

    def add_to_dataframe(self, path):
        """Add path metadata, including filesystem match check, to the DataFrame."""
        path_type = "Dir" if os.path.isdir(path) else "File"
        size = self.get_size(path)
        hr_size = self.human_readable_size(size)

        is_dest_fs_match = None  # Defer evaluation until recipient is selected
        new_row = pd.DataFrame(
            [[path, path_type, size, hr_size, False, is_dest_fs_match]],
            columns=["PATH", "PATHTYPE", "SIZE", "HRSIZE", "ISDUPLICATE", "ISDESTFSMATCH"]
        )
        self.paths_df = pd.concat([self.paths_df, new_row], ignore_index=True)

        self.paths = self.paths_df['PATH'].tolist()

    def remove_selected_paths(self):
        """Remove selected paths from the dataframe and update UI."""
        selected_items = self.paths_list.selectedItems()  # Get selected list items
        if not selected_items:  # Check if nothing is selected
            QMessageBox.warning(self, "No Selection", "Please select one or more items to delete.")
            return

        # Collect paths to delete
        paths_to_remove = [item.toolTip() for item in selected_items]  # Use tooltips to match paths

        # Remove from DataFrame
        self.paths_df = self.paths_df[~self.paths_df['PATH'].isin(paths_to_remove)]  # Filter out selected items

        # Update UI after deletion
        self.update_duplicates()
        self.update_total_size()
        self.update_listview()

        # QMessageBox.information(self, "Removed", f"{len(paths_to_delete)} item(s) deleted successfully!")

    def keyPressEvent(self, event):
        """Handle delete key to remove selected items."""
        if event.key() == Qt.Key_Delete:  # Check if Delete key is pressed
            self.delete_selected_paths()
        else:
            super().keyPressEvent(event)

    def get_size(self, path):
        """Calculate the size of a file or directory."""
        if os.path.isfile(path):
            return os.path.getsize(path)
        elif os.path.isdir(path):
            total_size = 0
            for dirpath, _, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
            return total_size
        return 0

    def update_duplicates(self):
        """Mark duplicate paths as duplicates in the DataFrame."""
        # self.paths = self.paths_df['PATH'].tolist()
        duplicates = []

        for i, path in enumerate(self.paths):
            for j, other_path in enumerate(self.paths):
                if i != j and path.startswith(other_path.rstrip("/") + "/"):
                    duplicates.append(i)

        self.paths_df['ISDUPLICATE'] = False
        self.paths_df.loc[duplicates, 'ISDUPLICATE'] = True

    def update_total_size(self):
        """Update the total size label, including cross-filesystem data size."""
        # Total size of non-duplicates
        filtered_df = self.paths_df[self.paths_df['ISDUPLICATE'] == False]
        total_size = filtered_df["SIZE"].sum()

        # Total size of cross-filesystem data
        cross_fs_df = filtered_df[filtered_df['ISDESTFSMATCH'] == False]
        cross_fs_size = cross_fs_df["SIZE"].sum()

        self.total_size_label.setText(
            f"Total Size: {self.human_readable_size(total_size)} "
            f"(Cross-FS: {self.human_readable_size(cross_fs_size)})"
        )

    def update_listview(self):
        """Update the ListView with paths from the DataFrame."""
        self.paths_list.clear()
        for _, row in self.paths_df.iterrows():
            display_text = self.format_display(row)
            item = QListWidgetItem(display_text)
            item.setToolTip(row["PATH"])
            self.paths_list.addItem(item)

    def format_display(self, row):
        """Format display text for a row in the DataFrame."""
        # Duplicate marker
        duplicate_marker = " [DUPLICATE]" if row['ISDUPLICATE'] else ""

        # Destination match marker
        if row['ISDESTFSMATCH'] is None:  # No destination set
            fs_marker = " [No Dest]"
        elif not row['ISDESTFSMATCH']:   # Cross-filesystem mismatch
            fs_marker = " [CROSS-FS]"
        else:                            # Match
            fs_marker = ""

        # Build and return the formatted string
        return f"{row['PATH']} ({row['PATHTYPE']}, {row['HRSIZE']}){duplicate_marker}{fs_marker}"

    def human_readable_size(self, size):
        """Convert bytes into a human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

    def setup_progress_dialog(self, total_steps):
        """Setup and display the progress dialog."""
        self.progress_dialog = QProgressDialog("Moving data...", "STOP", 0, total_steps, self)
        self.progress_dialog.setWindowTitle("Ingest Progress")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)  # Show immediately
        self.progress_dialog.canceled.connect(self.cancel_move)  # Connect STOP button

    def cancel_move(self):
        """Cancel the current move operation."""
        self.cancel_requested = True  # Set flag to stop further processing
        QMessageBox.information(self, "Cancelled", "Move operation cancelled!")

    def populate_destinations(self):
        """Populate the destination dropdown based on current selections."""
        if not self.validate_selection():
            return

        # Construct base path based on recipient type
        base_path = os.path.join(self.session_manager.root_directory, "IN")
        if self.recipient == "client":
            base_path = os.path.join(base_path, "client", self.client, self.project)
        else:
            base_path = os.path.join(base_path, "vendor", self.recipient, self.client, self.project)

        # Ensure directory exists and scan subfolders
        os.makedirs(base_path, exist_ok=True)
        existing_dirs = sorted(
            [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d)) and re.match(r"\d{8}_\d{3}", d)]
        )

        # Refresh dropdown
        self.destination_dropdown.clear()
        self.destination_dropdown.addItem("Create New Ingest Directory")
        self.destination_dropdown.addItems(existing_dirs)

        # Store base path for validation
        self.base_path = base_path

        self.recalculate_dest_fs_match()

    def recalculate_dest_fs_match(self):
        """Recalculate ISDESTFSMATCH after recipient selection."""
        for index, row in self.paths_df.iterrows():
            try:
                src_device = os.stat(row['PATH']).st_dev
                dest_device = os.stat(self.base_path).st_dev
                is_dest_fs_match = src_device == dest_device
            except Exception:
                is_dest_fs_match = False

            # Update the value
            self.paths_df.at[index, 'ISDESTFSMATCH'] = is_dest_fs_match
        
        # Refresh the ListView to reflect changes
        self.update_listview()

    def clear_destination_dropdown(self):
        self.destination_dropdown.clear()

    def merge_directories(self, src, dest, merge_strategy='replace'):
        """
        Merge contents of src directory into dest directory.

        Parameters:
        - src: Source directory path.
        - dest: Destination directory path.
        - merge_strategy: Strategy for handling conflicts ('replace', 'keep-newest', 'skip', 'fail').
        """
        if not os.path.exists(dest):
            os.makedirs(dest)

        for item in os.listdir(src):
            src_item = os.path.join(src, item)
            dest_item = os.path.join(dest, item)

            if os.path.isdir(src_item):
                self.merge_directories(src_item, dest_item, merge_strategy)
            else:
                if os.path.exists(dest_item):
                    if merge_strategy == 'replace':
                        shutil.move(src_item, dest_item)
                    elif merge_strategy == 'keep-newest':
                        if os.path.getmtime(src_item) > os.path.getmtime(dest_item):
                            shutil.move(src_item, dest_item)
                    elif merge_strategy == 'skip':
                        continue
                    elif merge_strategy == 'fail':
                        raise FileExistsError(f"Conflict: {dest_item} already exists.")
                else:
                    shutil.move(src_item, dest_item)

        # Optionally, remove the source directory after merging
        try:
            os.rmdir(src)
        except OSError:
            pass  # Directory not empty or other error

    def move_data(self):
        """Perform the move operation with progress and cancel support."""
        if self.paths_df.empty:
            QMessageBox.warning(self, "No Data", "No files or folders have been added.")
            return

        # === Destination Handling ===
        selected_dest = self.destination_dropdown.currentText()
        if selected_dest == "Create New Ingest Directory":
            date_str = datetime.utcnow().strftime("%Y%m%d")
            version = 1
            while True:
                dir_name = f"{date_str}_{version:03d}"
                destination = os.path.join(self.base_path, dir_name)
                if not os.path.exists(destination):
                    os.makedirs(destination)
                    break
                version += 1
        else:
            destination = os.path.join(self.base_path, selected_dest)

        # === Filesystem Warnings ===
        cross_fs_df = self.paths_df[self.paths_df['ISDESTFSMATCH'] == False]
        cross_fs_size = cross_fs_df["SIZE"].sum()

        if not cross_fs_df.empty:
            QMessageBox.warning(
                self,
                "Cross-Filesystem Move",
                f"WARNING: {len(cross_fs_df)} paths ({self.human_readable_size(cross_fs_size)}) "
                "are being moved across filesystems. Ensure sufficient space at the destination!"
            )

        # === Merge Strategy ===
        merge_strategy = self.merge_dropdown.currentText().lower().replace(" ", "-")  # e.g., 'Keep Newest' -> 'keep-newest'

        # === Sort Paths to Prioritize Directories ===
        self.paths.sort(key=lambda p: (not os.path.isdir(p), p))  # Directories first, then files

        # === Initialize Progress ===
        total_files = len(self.paths)
        self.setup_progress_dialog(total_files)
        self.cancel_requested = False

        # === Move Data ===
        errors = []
        for index, path in enumerate(self.paths):
            # === Check for Cancellation ===
            if self.cancel_requested:
                errors.append(f"Cancelled at {path}")
                break

            # === Skip Already Moved Paths ===
            if not os.path.exists(path):  # Path has already been moved inside a parent directory
                continue

            try:
                target = os.path.join(destination, os.path.basename(path))

                if os.path.isdir(path):
                    self.merge_directories(path, target, merge_strategy)
                else:
                    if os.path.exists(target):
                        if merge_strategy == 'replace':
                            shutil.move(path, target)
                        elif merge_strategy == 'keep-newest':
                            if os.path.getmtime(path) > os.path.getmtime(target):
                                shutil.move(path, target)
                        elif merge_strategy == 'skip':
                            continue
                        elif merge_strategy == 'fail':
                            raise FileExistsError(f"Conflict: {target} already exists.")
                    else:
                        print("Moving: ", path, " ----> ", target)
                        shutil.move(path, target)

                # === Update Progress ===
                self.progress_dialog.setValue(index + 1)

            except Exception as e:
                errors.append(str(e))

        # === Finalize Progress ===
        self.progress_dialog.setValue(total_files)

        # === Show Results ===
        if errors:
            QMessageBox.critical(self, "Errors", "\n".join(errors))
        else:
            QMessageBox.information(self, "Success", f"Data moved to:\n{destination}")
            self.populate_destinations()

    def copy_data(self):
        """Perform the copy operation with progress and cancel support."""
        if self.paths_df.empty:
            QMessageBox.warning(self, "No Data", "No files or folders have been added.")
            return

        # === Destination Handling ===
        selected_dest = self.destination_dropdown.currentText()
        if selected_dest == "Create New Ingest Directory":
            date_str = datetime.utcnow().strftime("%Y%m%d")
            version = 1
            while True:
                dir_name = f"{date_str}_{version:03d}"
                destination = os.path.join(self.base_path, dir_name)
                if not os.path.exists(destination):
                    os.makedirs(destination)
                    break
                version += 1
        else:
            destination = os.path.join(self.base_path, selected_dest)

        # === Filesystem Warnings ===
        cross_fs_df = self.paths_df[self.paths_df['ISDESTFSMATCH'] == False]
        cross_fs_size = cross_fs_df["SIZE"].sum()

        if not cross_fs_df.empty:
            QMessageBox.warning(
                self,
                "Cross-Filesystem copy",
                f"WARNING: {len(cross_fs_df)} paths ({self.human_readable_size(cross_fs_size)}) "
                "are being copied across filesystems. Ensure sufficient space at the destination!"
            )

        # === Merge Strategy ===
        merge_strategy = self.merge_dropdown.currentText().lower().replace(" ", "-")  # e.g., 'Keep Newest' -> 'keep-newest'

        # === Sort Paths to Prioritize Directories ===
        self.paths.sort(key=lambda p: (not os.path.isdir(p), p))  # Directories first, then files

        # === Initialize Progress ===
        total_files = len(self.paths)
        self.setup_progress_dialog(total_files)
        self.cancel_requested = False

        # === copy Data ===
        errors = []
        for index, path in enumerate(self.paths):
            # === Check for Cancellation ===
            if self.cancel_requested:
                errors.append(f"Cancelled at {path}")
                break

            # === Skip Already copyd Paths ===
            if not os.path.exists(path):  # Path has already been copyd inside a parent directory
                continue

            try:
                target = os.path.join(destination, os.path.basename(path))

                if os.path.isdir(path):
                    if not os.path.exists(target):
                        shutil.copytree(path, target, symlinks=True)  # Copy entire directory
                    else:
                        if merge_strategy == 'replace':
                            shutil.rmtree(target)
                            shutil.copytree(path, target, symlinks=True)
                        elif merge_strategy == 'keep-newest':
                            # Compare timestamps and copy newer files recursively
                            for src_dir, dirs, files in os.walk(path):
                                rel_path = os.path.relpath(src_dir, path)
                                dest_dir = os.path.join(target, rel_path)
                                os.makedirs(dest_dir, exist_ok=True)
                                for file in files:
                                    src_file = os.path.join(src_dir, file)
                                    dest_file = os.path.join(dest_dir, file)
                                    if not os.path.exists(dest_file) or os.path.getmtime(src_file) > os.path.getmtime(dest_file):
                                        shutil.copy2(src_file, dest_file)
                        elif merge_strategy == 'skip':
                            pass
                        elif merge_strategy == 'fail':
                            raise FileExistsError(f"Conflict: {target} already exists.")

                else:
                    if os.path.exists(target):
                        if merge_strategy == 'replace':
                            shutil.copy2(path, target)
                        elif merge_strategy == 'keep-newest':
                            if os.path.getmtime(path) > os.path.getmtime(target):
                                shutil.copy2(path, target)
                        elif merge_strategy == 'skip':
                            continue
                        elif merge_strategy == 'fail':
                            raise FileExistsError(f"Conflict: {target} already exists.")
                    else:
                        print("Copying: ", path, " ----> ", target)
                        shutil.copy2(path, target)

                # === Update Progress ===
                self.progress_dialog.setValue(index + 1)

            except Exception as e:
                errors.append(str(e))

        # === Finalize Progress ===
        self.progress_dialog.setValue(total_files)

        # === Show Results ===
        if errors:
            QMessageBox.critical(self, "Errors", "\n".join(errors))
        else:
            QMessageBox.information(self, "Success", f"Data copied to:\n{destination}")
            self.populate_destinations()

class MainAppWidget(QWidget):
    def __init__(self, session_manager, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Job Data Management")
        self.resize(1024, 768)

        # === Layout ===
        main_layout = QVBoxLayout(self)

        # Initialize widgets with cross-references
        self.ingest_widget = IngestWidget(session_manager=session_manager, parent=self)
        self.job_data_ingestor = JobDataIngestor(
            session_manager=session_manager,
            ingest_widget=self.ingest_widget,  # Pass reference to IngestWidget
            parent=self
        )

        # Now set the reverse reference inside the IngestWidget
        self.ingest_widget.job_data_ingestor = self.job_data_ingestor  # Cross-reference!

        # Add widgets to the layout
        main_layout.addWidget(self.job_data_ingestor)
        main_layout.addWidget(self.ingest_widget)

        # Exit Button
        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)
        main_layout.addWidget(self.exit_button)

        self.setLayout(main_layout)

    def populate_destinations_menu(self):
        self.ingest_widget.populate_destinations()

    def close_application(self):
        """
        Placeholder for cleanup routines before exiting.
        """
        # Add cleanup routines here if needed
        print("Performing cleanup before exit...")  # Example placeholder log
        QApplication.instance().quit()  # Close the app cleanly

if __name__ == "__main__":
    app = QApplication(sys.argv)
    session_manager = IngestSessionManager("~/.aufs/config/jobs/active")
    standalone_app = MainAppWidget(session_manager=session_manager)
    standalone_app.show()
    sys.exit(app.exec())
