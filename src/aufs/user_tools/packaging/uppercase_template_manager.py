# src/aufs/user_tools/packaging/uppercase_template_manager.py

import os
import sys
import pandas as pd
import shutil
import re
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QInputDialog, QHBoxLayout, QSplitter
)
from PySide6.QtCore import Qt

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')
sys.path.insert(0, src_path)

from src.aufs.user_tools.qtwidgets.widgets.cascading_panes_simple import CascadingPaneManager
from src.aufs.user_tools.packaging.pandas_deep_data_editor import DeepEditor, NestedEditor

class UppercaseTemplateManager(QWidget):
    def __init__(self, root_directory, client=None, project=None, recipient=None, root_job_path=None, task=None, parent=None):
        super().__init__(parent)
        self.root_directory = root_directory
        self.client = client
        self.project = project
        self.recipient = recipient
        self.root_job_path = root_job_path
        self.task = task

        # Blacklist of files and directories to ignore
        self.blacklist = {".DS_Store", "Thumbs.db", "__MACOSX"}

        # Initialize UI
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Uppercase Template Manager")
        layout = QVBoxLayout(self)

        # Add a label
        label = QLabel("Welcome to the Uppercase Template Manager", self)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # Add a splitter for the main cascading panes
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.setChildrenCollapsible(False)
        self.cascading_pane_manager = CascadingPaneManager(self.splitter)
        self.cascading_pane_manager.set_data_receiver(self.receive_returned_pane_manager_data)
        layout.addWidget(self.splitter)

        # Add buttons below the main splitter
        self.pane_work_buttons_layout = QHBoxLayout()
        self.pane_work_buttons_left_layout = QVBoxLayout()
        self.pane_work_buttons_middle_layout = QVBoxLayout()
        self.pane_work_buttons_right_layout = QVBoxLayout()

        # Button: New Directory
        new_dir_button = QPushButton("New Directory", self)
        new_dir_button.clicked.connect(self.create_new_directory)

        # Button: New Template File
        new_template_button = QPushButton("New Template File", self)
        new_template_button.clicked.connect(self.create_new_template_file)

        # Button: Copy, Paste, Rename, etc.
        copy_button = QPushButton("Copy File", self)
        copy_button.clicked.connect(self.copy_file)

        paste_button = QPushButton("Paste File", self)
        paste_button.clicked.connect(self.paste_file)

        rename_button = QPushButton("Rename Selected", self)
        rename_button.clicked.connect(self.rename_selected_item)

        refresh_button = QPushButton("Refresh List", self)
        refresh_button.clicked.connect(self.reload_current_pane)

        save_button = QPushButton("Save Something", self)
        save_button.clicked.connect(self.save_template)

        browse_button = QPushButton("File Browser", self)
        browse_button.clicked.connect(self.file_browser)

        # Arrange buttons
        self.pane_work_buttons_left_layout.addWidget(new_dir_button)
        self.pane_work_buttons_left_layout.addWidget(new_template_button)
        self.pane_work_buttons_left_layout.addWidget(save_button)

        self.pane_work_buttons_middle_layout.addWidget(copy_button)
        self.pane_work_buttons_middle_layout.addWidget(rename_button)
        self.pane_work_buttons_middle_layout.addWidget(browse_button)

        self.pane_work_buttons_right_layout.addWidget(paste_button)
        self.pane_work_buttons_right_layout.addWidget(refresh_button)

        self.pane_work_buttons_left_layout.addStretch()
        self.pane_work_buttons_middle_layout.addStretch()
        self.pane_work_buttons_right_layout.addStretch()

        self.pane_work_buttons_layout.addLayout(self.pane_work_buttons_left_layout)
        self.pane_work_buttons_layout.addLayout(self.pane_work_buttons_middle_layout)
        self.pane_work_buttons_layout.addLayout(self.pane_work_buttons_right_layout)
        self.pane_work_buttons_layout.addStretch()

        layout.addLayout(self.pane_work_buttons_layout)

        #
        # SPLIT/DIVIDE HERE
        #

        self.template_editing_layout = QVBoxLayout()

        self.template_editing_top_buttons_layout = QHBoxLayout()
        # Add a Load button to load a DataFrame into DeepEditor
        self.load_editor_button = QPushButton("Load Nested Editor", self)
        self.load_editor_button.clicked.connect(self.load_editor_data)
        self.template_editing_top_buttons_layout.addWidget(self.load_editor_button)
        # Add Save Progress button
        self.save_progress_button = QPushButton("Save Progress", self)
        self.save_progress_button.clicked.connect(self.save_template)  # Connect to save_template method
        self.template_editing_top_buttons_layout.addWidget(self.save_progress_button)
        # Add Save As button
        self.save_as_button = QPushButton("Save as", self)
        self.save_as_button.clicked.connect(self.save_template_as)  # Connect to save_template method
        self.template_editing_top_buttons_layout.addWidget(self.save_as_button)

        self.template_editing_layout.addLayout(self.template_editing_top_buttons_layout)

        self.deep_editor_container = QVBoxLayout()
        button_flags = {
            'search_replace': True,
            'add_row': True,
            'delete_row': True,
            'move_row_up': True,
            'move_row_down': True,
            'add_column': True,
            'delete_column': True,
            'move_column_left': True,
            'move_column_right': True,
            'sort_column': False,
            'clear_selection': True,
            'set_column_type': True,
            'dtype_dropdown': False,
            'reload': False,
            'save': False,
            'exit': False
        }
        self.deep_editor = DeepEditor(
            nested_mode=True,  # Enable nested mode
            auto_fit_columns=True,
            button_flags=button_flags,
            parent=self
        )
        self.deep_editor.setVisible(False)  # Initially hidden until loaded
        self.deep_editor_container.addWidget(self.deep_editor)
        self.template_editing_layout.addLayout(self.deep_editor_container)

        layout.addLayout(self.template_editing_layout)

        #
        # SPLIT/DIVIDE HERE
        #

        # Add a "Load Template" button to dynamically create the second set of panes
        self.load_template_button = QPushButton("Load Templating Snippet Explorer", self)
        self.load_template_button.clicked.connect(self.add_template_panes)
        layout.addWidget(self.load_template_button)

        # Placeholder for the template panes
        self.template_panes_container = QWidget(self)
        self.template_panes_layout = QVBoxLayout(self.template_panes_container)
        layout.addWidget(self.template_panes_container)

        # Add buttons below the main splitter
        # self.templating_pane_work_buttons_layout = QHBoxLayout()
        # self.templating_pane_work_buttons_left_layout = QVBoxLayout()
        # self.templating_pane_work_buttons_middle_layout = QVBoxLayout()
        # self.templating_pane_work_buttons_right_layout = QVBoxLayout()

        # # Button: New Directory
        # new_dir_button = QPushButton("New Directory", self)
        # new_dir_button.clicked.connect(self.create_new_directory)

        # # Button: New Template File
        # new_template_button = QPushButton("New Template File", self)
        # new_template_button.clicked.connect(self.create_new_template_file)

        # # Button: Copy, Paste, Rename, etc.
        # copy_button = QPushButton("Copy File", self)
        # copy_button.clicked.connect(self.copy_file)

        # paste_button = QPushButton("Paste File", self)
        # paste_button.clicked.connect(self.paste_file)

        # rename_button = QPushButton("Rename Selected", self)
        # rename_button.clicked.connect(self.rename_selected_item)

        # refresh_button = QPushButton("Refresh List", self)
        # refresh_button.clicked.connect(self.reload_current_pane)

        # save_button = QPushButton("Save Something", self)
        # save_button.clicked.connect(self.save_template)

        # browse_button = QPushButton("File Browser", self)
        # browse_button.clicked.connect(self.file_browser)

        # # Arrange buttons
        # # self.templating_pane_work_buttons_left_layout.addWidget(new_dir_button)
        # # self.templating_pane_work_buttons_left_layout.addWidget(new_template_button)
        # # self.templating_pane_work_buttons_left_layout.addWidget(save_button)

        # # self.templating_pane_work_buttons_middle_layout.addWidget(copy_button)
        # # self.templating_pane_work_buttons_middle_layout.addWidget(rename_button)
        # # self.templating_pane_work_buttons_middle_layout.addWidget(browse_button)

        # # self.templating_pane_work_buttons_right_layout.addWidget(paste_button)
        # # self.templating_pane_work_buttons_right_layout.addWidget(refresh_button)

        # # self.templating_pane_work_buttons_left_layout.addStretch()
        # # self.templating_pane_work_buttons_middle_layout.addStretch()
        # # self.templating_pane_work_buttons_right_layout.addStretch()

        # # self.templating_pane_work_buttons_layout.addLayout(self.templating_pane_work_buttons_left_layout)
        # # self.templating_pane_work_buttons_layout.addLayout(self.templating_pane_work_buttons_middle_layout)
        # # self.templating_pane_work_buttons_layout.addLayout(self.templating_pane_work_buttons_right_layout)
        # self.templating_pane_work_buttons_layout.addStretch()

        # layout.addLayout(self.templating_pane_work_buttons_layout)

        # Initialize the main pane
        self.first_pane_list_manager()

    def add_template_panes(self):
        """Dynamically add template cascading panes below the main UI."""
        # Prevent multiple sets of template panes
        if hasattr(self, "templating_cascading_pane_manager"):
            QMessageBox.information(self, "Already Loaded", "Template panes are already loaded.")
            return

        # Create a new splitter for the template cascading panes
        self.template_splitter = QSplitter(Qt.Horizontal, self)
        self.template_splitter.setChildrenCollapsible(False)

        # Create a new cascading pane manager for templates
        self.templating_cascading_pane_manager = CascadingPaneManager(self.template_splitter)
        self.templating_cascading_pane_manager.set_data_receiver(self.receive_returned_templating_data)

        # Add the splitter to the layout
        self.template_panes_layout.addWidget(self.template_splitter)

        # Load initial data for the template panes
        self.load_templating_root()

    def load_templating_root(self):
        """Load the root directory for template panes."""
        templating_root_directory = os.path.expanduser("~/.aufs/config/packaging/_templating")
        if not os.path.exists(templating_root_directory):
            QMessageBox.critical(self, "Error", f"Template root directory '{templating_root_directory}' does not exist.")
            return

        # Use the existing method to load and display the directory contents
        self.load_dir_contents_list(
            directory=templating_root_directory,
            title="Available Template Snippets",
            pane_manager=self.templating_cascading_pane_manager,
            filter_type="only_underscores"
        )

    def receive_returned_templating_data(self, data):
        """Handle data returned from the template cascading panes."""
        # print("Got some stuff returned to the template data receiver: ")
        # print(data)
        if data.empty:
            return
        print("templating data returned: ")
        print(data)

        self.templating_item = data.iloc[0]["Item"]
        self.templating_path = data.iloc[0]["Path"]
        object_type = data.iloc[0].get("OBJECTTYPE", "Unknown")  # Default to 'Unknown' if OBJECTTYPE is missing
        self.currently_selected_item = self.templating_item
        self.currently_selected_path = self.templating_path
        # print(f"template item: {self.templating_item}, template path: {self.templating_path}, OBJECTTYPE: {object_type}")

        if object_type == "Variable":
            # Handle "Variable" OBJECTTYPE
            usage_info = data.iloc[0].get("USAGEINFO", "No usage information is available for this variable.")
            if pd.isna(usage_info) or not usage_info.strip():
                usage_info = "No usage information is available for this variable."

            # Create a DataFrame for the basic_text pane
            df = pd.DataFrame({"Text": [usage_info]})

            # Display in the cascading panes
            self.templating_cascading_pane_manager.display_pane(
                title=f"Variable: {self.templating_item}",
                df=df,
                pane_type="basic_text"
            )
        elif os.path.isdir(self.templating_path):
            # Handle directory: Load its contents into the template panes
            self.load_dir_contents_list(
                directory=self.templating_path,
                title=f"Contents of {self.templating_item}",
                pane_manager=self.templating_cascading_pane_manager,
                filter_type="only_underscores"  # Ensure template panes are updated
            )
        elif os.path.isfile(self.templating_path):
            # Handle file: Load its contents into the template panes
            try:
                paths = [self.templating_path]
                self.load_file_contents_list(
                    paths,
                    title=f"File: {self.templating_item}",
                    pane_manager=self.templating_cascading_pane_manager
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file '{self.templating_item}': {e}")
        else:
            # Handle unknown cases
            QMessageBox.warning(self, "Unhandled Selection", f"Item: {self.templating_item}\nPath: {self.templating_path}")

    def rename_selected_item(self):
        """Rename the selected file or directory."""
        if not self.currently_selected_path:
            QMessageBox.warning(self, "Invalid Request", "Please select something to rename.")
            return

        # Extract the current file/directory name
        current_name, ext = os.path.splitext(os.path.basename(self.currently_selected_path))
        rename_name, ok = QInputDialog.getText(self, "Rename Item", "Enter new name:", text=current_name)

        if ok and rename_name.strip():
            # Construct the new path within the same directory
            rename_path = os.path.join(os.path.dirname(self.currently_selected_path), f"{rename_name.strip()}{ext}")
            try:
                os.rename(self.currently_selected_path, rename_path)
                QMessageBox.information(self, "Success", f"Renamed to '{rename_name}'.\n\n---BE AWARE---\n\nYou will need to click on the parent directory\nin the previous pane to refresh and see the New Name")
                self.reload_current_pane(replace_uuid="1_before")  # Refresh the pane to reflect the change
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to rename: {e}")

    def create_new_directory(self):
        """Create a new directory in the current path."""
        if not os.path.isdir(self.currently_selected_path):
            QMessageBox.warning(self, "Invalid Selection", "Please select a valid directory to create a new folder.")
            return

        dir_name, ok = QInputDialog.getText(self, "New Directory", "Enter directory name:")
        if ok and dir_name.strip():
            new_dir_path = os.path.join(self.currently_selected_path, dir_name.strip())
            try:
                os.makedirs(new_dir_path)
                QMessageBox.information(self, "Success", f"Directory '{dir_name}' created.")
                self.reload_current_pane()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create directory: {e}")

    def create_new_template_file(self):
        """Create a new template file in the current directory."""
        if not os.path.isdir(self.currently_selected_path):
            QMessageBox.warning(self, "Invalid Selection", "Please select a valid directory to create a template file.")
            return

        file_name, ok = QInputDialog.getText(self, "New Template File", "Enter template file name (without extension):")
        if not ok or not file_name.strip():
            file_name = "new_template"  # Default name if user cancels or provides no input

        new_file_path = os.path.join(self.currently_selected_path, f"{file_name.strip()}.csv")
        try:
            # Create a DataFrame with the specified structure
            data = {
                "PROVISIONEDLINK": ["./PACKAGE_PARENT/TASK/SHOTNAME_PARENTITEM_VERSION/exr/SHOTNAME_PARENTITEM_VERSION.PADDING.DOTEXTENSION"],
                "DOTEXTENSION": ["exr"],
            }
            df = pd.DataFrame(data)
            df.to_csv(new_file_path, index=False)
            QMessageBox.information(self, "Success", f"Template file '{file_name}.csv' created.")
            self.reload_current_pane()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create template file: {e}")

    def copy_file(self):
        """Set the file to be copied."""
        if not os.path.isfile(self.currently_selected_path):
            QMessageBox.warning(self, "Invalid Selection", "Please select a valid file to copy.")
            return

        self.file_to_be_copied = self.currently_selected_path
        QMessageBox.information(self, "Copy File", f"Copied '{self.file_to_be_copied}'.")

    def paste_file(self):
        """Paste the copied file to the current directory with a new name."""
        if not self.file_to_be_copied:
            QMessageBox.warning(self, "No File to Paste", "Please copy a file first.")
            return

        if not os.path.isdir(self.currently_selected_path):
            QMessageBox.warning(self, "Invalid Destination", "Please select a valid directory to paste the file.")
            return

        file_name, ext = os.path.splitext(os.path.basename(self.file_to_be_copied))
        suggested_name = f"{file_name}-copied-{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}{ext}"
        new_name, ok = QInputDialog.getText(self, "Paste File", "Enter new file name:", text=suggested_name)

        if ok and new_name.strip():
            new_file_path = os.path.join(self.currently_selected_path, new_name.strip())
            try:
                shutil.copy(self.file_to_be_copied, new_file_path)
                QMessageBox.information(self, "Success", f"File copied to '{new_file_path}'.")
                self.reload_current_pane()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to paste file: {e}")

    def first_pane_list_manager(self):
        """Build and display the first pane with available template options."""
        # Prepare directory paths
        directories = [
            # {"Item": "Root", "Path": os.path.join(self.root_directory)},
            {"Item": "Global Templates", "Path": os.path.join(self.root_directory, "packaging", "global")},
            {"Item": "Vendor Templates", "Path": os.path.join(self.root_directory, "packaging", "vendor", (self.recipient or ""))},
            {"Item": "Client Templates", "Path": os.path.join(self.root_directory, "packaging", "client", (self.client or ""))},
            {"Item": "Project Templates", "Path": os.path.join(self.root_directory, "packaging", "client", (self.client or ""), (self.project or ""))},
            {"Item": "Job Templates", "Path": os.path.join(self.root_job_path or "", "templates")},
        ]

        # Filter out unavailable or invalid directories
        filtered_directories = [
            entry for entry in directories
            if entry["Path"] and os.path.exists(entry["Path"]) and entry["Item"] is not None
        ]

        # Build a DataFrame for the available directories
        if filtered_directories:
            df = pd.DataFrame(filtered_directories)
            df["OBJECTTYPE"] = "Directory"  # Add OBJECTTYPE column for consistency
        else:
            # No valid directories, display an empty message
            df = pd.DataFrame({"Text": ["No valid directories found"]})
            self.cascading_pane_manager.display_pane("Initial Pane", df, pane_type="basic_text")
            return

        # Display the DataFrame in the first pane
        self.cascading_pane_manager.display_pane("Available Template Locations", df, pane_type="filterable_list")

    def reload_current_pane(self, replace_uuid="no"):
        print("Replace UUID: ", replace_uuid)
        pane_uuid = self.cascading_pane_manager.selected_pane
        if not pane_uuid:
            QMessageBox.information(self, "No Pane Selected", "No pane is currently selected to refresh.")
            return
        
        self.cascading_pane_manager.handle_selection(self.selected_item, pane_uuid, refresh=True, replace_uuid=replace_uuid)

    def load_dir_contents_list(self, directory, title, pane_manager=None, filter_type=None):
        """Load the contents of a directory into the specified cascading panes."""
        pane_manager = pane_manager or self.cascading_pane_manager

        if not os.path.exists(directory):
            QMessageBox.critical(self, "Error", f"Directory '{directory}' does not exist.")
            return

        try:
            items = [
                item for item in os.listdir(directory) if item not in self.blacklist
            ]

            if items:
                df = pd.DataFrame({
                    "Item": items,
                    "Path": [os.path.join(directory, item) for item in items],
                    "OBJECTTYPE": [
                        "Directory" if os.path.isdir(os.path.join(directory, item)) else "File"
                        for item in items
                    ]
                })

                # Apply the filter if specified
                if filter_type == "remove_underscores":
                    df = FilterSort.df_filter_underscores(df)
                    df = FilterSort.df_add_displayname(df)
                    df = FilterSort.sort_df(df)

                elif filter_type == "only_underscores":
                    df = FilterSort.df_filter_underscores(df, keep_underscores=True)
                    df = FilterSort.df_add_displayname(df)
                    df = FilterSort.df_remove_extensions(df)
                    df = FilterSort.df_add_displayname(df, parsers=["underscores", "spaces", "capitalise"])
                    df = FilterSort.sort_df(df)

                pane_manager.display_pane(title, df, pane_type="filterable_list")
            else:
                df = pd.DataFrame({"Text": ["This directory is empty"]})
                pane_manager.display_pane(title, df, pane_type="basic_text")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load directory: {e}")

    def load_file_contents_list(self, file_paths, title, pane_manager=None):
        """
        Load the contents of multiple files into a concatenated DataFrame and display in a draggable pane.

        Args:
            file_paths (list): List of file paths to process.
            title (str): Title for the pane.
            pane_manager (CascadingPaneManager): The pane manager to use for displaying the data.
        """
        pane_manager = pane_manager or self.cascading_pane_manager

        combined_data = []

        for file_path in file_paths:
            if not os.path.isfile(file_path):
                continue

            try:
                # Read the file into a DataFrame
                df = pd.read_csv(file_path)

                # Ensure 'OBJECTTYPE' column exists and populate with "File" if missing
                if "OBJECTTYPE" not in df.columns:
                    df["OBJECTTYPE"] = "Variable"

                # Add a 'Path' column with the source file path for each row
                df["Path"] = file_path

                # Use the first column's values as the 'Item' column
                if "Item" not in df.columns:
                    first_column = df.columns[0]
                    df.rename(columns={first_column: "Item"}, inplace=True)

                # Add the DataFrame to the combined list
                combined_data.append(df)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to process file '{file_path}': {e}")

        # Concatenate all DataFrames into one
        if combined_data:
            combined_df = pd.concat(combined_data, ignore_index=True)

            # Display in the cascading panes as a draggable list
            pane_manager.display_pane(
                title, combined_df, pane_type="list", is_sender=True, is_receiver=True
            )
        else:
            QMessageBox.information(self, "No Data", "No valid files could be loaded.")

    def receive_returned_pane_manager_data(self, data):
        """Handle data returned from the cascading panes."""
        if data.empty:
            return

        self.selected_item = data.iloc[0]["Item"]
        self.selected_path = data.iloc[0]["Path"]
        self.currently_selected_item = self.selected_item
        self.currently_selected_path = self.selected_path
        print("item:", self.selected_item, "  path:", self.selected_path)

        # print(f"Received Data: Item: {self.selected_item}, Path: {self.selected_path}")

        # Directory: Load its contents
        if os.path.isdir(self.selected_path):
            self.load_dir_contents_list(self.selected_path, f"Contents of {self.selected_item}", filter_type="remove_underscores")

        # File: Display its contents in a basic_text pane
        elif os.path.isfile(self.selected_path):
            try:
                with open(self.selected_path, "r") as file:
                    text_content = file.read()
                df = pd.DataFrame({
                    "Text": [text_content]
                })
                self.cascading_pane_manager.display_pane(f"File: {self.selected_item}", df, pane_type="basic_text")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to read file '{self.selected_item}': {e}")

        # Other cases: Handle as needed
        else:
            QMessageBox.warning(self, "Unhandled Selection", f"Item: {self.selected_item}\nPath: {self.selected_path}")

    def load_editor_data(self, create_embedded=False):
        """Read the file at self.templating_path, prepare the data, and load it into DeepEditor."""
        if not self.selected_path or not os.path.isfile(self.selected_path):
            QMessageBox.warning(self, "No File Selected", "Please select a valid file to load.")
            return

        try:
            df = self.load_template_file_to_df(self.selected_path)
            df = self.template_file_deep_df(df, create_embedded=create_embedded)
            
            if not create_embedded:
                df = self.create_nested_components(df)

            # Load the DataFrame into the editor
            self.deep_editor.load_from_dataframe(df, create_embedded=create_embedded)
            self.deep_editor.setVisible(True)  # Make the editor visible
            # QMessageBox.information(self, "File Loaded", f"Loaded data from {self.selected_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load the file: {e}")

    def load_template_file_to_df(self, file_path, header=True, column_index=0):
        """
        Load a template CSV into a DataFrame and create a working DataFrame.

        Args:
            file_path (str): Path to the template file.
            header (bool): Whether the file has headers.
            column_index (int): Index of the column to use if no headers.

        Returns:
            pd.DataFrame: The loaded and staged DataFrame.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Load the DataFrame
        if header:
            df = pd.read_csv(file_path)
        else:
            df = pd.read_csv(file_path, header=None)
            if column_index >= len(df.columns):
                raise ValueError(f"Invalid column index {column_index}. File has {len(df.columns)} columns.")
            df.rename(columns={column_index: "PROVISIONEDLINK"}, inplace=True)

        # Use the first column if "PROVISIONEDLINK" not found
        if "PROVISIONEDLINK" not in df.columns:
            df.rename(columns={df.columns[0]: "PROVISIONEDLINK"}, inplace=True)

        if df["PROVISIONEDLINK"].isnull().all():
            print("No valid data in the PROVISIONEDLINK column. Exiting peacefully.")
            return None

        return df

    def template_file_deep_df(self, df, create_embedded):
        """
        Transform the input DataFrame by splitting `PROVISIONEDLINK` into segments.

        Args:
            df (pd.DataFrame): The input DataFrame with `PROVISIONEDLINK`.

        Returns:
            pd.DataFrame: A transformed DataFrame with additional split columns.
        """
        # Split `PROVISIONEDLINK` into segments by `/`
        split_data = df["PROVISIONEDLINK"].str.split("/", expand=True)
        split_columns = [f"Segment {i+1}" for i in range(split_data.shape[1])]

        # Append these new columns to the working DataFrame
        working_df = df.copy()
        working_df[split_columns] = split_data

        # Track new columns for later updates
        if not create_embedded:
            working_df.attrs["split_columns"] = split_columns

        return working_df

    def create_nested_components(self, df):
        """
        Create nested lists for split columns in the DataFrame.
        
        Args:
            df (pd.DataFrame): Input DataFrame with split columns created by `template_file_deep_df`.

        Returns:
            pd.DataFrame: Updated DataFrame with embedded lists for nested data.
        """
        # Retrieve split columns created by `template_file_deep_df`
        split_columns = df.attrs.get("split_columns", [])
        if not split_columns:
            raise ValueError("No split columns found in DataFrame. Ensure `template_file_deep_df` was applied.")

        df = self.embed_nested_lists(df, split_columns)

        return df

    def embed_nested_lists(self, df, columns):
        """
        Embed nested lists into specified columns while keeping main cell content intact.

        Args:
            df (pd.DataFrame): The DataFrame to process.
            columns (list): List of column names to embed nested lists for.

        Returns:
            pd.DataFrame: The original DataFrame with nested data stored in `attrs`.
        """
        if "nested_data" not in df.attrs:
            df.attrs["nested_data"] = {}

        for column in columns:
            if column not in df.columns:
                raise ValueError(f"Column '{column}' not found in DataFrame.")
            
            # Generate nested components for each cell in the column
            nested_lists = df[column].apply(self.split_into_components).tolist()
            
            # Store the nested lists in `attrs` under the column name
            df.attrs["nested_data"][column] = nested_lists

        return df

    def split_into_components(self, value):
        """
        Split a string value into nested components while retaining delimiters.

        Args:
            value (str): The cell value to split.

        Returns:
            list: A list of components split by `_`, `-`, and `.` while keeping delimiters.
        """
        if pd.isnull(value) or not isinstance(value, str):
            return []
        return re.split(r'(_|-|\.)', value)

    def insert_column(self, df, index, column_name, values=None):
        """
        Insert a new column into the DataFrame at the specified index.

        Args:
            df (pd.DataFrame): Target DataFrame.
            index (int): Index where the column should be inserted.
            column_name (str): Name of the new column.
            values (list): Optional values for the column.

        Returns:
            pd.DataFrame: DataFrame with the new column inserted.
        """
        values = values or [None] * len(df)
        if len(values) != len(df):
            raise ValueError("Values must match the number of rows in the DataFrame.")

        df.insert(index, column_name, values)
        return df

    def file_browser(self):
        """Browse for template files."""
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Select a Template File")
        dialog.setFileMode(QFileDialog.ExistingFile)
        if dialog.exec():
            selected_file = dialog.selectedFiles()[0]
            QMessageBox.information(self, "Selected Template", f"You selected: {selected_file}")

    def save_template(self):
        """
        Save the currently loaded template in DeepEditor to a file.
        """
        if not self.deep_editor.isVisible():
            QMessageBox.warning(self, "No Data to Save", "No template data is currently loaded or visible.")
            return

        try:
            # Get the current DataFrame from DeepEditor
            df = self.deep_editor.model.get_dataframe()

            # Retain only the required columns
            columns_to_save = ['PROVISIONEDLINK', 'DOTEXTENSION']
            if not all(col in df.columns for col in columns_to_save):
                QMessageBox.critical(self, "Missing Columns", f"One or more required columns ({', '.join(columns_to_save)}) are missing.")
                return

            df = df[columns_to_save]

            if df.empty:
                QMessageBox.warning(self, "No Data", "The current template is empty and cannot be saved.")
                return

            # Save the DataFrame to the specified file path
            df.to_csv(self.selected_path, index=False)
            QMessageBox.information(self, "Success", f"Updated template: '{self.selected_path}'.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save the template: {e}")

    def save_template_as(self):
        """
        Save the currently loaded template in DeepEditor to a file.
        """
        if not self.deep_editor.isVisible():
            QMessageBox.warning(self, "No Data to Save", "No template data is currently loaded or visible.")
            return

        # Get the current DataFrame from DeepEditor
        df = self.deep_editor.model.get_dataframe()

        if df.empty:
            QMessageBox.warning(self, "No Data", "The current template is empty and cannot be saved.")
            return

        # Open a file dialog for the user to specify the save location
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Save Template")
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilter("CSV Files (*.csv);;All Files (*)")
        dialog.setDefaultSuffix("csv")

        if dialog.exec():
            save_path = dialog.selectedFiles()[0]

            try:
                # Save the DataFrame to the specified file path
                df.to_csv(save_path, index=False)
                QMessageBox.information(self, "Success", f"Template saved to '{save_path}'.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save template: {e}")

    @staticmethod
    def main():
        """Launch the widget for testing purposes."""
        root_directory = os.path.expanduser("~/.aufs/config")
        app = QApplication(sys.argv)
        manager = UppercaseTemplateManager(root_directory)
        manager.resize(1600, 1400)
        manager.show()
        sys.exit(app.exec())

class FilterSort:
    @staticmethod
    def item_filter_underscores(item):
        """Filter out items starting with a single leading underscore."""
        return not item.startswith("_")
    @staticmethod
    def df_filter_underscores(df, keep_underscores=False, object_type="dirs"):
        """
        Filter rows based on leading underscores in the Item column, with control over object types.

        Args:
            df (pd.DataFrame): The DataFrame to filter.
            keep_underscores (bool): If True, keep items with leading underscores.
            object_type (str): The type of objects to filter:
                - "dirs": Only filter directories (OBJECTTYPE == "Directory").
                - "files": Only filter files (OBJECTTYPE == "File").
                - "all": Filter both files and directories (default).

        Returns:
            pd.DataFrame: The filtered DataFrame.
        """
        if "OBJECTTYPE" not in df.columns:
            raise ValueError("DataFrame must contain an 'OBJECTTYPE' column.")

        # Define the filtering condition
        if keep_underscores:
            filter_condition = df["Item"].str.startswith("_")
        else:
            filter_condition = ~df["Item"].str.startswith("_")

        # Apply filtering based on object_type
        if object_type == "dirs":
            return df[(df["OBJECTTYPE"] != "Directory") | filter_condition]
        elif object_type == "files":
            return df[(df["OBJECTTYPE"] != "File") | filter_condition]
        elif object_type == "all":
            return df[filter_condition]
        else:
            raise ValueError(f"Invalid object_type: {object_type}. Must be 'dirs', 'files', or 'all'.")

    @staticmethod
    def df_add_displayname(df, parsers=["copy"], force_copy=False):
        """
        Add or modify the DISPLAYNAME column in the DataFrame with multiple parsers.

        Parsers:
            - "copy": Copy Item column as is (default).
            - "underscores": Remove leading underscores from Item or existing DISPLAYNAME.
            - "capitalise": Capitalise the first letter of each word in Item or DISPLAYNAME.
            - "spaces": Replace underscores and hyphens with spaces in Item or DISPLAYNAME.

        If the DISPLAYNAME column exists and force_copy is False, the parsers will
        operate on existing DISPLAYNAME values. Otherwise, it will copy from Item.

        Args:
            df (pd.DataFrame): The DataFrame to modify.
            parsers (list): A list of parsers to apply sequentially to DISPLAYNAME.
            force_copy (bool): Whether to force copying from Item column to DISPLAYNAME.

        Returns:
            pd.DataFrame: The modified DataFrame with updated DISPLAYNAME.
        """
        # Ensure parsers is a list
        if not isinstance(parsers, list):
            parsers = [parsers]

        # If DISPLAYNAME doesn't exist or force_copy is True, start with Item values
        if "DISPLAYNAME" not in df.columns or force_copy:
            df["DISPLAYNAME"] = df["Item"]

        # Apply each parser sequentially
        for parser in parsers:
            if parser == "underscores":
                df["DISPLAYNAME"] = df["DISPLAYNAME"].str.lstrip("_")
            elif parser == "capitalise":
                df["DISPLAYNAME"] = df["DISPLAYNAME"].str.title()
            elif parser == "spaces":
                df["DISPLAYNAME"] = df["DISPLAYNAME"].str.replace(r"[_-]", " ", regex=True)
            elif parser == "copy":
                df["DISPLAYNAME"] = df["Item"]  # Copy from Item if specified explicitly
            else:
                raise ValueError(f"Unknown parser: {parser}")

        return df

    @staticmethod
    def sort_items(items):
        """Sort items alphabetically."""
        return sorted(items)

    @staticmethod
    def sort_df(df, by="Item"):
        """Sort the DataFrame by the specified column."""
        return df.sort_values(by=by).reset_index(drop=True)
    @staticmethod
    def df_remove_extensions(df, column="Item", target_column="DISPLAYNAME", extensions=None, keep_extensions=True):
        """
        Remove file extensions and filter rows based on extensions.

        Args:
            df (pd.DataFrame): The DataFrame to modify.
            column (str): The source column to process (default: "Item").
            target_column (str): The target column to store processed values (default: "DISPLAYNAME").
            extensions (list or None): List of extensions to filter by (e.g., [".txt", ".csv"]).
                                    If None, no filtering based on extensions is performed.
            keep_extensions (bool): If True, keep rows with specified extensions.
                                    If False, exclude rows with specified extensions.

        Returns:
            pd.DataFrame: The modified DataFrame with updated target column and optional filtering applied.
        """
        def remove_extension(value):
            try:
                name, ext = os.path.splitext(value)
                return name, ext
            except Exception as e:
                print(f"DEBUG: Failed to process '{value}': {e}")
                return value, None

        # Apply the extension removal
        df[[target_column, "TEMP_EXT"]] = df[column].apply(
            lambda value: pd.Series(remove_extension(value))
        )

        # If extensions are provided, filter the DataFrame
        if extensions:
            if keep_extensions:
                df = df[df["TEMP_EXT"].isin(extensions)]
            else:
                df = df[~df["TEMP_EXT"].isin(extensions)]

        # Drop the temporary extension column
        df = df.drop(columns=["TEMP_EXT"])

        return df

# For running the module independently
if __name__ == "__main__":
    UppercaseTemplateManager.main()
