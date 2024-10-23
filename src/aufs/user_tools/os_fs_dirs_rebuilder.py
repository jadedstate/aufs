import sys
import os
import pyarrow as pa
import pyarrow.parquet as pq
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QFileDialog, QTreeWidget, QTreeWidgetItem, QMessageBox, QCheckBox)
from PySide6.QtCore import Qt

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.core.extractor import extract_table
import re
import ast  # To convert string representation of metadata back to a dictionary

class ParquetDirRebuilderApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set up window properties
        self.setWindowTitle("Parquet Directory Rebuilder")
        self.setGeometry(300, 300, 600, 400)

        # Main layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add file path input and browse button
        self.file_label = QLabel("Parquet File:")
        self.file_input = QLineEdit(self)
        self.file_input.setText(os.path.expanduser("~/.aufs/parquet/dev"))  # Default value
        self.browse_button = QPushButton("Browse", self)
        self.browse_button.clicked.connect(self.browse_for_file)

        layout.addWidget(self.file_label)
        layout.addWidget(self.file_input)
        layout.addWidget(self.browse_button)

        # Add checkbox for toggling merge
        self.merge_checkbox = QCheckBox("Merge Directories", self)
        self.merge_checkbox.setChecked(False)  # Default to not merging
        self.merge_checkbox.stateChanged.connect(self.load_parquet_schema)
        layout.addWidget(self.merge_checkbox)

        # Checkbox to show or hide "Root Directory"
        self.show_root_checkbox = QCheckBox("Show Root Directory", self)
        self.show_root_checkbox.setChecked(True)  # Default to showing the root directory
        self.show_root_checkbox.stateChanged.connect(self.load_parquet_schema)
        layout.addWidget(self.show_root_checkbox)

        # Add load button
        self.load_button = QPushButton("Load Parquet Schema", self)
        self.load_button.clicked.connect(self.load_parquet_schema)
        layout.addWidget(self.load_button)

        # Add tree view to display directory structure
        self.dir_tree = QTreeWidget(self)
        self.dir_tree.setHeaderLabels(["Directory Structure"])
        layout.addWidget(self.dir_tree)

    def browse_for_file(self):
        """
        Opens a file dialog to let the user browse for a Parquet file.
        """
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Select Parquet File", "", "Parquet Files (*.parquet)")
        if file_path:
            self.file_input.setText(file_path)

    def load_parquet_schema(self):
        """
        Loads the Parquet schema from the specified file and regenerates the original directory tree.
        """
        file_path = self.file_input.text()
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "Error", "File does not exist. Please check the path.")
            return

        table = extract_table(file_path)
        if table is None:
            QMessageBox.critical(self, "Error", "Failed to extract Parquet file.")
            return

        schema = table.schema
        metadata = schema.metadata

        # Print the metadata to see its structure
        if metadata:
            print("Metadata:", metadata)

        # Check if metadata contains the 'directory_tree'
        if metadata is None or b'directory_tree' not in metadata:
            QMessageBox.critical(self, "Error", "Parquet file does not contain directory tree metadata.")
            return

        # Load the directory tree metadata
        tree_metadata = metadata[b'directory_tree'].decode('utf-8')
        tree_structure = ast.literal_eval(tree_metadata)  # Convert string back to dict

        # Build the directory tree from the full tree structure
        self.build_directory_tree_from_metadata(tree_structure)

    def add_node_to_tree(self, parent_item, node_id, tree_structure, merge):
        """
        Recursively adds nodes (directories) to the QTreeWidget based on the tree structure.
        """
        # Get the children of the current node from the tree structure
        if node_id in tree_structure:
            for child in tree_structure[node_id]:
                # Create a new tree item for each child
                child_item = QTreeWidgetItem(parent_item, [child['name']])
                
                # Debugging print statement
                print(f"Processing child: {child['name']} (ID: {child['id']})")
                
                # Recur to add children of this child node
                self.add_node_to_tree(child_item, child['id'], tree_structure, merge)

    def parse_metadata(self, metadata):
        """
        Parses the directory tree from the Parquet metadata.
        """
        # Decode and evaluate the directory tree from the metadata
        tree_structure = eval(metadata[b'directory_tree'].decode('utf-8'))
        
        # Print the tree structure for debugging
        print(f"Parsed tree structure: {tree_structure}")
        
        return tree_structure

    def build_directory_tree_from_metadata(self, tree_structure):
        """
        Rebuilds the directory tree from the metadata and displays it in the QTreeWidget.
        """
        self.dir_tree.clear()

        # Root ID based on the metadata structure
        root_id = 'f2355e9ac075b04cb2a9b6e419e1077638a700fec39fd1847a207d70d59a495c'
        print(f"Root ID: {root_id}")

        # Add the root directory
        root_node = QTreeWidgetItem(self.dir_tree, ["Root Directory"])

        # Add the children of the root directory
        if root_id in tree_structure:
            print(f"Adding children of {root_id}")
            self.add_node_to_tree(root_node, root_id, tree_structure, self.merge_checkbox.isChecked())

        self.dir_tree.expandAll()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ParquetDirRebuilderApp()
    window.show()
    sys.exit(app.exec())
