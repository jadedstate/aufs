# src/aufs/user_tools/aufs_runner_ui.py

import os
import sys
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
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

class AUFSRunner(QMainWindow):
    def __init__(self):
        super().__init__()

        self.csv_file = os.path.expanduser("~/.aufs/config/aufsparquet_list.csv")

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

    def load_selected_parquet(self, parquet_path):
        """Load schema as DataFrame and send it to the controller."""
        schema_df = self.extract_schema_as_paths(parquet_path)

        # Ensure any old widget is removed before adding a new one
        if self.main_widget:
            self.right_panel_widget.layout().removeWidget(self.main_widget)
            self.main_widget.deleteLater()

        # Create new MainWidgetWindow and pass DataFrame directly
        self.main_widget = MainWidgetWindow(use_dataframe=True, dataframe=schema_df)
        if self.right_panel_widget.layout() is None:
            self.right_panel_widget.setLayout(QVBoxLayout())
        self.right_panel_widget.layout().addWidget(self.main_widget)

    def extract_schema_as_paths(self, parquet_path):
        """Extract schema and format it as a list of paths for edge nodes."""
        try:
            parquet_file = pq.ParquetFile(parquet_path)
            schema = parquet_file.schema_arrow
            print(schema)

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
