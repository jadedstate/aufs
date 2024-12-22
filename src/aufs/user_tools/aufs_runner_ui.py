# src/aufs/user_tools/aufs_runner_ui.py

import os
import sys
import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa
import json
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

    def load_selected_parquet(self, parquet_path, use_meta_tree=True):
        if use_meta_tree:
            try:
                # --- Extract Parquet file data ---
                parquet_file = pq.ParquetFile(parquet_path)
                schema = parquet_file.schema  # Extract the schema directly
                metadata = parquet_file.metadata.metadata  # Extract metadata

                # --- Pass schema to build_paths_from_meta_tree ---
                schema_df = self.build_paths_from_meta_tree(schema, metadata)

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

    def replace_uuids_with_names_in_df(self, df, uuid_mapping):
        """Replaces UUIDs in each path while preserving full structure."""
        def resolve_path(path):
            # Replace UUID components with readable names
            components = path.split(os.sep)
            return os.sep.join([uuid_mapping.get(comp, f"UNKNOWN-{comp}") for comp in components])

        # Apply replacements
        df['Root'] = df['Root'].apply(resolve_path)
        return df

    def add_non_tree_schema_components_to_df(self, df, schema, metadata):
        """Find schema elements outside the tree and add them to the DataFrame."""
        try:
            # --- 1. Extract metadata and schema info ---
            uuid_mapping = json.loads(metadata[b'uuid_dirname_mapping'].decode('utf-8'))
            schema_columns = set(schema.names)  # Get all schema columns
            print(uuid_mapping)

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

    def build_paths_from_meta_tree(self, schema, metadata):
        try:
            # --- Load metadata ---
            directory_tree = json.loads(metadata[b'directory_tree'].decode('utf-8'))
            uuid_mapping = json.loads(metadata[b'uuid_dirname_mapping'].decode('utf-8'))

            # --- Stage 1: Build UUID leaf paths ---
            uuid_paths = self.build_uuid_leaf_paths(directory_tree)

            # --- Stage 2: Create DataFrame ---
            df = pd.DataFrame({"Root": uuid_paths})

            # --- Stage 3: Replace UUIDs with names ---
            resolved_df = self.replace_uuids_with_names_in_df(df, uuid_mapping)

            resolved_df = self.add_non_tree_schema_components_to_df(resolved_df, schema, metadata)

            # --- Stage 4: Transform for Controller ---
            transformed_df = self.transform_to_controller_format(resolved_df)

            # Print for validation
            # print("Final Controller-Compatible DataFrame:")
            # print(transformed_df)

            return transformed_df
        except Exception as e:
            print(f"Error extracting schema from metadata: {e}")
            return pd.DataFrame()  # Return an empty DataFrame on failure

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
