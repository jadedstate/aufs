# src/aufs/user_tools/config_controller.py

import os
import sys
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QPushButton, QTabWidget, QLabel, QListWidget, QHBoxLayout,
                               QListWidgetItem, QInputDialog, QMessageBox, QTreeWidget, QTreeWidgetItem, QMenu)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
import pandas as pd

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.scraper import DirectoryScraper
from src.aufs.user_tools.popup_editor import PopupEditor

class DirectoryTabbedView(QTabWidget):
    def __init__(self, dataframe: pd.DataFrame, root_path: str, main_window, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe
        self.root_path = root_path
        self.main_window = main_window
        self.whitelist = ['.csv']
        self.tab_paths = {}  # Map each tab index to its full path
        self.currentChanged.connect(self.update_selected_dir)
        self.setup_tabs()

    def setup_tabs(self):
        self.clear()
        self.tab_paths.clear()  # Reset tab paths whenever tabs are reloaded

        # Create the summary tab
        summary_tab = self.create_summary_tab()
        self.addTab(summary_tab, "Summary")
        self.tab_paths[self.indexOf(summary_tab)] = self.root_path  # Root path for the summary tab

        # Add a tab for each directory in the dataframe
        for col in self.dataframe.columns:
            full_dir_path = os.path.join(self.root_path, col)  # Full path for the directory
            tab = self.create_directory_tab(col, self.dataframe[col])
            tab_title = os.path.basename(full_dir_path)  # Use only the directory name for display
            self.addTab(tab, tab_title)
            self.tab_paths[self.indexOf(tab)] = full_dir_path  # Store the full path for this tab

    def update_tabs(self, new_dataframe: pd.DataFrame):
        self.dataframe = new_dataframe
        self.setup_tabs()

    def create_summary_tab(self):
        summary_widget = QWidget()
        layout = QVBoxLayout()
        directory_tree_view = DirectoryTreeView(self.dataframe, self.root_path, self.main_window, self)
        layout.addWidget(directory_tree_view)
        summary_widget.setLayout(layout)
        return summary_widget

    def create_directory_tab(self, directory_name, file_series):
        tab_widget = QWidget()
        layout = QVBoxLayout()
        tab_abs_dir = QLabel(directory_name)
        layout.addWidget(tab_abs_dir)
        file_list_widget = QListWidget()
        file_list_widget.setSelectionMode(QListWidget.SingleSelection)

        for file_name in file_series.dropna():
            if file_name.strip():
                file_list_widget.addItem(QListWidgetItem(file_name))

        layout.addWidget(file_list_widget)
        edit_button = QPushButton("Edit selected")
        edit_button.setEnabled(False)
        layout.addWidget(edit_button)
        file_list_widget.currentItemChanged.connect(lambda: self.update_edit_button(file_list_widget, edit_button))
        edit_button.clicked.connect(lambda: self.edit_selected_file(file_list_widget))
        tab_widget.setLayout(layout)
        return tab_widget

    def update_edit_button(self, file_list_widget, edit_button):
        selected_item = file_list_widget.currentItem()
        if selected_item:
            file_name = selected_item.text()
            edit_button.setEnabled(any(file_name.endswith(ext) for ext in self.whitelist))
        else:
            edit_button.setEnabled(False)

    def edit_selected_file(self, file_list_widget, mode=False):
        selected_item = file_list_widget.currentItem()
        if selected_item:
            file_name = selected_item.text()
            if any(file_name.endswith(ext) for ext in self.whitelist):
                # Retrieve the full path for the selected tab from tab_paths
                full_dir_path = self.tab_paths.get(self.currentIndex(), self.root_path)
                full_file_path = os.path.join(full_dir_path, file_name)
                editor = PopupEditor(full_file_path, file_type='csv', nested_mode=mode)
                editor.exec()

    def update_selected_dir(self):
        """Update `selected_dir` in MainWidgetWindow based on the selected tab."""
        # Get the full directory path for the currently selected tab from tab_paths
        self.main_window.selected_dir = self.tab_paths.get(self.currentIndex(), self.root_path)

class DirectoryTreeView(QWidget):
    def __init__(self, dataframe: pd.DataFrame, root_path: str, main_window, tab_widget: DirectoryTabbedView, whitelist=None, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe
        self.root_path = root_path
        self.main_window = main_window
        self.tab_widget = tab_widget
        self.whitelist = whitelist if whitelist else ['.csv']
        self.layout = QVBoxLayout(self)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setColumnCount(1)
        self.tree_widget.setHeaderLabel("Directories")
        self.layout.addWidget(self.tree_widget)
        self.populate_tree()

        self.tree_widget.itemClicked.connect(self.on_item_clicked)
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        selected_item = self.tree_widget.itemAt(position)
        if selected_item:
            context_menu = QMenu(self)

            # Add "Open Tab" action
            open_tab_action = QAction("Open Tab", self)
            open_tab_action.triggered.connect(lambda: self.open_tab_for_item(selected_item))
            context_menu.addAction(open_tab_action)

            # Add "Edit Selected" action if the item is a file in the whitelist
            if any(selected_item.text(0).endswith(ext) for ext in self.whitelist):
                edit_action = QAction("Edit Selected", self)
                edit_action.triggered.connect(self.edit_selected_file)
                context_menu.addAction(edit_action)

            context_menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def open_tab_for_item(self, item):
        # Build the full path from the tree structure
        path_parts = []
        current_item = item
        while current_item:
            path_parts.insert(0, current_item.text(0))
            current_item = current_item.parent()
        full_path = os.path.join(self.root_path, *path_parts)

        # Check if the selected item is a file and use its parent directory for the tab
        if os.path.isfile(full_path):
            parent_path = os.path.dirname(full_path)
            tab_title = os.path.basename(parent_path)
            path_for_tab = parent_path
        else:
            tab_title = os.path.basename(full_path)
            path_for_tab = full_path

        # Check if this directory path already has a tab open
        if path_for_tab in self.tab_widget.tab_paths.values():
            # If it exists, switch to the existing tab
            tab_index = list(self.tab_widget.tab_paths.keys())[list(self.tab_widget.tab_paths.values()).index(path_for_tab)]
            self.tab_widget.setCurrentIndex(tab_index)
        else:
            # Otherwise, create a new tab for this directory path
            file_series = self.dataframe.get("/".join(path_parts), pd.Series([]))
            tab_content = self.tab_widget.create_directory_tab(path_for_tab, file_series)
            self.tab_widget.addTab(tab_content, tab_title)

            # Map this tab's full path in `tab_paths` for future reference
            self.tab_widget.tab_paths[self.tab_widget.indexOf(tab_content)] = path_for_tab
            self.tab_widget.setCurrentWidget(tab_content)

    def on_item_clicked(self, item, column):
        """Update the current directory and `selected_dir` based on the clicked item in the tree."""
        path_parts = []
        current_item = item
        while current_item:
            path_parts.insert(0, current_item.text(0))
            current_item = current_item.parent()
        self.current_directory = os.path.join(self.root_path, *path_parts)
        self.main_window.selected_dir = self.current_directory
        self.current_selected_item = item  # Keep track of the selected item

    def edit_selected_file(self):
        """Edit the selected file in the PopupEditor."""
        if self.current_selected_item:
            file_name = self.current_selected_item.text(0)
            if any(file_name.endswith(ext) for ext in self.whitelist):
                file_path = self.main_window.selected_dir
                editor = PopupEditor(file_path, file_type='csv')
                editor.exec()

    def populate_tree(self):
        self.tree_widget.clear()
        for directory in self.dataframe.columns:
            if directory == "Root":
                for file_name in self.dataframe[directory].dropna():
                    if file_name.strip():
                        self.add_tree_node(self.tree_widget.invisibleRootItem(), [file_name])
            else:
                directory_parts = directory.split(os.sep)
                self.add_tree_node(self.tree_widget.invisibleRootItem(), directory_parts)
                for file_name in self.dataframe[directory].dropna():
                    if file_name.strip():
                        full_path = directory_parts + [file_name]
                        self.add_tree_node(self.tree_widget.invisibleRootItem(), full_path)
        self.tree_widget.expandAll()

    def add_tree_node(self, parent_item, path_list):
        if not path_list:
            return
        current_part = path_list[0]
        remaining_parts = path_list[1:]
        for i in range(parent_item.childCount()):
            if parent_item.child(i).text(0) == current_part:
                self.add_tree_node(parent_item.child(i), remaining_parts)
                return
        new_item = QTreeWidgetItem([current_part])
        parent_item.addChild(new_item)
        self.add_tree_node(new_item, remaining_parts)

    def update_selected_dir_from_tree(self, item):
        """Update the `selected_dir` based on the clicked item in the tree."""
        path_parts = []
        current_item = item
        while current_item:
            path_parts.insert(0, current_item.text(0))
            current_item = current_item.parent()
        full_path = os.path.join(self.root_path, *path_parts)
        self.main_window.selected_dir = full_path

class MainWidgetWindow(QMainWindow):
    def __init__(self, root_path: str = None, use_dataframe=False, dataframe=None):
        super().__init__()
        self.setWindowTitle("AUFS Controller")
        self.resize(600, 800)

        # Handle inputs
        self.root_path = root_path if root_path else ""
        self.selected_dir = self.root_path

        # Set the dataframe based on input mode
        if use_dataframe and dataframe is not None:
            self.dataframe = dataframe
        else:
            # Fall back to scraper if no DataFrame provided
            os.chdir(self.root_path)
            self.dataframe = DirectoryScraper().files_to_dataframe(self.root_path)

        self.filter_dataframe()
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        # UI Controls
        self.create_dir_button = QPushButton("Add Directory")
        self.create_dir_button.clicked.connect(self.create_directory)
        self.button_layout.addWidget(self.create_dir_button)

        self.create_file_button = QPushButton("Add File")
        self.create_file_button.clicked.connect(self.create_file)
        self.button_layout.addWidget(self.create_file_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(lambda: self.refresh_data(self.root_path))
        self.button_layout.addWidget(self.refresh_button)
        
        self.main_layout.addLayout(self.button_layout)

        # Tabbed View for Schema/Data Display
        self.tab_widget = DirectoryTabbedView(self.dataframe, self.root_path, self)
        self.tree_view_widget = DirectoryTreeView(self.dataframe, self.root_path, self, self.tab_widget)
        self.main_layout.addWidget(self.tab_widget)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

    def create_directory(self):
        dir_name, ok = QInputDialog.getText(self, "Create Directory", "Enter new directory name:")
        if ok and dir_name:
            new_dir_path = os.path.join(self.selected_dir, dir_name)
            if not os.path.exists(new_dir_path):
                os.makedirs(new_dir_path)
                QMessageBox.information(self, "Success", f"Directory '{dir_name}' created at {self.selected_dir}.")
                self.refresh_data(self.root_path)
            else:
                QMessageBox.warning(self, "Error", f"Directory '{dir_name}' already exists at {self.selected_dir}.")

    def create_file(self):
        file_name, ok = QInputDialog.getText(self, "Create File", "Enter new file name:")
        if ok and file_name:
            new_file_path = os.path.join(self.selected_dir, f"{file_name}.csv" if not file_name.endswith('.csv') else file_name)
            if not os.path.exists(new_file_path):
                open(new_file_path, 'w').close()
                QMessageBox.information(self, "Success", f"File '{file_name}' created at {self.selected_dir}.")
                self.refresh_data(self.root_path)
            else:
                QMessageBox.warning(self, "Error", f"File '{file_name}' already exists at {self.selected_dir}.")

    def refresh_data(self, root_path: str = None, use_dataframe=False, dataframe=None):
        """Refresh data, optionally using a direct DataFrame input."""
        if use_dataframe and dataframe is not None:
            # Update using the provided DataFrame
            self.dataframe = dataframe
        else:
            # Fallback: scrape from the filesystem
            self.dataframe = DirectoryScraper().files_to_dataframe(root_path if root_path else self.root_path)

        self.filter_dataframe()
        self.tab_widget.update_tabs(self.dataframe)
        self.tree_view_widget.dataframe = self.dataframe
        self.tree_view_widget.populate_tree()

    def filter_dataframe(self):
        for col in self.dataframe.columns:
            self.dataframe[col] = self.dataframe[col].apply(lambda x: '' if any(b in str(x) for b in ['Thumbs.db', '.DS_Store', '.git', '.log']) else x)

    def toggle_view(self):
        if self.current_view == "tab":
            self.main_layout.removeWidget(self.tab_widget)
            self.tab_widget.hide()
            self.main_layout.addWidget(self.tree_view_widget)
            self.tree_view_widget.show()
            self.current_view = "tree"
        else:
            self.main_layout.removeWidget(self.tree_view_widget)
            self.tree_view_widget.hide()
            self.main_layout.addWidget(self.tab_widget)
            self.tab_widget.show()
            self.current_view = "tab"

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
