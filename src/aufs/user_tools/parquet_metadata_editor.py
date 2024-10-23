from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt
from deep_editor import DeepEditor  # Import DeepEditor for complex metadata handling
import pandas as pd

class MetadataObjectsList(QWidget):
    def __init__(self, metadata_df=None, parent=None):
        super().__init__(parent)
        self.metadata_df = metadata_df  # Expecting a DataFrame directly

        self.setWindowTitle("Metadata Objects and Editor")
        self.resize(1000, 800)

        # Splitter for dividing list/buttons and DeepEditor
        self.splitter = QSplitter(self)
        self.splitter.setOrientation(Qt.Vertical)

        # === Top Pane (List + Buttons) ===
        self.top_widget = QWidget(self)
        self.top_layout = QVBoxLayout(self.top_widget)

        # List of metadata objects (keys)
        self.metadata_list = QListWidget(self)
        self.top_layout.addWidget(self.metadata_list)

        # Buttons to interact with metadata objects
        self.buttons_layout = QHBoxLayout()
        self.open_button = QPushButton("Open Metadata", self)
        self.buttons_layout.addWidget(self.open_button)
        self.top_layout.addLayout(self.buttons_layout)

        # Add top widget to the splitter (top pane)
        self.splitter.addWidget(self.top_widget)

        button_flags = {
            'exit': False,
            'save': False,
            'sort_column': False
        }

        # === Bottom Pane (DeepEditor) ===
        self.deep_editor = DeepEditor(button_flags=button_flags, nested_mode=True, parent=self)
        self.splitter.addWidget(self.deep_editor)

        # Main layout using the splitter
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.splitter)

        # Load metadata objects into the list
        self.load_metadata_objects()

        # Connect buttons
        self.open_button.clicked.connect(self.open_metadata)

    def load_metadata_objects(self):
        """Load the metadata keys from the DataFrame into the QListWidget."""
        self.metadata_list.clear()  # Clear existing list
        if self.metadata_df is not None:
            for key in self.metadata_df['Key']:  # Assuming 'Key' column exists in the DataFrame
                self.metadata_list.addItem(str(key))

    def open_metadata(self):
        """Open the selected metadata object in DeepEditor."""
        selected_item = self.metadata_list.currentItem()
        if selected_item:
            metadata_key = selected_item.text()
            try:
                # Filter the DataFrame to the selected key
                metadata_row = self.metadata_df[self.metadata_df['Key'] == metadata_key]

                if metadata_row.empty:
                    QMessageBox.warning(self, "No Data", f"No metadata found for key: {metadata_key}")
                    return

                # Load the row as a DataFrame into DeepEditor for editing
                self.deep_editor.load_from_dataframe(metadata_row)

            except KeyError as e:
                QMessageBox.critical(self, "Error", f"Metadata not found for key: {metadata_key}")

    def get_modified_metadata(self):
        """Return the modified DataFrame."""
        # We assume that DeepEditor modifies the DataFrame in place, so we just return the updated DataFrame.
        return self.metadata_df
