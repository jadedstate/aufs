# src/aufs/user_tools/aufs_runner_complete_ui.py

import os
import sys
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
import json
from PySide6.QtWidgets import (
    QApplication, QTabWidget, QFileDialog, QMessageBox, QVBoxLayout, QWidget, QPushButton, QLineEdit, QSplitter, QTableView, QHBoxLayout,
    QInputDialog, QMainWindow, QTreeWidget, QTreeWidgetItem, QLabel, QListWidget,
                               QListWidgetItem, QMenu)
from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtGui import QAction

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.editable_pandas_model import EditablePandasModel
from src.aufs.user_tools.popup_editor import PopupEditor
from src.aufs.user_tools.scraper import DirectoryScraper

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

class AUFSRunner(QMainWindow):
    def __init__(self):
        super().__init__()

        self.csv_file = os.path.expanduser("~/.aufs/config/aufsparquet_list.csv")
        self.nullify_coords = []  
        # Initialize ParquetPlaceholder
        self.parquet_placeholder = ParquetPlaceholder()
        
        self.setWindowTitle("AUFS Runner")
        self.resize(1000, 800)

        # ================== Main Layout ==================
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        self.splitter = QSplitter(self)

        # ================== Left Panel (AUFS List) ==================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Add buttons above the search bar
        button_control_layout = QHBoxLayout()
        self.add_to_aufsparquet_list_button = QPushButton("Add Parquet File", self)
        self.add_to_aufsparquet_list_button.clicked.connect(self.add_to_aufsparquet_list)

        self.edit_aufsparquet_list_button = QPushButton("Edit Parquet List", self)
        self.edit_aufsparquet_list_button.clicked.connect(self.edit_aufsparquet_list)

        self.load_aufsparquet_list_button = QPushButton("Load Parquet List", self)
        self.load_aufsparquet_list_button.clicked.connect(self.load_aufsparquet_list)

        button_control_layout.addWidget(self.add_to_aufsparquet_list_button)
        button_control_layout.addWidget(self.edit_aufsparquet_list_button)
        button_control_layout.addWidget(self.load_aufsparquet_list_button)
        left_layout.addLayout(button_control_layout)

        # Search bar for filtering the parquets
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search Parquet list...")
        self.search_bar.textChanged.connect(self.apply_filter)
        left_layout.addWidget(self.search_bar)

        # AUFS list (QTableView using EditablePandasModel)
        self.parquet_table = QTableView(self)
        self.parquet_table.setSelectionBehavior(QTableView.SelectRows)
        left_layout.addWidget(self.parquet_table)

        button_layout = QHBoxLayout()
        self.hide_selected_button = QPushButton("Hide Selected", self)
        self.placeholder_button = QPushButton("Placeholder", self)
        self.set_new_wd_button = QPushButton("Set new WD", self)
        self.set_new_wd_button.clicked.connect(self.set_new_working_directory)

        button_layout.addWidget(self.hide_selected_button)
        button_layout.addWidget(self.placeholder_button)
        button_layout.addWidget(self.set_new_wd_button)
        left_layout.addLayout(button_layout)

        left_widget.setLayout(left_layout)

        # ================== Right Panel (AUFS Runner + Buttons) ==================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        tab_control_layout = QHBoxLayout()
        self.edit_tabs_parquet_button = QPushButton("Does nothing Button")
        tab_control_layout.addWidget(self.edit_tabs_parquet_button)
        self.edit_tabs_parquet_button.clicked.connect(self.open_popup_editor)

        right_layout.addLayout(tab_control_layout)

        self.right_panel_widget = QWidget()
        right_layout.addWidget(self.right_panel_widget)

        right_widget.setLayout(right_layout)

        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(right_widget)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.splitter)
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        self.splitter.setSizes([300, self.width() - 300])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        self.exit_button = QPushButton("Exit", self)
        self.exit_button.clicked.connect(self.close)
        main_layout.addWidget(self.exit_button)

        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.parquet_table.setModel(self.proxy_model)

        self.search_bar.textChanged.connect(self.apply_filter)
        self.main_widget = None

        # Prompt the user for the initial working directory or load from CSV
        self.initial_setup()

    def initial_setup(self):
        """Ensure the CSV file exists and load it, or prompt the user for a directory."""
        if not os.path.exists(self.csv_file):
            # Create the CSV file with required columns if it doesn't exist
            self.create_csv_file()
        self.load_from_csv()

    def create_csv_file(self):
        """Create a new CSV file with the correct columns."""
        try:
            # Define initial columns
            df = pd.DataFrame(columns=["File Name", "Path", "Last Modified"])
            df.to_csv(self.csv_file, index=False)
            QMessageBox.information(self, "CSV Created", f"Initialized new CSV file: {self.csv_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create CSV file: {str(e)}")

    def load_from_csv(self):
        """Load Parquet files from the AUFS Parquet List CSV."""
        try:
            # Ensure the CSV file exists with correct columns
            if not os.path.exists(self.csv_file):
                self.create_csv_file()

            # Load data into the model
            df = pd.read_csv(self.csv_file)
            required_columns = {"File Name", "Path", "Last Modified"}

            # Validate columns or recreate the file if invalid
            if not required_columns.issubset(df.columns):
                QMessageBox.warning(self, "Invalid CSV", "Detected invalid columns. Reinitializing CSV file.")
                self.create_csv_file()
                df = pd.read_csv(self.csv_file)

            # Load data into the UI model
            self.model = EditablePandasModel(df, editable=False)
            self.proxy_model.setSourceModel(self.model)
            self.parquet_table.selectionModel().selectionChanged.connect(self.on_selection_change)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")

    def refresh_parquet_list(self, root_dir):
        """Scan the directory for Parquet files and update the list."""
        parquet_data = []
        for item in os.listdir(root_dir):
            full_path = os.path.join(root_dir, item)
            if os.path.isfile(full_path) and item.endswith('.parquet'):
                last_modified = os.path.getmtime(full_path)
                parquet_data.append({
                    'File Name': item,
                    'Path': full_path,
                    'Last Modified': pd.Timestamp(last_modified, unit='s'),
                })

        df = pd.DataFrame(parquet_data)
        df.to_csv(self.csv_file, index=False)  # Save updated list
        self.load_from_csv()

    def add_to_aufsparquet_list(self):
        """Add a new Parquet file to the AUFS Parquet List (CSV file)."""
        # Open file dialog to select a single Parquet file
        parquet_path, _ = QFileDialog.getOpenFileName(self, "Select a Parquet File", "", "Parquet Files (*.parquet);;All Files (*)")
        if parquet_path:
            # Extract the file name
            parquet_name = os.path.basename(parquet_path)
            new_entry = pd.DataFrame([[parquet_name, parquet_path]], columns=["File Name", "Path"])
            
            # Append to the CSV file
            if os.path.exists(self.csv_file):
                df = pd.read_csv(self.csv_file)
                df = pd.concat([df, new_entry], ignore_index=True)
            else:
                df = new_entry
            
            df.to_csv(self.csv_file, index=False)
            QMessageBox.information(self, "Added to AUFS Parquet List", f"Added '{parquet_name}' to AUFS Parquet List.")
            self.load_from_csv()

    def edit_aufsparquet_list(self):
        """Open the AUFS Parquet List (CSV file) in a popup editor for editing."""
        # csv_file = os.path.expanduser("~/.aufs/parquets_main.csv")
        if os.path.exists(self.csv_file):
            editor = PopupEditor(self.csv_file, file_type='csv')
            editor.exec()
            self.load_from_csv()
        else:
            QMessageBox.warning(self, "No AUFS Parquet List", "No AUFS Parquet List file found to edit.")

    def load_aufsparquet_list(self):
        """Load the parquet list from the AUFS Parquet List (CSV file)."""
        # csv_file = os.path.expanduser("~/.aufs/parquets_main.csv")
        if os.path.exists(self.csv_file):
            self.load_from_csv()
        else:
            QMessageBox.warning(self, "No AUFS Parquet List", "No AUFS Parquet List file found to load.")

    def apply_filter(self, filter_text):
        self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.setFilterFixedString(filter_text)

    def set_new_working_directory(self):
        new_directory = self.parquet_placeholder.select_parquet_root()
        if new_directory:
            self.refresh_parquet_list(new_directory)
            QMessageBox.information(self, "Directory Changed", f"Working directory changed to: {new_directory}")

    def on_selection_change(self, selected, deselected):
        if selected.indexes():
            index = selected.indexes()[0]
            parquet_path = self.model.get_dataframe().iloc[index.row()]['Path']
            self.load_selected_parquet(parquet_path)

    def open_popup_editor(self):
        """Open the popup editor for editing tabs parquet."""
        editor = PopupEditor('path_to_parquet')  # Example: pass the path to the parquet
        editor.exec()

    def load_selected_parquet(self, parquet_path, use_meta_tree=True):
        if use_meta_tree:
            try:
                # --- Extract Parquet file data ---
                self.parquet_file = pq.ParquetFile(parquet_path)
                self.schema = self.parquet_file.schema  # Extract the schema directly
                self.metadata = self.parquet_file.metadata.metadata  # Extract metadata
                print(self.metadata)
                self.table_data = self.parquet_file.read().to_pandas()  

                # --- Pass schema to build_aufs_dataframe ---
                schema_df = self.build_aufs_dataframe(self.schema, self.metadata)

            except Exception as e:
                print(f"Error extracting schema from metadata: {e}")
                schema_df = pd.DataFrame()  # Fallback to empty DataFrame

        else:
            # --- Fallback: Extract schema paths directly ---
            schema_df = self.extract_schema_as_paths(parquet_path)

        # --- Remove old widget ---
        if self.main_widget:
            self.right_panel_widget.layout().removeWidget(self.main_widget)
            self.main_widget.deleteLater()

        # --- Create and add the new widget ---
        self.main_widget = MainWidgetWindow(use_dataframe=True, dataframe=schema_df)
        if self.right_panel_widget.layout() is None:
            self.right_panel_widget.setLayout(QVBoxLayout())
        self.right_panel_widget.layout().addWidget(self.main_widget)

    def find_roots(self, directory_tree):
        """Identify nodes that have no parent (true roots)."""
        all_children = {child['id'] for children in directory_tree.values() for child in children}
        return [node_id for node_id in directory_tree if node_id not in all_children]

    def build_uuid_leaf_paths(self, directory_tree):
        """Build paths with UUIDs but only includes leaf paths."""
        paths = []

        def walk_tree(node_id, parent_path=""):
            # Append the current node ID to the parent path
            current_path = os.path.join(parent_path, node_id) if parent_path else node_id

            # If the node has no children, treat it as a leaf and add the path
            if node_id not in directory_tree or not directory_tree[node_id]:
                paths.append(current_path)
            else:
                # Recurse into children
                for child in directory_tree[node_id]:
                    walk_tree(child['id'], current_path)

        # Find the true roots and start traversal from them
        roots = self.find_roots(directory_tree)
        for root_id in roots:
            walk_tree(root_id)

        return paths

    def create_dataframe_from_uuid_paths(self, paths):
        """Creates a DataFrame directly from UUID paths."""
        # Convert paths into a DataFrame format
        df = pd.DataFrame({"Root": paths})
        return df

    def add_non_tree_schema_components_to_df(self, df, schema, metadata):
        """Find schema elements outside the tree and add them to the DataFrame."""
        try:
            # --- 1. Extract metadata and schema info ---
            uuid_mapping = json.loads(metadata[b'uuid_dirname_mapping'].decode('utf-8'))
            schema_columns = set(schema.names)  # Get all schema columns
            # print(uuid_mapping)

            # --- 2. Identify UUIDs already used in the tree ---
            used_uuids = set(uuid_mapping.keys())

            # --- 3. Find remaining schema elements ---
            # Drop schema elements that match UUIDs (tree nodes)
            def is_partial_uuid_match(field_name):
                """Returns True if any UUID substring exists within the field name."""
                return any(uuid in field_name for uuid in used_uuids)

            # Filter schema fields based on partial matches
            remaining_fields = [field.name for field in schema if not is_partial_uuid_match(field.name)]

            # --- 4. Append missing elements to DataFrame ---
            new_rows = pd.DataFrame({'Root': remaining_fields})
            df = pd.concat([df, new_rows], ignore_index=True)

            return df

        except Exception as e:
            print(f"Error adding non-tree schema components: {e}")
            return df  # Return original DataFrame if something fails

    def transform_to_controller_format(self, df):
        """Transform 'Root' column into headers for the controller."""
        # Treat each value in 'Root' as a header
        transformed_df = pd.DataFrame(columns=df['Root'].tolist())
        # print("Transformed DataFrame for Controller:")
        # print(transformed_df)
        return transformed_df

    def build_aufs_dataframe(self, schema, metadata):
        try:
            # --- Load metadata ---
            directory_tree = json.loads(metadata[b'directory_tree'].decode('utf-8'))
            self.uuid_mapping = json.loads(metadata[b'uuid_dirname_mapping'].decode('utf-8'))

            # --- Stage 1: Build UUID leaf paths ---
            uuid_paths = self.build_uuid_leaf_paths(directory_tree)

            # --- Stage 2: Create DataFrame ---
            df = pd.DataFrame({"Root": uuid_paths})

            # --- Stage 3: Replace UUIDs with names ---
            # resolved_df = self.replace_uuids_with_names_in_df(df, uuid_mapping)

            resolved_df = self.add_non_tree_schema_components_to_df(df, schema, metadata)

            # --- Stage 4: Transform for Controller ---
            self.transformed_df = self.transform_to_controller_format(resolved_df)

            full_schema_df = self.transformed_df # self.add_table_chunks_to_df(self.transformed_df)

            controller_df = self.prepare_controller_df(full_schema_df)

            # Print for validation
            # print("Final Controller-Compatible DataFrame:")
            # print(transformed_df)

            return controller_df
        except Exception as e:
            print(f"Error extracting schema from metadata: {e}")
            return pd.DataFrame()  # Return an empty DataFrame on failure

    def map_schema_to_headers(self):
        """Map schema columns to transformed_df headers based on UUIDs."""
        try:
            # 1. Build UUID-to-header lookup
            header_map = {}
            for header in self.transformed_df.columns:  # Headers in transformed_df
                header_uuid = header.split("/")[-1]     # Extract last UUID component
                header_map[header_uuid] = header       # Map UUID to header path

            # 2. Match schema columns using middle UUID part
            remap_dict = {}
            for col in self.schema.names:             # Schema columns
                uuid = col.split("-")[1]              # Extract middle UUID
                if uuid in header_map:                # Match with header UUID
                    remap_dict[col] = header_map[uuid]  # Map schema name -> header path

            return remap_dict

        except Exception as e:
            print(f"Error mapping schema to headers: {e}")
            return {}

    def add_table_chunks_to_df(self, df):
        """Populate transformed_df headers with data chunks from the table."""
        try:
            # 1. Generate schema-to-header mapping
            remap_dict = self.map_schema_to_headers()

            # 2. Transfer data based on mapping
            for schema_col, header in remap_dict.items():
                # Map schema column data to corresponding header
                df[header] = self.table_data[schema_col]

            return df

        except Exception as e:
            print(f"Error adding table chunks: {e}")
            return df  # Return the existing DataFrame if something fails

    def prepare_controller_df(self, df):
        """Final preparation of the DataFrame for controller delivery, including UUID replacement."""
        self.nullify_coords = []  # Reset nullification list

        try:
            # Replace UUIDs with names in headers
            df = self.replace_uuids_with_names_in_headers(df, self.uuid_mapping)
            
            # Add platform-specific columns and process nullification
            df = self.add_platform_specific_columns(df)
            df = self.nullify_cells(df)
            
            return df

        except Exception as e:
            print(f"Error preparing controller DataFrame: {e}")
            return df  # Return original DataFrame if something fails

    def add_platform_specific_columns(self, df):
        """Add platform-specific columns and cells based on file metadata."""
        try:
            # Example metadata structure
            metadata = {
                "platform_scripts": {
                    "win_script": "0",
                    "darwin_script": "1",
                    "linux_script": "2"
                }
            }

            # Map platforms to columns
            platform_mapping = {
                'win': metadata['platform_scripts']['win_script'],
                'mac': metadata['platform_scripts']['darwin_script'],
                'linux': metadata['platform_scripts']['linux_script']
            }

            # Add columns and default cell values
            for platform, col_index in platform_mapping.items():
                header = f'ROOT_SPRING_0/SMB/{platform}'
                df[header] = "London"

                # Track cell coordinates for nullification
                self.nullify_coords.append((0, int(col_index)))  # (row, col)

            return df
        except Exception as e:
            print(f"Error adding platform-specific columns: {e}")
            return df

    def nullify_cells(self, df):
        """Clear specific cells in the DataFrame based on the provided coordinates."""
        for row, col in self.nullify_coords:
            try:
                col_name = df.columns[col]
                df.at[row, col_name] = None  # Clear the value
            except IndexError as e:
                print(f"Error nullifying cell ({row}, {col}): {e}")
        return df

    def replace_uuids_with_names_in_headers(self, df, uuid_mapping):
        """Replaces UUIDs in headers while preserving path structure."""
        def resolve_header(header):
            components = header.split("/")
            return "/".join([uuid_mapping.get(comp, f"UNKNOWN-{comp}") for comp in components])

        df.columns = [resolve_header(col) for col in df.columns]
        return df

    def extract_schema_as_paths(self, parquet_path):
        """Extract schema and format it as a list of paths for edge nodes."""
        try:
            parquet_file = pq.ParquetFile(parquet_path)
            schema = parquet_file.schema_arrow
            # print(schema)

            # Treat each field as an edge/leaf node
            paths = []
            for field in schema:
                if isinstance(field.type, (pa.ListType, pa.StructType, pa.MapType)):
                    paths.extend(self.flatten_nested_schema(field, prefix=field.name))
                else:
                    paths.append(field.name)

            df = pd.DataFrame({"Root": paths})
            return df

        except Exception as e:
            print(f"Error extracting schema: {e}")
            return pd.DataFrame()

    def flatten_nested_schema(self, field, prefix=""):
        """Recursively flatten nested schemas into full paths."""
        paths = []

        # Build full path for the current field
        current_path = f"{prefix}.{field.name}" if prefix else field.name

        # Handle StructType: Iterate through children
        if isinstance(field.type, pa.StructType):
            for subfield in field.type:
                paths.extend(self.flatten_nested_schema(subfield, prefix=current_path))
        # Handle ListType: Assume elements may also be nested
        elif isinstance(field.type, pa.ListType):
            paths.extend(self.flatten_nested_schema(field.type.value_field, prefix=f"{current_path}[]"))
        # Handle MapType: Expand key/value pairs
        elif isinstance(field.type, pa.MapType):
            paths.extend(self.flatten_nested_schema(field.type.key_field, prefix=f"{current_path}[key]"))
            paths.extend(self.flatten_nested_schema(field.type.item_field, prefix=f"{current_path}[value]"))
        else:
            # Append leaf nodes directly
            paths.append(current_path)

        return paths

class ParquetPlaceholder:
    def __init__(self):
        self.root_parquet = None
        self.root_directory = None

    def select_parquet_root(self):
        """Prompt user to select the root Parquet file location."""
        self.root_parquet = QFileDialog.getExistingDirectory(None, "Select Parquet Root Directory")
        if not self.root_parquet:
            QMessageBox.warning(None, "No Directory Selected", "You must select a directory to continue.")
        return self.root_parquet

    def select_parquet_root(self):
        """Prompt user to select the root directory where parquets are located."""
        self.root_directory = QFileDialog.getExistingDirectory(None, "Select Config Root Directory")
        if not self.root_directory:
            QMessageBox.warning(None, "No Directory Selected", "You must select a directory to continue.")
        return self.root_directory

if __name__ == "__main__":
    app = QApplication([])

    # Initialize and show the Runner 
    window = AUFSRunner()
    window.show()
    app.exec()
