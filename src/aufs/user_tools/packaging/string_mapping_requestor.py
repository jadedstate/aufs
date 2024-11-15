# src/aufs/user_tools/packaging/string_mapping_requestor.py

import os
import sys
import re
import pandas as pd
import shutil
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QMessageBox, QLineEdit, QLabel, QTextEdit, QFileDialog, QMenu,
                               QApplication, QComboBox, QListWidget, QListWidgetItem, QToolButton, QInputDialog, QTabWidget)
from PySide6.QtCore import Qt

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')
sys.path.insert(0, src_path)

from src.aufs.user_tools.packaging.string_mapping_manager import StringMappingManager

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

    # Naming convention methods
    def _original_name(self, file_path):
        return file_path

    def _save_as_name(self, file_path):
        save_path, _ = QFileDialog.getSaveFileName(None, "Save As", file_path, "All Files (*)")
        return save_path  # Directly return the selected or empty path (if canceled)

    def _timestamped_name(self, file_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        base, ext = os.path.splitext(file_path)
        return f"{base}_{timestamp}{ext}"

    # Format-specific writing methods
    def _write_csv(self, data, save_path):
        if isinstance(data, str):
            pd.DataFrame({'Remapped_Text': data.split("\n")}).to_csv(save_path, index=False)

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
    def chunk_data(self, data, columns=None):
        if isinstance(data, pd.DataFrame):
            # Select specified columns, or use all columns if none are specified
            data = data[columns] if columns else data
            for _, row in data.iterrows():
                # Yield each field as a full string without using to_string()
                yield " ".join(str(value) for value in row.values)
        else:
            # Handle plain text data for non-CSV files
            yield data

    def reintegrate(self, processed_chunks, data):
        return pd.DataFrame(processed_chunks) if isinstance(data, pd.DataFrame) else "\n".join(processed_chunks)

    def parse(self, chunk, parse_type):
        """Route to the appropriate parser based on the parse_type."""
        if parse_type == "uppercase":
            return Parsers.extract_uppercase(chunk)
        elif parse_type == "path":
            return Parsers.extract_paths(chunk)
        elif parse_type == "raw_item_name":
            return Parsers.extract_raw_item_names(chunk)  # New functionality for raw_item_name
        else:
            raise ValueError(f"Unknown parse_type: {parse_type}")

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

class SessionManager:
    def __init__(self, root_directory):
        self.root_directory = os.path.expanduser(root_directory)
        self.session_csv = os.path.join(self.root_directory, "sessions.csv")

        # Ensure the session CSV exists
        if not os.path.exists(self.session_csv):
            pd.DataFrame(columns=["session_name"]).to_csv(self.session_csv, index=False)

    def get_clients(self):
        return [d for d in os.listdir(self.root_directory) if os.path.isdir(os.path.join(self.root_directory, d))]

    def get_projects(self, client):
        client_path = os.path.join(self.root_directory, client)
        return [d for d in os.listdir(client_path) if os.path.isdir(os.path.join(client_path, d))]

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
        Get the list of requests from the {session_name}_requests.csv file.

        Parameters:
        - client (str): Client name.
        - project (str): Project name.
        - recipient (str): Recipient name.
        - session_name (str): Session name.

        Returns:
        - List[str]: List of request names from the CSV file.
        """
        session_dir = os.path.join(self.root_directory, client, project, "packaging", recipient, "sessions", session_name)
        requests_file = os.path.join(session_dir, f"{session_name}_requests.csv")
        
        if not os.path.exists(requests_file):
            return []  # Return an empty list if the file does not exist

        try:
            requests_df = pd.read_csv(requests_file)
            return requests_df['request_name'].tolist()
        except Exception as e:
            raise IOError(f"Failed to read requests file: {str(e)}")

    def create_directory_structure(self, client, project, recipient, session_name):
        """Ensure directory structure is in place for a new session."""
        path = os.path.join(self.root_directory, client, project, "packaging", recipient, "sessions", session_name)
        os.makedirs(path, exist_ok=True)
        return path

    def handle_new_item(self, parent_widget, dropdown, type_label, create_func):
        """Handles the creation of a new item for a dropdown."""
        new_item, ok = QInputDialog.getText(
            parent_widget, f"New {type_label}", f"Enter a new {type_label}:"
        )
        if not ok or not new_item.strip():  # Ensure the dialog wasn't canceled and input is not empty
            print(f"No action taken for {type_label}.")  # Debug log
            return  # Do nothing if canceled
        create_func(new_item.strip())  # Strip whitespace and call the creation function
        dropdown.insertItem(dropdown.count() - 1, new_item.strip())  # Add new item above "New {Item}"
        dropdown.setCurrentText(new_item.strip())  # Set the new item as selected

    def add_new_client(self, client):
        self.client = client
        client_path = os.path.join(self.root_directory, client)
        os.makedirs(client_path, exist_ok=True)

    def add_new_project(self, client, project):
        self.project = project
        project_path = os.path.join(self.root_directory, client, project)
        os.makedirs(project_path, exist_ok=True)

    def add_new_recipient(self, client, project, recipient_name):
        self.recipient = recipient_name
        recipient_path = os.path.join(self.root_directory, client, project, "packaging", recipient_name)
        os.makedirs(recipient_path, exist_ok=True)

    def add_new_session(self, client, project, recipient, session_name):
        self.session_name = session_name
        session_path = os.path.join(self.root_directory, client, project, "packaging", recipient, "sessions", session_name)
        os.makedirs(session_path, exist_ok=True)

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
        os.makedirs(session_dir, exist_ok=True)

        # Copy and rename the source files CSV
        source_file_target = os.path.join(session_dir, f"{request_name}_source_files.csv")
        try:
            shutil.copyfile(source_csv_path, source_file_target)
        except Exception as e:
            raise IOError(f"Failed to copy Source Files CSV: {str(e)}")

        # Copy and rename the provisioning template
        provisioning_file_target = os.path.join(session_dir, f"{request_name}_provisioning_template.csv")
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
        
class RequestorUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("String Mapping Workflow")
        self.resize(1000, 900)

        # Initialize class variables
        self.file_io = FileIO()
        self.payload_handler = PayloadHandler()
        self.mapping_requestor = MappingRequestor()
        self.manager = StringMappingManager()
        self.output_manager = OutputManager()
        self.session_manager = SessionManager("~/.aufs/config/jobs/active")

        # Default paths and settings
        self.client = ''
        self.project = ''
        self.recipient = ''
        self.session_name = None
        self.request_name = None

        # Main layout setup using tabs
        self.tabs = QTabWidget(self)
        self.requestor_tab = QWidget()
        self.manager_tab = QWidget()
        self.manager_layout = QVBoxLayout(self.manager_tab)
        self.manager_layout.addWidget(self.manager)

        # Add manager and requestor tabs
        self.tabs.addTab(self.requestor_tab, "Requestor Interface")
        self.tabs.addTab(self.manager_tab, "String Mapping Manager")

        # Setup the requestor UI within the `requestor_tab`
        self.setup_requestor_ui()

        # Set layout and add tabs
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

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
        self.session_setup_widget.setVisible(True)  # Hidden by default
        session_layout = QVBoxLayout(self.session_setup_widget)

        # Jobs Directory setup
        self.jobs_directory_input = QLineEdit(os.path.expanduser("~/.aufs/config/jobs/active"))
        self.browse_jobs_dir_button = QPushButton("Browse")
        self.browse_jobs_dir_button.clicked.connect(self.on_jobs_dir_change)
        
        jobs_directory_layout = QHBoxLayout()
        jobs_directory_layout.addWidget(QLabel("Jobs Directory:"))
        jobs_directory_layout.addWidget(self.jobs_directory_input)
        jobs_directory_layout.addWidget(self.browse_jobs_dir_button)

        # Dropdowns for Client, Project, Recipient, Session, Request
        client_layout = QHBoxLayout()
        self.client_dropdown = QComboBox()
        self.populate_clients()
        self.client_dropdown.currentTextChanged.connect(self.on_client_change)
        client_layout.addWidget(QLabel("Client:"))
        client_layout.addWidget(self.client_dropdown)

        project_layout = QHBoxLayout()
        self.project_dropdown = QComboBox()
        self.project_dropdown.currentTextChanged.connect(self.on_project_change)
        project_layout.addWidget(QLabel("Project:"))
        project_layout.addWidget(self.project_dropdown)

        recipient_layout = QHBoxLayout()
        self.recipient_dropdown = QComboBox()
        self.recipient_dropdown.currentTextChanged.connect(self.on_recipient_change)
        recipient_layout.addWidget(QLabel("Recipient:"))
        recipient_layout.addWidget(self.recipient_dropdown)

        session_chooser_layout = QHBoxLayout()
        self.session_dropdown = QComboBox()
        self.session_dropdown.currentTextChanged.connect(self.on_session_change)
        session_chooser_layout.addWidget(QLabel("Session:"))
        session_chooser_layout.addWidget(self.session_dropdown)

        request_layout = QHBoxLayout()
        self.request_dropdown = QComboBox()
        self.request_dropdown.currentTextChanged.connect(self.on_request_change)
        request_layout.addWidget(QLabel("Request:"))
        request_layout.addWidget(self.request_dropdown)

        # Add all dropdown layouts to the session layout
        session_layout.addLayout(jobs_directory_layout)
        session_layout.addLayout(client_layout)
        session_layout.addLayout(project_layout)
        session_layout.addLayout(recipient_layout)
        session_layout.addLayout(session_chooser_layout)
        session_layout.addLayout(request_layout)

        # Add session setup layout to main layout
        session_setup_layout.addWidget(self.session_setup_widget)
        layout.addLayout(session_setup_layout)
        
        # === Source File Loader Section ===
        source_file_layout = QHBoxLayout()
        self.source_file_input = QLineEdit()
        self.load_source_button = QPushButton("Load Source Files CSV")
        self.load_source_button.clicked.connect(self.load_source_csv)
        source_file_layout.addWidget(QLabel("Source Files CSV:"))
        source_file_layout.addWidget(self.source_file_input)
        source_file_layout.addWidget(self.load_source_button)
        layout.addLayout(source_file_layout)

        # === File Processing Section ===
        file_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.load_button = QPushButton("Load Provisioning Template")
        self.load_button.clicked.connect(self.load_file)
        file_layout.addWidget(QLabel("Provisioning template path:"))
        file_layout.addWidget(self.file_path_input)
        file_layout.addWidget(self.load_button)
        layout.addLayout(file_layout)

        # # === Remap Type Section ===
        # remap_type_layout = QHBoxLayout()
        # self.remap_type_combo = QComboBox()
        # self.remap_type_options = {
        #     "Uppercase Variables": "uppercase",
        #     "Raw Item Names": "raw_item_name"
        # }
        # self.remap_type_combo.addItems(self.remap_type_options.keys())
        # # remap_type_layout.addWidget(QLabel("Remap Type:"))
        # remap_type_layout.addWidget(self.remap_type_combo)
        # # layout.addLayout(remap_type_layout)

        # === Column Selection for CSV ===
        self.column_list_widget = QListWidget()
        self.column_list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.column_list_widget.setVisible(False)
        layout.addWidget(QLabel("Select Columns to Work On:"))
        layout.addWidget(self.column_list_widget)

        # === Preview Display ===
        self.preview_display = QTextEdit()
        self.preview_display.setReadOnly(True)
        layout.addWidget(QLabel("Preview of Remapped Data:"))
        layout.addWidget(self.preview_display)

        # === Process Button ===
        self.remap_button = QPushButton("Process and Preview Remap")
        self.remap_button.clicked.connect(self.process_remap)
        layout.addWidget(self.remap_button)

        # === Save Button with Dropdown Menu ===
        save_button_layout = QHBoxLayout()
        self.save_button = QToolButton(self)
        self.save_button.setText("Save")
        self.save_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.save_button.setPopupMode(QToolButton.MenuButtonPopup)
        self.save_button.setFixedWidth(150)

        # Create a dropdown menu for additional save options
        save_menu = QMenu(self)
        save_as_action = save_menu.addAction("Save As")
        timestamped_action = save_menu.addAction("Save with Timestamp")
        self.save_button.setMenu(save_menu)

        # Connect save button and menu actions
        self.save_button.clicked.connect(lambda: self.save_remapped_file("original"))
        save_as_action.triggered.connect(lambda: self.save_remapped_file("save_as"))
        timestamped_action.triggered.connect(lambda: self.save_remapped_file("timestamped"))

        save_button_layout.addWidget(self.save_button)
        layout.addLayout(save_button_layout)

        # Add final layout to requestor_tab
        self.requestor_tab.setLayout(layout)

    def load_source_csv(self, source_file_path=None):
        """Load a Source Files CSV into the manager."""
        
        if source_file_path:
            self.source_file_input.setText(source_file_path)
            self.manager.initialize_manager_with_csv(source_file_path)  # Reinitialize manager
        else:
            source_file_path, _ = QFileDialog.getOpenFileName(self, "Open Source Files CSV", "", "CSV Files (*.csv);;All Files (*)")
            self.source_file_input.setText(source_file_path)
            self.manager.initialize_manager_with_csv(source_file_path)  # Reinitialize manager            

    def load_provisioning_template(self, file_path):
        """Load a provisioning template into the requestor."""
        self.file_path_input.setText(file_path)
        self.load_file(file_path)

    def clear_clients(self):
        """Clears the clients dropdown and all dependent dropdowns."""
        self.client_dropdown.clear()
        self.clear_projects()

    def clear_projects(self):
        self.project_dropdown.clear()
        self.clear_recipients()  # Clear subsequent dependent dropdowns

    def clear_recipients(self):
        self.recipient_dropdown.clear()
        self.clear_sessions()

    def clear_sessions(self):
        self.session_dropdown.clear()
        self.clear_requests()

    def clear_requests(self):
        self.request_dropdown.clear()

    def populate_clients(self):
        """Populates the clients dropdown based on the current jobs directory."""
        jobs_dir = self.jobs_directory_input.text()
        if os.path.isdir(jobs_dir):  # Validate that the directory exists
            self.session_manager.root_directory = os.path.expanduser(jobs_dir)
            clients = self.session_manager.get_clients()
            self.client_dropdown.addItem("")  # Add a blank item
            self.client_dropdown.addItems(clients)
            self.client_dropdown.addItem("New Client")  # Add "New Client" at the end

    def populate_projects(self):
        self.project_dropdown.clear()
        self.project_dropdown.addItem("")  # Add a blank item
        selected_client = self.client_dropdown.currentText()
        if selected_client:
            projects = self.session_manager.get_projects(selected_client)
            self.project_dropdown.addItems(projects)
        self.project_dropdown.addItem("New Project")  # Add "New Project" at the end

    def populate_recipients(self):
        self.recipient_dropdown.clear()
        self.recipient_dropdown.addItem("")  # Add a blank item
        selected_client = self.client_dropdown.currentText()
        selected_project = self.project_dropdown.currentText()
        if selected_client and selected_project:
            recipients = self.session_manager.get_recipients(selected_client, selected_project)
            self.recipient_dropdown.addItems(recipients)
        self.recipient_dropdown.addItem("New Recipient")  # Add "New Recipient" at the end

    def populate_sessions(self):
        self.session_dropdown.clear()
        self.session_dropdown.addItem("")  # Add a blank item
        selected_client = self.client_dropdown.currentText()
        selected_project = self.project_dropdown.currentText()
        selected_recipient = self.recipient_dropdown.currentText()
        if selected_client and selected_project and selected_recipient:
            sessions = self.session_manager.get_sessions(selected_client, selected_project, selected_recipient)
            self.session_dropdown.addItems(sessions)
        self.session_dropdown.addItem("New Session")  # Add "New Session" at the end

    def populate_requests(self):
        self.request_dropdown.clear()
        self.request_dropdown.addItem("")  # Add a blank item
        selected_client = self.client_dropdown.currentText()
        selected_project = self.project_dropdown.currentText()
        selected_recipient = self.recipient_dropdown.currentText()
        selected_session = self.session_dropdown.currentText()
        if selected_session:
            requests = self.session_manager.get_requests(selected_client, selected_project, selected_recipient, selected_session)
            self.request_dropdown.addItems(requests)
        self.request_dropdown.addItem("New Request")  # Add "New Request" at the end

    def on_jobs_dir_change(self):
        """Handles changes to the jobs directory."""
        new_jobs_dir = QFileDialog.getExistingDirectory(self, "Select Jobs Directory", self.jobs_directory_input.text())
        self.jobs_directory_input = new_jobs_dir
        if new_jobs_dir:  # If a valid directory was selected
            self.jobs_directory_input.setText(new_jobs_dir)
            self.clear_clients()  # Clear existing dropdowns
            self.populate_clients()  # Repopulate with the new jobs directory

    def on_client_change(self):
        selected_client = self.client_dropdown.currentText()
        self.client = selected_client
        if selected_client == "New Client":
            self.session_manager.handle_new_item(
                self,
                self.client_dropdown,
                "Client",
                self.session_manager.add_new_client
            )
        elif selected_client == "":
            return  # Skip further processing if the blank item is selected
        else:
            self.clear_projects()
            self.populate_projects()

    def on_project_change(self):
        selected_project = self.project_dropdown.currentText()
        self.project = selected_project
        if selected_project == "New Project":
            selected_client = self.client_dropdown.currentText()
            if selected_client:
                self.session_manager.handle_new_item(
                    self,
                    self.project_dropdown,
                    "Project",
                    lambda project: self.session_manager.add_new_project(selected_client, project),
                )
        elif selected_project == "":
            return
        else:
            self.clear_recipients()
            self.populate_recipients()

    def on_recipient_change(self):
        selected_recipient = self.recipient_dropdown.currentText()
        self.recipient = selected_recipient
        if selected_recipient == "New Recipient":
            selected_client = self.client_dropdown.currentText()
            selected_project = self.project_dropdown.currentText()
            if selected_client and selected_project:
                self.session_manager.handle_new_item(
                    self,
                    self.recipient_dropdown,
                    "Recipient",
                    lambda recipient: self.session_manager.add_new_recipient(selected_client, selected_project, recipient),
                )
        elif selected_recipient == "":
            return
        else:
            self.clear_sessions()
            self.populate_sessions()

    def on_session_change(self):
        selected_session = self.session_dropdown.currentText()
        self.session_name = selected_session
        if selected_session == "New Session":
            selected_client = self.client_dropdown.currentText()
            selected_project = self.project_dropdown.currentText()
            selected_recipient = self.recipient_dropdown.currentText()
            # print(f"Client: {selected_client}, Project: {selected_project}, Recipient: {selected_recipient}")
            if selected_client and selected_project and selected_recipient:
                self.session_manager.handle_new_item(
                    self,
                    self.session_dropdown,
                    "Session",
                    lambda session: self.session_manager.add_new_session(
                        selected_client, selected_project, selected_recipient, session
                    ),
                )
        elif selected_session == "":
            return
        else:
            self.clear_requests()
            self.populate_requests()

    def on_request_change(self):
        """Handle changes in the Request dropdown."""
        selected_request = self.request_dropdown.currentText()

        if selected_request == "New Request":
            # Handle new request creation
            self.handle_new_request()
        elif selected_request == "":
            # Do nothing on blank selection
            return
        else:
            # Handle an existing request
            jobs_dir = self.jobs_directory_input.text()
            session_dir = os.path.join(
                jobs_dir, self.client, self.project, "packaging", self.recipient, "sessions", self.session_name
            )

            source_file_path = os.path.join(session_dir, f"{selected_request}_source_files.csv")
            provisioning_template_path = os.path.join(session_dir, f"{selected_request}_provisioning_template.csv")

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
                # Load existing files into manager and requestor
                try:
                    self.load_source_csv(source_file_path=source_file_path)
                    self.load_provisioning_template(provisioning_template_path)
                    QMessageBox.information(self, "Request Loaded", f"Request '{selected_request}' loaded successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load the request: {str(e)}")

    def handle_new_request(self, request_name=None):
        """Handle the creation of a new request or missing files for an existing request."""
        # If no name is provided, prompt the user for a new request name
        if not request_name:
            request_name, ok = QInputDialog.getText(self, "New Request", "Enter a name for the new request:")
            if not ok or not request_name.strip():
                QMessageBox.warning(self, "Request Not Created", "Request creation was canceled.")
                return
            request_name = request_name.strip()

        # Prompt for source_files_csv and provisioning_template_csv
        source_file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Source Files CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        provisioning_template_path, _ = QFileDialog.getOpenFileName(
            self, "Select Provisioning Template CSV", "", "CSV Files (*.csv);;All Files (*)"
        )

        if source_file_path and provisioning_template_path:
            # Create the request by copying the provided files
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
                QMessageBox.information(self, "Request Created", f"Request '{request_name}' setup has been completed.")
                self.populate_requests()  # Refresh the requests dropdown
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create the request: {str(e)}")
        else:
            QMessageBox.warning(self, "Request Not Created", "Both Source Files and Provisioning Template files are required.")

    def toggle_session_setup(self, checked):
        """Toggle the visibility of the session setup widget."""
        self.session_setup_widget.setVisible(checked)

    def load_file(self, file_path):
        
        if file_path:
            self.file_path_input.setText(file_path)
            self.file_type = 'csv' if file_path.endswith('.csv') else 'txt'
            if self.file_type == 'csv':
                self.preview_data = pd.read_csv(file_path)
                self.column_list_widget.clear()
                self.column_list_widget.setVisible(True)
                all_cols_item = QListWidgetItem("all-cols")
                all_cols_item.setCheckState(Qt.Unchecked)
                self.column_list_widget.addItem(all_cols_item)
                for col in self.preview_data.columns:
                    item = QListWidgetItem(col)
                    item.setCheckState(Qt.Unchecked)
                    self.column_list_widget.addItem(item)
            else:
                with open(file_path, 'r') as file:
                    text = file.read()
                self.preview_data = pd.DataFrame([[text]], columns=['text'])
                self.column_list_widget.setVisible(False)
            self.preview_display.setText(str(self.preview_data))

    def process_remap(self):
        if self.preview_data is None:
            QMessageBox.warning(self, "Warning", "Please load a file to process.")
            return

        # Retrieve ID header, ID value, and parse type from UI inputs
        # id_header = self.manager.id_header_input.text().strip()
        # id_value = self.manager.id_value_input.text().strip()

        # Retrieve parse_type using the selected display name
        # displayed_parse_type = self.remap_type_combo.currentText()
        parse_type = 'uppercase' # self.remap_type_options.get(displayed_parse_type)

        
        self.preview_display.clear()
        remapped_texts = []

        # Determine selected columns for remapping in CSV files
        selected_columns = []
        if self.file_type == 'csv':
            for i in range(self.column_list_widget.count()):
                item = self.column_list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    selected_columns.append(item.text())
            if "all-cols" in selected_columns:
                selected_columns = self.preview_data.columns.tolist()

        # Set a flag for handling raw filenames
        is_raw_item_name = (parse_type == "raw_item_name")

        # Process each chunk using PayloadHandler
        for chunk in self.payload_handler.chunk_data(self.preview_data, selected_columns):
            # Use the parse_type to determine which parser method to call
            parsed_strings = self.payload_handler.parse(chunk, parse_type)

            # Initialize remapped chunk to be modified in place
            remapped_chunk = chunk

            if is_raw_item_name:
                # For raw_item_name, use (path_suspect, to_find) tuples for mapping
                for path_suspect, to_find in parsed_strings:
                    # Perform mapping with custom ID header, value, and target for raw_item_name
                    print(path_suspect)
                    mappings = self.manager.map_requested_values("RAWITEMNAME", to_find, ["FILE"]) or []
                    print("rawitemname mappings ARE: ", mappings)

                    # Filter mappings for valid (non-empty) replacement values
                    valid_mappings = [
                        (existing_value, replacement_value) for existing_value, replacement_value in mappings
                        if isinstance(replacement_value, str) and replacement_value.strip()
                    ]

                    # Replace path_suspect in remapped_chunk with the replacement value
                    for existing_value, replacement_value in valid_mappings:
                        remapped_chunk = remapped_chunk.replace(path_suspect, replacement_value)

            else:
                # For other parse types ("uppercase", "path"), continue as before
                mappings = self.manager.map_requested_values(parsed_strings) or []

                # Apply valid mappings to the chunk
                valid_mappings = [
                    (existing_value, replacement_value) for existing_value, replacement_value in mappings
                    if isinstance(replacement_value, str) and replacement_value.strip()
                ]
                for existing_value, replacement_value in valid_mappings:
                    remapped_chunk = remapped_chunk.replace(existing_value, replacement_value)

            # Append remapped chunk to the list for preview display
            remapped_texts.append(remapped_chunk)

        # Update preview display with remapped content
        self.preview_display.setText("\n".join(remapped_texts))

    def save_remapped_file(self, save_option):
        """Save the remapped data based on selected save options."""
        file_path = self.file_path_input.text()
        format_type = 'csv' if file_path.endswith('.csv') else 'txt'
        remapped_data = self.preview_display.toPlainText()

        # Call OutputManager to handle the save operation
        self.output_manager.save(remapped_data, file_path, format_type, save_option)
        
        # Trigger final version logging in StringMappingManager
        self.manager.finalize_logging()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    coordinator = RequestorUI()
    coordinator.show()
    sys.exit(app.exec())