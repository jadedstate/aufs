import os
import pandas as pd
import pyarrow as pa
from PySide6.QtWidgets import (
    QFileDialog, QDialog, QVBoxLayout, QTableView, QPushButton, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
import difflib

class EditablePandasModel(QAbstractTableModel):
    def __init__(self, dataframe: pd.DataFrame, schema: pa.Schema, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe
        self.schema = schema

    def rowCount(self, parent=QModelIndex()):
        return len(self._dataframe) if not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()):
        return len(self._dataframe.columns) if not parent.isValid() else 0

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            value = self._dataframe.iloc[index.row(), index.column()]
            return str(value)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        row = index.row()
        col = index.column()
        try:
            dtype = self._dataframe.dtypes[col]
            if dtype != object:
                value = dtype.type(value)
            self._dataframe.iloc[row, col] = value
            self.dataChanged.emit(index, index, [role])
            return True
        except ValueError:
            return False

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return super().flags(index) | Qt.ItemIsEditable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])
            else:
                return str(section)
        return None

class SourceDestinationLinkingDialog(QDialog):
    def __init__(self, package_full_df, template_schema, parent=None):
        super().__init__(parent)
        self.package_full_df = package_full_df
        self.template_schema = template_schema

        # Ensure the DEST column is of type 'object' (string)
        if 'DEST' not in self.package_full_df.columns:
            self.package_full_df['DEST'] = None
        else:
            self.package_full_df['DEST'] = self.package_full_df['DEST'].astype(object)

        self.setWindowTitle("Source-Destination Linking")
        self.setGeometry(100, 100, 1200, 600)

        # Main layout
        layout = QVBoxLayout(self)

        # Filter/search bar
        self.filter_input = QLineEdit(self)
        self.filter_input.setPlaceholderText("Filter files...")
        layout.addWidget(self.filter_input)

        # Table view
        self.table_view = QTableView(self)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.model = EditablePandasModel(self.package_full_df, None, self)
        self.table_view.setModel(self.model)
        layout.addWidget(self.table_view)

        # Auto-assign DEST button
        self.auto_assign_button = QPushButton("Auto-assign DEST", self)
        self.auto_assign_button.clicked.connect(self.auto_assign_dest)
        layout.addWidget(self.auto_assign_button)

        # Edit Selected Rows button (for manual intervention)
        self.edit_selected_button = QPushButton("Edit Selected Rows", self)
        self.edit_selected_button.clicked.connect(self.edit_selected_rows)
        layout.addWidget(self.edit_selected_button)

        # Save and Load buttons
        self.save_button = QPushButton("Save", self)
        self.save_button.clicked.connect(self.save_dataframe)
        layout.addWidget(self.save_button)

        self.load_button = QPushButton("Load", self)
        self.load_button.clicked.connect(self.load_dataframe)
        layout.addWidget(self.load_button)

        # Close button
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.close_application)
        layout.addWidget(close_button)

        # Initial setup for filtering
        self.filter_input.textChanged.connect(self.apply_filter)

    def apply_filter(self, filter_text):
        """Applies a filter based on the input text."""
        filter_text = filter_text.lower()
        if filter_text:
            filtered_df = self.package_full_df[self.package_full_df['SRC'].str.contains(filter_text, case=False)]
        else:
            filtered_df = self.package_full_df  # Reset to original when filter is cleared
        self.model._dataframe = filtered_df
        self.model.layoutChanged.emit()

    def match_file_extension(self, src_file):
        """
        Matches file extension by splitting the filename on '.' and taking the last element.
        Handles fuzzy matches like jpg/jpeg, tif/tiff.
        """
        # Split the filename and get the last element as the extension
        file_extension = '.' + src_file.split('.')[-1].lower()  # Get the extension after the last period

        # Extension mappings for fuzzy matches
        extension_mapping = {
            ".jpg": [".jpeg", ".jpg"],
            ".jpeg": [".jpg", ".jpeg"],
            ".tif": [".tiff", ".tif"],
            ".tiff": [".tif", ".tiff"]
            # Add more extensions as needed
        }

        # Check if the file_extension has a fuzzy match
        for ext, variations in extension_mapping.items():
            if file_extension in variations:
                return ext  # Return the normalized extension

        # If no fuzzy match, return the original extension
        return file_extension

    def auto_assign_dest(self):
        """
        Automatically assign DEST and populate DESTOPTIONS column based on file extensions and matching schema leaves.
        """
        for idx, row in self.package_full_df.iterrows():
            src_file = row['SRC']

            # Handling image sequences (e.g., file.%04d.jpg)
            if '%' in src_file:
                file_extension = '.' + src_file.split('.')[-1].lower()  # Get file extension
            else:
                file_extension = self.match_file_extension(src_file)

            possible_dests = []

            # Debug print statements for troubleshooting
            print(f"Processing SRC: {src_file}, File Extension: {file_extension}")

            # Match template schema leaves (files) based on the matched extension
            for dest in self.template_schema:
                if file_extension in os.path.basename(dest).lower():  # Check if extension matches
                    possible_dests.append(dest)

            # Update DESTOPTIONS with only relevant matching destinations
            if possible_dests:
                self.package_full_df.at[idx, 'DESTOPTIONS'] = ', '.join(possible_dests)
            else:
                self.package_full_df.at[idx, 'DESTOPTIONS'] = None  # Clear if no match

            # Auto-assign the first match if only one match exists
            if len(possible_dests) == 1:
                self.package_full_df.at[idx, 'DEST'] = possible_dests[0]

        # Update the table view to reflect changes
        self.model.layoutChanged.emit()

    def save_dataframe(self):
        """Save the package_full_df to a CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        if file_path:
            try:
                self.package_full_df.to_csv(file_path, index=False)
                QMessageBox.information(self, "Save Successful", "Data saved successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Save Failed", f"An error occurred while saving: {e}")

    def load_dataframe(self):
        """Load a CSV file into package_full_df."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv)")
        if file_path:
            try:
                loaded_df = pd.read_csv(file_path)
                
                # Replace the entire dataframe with the newly loaded data
                self.package_full_df = loaded_df
                
                # Create a new model to reflect the changes
                self.model = EditablePandasModel(self.package_full_df, None, self)
                self.table_view.setModel(self.model)

                # Refresh the table view
                self.model.layoutChanged.emit()
                QMessageBox.information(self, "Load Successful", "Data loaded successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Load Failed", f"An error occurred while loading: {e}")

    def edit_selected_rows(self):
        """
        Open a popup to let the user manually resolve the DEST column for selected rows.
        Each row will show options stored in the DESTOPTIONS column.
        """
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if not selected_indexes:
            return  # No rows selected

        # Collect selected rows
        selected_rows_df = self.package_full_df.iloc[[index.row() for index in selected_indexes]].copy()

        # Prepare the popup dialog for manual resolution
        for idx, row in selected_rows_df.iterrows():
            dest_options = row['DESTOPTIONS']
            if dest_options is not None:
                dest_options_list = dest_options.split(", ")
            else:
                dest_options_list = []  # Empty list if no options exist

            # Open dialog even if no DESTOPTIONS (allow manual input)
            dialog = SourceDestinationLinkingDialogForSelection(row, dest_options_list)
            if dialog.exec_() == QDialog.Accepted:
                # Retrieve the selected DEST and update the main DataFrame
                selected_dest = dialog.get_selected_dest()
                self.package_full_df.at[row.name, 'DEST'] = selected_dest

        # Refresh the table view
        self.model.layoutChanged.emit()

    def close_application(self):
        """Closes the app and ensures that the application fully quits."""
        self.close()
class SourceDestinationLinkingDialogForSelection(QDialog):
    def __init__(self, selected_row, dest_options_list, parent=None):
        """
        Initialize the dialog for selecting or manually inputting DEST.
        - `selected_row`: The row from the main DataFrame for which the user is selecting the DEST.
        - `dest_options_list`: List of possible DEST options (can be empty).
        """
        super().__init__(parent)
        self.selected_row = selected_row
        self.dest_options_list = dest_options_list

        # Set the window title to include the SRC value
        src_value = self.selected_row['SRC']  # Assuming 'SRC' is in the row
        self.setWindowTitle(f"Select or Edit DEST for {src_value}")
        self.setGeometry(300, 200, 1200, 500)

        # Main layout
        layout = QVBoxLayout(self)

        # Table view to display the DESTOPTIONS if available
        exploded_df = pd.DataFrame({"DESTOPTIONS": self.dest_options_list or [""]})
        self.model = EditablePandasModel(exploded_df, None, self)

        self.table_view = QTableView(self)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setModel(self.model)
        layout.addWidget(self.table_view)

        # Manual input option, available at all times
        self.manual_input = QLineEdit(self)
        self.manual_input.setPlaceholderText("Enter or edit DEST manually...")
        layout.addWidget(self.manual_input)

        # Select button
        select_button = QPushButton("Select", self)
        select_button.clicked.connect(self.select_dest)
        layout.addWidget(select_button)

        # Close button
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.reject)
        layout.addWidget(close_button)

    def select_dest(self):
        """
        Confirm the selected or manually entered DEST option and close the dialog.
        """
        # Check if the user selected a row from the table or manually entered a value
        selected_row = self.table_view.selectionModel().currentIndex().row()
        manual_dest = self.manual_input.text().strip()

        if selected_row >= 0 and not manual_dest:
            self.selected_dest = self.dest_options_list[selected_row]  # Use selected option from the table
        elif manual_dest:
            self.selected_dest = manual_dest  # Use manually entered value
        else:
            print("No valid DEST selected or entered.")
            return

        self.accept()  # Close dialog with Accepted status

    def get_selected_dest(self):
        """
        Returns the selected or manually entered DEST value from the dialog.
        """
        return self.selected_dest

    def get_updated_dataframe(self):
        """Return the DataFrame with manually updated DEST rows."""
        return self.selected_row_df

    def save_selection(self):
        """
        Saves the manually selected DEST options and closes the dialog.
        """
        # Process the user's choice and update the main DataFrame (selected_rows_df)
        self.accept()  # Close the dialog with an accepted status

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        row = index.row()
        col = index.column()
        try:
            dtype = self._dataframe.dtypes[col]
            if dtype != object:
                value = dtype.type(value)
            self._dataframe.iloc[row, col] = value
            self.dataChanged.emit(index, index, [role])
            return True
        except ValueError:
            return False
