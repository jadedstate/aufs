# src/aufs/user_tools/configs_manager.py

import os
import sys
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QTabWidget, QFileDialog, QMessageBox, QVBoxLayout, QWidget, QPushButton, QLineEdit, QSplitter, QTableView, QHBoxLayout,
    QInputDialog, QMainWindow
)
from PySide6.QtCore import Qt, QSortFilterProxyModel

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.editable_pandas_model import EditablePandasModel
from src.aufs.user_tools.config_controller import MainWidgetWindow  # Import MainWidgetWindow
from src.aufs.user_tools.popup_editor import PopupEditor

class ConfigsManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.csv_file = os.path.expanduser("~/.aufs/config/configs_main.csv")

        # Initialize ParquetPlaceholder
        self.parquet_placeholder = ParquetPlaceholder()
        
        self.setWindowTitle("Configs Manager")
        self.resize(1000, 800)

        # ================== Main Layout ==================
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        self.splitter = QSplitter(self)

        # ================== Left Panel (Config List) ==================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Add buttons above the search bar
        button_control_layout = QHBoxLayout()
        self.add_to_clist_button = QPushButton("Add to CList", self)
        self.add_to_clist_button.clicked.connect(self.add_to_clist)

        self.edit_clist_button = QPushButton("Edit CList", self)
        self.edit_clist_button.clicked.connect(self.edit_clist)

        self.load_clist_button = QPushButton("Load CList", self)
        self.load_clist_button.clicked.connect(self.load_clist)

        button_control_layout.addWidget(self.add_to_clist_button)
        button_control_layout.addWidget(self.edit_clist_button)
        button_control_layout.addWidget(self.load_clist_button)
        left_layout.addLayout(button_control_layout)

        # Search bar for filtering the configs
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search Configs...")
        self.search_bar.textChanged.connect(self.apply_filter)
        left_layout.addWidget(self.search_bar)

        # Config list (QTableView using EditablePandasModel)
        self.config_table = QTableView(self)
        self.config_table.setSelectionBehavior(QTableView.SelectRows)
        left_layout.addWidget(self.config_table)

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

        # ================== Right Panel (Config Editor + Buttons) ==================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        tab_control_layout = QHBoxLayout()
        self.edit_tabs_config_button = QPushButton("Does nothing Button")
        tab_control_layout.addWidget(self.edit_tabs_config_button)
        self.edit_tabs_config_button.clicked.connect(self.open_popup_editor)

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
        self.config_table.setModel(self.proxy_model)

        self.search_bar.textChanged.connect(self.apply_filter)
        self.main_widget = None

        # Prompt the user for the initial working directory or load from CSV
        self.initial_setup()

    def initial_setup(self):
        """Check for CSV file and load it, or prompt the user for a directory."""
        if os.path.exists(self.csv_file):
            self.load_from_csv()
        else:
            root_dir = self.parquet_placeholder.select_config_root()
            if root_dir:
                self.refresh_config_list(root_dir)
            else:
                QMessageBox.critical(self, "Error", "No working directory selected. Exiting.")
                self.close()

    def load_from_csv(self):
        """Load configs from a CSV file."""
        try:
            df = pd.read_csv(self.csv_file)
            if 'Config Name' not in df.columns or 'Path' not in df.columns:
                raise ValueError("CSV missing required columns 'Config Name' and 'Path'")
            self.model = EditablePandasModel(df, editable=False)
            self.proxy_model.setSourceModel(self.model)
            self.config_table.selectionModel().selectionChanged.connect(self.on_selection_change)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")

    def refresh_config_list(self, root_dir):
        """Refresh the config list by scanning the root directory for configs."""
        config_data = []
        for item in os.listdir(root_dir):
            full_path = os.path.join(root_dir, item)
            if os.path.isdir(full_path):
                last_modified = os.path.getmtime(full_path)
                config_data.append({
                    'Config Name': item,
                    'Path': full_path,
                    'Last Modified': pd.Timestamp(last_modified, unit='s'),
                })

        df = pd.DataFrame(config_data)
        self.model = EditablePandasModel(df, editable=False)
        self.proxy_model.setSourceModel(self.model)
        self.config_table.selectionModel().selectionChanged.connect(self.on_selection_change)

    def add_to_clist(self):
        """Add a new config to the CList (CSV file)."""
        # csv_file = os.path.expanduser("~/.aufs/configs_main.csv")
        config_path = QFileDialog.getExistingDirectory(self, "Select Config Directory")
        if config_path:
            config_name = os.path.basename(config_path)
            new_entry = pd.DataFrame([[config_name, config_path]], columns=["Config Name", "Path"])
            
            if os.path.exists(self.csv_file):
                df = pd.read_csv(self.csv_file)
                df = pd.concat([df, new_entry], ignore_index=True)
            else:
                df = new_entry
            
            df.to_csv(self.csv_file, index=False)
            QMessageBox.information(self, "Added to CList", f"Added '{config_name}' to CList.")
            self.load_from_csv()

    def edit_clist(self):
        """Open the CList (CSV file) in a popup editor for editing."""
        # csv_file = os.path.expanduser("~/.aufs/configs_main.csv")
        if os.path.exists(self.csv_file):
            editor = PopupEditor(self.csv_file, file_type='csv')
            editor.exec()
            self.load_from_csv()
        else:
            QMessageBox.warning(self, "No CList", "No CList file found to edit.")

    def load_clist(self):
        """Load the config list from the CList (CSV file)."""
        # csv_file = os.path.expanduser("~/.aufs/configs_main.csv")
        if os.path.exists(self.csv_file):
            self.load_from_csv()
        else:
            QMessageBox.warning(self, "No CList", "No CList file found to load.")

    def apply_filter(self, filter_text):
        self.proxy_model.setFilterKeyColumn(0)
        self.proxy_model.setFilterFixedString(filter_text)

    def set_new_working_directory(self):
        new_directory = self.parquet_placeholder.select_config_root()
        if new_directory:
            self.refresh_config_list(new_directory)
            QMessageBox.information(self, "Directory Changed", f"Working directory changed to: {new_directory}")

    def on_selection_change(self, selected, deselected):
        if selected.indexes():
            index = selected.indexes()[0]
            config_path = self.model.get_dataframe().iloc[index.row()]['Path']
            self.load_selected_config(config_path)

    def load_selected_config(self, config_path):
        """Load the selected configuration from the config list and update the views."""
        
        # Instead of reusing the old widget, always create a new MainWidgetWindow
        if self.main_widget:
            # Remove the old widget from the layout if it exists
            self.right_panel_widget.layout().removeWidget(self.main_widget)
            self.main_widget.deleteLater()

        # Create a new MainWidgetWindow for each new config selection
        self.main_widget = MainWidgetWindow(config_path)
        if self.right_panel_widget.layout() is None:
            self.right_panel_widget.setLayout(QVBoxLayout())
        self.right_panel_widget.layout().addWidget(self.main_widget)

        # This will ensure the root_path and everything is fresh and correct
        self.main_widget.refresh_data(config_path)

    def open_popup_editor(self):
        """Open the popup editor for editing tabs config."""
        editor = PopupEditor('path_to_config_or_file')  # Example: pass the path to the config
        editor.exec()

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

    def select_config_root(self):
        """Prompt user to select the root directory where configs are located."""
        self.root_directory = QFileDialog.getExistingDirectory(None, "Select Config Root Directory")
        if not self.root_directory:
            QMessageBox.warning(None, "No Directory Selected", "You must select a directory to continue.")
        return self.root_directory

if __name__ == "__main__":
    app = QApplication([])

    # Initialize and show the Config Manager 
    window = ConfigsManagerApp()
    window.show()
    app.exec()
