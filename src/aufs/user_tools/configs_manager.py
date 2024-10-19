import os
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QTabWidget, QFileDialog, QMessageBox, QVBoxLayout, QWidget, QPushButton, QLineEdit, QSplitter, QTableView, QHBoxLayout,
    QInputDialog, QMainWindow
)
from PySide6.QtCore import Qt, QSortFilterProxyModel

from editable_pandas_model import EditablePandasModel
from config_controller import MainWidgetWindow  # Import MainWidgetWindow
from popup_editor import PopupEditor

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

class ConfigsManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize ParquetPlaceholder
        self.parquet_placeholder = ParquetPlaceholder()
        self.setWindowTitle("Configs Manager")
        self.resize(1000, 800)

        # ================== Main Layout ==================
        main_widget = QWidget()  # QWidget for holding main layout
        self.setCentralWidget(main_widget)  # Correctly set the central widget
        main_layout = QVBoxLayout(main_widget)

        # Splitter to divide the left (config list) and right (tabbed config editor)
        self.splitter = QSplitter(self)
        
        # ================== Left Panel (Config List) ==================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Search bar for filtering the configs
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search Configs...")
        self.search_bar.textChanged.connect(self.apply_filter)
        left_layout.addWidget(self.search_bar)

        # Config list (QTableView using EditablePandasModel)
        self.config_table = QTableView(self)
        self.config_table.setSelectionBehavior(QTableView.SelectRows)
        left_layout.addWidget(self.config_table)

        # Control buttons below the list
        button_layout = QHBoxLayout()
        self.hide_selected_button = QPushButton("Hide Selected", self)
        self.placeholder_button = QPushButton("Placeholder", self)
        button_layout.addWidget(self.hide_selected_button)
        button_layout.addWidget(self.placeholder_button)
        left_layout.addLayout(button_layout)

        left_widget.setLayout(left_layout)

        # ================== Right Panel (Config Editor + Buttons) ==================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Top control buttons for tabs
        tab_control_layout = QHBoxLayout()
        self.edit_tabs_config_button = QPushButton("Edit Tabs Config")
        tab_control_layout.addWidget(self.edit_tabs_config_button)
        self.edit_tabs_config_button.clicked.connect(self.open_popup_editor)

        right_layout.addLayout(tab_control_layout)

        # Placeholder for tabbed config editor (MainWidgetWindow)
        self.right_panel_widget = QWidget()
        right_layout.addWidget(self.right_panel_widget)

        right_widget.setLayout(right_layout)

        # Add left and right widgets to splitter
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(right_widget)

        # Add the splitter to the main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.splitter)
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Set initial splitter size: 300px for the left, and the rest for the right
        # This should only be done once on initialization
        self.splitter.setSizes([300, self.width() - 300])
        # Stretch the right panel dynamically, keeping the left side static
        self.splitter.setStretchFactor(0, 0)  # Left panel fixed
        self.splitter.setStretchFactor(1, 1)  # Right panel expands
        # Exit button at the bottom
        self.exit_button = QPushButton("Exit", self)
        self.exit_button.clicked.connect(self.close)
        main_layout.addWidget(self.exit_button)

        # Initialize the tabbed config editor (MainWidgetWindow)
        # Initialize the filter proxy model
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)  # Case-insensitive filtering

        # Set up the table view to use the proxy model instead of the actual model
        self.config_table.setModel(self.proxy_model)

        # Connect search bar signal to the filter method
        self.search_bar.textChanged.connect(self.apply_filter)

        self.main_widget = None  # Placeholder for the main widget (tabs)
        self.refresh_config_list()

    def refresh_config_list(self):
        """Refresh the config list by scanning the root directory for configs."""
        root_dir = self.parquet_placeholder.select_config_root()
        if not root_dir:
            return  # User cancelled

        # Scan the root directory for subdirectories (configs)
        config_data = []
        for item in os.listdir(root_dir):
            full_path = os.path.join(root_dir, item)
            if os.path.isdir(full_path):
                last_modified = os.path.getmtime(full_path)
                config_data.append({
                    'Config Name': item,
                    'Last Modified': pd.Timestamp(last_modified, unit='s'),
                })

        # Create a DataFrame for the config list
        df = pd.DataFrame(config_data)

        # Update the EditablePandasModel with the new DataFrame
        self.model = EditablePandasModel(df, editable=False)
        
        # Set the proxy model's source model to the actual model
        self.proxy_model.setSourceModel(self.model)

        # Connect the selection event **after** setting the model
        self.config_table.selectionModel().selectionChanged.connect(self.on_selection_change)

    def apply_filter(self, filter_text):
        """Filter the config list based on user input in the search bar."""
        # Set the filter string to the proxy model. This will filter rows based on the "Config Name" column (column 0).
        self.proxy_model.setFilterKeyColumn(0)  # Assuming "Config Name" is the first column
        self.proxy_model.setFilterFixedString(filter_text)

    def on_selection_change(self, selected, deselected):
        """Triggered when a config list item is selected."""
        if selected.indexes():
            index = selected.indexes()[0]
            config_name = self.model.get_dataframe().iloc[index.row(), 0]  # Get selected config name
            config_path = os.path.join(self.parquet_placeholder.root_directory, config_name)
            self.load_selected_config(config_path)

    def load_selected_config(self, config_path):
        """Load the selected config into the tabbed editor (MainWidgetWindow)."""
        # Initialize the MainWidgetWindow if it's not already set
        if not self.main_widget:
            self.main_widget = MainWidgetWindow(config_path)
            # Ensure the right panel has a layout before adding the widget
            if self.right_panel_widget.layout() is None:
                self.right_panel_widget.setLayout(QVBoxLayout())  # Set layout if not set

            self.right_panel_widget.layout().addWidget(self.main_widget)  # Add the MainWidgetWindow to the layout
        else:
            self.main_widget.update_root_path(config_path)  # Update existing widget's path

    def create_new_config(self):
        """Prompt user for the config location and name, then create the config directory."""
        root_dir = self.parquet_placeholder.select_config_root()
        if not root_dir:
            return  # User cancelled or didn't select a directory

        # Ask user for a config name
        config_name, ok = QInputDialog.getText(self, "New Config", "Enter config name:")
        if ok and config_name:
            config_path = os.path.join(root_dir, config_name)
            if not os.path.exists(config_path):
                os.makedirs(config_path)
                QMessageBox.information(self, "Config Created", f"New config '{config_name}' created.")
                self.refresh_config_list()  # Refresh config list after creation
            else:
                QMessageBox.warning(self, "Error", f"Config '{config_name}' already exists.")
        else:
            QMessageBox.warning(self, "Error", "Invalid config name.")

    def open_popup_editor(self):
        """Open the popup editor for editing tabs config."""
        editor = PopupEditor('path_to_config_or_file')  # Example: pass the path to the config
        editor.exec()

if __name__ == "__main__":
    app = QApplication([])

    # Initialize and show the Config Manager
    window = ConfigsManagerApp()
    window.show()
    app.exec()
