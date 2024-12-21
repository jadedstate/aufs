import os
import sys
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QCheckBox, QLabel
)
from PySide6.QtCore import Qt

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.deep_editor import DeepEditor
from contextlib import contextmanager

class DataProvisioningWidget(QWidget):
    def __init__(self, input_df, root_package_path, parent=None):
        super().__init__(parent)
        self.root_package_path = root_package_path
        self.input_df = input_df.copy()  # Copy the input DataFrame
        self.working_files_df = input_df.copy()  # Main DataFrame for preview and processing
        self.working_seqs_df = None  # Temporary DataFrame for sequence rows
        self.editor_instance = None  # Keep track of the active DeepEditor instance
        self.init_ui()

    def init_ui(self):
        self.resize(3000, 900)
        layout = QVBoxLayout()

        layout.addStretch()
        # Display root package path
        self.label = QLabel(f"Root Package Path: {self.root_package_path}")
        layout.addWidget(self.label)

        # Checkbox to toggle display mode
        self.display_checkbox = QCheckBox("Display expanded seqs")
        self.display_checkbox.setChecked(False)  # Default to unexpanded view
        self.display_checkbox.stateChanged.connect(self.preview_data)
        layout.addWidget(self.display_checkbox)

        # Button to separate sequences
        self.separate_button = QPushButton("Separate Sequences")
        self.separate_button.clicked.connect(self.separate_sequences)
        # layout.addWidget(self.separate_button)

        # Button to preview data
        self.preview_button = QPushButton("Preview and Edit Data")
        self.preview_button.clicked.connect(self.preview_data)
        # layout.addWidget(self.preview_button)

        # Button to process data
        self.process_button = QPushButton("Process Data")
        self.process_button.clicked.connect(self.process_data)
        layout.addWidget(self.process_button)

        self.setLayout(layout)
        self.separate_sequences()

    def preview_data(self):
        """
        Display data using DeepEditor based on the checkbox state.
        """
        if self.editor_instance:
            # Close the existing editor instance before creating a new one
            self.editor_instance.close()
            self.editor_instance = None

        if self.display_checkbox.isChecked():
            # Use expanded view
            input_dataframe = self.working_files_df
        else:
            # Use unexpanded view and transform paths
            input_dataframe = self.transform_paths(self.input_df[["FILE", "PROVISIONEDLINK"]])

        if input_dataframe.empty:
            raise ValueError("No data to preview.")

        # Show the DeepEditor with the selected DataFrame
        self.editor_instance = DeepEditor(dataframe_input=input_dataframe, parent=self)
        self.editor_instance.setWindowTitle("Preview and Edit Data")
        self.editor_instance.show()

    def separate_sequences(self):
        """
        Separate sequence rows into working_seqs_df, and retain single-file rows in working_files_df.
        """
        seq_mask = self.working_files_df["FIRSTFRAME"].notna()
        self.working_seqs_df = self.working_files_df[seq_mask].copy()
        self.working_files_df = self.working_files_df[~seq_mask].reset_index(drop=True)

        # Expand sequences into working_files_df for processing
        self.expand_sequences()

        # Transform paths to ensure consistency
        self.working_files_df = self.transform_paths(self.working_files_df)

        # Update display after processing
        self.preview_data()

    def expand_sequences(self):
        """
        Expand each sequence row in working_seqs_df into individual rows in working_files_df.
        """
        if self.working_seqs_df is None or self.working_seqs_df.empty:
            print("No sequences to expand.")
            return

        expanded_data = []

        for _, row in self.working_seqs_df.iterrows():
            source = row["FILE"]
            destination = row["PROVISIONEDLINK"]
            padding = int(row["PADDING"])
            first_frame = int(row["FIRSTFRAME"])
            last_frame = int(row["LASTFRAME"])

            for frame in range(first_frame, last_frame + 1):
                frame_str = f"{frame:0{padding}d}"
                expanded_data.append({
                    "type": "sequence",
                    "FILE": source.replace("%0{}d".format(padding), frame_str),
                    "PROVISIONEDLINK": destination.replace("%0{}d".format(padding), frame_str),
                    "frame": frame,
                })

        expanded_df = pd.DataFrame(expanded_data)
        self.working_files_df = pd.concat([self.working_files_df, expanded_df], ignore_index=True)

    def transform_paths(self, df, source_col="FILE", destination_col="PROVISIONEDLINK"):
        """
        Transform paths in the given DataFrame relative to self.root_package_path.
        """
        if df is None or df.empty:
            raise ValueError("Input DataFrame is empty or not initialized.")

        transformed_rows = []

        for _, row in df.iterrows():
            source_abs = row[source_col]

            # Transform the destination path to be relative to self.root_package_path
            destination_abs = os.path.join(self.root_package_path, row[destination_col])
            destination_rel = os.path.relpath(destination_abs, self.root_package_path)

            # Add transformed values to a new row
            transformed_rows.append({
                source_col: source_abs,
                destination_col: destination_rel,  # Relative to root_package_path
            })

        return pd.DataFrame(transformed_rows, columns=[source_col, destination_col])

    def process_data(self):
        """
        Transform paths and process the data directly from working_files_df.
        """
        for _, row in self.working_files_df.iterrows():
            source = row["FILE"]
            destination = row["PROVISIONEDLINK"]

            # print(f"Processing: {source} -> {destination}")
            self.create_relative_symlink(source, destination)

    def create_relative_symlink(self, source, destination):
        """
        Create a symlink from the absolute source to the relative destination, anchored to self.root_package_path.
        """
        if not os.path.exists(source):
            print(f"Warning: Source does not exist: {source}")
            return

        # Switch to self.root_package_path as the working directory
        with self.change_working_directory(self.root_package_path):
            destination_dir = os.path.dirname(destination)
            os.makedirs(destination_dir, exist_ok=True)  # Ensure the destination directory exists

            try:
                os.symlink(source, destination)
                print(f"Created symlink: {source} -> {destination}")
            except OSError as e:
                print(f"Failed to create symlink: {e}")

    @contextmanager
    def change_working_directory(self, directory):
        """
        Context manager to temporarily change the working directory.
        """
        original_directory = os.getcwd()
        try:
            os.chdir(directory)
            yield
        finally:
            os.chdir(original_directory)
