import os
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QTabWidget, QLabel, QListWidget, QHBoxLayout, QListWidgetItem, QInputDialog, QMessageBox
from PySide6.QtCore import Qt
import pandas as pd
from scraper import DirectoryScraper
from popup_editor import PopupEditor

class ConfigController(QTabWidget):
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

    def edit_selected_file(self, file_list_widget):
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
                editor = PopupEditor(file_path)
                editor.exec()  # Open the popup editor dialog

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
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        button_layout = QHBoxLayout()

        # Restore original Create Directory and Create File buttons
        self.create_dir_button = QPushButton("Create Directory")
        self.create_dir_button.clicked.connect(self.create_directory)
        button_layout.addWidget(self.create_dir_button)

        self.create_file_button = QPushButton("Create File")
        self.create_file_button.clicked.connect(self.create_file)
        button_layout.addWidget(self.create_file_button)

        # Refresh button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(lambda: self.refresh_data(self.root_path))
        button_layout.addWidget(self.refresh_button)

        main_layout.addLayout(button_layout)

        self.tab_widget = ConfigController(self.dataframe, root_path)
        main_layout.addWidget(self.tab_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def update_root_path(self, new_root_path: str):
        """Updates the root path and refreshes the content based on the new directory."""
        self.root_path = new_root_path
        os.chdir(new_root_path)  # Change the working directory
        self.refresh_data(new_root_path)

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
        """Create a directory inside the currently selected tab's directory."""
        current_tab = self.tab_widget.tabText(self.tab_widget.currentIndex())
        if current_tab:  # Ensure a tab is selected
            new_dir_path = os.path.join(self.root_path, current_tab, dir_name)
            if not os.path.exists(new_dir_path):
                os.makedirs(new_dir_path)
                QMessageBox.information(self, "Success", f"Directory '{dir_name}' created in '{current_tab}'.")
                self.refresh_data(self.root_path)
            else:
                QMessageBox.warning(self, "Error", f"Directory '{dir_name}' already exists.")
        else:
            QMessageBox.warning(self, "Error", "No directory selected.")

    def create_file_csv(self, file_name):
        """Create a CSV file inside the currently selected tab's directory."""
        current_tab = self.tab_widget.tabText(self.tab_widget.currentIndex())
        if current_tab:  # Ensure a tab is selected
            # Check if the user already included the .csv extension
            if not file_name.endswith('.csv'):
                file_name += ".csv"  # Append .csv if missing

            new_file_path = os.path.join(self.root_path, current_tab, file_name)
            if not os.path.exists(new_file_path):
                open(new_file_path, 'w').close()  # Create an empty CSV file
                QMessageBox.information(self, "Success", f"CSV file '{file_name}' created in '{current_tab}'.")
                self.refresh_data(self.root_path)
            else:
                QMessageBox.warning(self, "Error", f"File '{file_name}' already exists.")
        else:
            QMessageBox.warning(self, "Error", "No directory selected.")

    def refresh_data(self, root_path: str):
        """Handles the refresh action by re-scraping the directory structure and updating the tabs."""
        new_dataframe = self.scraper.files_to_dataframe(root_path)

        # Apply blacklist filter
        for col in new_dataframe.columns:
            new_dataframe[col] = new_dataframe[col].apply(lambda x: '' if any(blacklisted in str(x) for blacklisted in self.blacklist) else x)

        # Now update the ConfigController tabs with the new data
        self.tab_widget.update_tabs(new_dataframe)

    def filter_dataframe(self):
        """
        Filters the DataFrame to exclude files that match the blacklist.
        """
        for col in self.dataframe.columns:
            self.dataframe[col] = self.dataframe[col].apply(lambda x: '' if any(blacklisted in str(x) for blacklisted in self.blacklist) else x)
