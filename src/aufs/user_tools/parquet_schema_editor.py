import os
import sys
import pandas as pd
import pyarrow.parquet as pq  # pyarrow for parquet file handling
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QFileDialog
)

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from deep_editor import DeepEditor  # Assuming PopupEditor is a QWidget
from src.aufs.utils import validate_schema

class ParquetSchemaEditor(QWidget):  # Now inheriting from QWidget instead of QDialog
    def __init__(self, parquet_file=None, dataframe_input=None, parent=None):
        super().__init__(parent)

        self.parquet_file = parquet_file
        self.dataframe_input = dataframe_input

        self.setWindowTitle("Parquet Schema Editor")
        self.resize(1000, 800)

        # Main layout of the widget
        self.main_layout = QVBoxLayout(self)

        value_options = {
            'Data Type': [
                # Commonly used types
                'int64', 'float64', 'string', 'bool', 
                'timestamp[ns]', 'date32',
                
                # Complex/nested types
                'list', 'struct', 'map', 'binary',
                
                '-------',
                
                # Less common types (grouped by category)
                # Integers
                'int8', 'int16', 'int32', 'uint8', 'uint16', 'uint32', 'uint64',
                
                # Floating-point types
                'float32',
                
                # Timestamp and Date Types
                'timestamp[us]', 'timestamp[ms]', 'timestamp[s]',
                'date64', 'time32', 'time64',
                
                # Fixed-point decimal types
                'decimal128', 'decimal256',
            ],
            'Compression': ['NONE', 'SNAPPY', 'GZIP', 'LZ4', 'ZSTD', 'BROTLI'],
            'Encryption': ['None', 'AES-GCM-V1', 'AES-GCM-V2']
        }

        button_flags = {
            'exit': False,
            'save': False,
            'sort_column': False
        }

        # === PopupEditor (Embedded here) ===
        self.deep_editor = DeepEditor(value_options=value_options, button_flags=button_flags, nested_mode=True, parent=self)  # PopupEditor is now embedded as a QWidget


        # Footer buttons for loading, creating new schema, saving, and exiting
        self.footer_layout = QHBoxLayout()

        self.load_button = QPushButton("Load Schema", self)
        self.create_schema_button = QPushButton("Create New Schema", self)
        self.save_button = QPushButton("Save Schema", self)
        self.exit_button = QPushButton("Exit", self)

        self.footer_layout.addWidget(self.load_button)
        self.footer_layout.addWidget(self.create_schema_button)
        self.footer_layout.addWidget(self.save_button)
        self.footer_layout.addWidget(self.exit_button)

        # Add footer buttons to main layout
        self.main_layout.addLayout(self.footer_layout)
        self.main_layout.addWidget(self.deep_editor)

        # Connect buttons to their respective functions
        self.load_button.clicked.connect(self.load_schema)
        self.create_schema_button.clicked.connect(self.create_default_schema)
        self.save_button.clicked.connect(self.save_schema)
        self.exit_button.clicked.connect(self.close)

    def load_schema(self):
        """Open file dialog to select a Parquet file and load the schema into PopupEditor."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Parquet File", "", "Parquet Files (*.parquet)")
        
        if file_path:
            self.parquet_file = file_path
            try:
                # Use pyarrow to read the parquet schema
                parquet_table = pq.read_table(self.parquet_file)
                schema = parquet_table.schema
                schema_data = {
                    'Field': [field.name for field in schema],
                    'Data Type': [str(field.type) for field in schema],
                }

                # Collect additional metadata if available
                for field in schema:
                    if field.metadata:  # Check if metadata exists for the field
                        for key, value in field.metadata.items():
                            if key not in schema_data:
                                schema_data[key] = []
                            schema_data[key].append(value.decode('utf-8') if isinstance(value, bytes) else value)
                    else:
                        # Fill missing metadata with None
                        for key in schema_data.keys():
                            if key != 'Field' and key != 'Data Type':
                                schema_data[key].append(None)

                # Convert the schema_data dict to a pandas DataFrame
                schema_df = pd.DataFrame(schema_data)

                # Load the schema into PopupEditor
                self.deep_editor.load_from_dataframe(schema_df)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load Parquet schema: {str(e)}")

    def create_default_schema(self):
        """Create a default schema with typical fields and load it into PopupEditor."""
        try:
            default_schema = pd.DataFrame({
                'Field': ['field1', 'field2', 'field3'],
                'Data Type': ['int64', 'float', 'string'],
                'Compression': ['NONE', 'SNAPPY', 'GZIP'],
                'Encryption': ['None', 'None', 'AES-GCM-V1']
            })

            # Load the default schema into PopupEditor
            self.deep_editor.load_from_dataframe(default_schema)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create default schema: {str(e)}")

    def save_schema(self):
        """Save the schema from PopupEditor to the Parquet file using pyarrow."""
        if not self.parquet_file:
            # Show file dialog to save if no file path is provided
            self.parquet_file, _ = QFileDialog.getSaveFileName(self, "Save Parquet File", "", "Parquet Files (*.parquet)")
        
        if self.parquet_file:
            try:
                # Get the dataframe from the PopupEditor
                dataframe = self.deep_editor.model.get_dataframe()  # Get the full dataframe as-is

                # Step 1: Validate the schema (using utils.validate_schema)
                fields = [
                    pa.field(row['Field'], pa.from_numpy_dtype(row['Data Type']))  # Assuming Data Type is numpy-like dtype
                    for _, row in dataframe.iterrows()
                ]

                valid, validation_message = validate_schema(fields)
                if not valid:
                    QMessageBox.critical(self, "Invalid Schema", f"Schema validation failed: {validation_message}")
                    return  # Stop if schema validation fails

                # Step 2: Convert the DataFrame to PyArrow table, preserving all columns
                arrow_table = pq.Table.from_pandas(dataframe)
                
                # Step 3: Write the PyArrow table to the Parquet file
                pq.write_table(arrow_table, self.parquet_file)
                
                QMessageBox.information(self, "Success", f"Schema saved to {self.parquet_file}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save schema: {str(e)}")
        else:
            QMessageBox.warning(self, "No File", "No file specified for saving the schema.")

# Usage
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = ParquetSchemaEditor()
    window.show()
    sys.exit(app.exec())
