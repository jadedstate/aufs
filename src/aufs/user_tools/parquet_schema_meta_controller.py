import os
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QPushButton, QTabWidget, QLabel, QListWidget,QHBoxLayout,
                               QListWidgetItem, QInputDialog, QMessageBox, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt
import pandas as pd
from scraper import DirectoryScraper
from popup_editor import PopupEditor

class DirectoryTabbedView(QTabWidget):
    def __init__(self, dataframe: pd.DataFrame, root_path: str, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe
        self.root_path = root_path  # This is the directory we're managing
        self.setup_tabs()
        self.whitelist = ['.csv']  # Only allow editing CSV files for now

    def setup_tabs(self):
        # Clear existing tabs
        self.clear()
        # Summary tab
        summary_tab = self.create_summary_tab()
        self.addTab(summary_tab, "Summary")

        # Individual tabs for each directory
        for col in self.dataframe.columns:
            tab = self.create_directory_tab(col, self.dataframe[col])
            self.addTab(tab, col)

    def update_tabs(self, new_dataframe: pd.DataFrame):
        """Update the tabs based on a new DataFrame."""
        self.dataframe = new_dataframe
        self.setup_tabs()

    def create_summary_tab(self):
        """
        Creates the 'Summary' tab showing an overview of the directories and file counts.
        Only directories containing files (non-empty columns) are counted as non-empty.
        """
        summary_widget = QWidget()
        layout = QVBoxLayout()

        num_tabs = len(self.dataframe.columns)
        # Count empty directories: a directory (column) is considered empty if it contains only empty values
        num_empty_tabs = sum(self.dataframe[col].isnull().all() or (self.dataframe[col] == '').all() for col in self.dataframe.columns)

        if num_tabs == 1 and num_empty_tabs == 1:  # Only root directory with no files
            summary_label = QLabel("There is nothing to display.")
        else:
            summary_label = QLabel(f"{num_tabs} tabs made, {num_empty_tabs} are empty.")
        
        layout.addWidget(summary_label)
        summary_widget.setLayout(layout)
        return summary_widget

    def create_directory_tab(self, directory_name, file_series):
        """
        Creates a tab for each directory, showing a list of files and an "Edit" button.
        """
        tab_widget = QWidget()
        layout = QVBoxLayout()

        # File list widget
        file_list_widget = QListWidget()
        file_list_widget.setSelectionMode(QListWidget.SingleSelection)  # Single file selection

        # Populate the list widget with files, removing empty rows
        for file_name in file_series.dropna():  # Drop NaN values (empty fields)
            if file_name.strip():  # Ensure non-empty file name
                file_list_widget.addItem(QListWidgetItem(file_name))

        layout.addWidget(file_list_widget)

        # Edit button
        edit_button = QPushButton(f"Edit {directory_name}")
        edit_button.setEnabled(False)  # Disabled by default
        layout.addWidget(edit_button)

        # Connect the list widget selection to enable/disable the Edit button
        file_list_widget.currentItemChanged.connect(lambda: self.update_edit_button(file_list_widget, edit_button))

        # Connect the Edit button to the editing action
        edit_button.clicked.connect(lambda: self.edit_selected_file(file_list_widget))

        tab_widget.setLayout(layout)
        return tab_widget

    def update_edit_button(self, file_list_widget, edit_button):
        """
        Enable or disable the Edit button based on the selected file.
        Only enable if the file is in the whitelist (e.g., .csv).
        """
        selected_item = file_list_widget.currentItem()
        if selected_item:
            file_name = selected_item.text()
            if any(file_name.endswith(ext) for ext in self.whitelist):
                edit_button.setEnabled(True)
            else:
                edit_button.setEnabled(False)
        else:
            edit_button.setEnabled(False)

    def edit_selected_file(self, file_list_widget, mode=False):
        """
        Open the selected file in the PopupEditor if it's editable.
        """

        selected_item = file_list_widget.currentItem()
        if selected_item:
            file_name = selected_item.text()

            # Check if the file is editable (in whitelist)
            if any(file_name.endswith(ext) for ext in self.whitelist):
                # Get the current tab's directory (header)
                current_tab_index = self.currentIndex()
                directory = self.tabText(current_tab_index)

                # Build the file path relative to the working directory
                if directory == "Root":
                    file_path = os.path.join(self.root_path, file_name)  # Root directory
                else:
                    file_path = os.path.join(self.root_path, directory, file_name)  # Directory + file name

                # Open the file in PopupEditor
                editor = PopupEditor(file_path, file_type='csv', nested_mode=mode)
                editor.exec()  # Open the popup editor dialog

class DirectoryTreeView(QWidget):
    """
    Tree View implementation to display directories and files, including empty directories.
    Tracks the current directory and manages its own 'Edit Selected' button for editing files.
    """
    def __init__(self, dataframe: pd.DataFrame, root_path: str, whitelist=None, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe
        self.root_path = root_path
        self.whitelist = whitelist if whitelist else ['.csv']  # Allow CSV files for now

        # Initialize current directory
        self.current_directory = None  # Track the current directory

        # Main layout for the tree view and the edit button
        self.layout = QVBoxLayout(self)

        # Tree widget to display directories and files
        self.tree_widget = QTreeWidget()
        self.tree_widget.setColumnCount(1)  # Only one column for filenames
        self.tree_widget.setHeaderLabel("Directories")
        self.layout.addWidget(self.tree_widget)

        # Add Edit Button for the TreeView
        self.edit_button = QPushButton("Edit Selected")
        self.edit_button.setEnabled(False)  # Disabled initially
        self.layout.addWidget(self.edit_button)

        # Populate the tree
        self.populate_tree()

        # Store the current selected directory or file
        self.current_selected_item = None

        # Connect tree selection to update the button state
        self.tree_widget.itemClicked.connect(self.on_item_clicked)

        # Connect the Edit button to editing action
        self.edit_button.clicked.connect(self.edit_selected_file)

    def on_item_clicked(self, item, column):
        """Track the currently selected directory or file and update the current directory."""
        self.current_selected_item = item  # Track the clicked item

        # To track the full path of the selected directory or the parent directory of a file
        path_parts = []

        # Traverse up the tree to build the full path
        while item:
            path_parts.insert(0, item.text(0))  # Insert each directory/file at the start of the list
            item = item.parent()  # Move up to the parent item

        # Build the full path of the current directory
        self.current_directory = os.path.join(self.root_path, *path_parts)

        file_name = self.current_selected_item.text(0)
        if any(file_name.endswith(ext) for ext in self.whitelist):
            self.edit_button.setEnabled(True)  # Enable if a valid file is selected
        else:
            self.edit_button.setEnabled(False)  # Disable if not a valid file

    def get_selected_file_path(self):
        """Return the full file path of the selected file based on the working directory (WD)."""
        if self.current_selected_item:
            file_path_parts = []  # To store the parts of the path

            # Traverse up the tree to construct the full path
            item = self.current_selected_item
            while item:
                file_path_parts.insert(0, item.text(0))  # Insert each part of the path at the start
                item = item.parent()  # Move up to the parent item

            # Join the parts of the path and prepend the root_path (WD)
            file_path = os.path.join(self.root_path, *file_path_parts)

            # Check if the file is in the whitelist (e.g., CSV file)
            file_name = self.current_selected_item.text(0)
            if any(file_name.endswith(ext) for ext in self.whitelist):
                return file_path

        return None

    def edit_selected_file(self):
        """Edit the selected file in the PopupEditor."""
        selected_file_path = self.get_selected_file_path()
        if selected_file_path:
            # Open the file in PopupEditor
            editor = PopupEditor(selected_file_path, file_type='csv')
            editor.exec()  # Open the popup editor dialog

    def add_tree_node(self, parent_item, path_list):
        """Recursively create tree structure from path."""
        if not path_list:
            return

        current_part = path_list[0]  # First part of the path
        remaining_parts = path_list[1:]  # Remaining part of the path

        # Look for an existing child node for the current part (directory or file)
        for i in range(parent_item.childCount()):
            if parent_item.child(i).text(0) == current_part:
                # If it exists, continue down the tree
                self.add_tree_node(parent_item.child(i), remaining_parts)
                return

        # Create a new tree item for the current part
        new_item = QTreeWidgetItem([current_part])
        parent_item.addChild(new_item)

        # Continue adding the rest of the path (recursively)
        self.add_tree_node(new_item, remaining_parts)

    def populate_tree(self):
        """Populate the tree structure based on the DataFrame, with no 'Root' node."""
        self.tree_widget.clear()  # Clear the tree before populating

        # Iterate over each directory (column in DataFrame)
        for directory in self.dataframe.columns:
            # Check if this is the "Root" directory
            if directory == "Root":
                # For the root directory, add files directly at the top level (not under any "Root" node)
                for file_name in self.dataframe[directory].dropna():
                    if file_name.strip():  # Ensure non-empty file name
                        # Add root-level files directly under the invisible root item
                        self.add_tree_node(self.tree_widget.invisibleRootItem(), [file_name])
            else:
                # Handle other directories (subdirectories or regular directories)
                directory_parts = directory.split(os.sep)  # Split directory path for hierarchy
                self.add_tree_node(self.tree_widget.invisibleRootItem(), directory_parts)  # Add the directory

                # Now add files under this directory, if any
                for file_name in self.dataframe[directory].dropna():
                    if file_name.strip():  # Ensure non-empty file name
                        full_path = directory_parts + [file_name]  # Full path of file
                        self.add_tree_node(self.tree_widget.invisibleRootItem(), full_path)  # Add file

        self.tree_widget.expandAll()  # Expand all directories by default

    def recurse_struct(self, struct_data, path_str):
        for field_name, value in struct_data.items():
            field_type = type(value).__name__
            unique_id = str(uuid.uuid4())
            self.id_df.append({
                "uuid": unique_id,
                "data_type": field_type,
                "path": f"{path_str}.{field_name}",
                "cell_coords": (row, col)
            })
            # Recursively handle nested structs or lists inside fields
            if isinstance(value, dict):  # Struct fields
                self.recurse_struct(value, f"{path_str}.{field_name}")
            elif isinstance(value, list):  # Arrays inside struct fields
                self.recurse_list(value, f"{path_str}.{field_name}")

class MainWidgetWindow(QMainWindow):
    def __init__(self, root_path: str):
        super().__init__()
        self.setWindowTitle("Directory Viewer")
        self.resize(600, 800)
        self.root_path = root_path
        os.chdir(root_path)

        # Scraper and DataFrame
        self.scraper = DirectoryScraper()
        self.blacklist = ['Thumbs.db', '.DS_Store', '.git', '.log']
        self.dataframe = self.scraper.files_to_dataframe(root_path)
        self.filter_dataframe()

        # Main layout
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        # Restore original Create Directory and Create File buttons
        self.create_dir_button = QPushButton("Add Main Object")
        self.create_dir_button.clicked.connect(self.create_directory)
        self.button_layout.addWidget(self.create_dir_button)

        self.create_file_button = QPushButton("Insert Item")
        self.create_file_button.clicked.connect(self.create_file)
        self.button_layout.addWidget(self.create_file_button)

        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(lambda: self.refresh_data(self.root_path))
        self.button_layout.addWidget(self.refresh_button)

        # Toggle View button (between Tab and Tree view)
        self.toggle_view_button = QPushButton("Toggle View")
        self.toggle_view_button.clicked.connect(self.toggle_view)
        self.button_layout.addWidget(self.toggle_view_button)

        self.main_layout.addLayout(self.button_layout)

        # Initially show the tabbed widget
        self.tab_widget = DirectoryTabbedView(self.dataframe, root_path)
        self.tree_view_widget = DirectoryTreeView(self.dataframe, root_path)
        self.current_view = "tree"  # Start with the tab view

        self.main_layout.addWidget(self.tree_view_widget)  # Add tabbed view initially
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

    def toggle_view(self):
        """Toggle between the tabbed and tree views."""
        if self.current_view == "tab":
            # Switch to tree view
            self.main_layout.removeWidget(self.tab_widget)
            self.tab_widget.hide()
            self.main_layout.addWidget(self.tree_view_widget)
            self.tree_view_widget.show()
            self.current_view = "tree"
        else:
            # Switch back to tabbed view
            self.main_layout.removeWidget(self.tree_view_widget)
            self.tree_view_widget.hide()
            self.main_layout.addWidget(self.tab_widget)
            self.tab_widget.show()
            self.current_view = "tab"

    def refresh_data(self, root_path: str):
        """Handles the refresh action by re-scraping the directory structure and updating the views."""
        new_dataframe = self.scraper.files_to_dataframe(root_path)

        # Apply blacklist filter
        for col in new_dataframe.columns:
            new_dataframe[col] = new_dataframe[col].apply(
                lambda x: '' if any(blacklisted in str(x) for blacklisted in self.blacklist) else x)

        self.dataframe = new_dataframe

        # Update both tab and tree views
        self.tab_widget.update_tabs(new_dataframe)
        self.tree_view_widget.dataframe = new_dataframe  # Update the dataframe in the tree view
        self.tree_view_widget.populate_tree()  # Repopulate the tree view

    def update_root_path(self, new_root_path: str):
        """Updates the root path and refreshes the content based on the new directory."""
        self.root_path = new_root_path
        os.chdir(new_root_path)  # Change the working directory
        self.refresh_data(new_root_path)  # Refresh the data in both views (tabs and tree)

    def create_directory(self):
        """Create a directory inside the currently selected tab's directory."""
        dir_name, ok = QInputDialog.getText(self, "Create Directory", "Enter new directory name:")
        if ok and dir_name:
            self.make_node(f"{dir_name}:dir")  # Use the node maker to handle directory creation

    def create_file(self):
        """Create a CSV file inside the currently selected tab's directory."""
        file_name, ok = QInputDialog.getText(self, "Create File", "Enter new file name:")
        if ok and file_name:
            self.make_node(f"{file_name}:csv")  # Use the node maker to handle file creation

    def make_node(self, node_info):
        """Generic node creator: handles any action based on 'name:action'."""
        try:
            name, action = node_info.split(":")
            self.handle_node_action(name, action)
        except ValueError:
            QMessageBox.warning(self, "Error", "Input must be in format 'name:action' (e.g., prefs:csv or jane:dir).")

    def handle_node_action(self, name, action):
        """Map action to a function, allowing future devs to implement arbitrary operations."""
        action_map = {
            'dir': self.create_directory_node,
            'csv': self.create_file_csv,
            # Future actions can be added here by other developers
        }

        # Execute the action, if it exists
        if action in action_map:
            action_map[action](name)  # Call the appropriate action handler with the provided name
        else:
            QMessageBox.warning(self, "Error", f"Action '{action}' is not supported. Future actions can be added.")

    def create_directory_node(self, dir_name):
        """Create a directory inside the currently selected directory."""
        if self.current_view == "tab":
            # Handle tab view case
            current_tab = self.tab_widget.tabText(self.tab_widget.currentIndex())
            if current_tab:  # Ensure a tab is selected
                new_dir_path = os.path.join(self.root_path, current_tab, dir_name)
        else:
            # Handle tree view case
            if self.tree_view_widget.current_directory:
                new_dir_path = os.path.join(self.root_path, self.tree_view_widget.current_directory, dir_name)
            else:
                QMessageBox.warning(self, "Error", "No directory selected in the tree view.")
                return

        if not os.path.exists(new_dir_path):
            os.makedirs(new_dir_path)
            QMessageBox.information(self, "Success", f"Directory '{dir_name}' created.")
            self.refresh_data(self.root_path)
        else:
            QMessageBox.warning(self, "Error", f"Directory '{dir_name}' already exists.")

    def create_file_csv(self, file_name):
        """Create a CSV file inside the currently selected directory."""
        if self.current_view == "tab":
            # Handle tab view case
            current_tab = self.tab_widget.tabText(self.tab_widget.currentIndex())
            if current_tab:  # Ensure a tab is selected
                new_file_path = os.path.join(self.root_path, current_tab, file_name)
        else:
            # Handle tree view case
            if self.tree_view_widget.current_directory:
                new_file_path = os.path.join(self.root_path, self.tree_view_widget.current_directory, file_name)
            else:
                QMessageBox.warning(self, "Error", "No directory selected in the tree view.")
                return

        # Check if the user already included the .csv extension
        if not file_name.endswith('.csv'):
            new_file_path += ".csv"  # Append .csv if missing

        if not os.path.exists(new_file_path):
            open(new_file_path, 'w').close()  # Create an empty CSV file
            QMessageBox.information(self, "Success", f"CSV file '{file_name}' created.")
            self.refresh_data(self.root_path)
        else:
            QMessageBox.warning(self, "Error", f"File '{file_name}' already exists.")

    def filter_dataframe(self):
        """Filters the DataFrame to exclude files that match the blacklist."""
        for col in self.dataframe.columns:
            self.dataframe[col] = self.dataframe[col].apply(lambda x: '' if any(blacklisted in str(x) for blacklisted in self.blacklist) else x)

    def save_parquet(self, dataframe, save_path):
        try:
            dataframe.to_parquet(save_path, partition_cols=['nested_field1', 'nested_field2'])  # Specify nested columns for partitioning
            QMessageBox.information(self, "Success", "Changes saved to Parquet.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save Parquet: {str(e)}")

    def detect_parquet_column_type(self, column):
        # Check if the column contains nested types (list, map, struct)
        if isinstance(column, list):
            return 'list'
        elif isinstance(column, dict):
            return 'map'
        elif isinstance(column, pd.DataFrame):  # Struct-like data
            return 'struct'
        return 'simple'
