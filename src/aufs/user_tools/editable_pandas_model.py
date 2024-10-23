import pandas as pd
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import QMessageBox
import uuid  # To generate UUIDs

class EditablePandasModel(QAbstractTableModel):
    VALID_DTYPES = ["int64", "float64", "object", "bool", "datetime64[ns]"]

    def __init__(self, dataframe: pd.DataFrame, value_options=None, editable=True, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe if dataframe is not None else pd.DataFrame()
        self._editable = editable
        self.value_options = value_options if value_options is not None else {}

    def rowCount(self, parent=QModelIndex()):
        return len(self._dataframe) if not parent.isValid() and not self._dataframe.empty else 0

    def columnCount(self, parent=QModelIndex()):
        return len(self._dataframe.columns) if not parent.isValid() and not self._dataframe.empty else 0

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self._dataframe.empty:
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            value = self._dataframe.iloc[index.row(), index.column()]
            return str(value)
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        flags = super().flags(index)
        if self._editable:
            flags |= Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])
            else:
                return str(section)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole or not self._editable:
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
        except (ValueError, TypeError) as e:
            print(f"Error updating data at ({row}, {col}): {e}")
            return False

    def update_dataframe(self, new_dataframe: pd.DataFrame):
        """Updates the DataFrame and refreshes the model."""
        self.beginResetModel()
        self._dataframe = new_dataframe
        self.endResetModel()

    def get_dataframe(self):
        """Returns the current DataFrame being edited."""
        return self._dataframe

    # --- Key Changes for Popup/Dropdown Editing ---
    
    def createEditor(self, parent, option, index):
        """Creates the appropriate editor based on the column."""
        column_name = self._dataframe.columns[index.column()]
        
        if column_name in self.value_options:
            # Create a QComboBox for predefined options
            combo_box = QComboBox(parent)
            combo_box.addItems(self.value_options[column_name])
            return combo_box

        # Fall back to the default editor for other columns
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        """Sets the editor data when the editor is displayed."""
        value = self._dataframe.iloc[index.row(), index.column()]
        
        if isinstance(editor, QComboBox):
            # Set the current value in the QComboBox
            current_index = editor.findText(str(value))
            if current_index >= 0:
                editor.setCurrentIndex(current_index)

        else:
            # Fall back to default behavior
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        """Saves the data from the editor back to the model."""
        if isinstance(editor, QComboBox):
            # Get the selected value from the QComboBox
            value = editor.currentText()
            self.setData(index, value, Qt.EditRole)
        else:
            # Fall back to default behavior
            super().setModelData(editor, model, index)

    def show_value_selector(self, index, column_name):
        """Show a dialog with predefined options for a given column."""
        row = index.row()
        current_value = self._dataframe.iloc[row, index.column()]

        # Create the dialog with a list of options
        dialog = QDialog()
        dialog.setWindowTitle(f"Select value for {column_name}")
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()

        # Populate the list of options
        options_list = QListWidget()
        for value in self.value_options[column_name]:
            item = QListWidgetItem(value)
            if value == current_value:
                item.setSelected(True)
            options_list.addItem(item)

        layout.addWidget(QLabel(f"Select value for column '{column_name}'"))
        layout.addWidget(options_list)

        # Add an "OK" button
        ok_button = QPushButton("OK")
        layout.addWidget(ok_button)

        def set_value():
            selected_items = options_list.selectedItems()
            if selected_items:
                selected_value = selected_items[0].text()
                # Set the new value in the DataFrame
                self.setData(index, selected_value, Qt.EditRole)
            dialog.close()

        ok_button.clicked.connect(set_value)
        
        # Show the dialog
        dialog.setLayout(layout)
        dialog.exec_()

    def clear_selection(self, selection):
        """Clears the data in the selected cells."""
        for index in selection:
            row = index.row()
            col = index.column()
            self._dataframe.iloc[row, col] = None  # Set the selected cell to None
            self.dataChanged.emit(index, index, [Qt.EditRole])

    def generate_id_df(self, row, col):
        """
        Generates an id_df for the specific cell at (row, col) in the DataFrame.
        The id_df contains a 'uuid', 'data_type', 'path to data', and 'cell_coords'.
        """
        cell_data = self._dataframe.iloc[row, col]
        id_rows = []  # Collect rows for id_df here
        
        # Recurse through nested structures to generate id_df entries
        def recurse(data, path_str):
            unique_id = str(uuid.uuid4())  # Generate a UUID for this data entry
            data_type = type(data).__name__

            print(f"Generating ID for path: {path_str}, Type: {data_type}, ID: {unique_id}")

            id_rows.append({
                "uuid": unique_id, 
                "data_type": data_type, 
                "path": path_str, 
                "cell_coords": (row, col)  # Store the cell's row and column
            })
            
            # If it's a list or dict, recurse further
            if isinstance(data, dict):
                for key, value in data.items():
                    recurse(value, f"{path_str}[{repr(key)}]")
            elif isinstance(data, list):
                for index, value in enumerate(data):
                    recurse(value, f"{path_str}[{index}]")
        
        # Start with the root element (top-level cell data)
        recurse(cell_data, "(root)")

        # Convert collected rows into a DataFrame
        self.id_df = pd.DataFrame(id_rows)
        return self.id_df

    def get_data_by_uuid(self, node_uuid):
        """
        Returns the data from the dataframe corresponding to the given UUID.
        """
        if self.id_df is None or self.id_df.empty:
            return None
        
        # Find the row in id_df matching the UUID
        row = self.id_df[self.id_df['uuid'] == node_uuid]
        if row.empty:
            return None

        # Extract the coordinates and path from the id_df
        cell_coords = row.iloc[0]['cell_coords']
        path = row.iloc[0]['path']
        
        # Retrieve the data from the DataFrame
        data = self._dataframe.iloc[cell_coords]

        # If the path is "(root)", return the top-level data
        if path == "(root)":
            return data

        # Remove "(root)" from the start of the path if it exists
        path = path.replace("(root)", "", 1).strip()

        # Traverse the path to retrieve the nested data
        if path:
            for step in path.split("]["):  # Split on ][ and manually adjust the path parsing
                step = step.strip("[]")  # Remove surrounding brackets
                if isinstance(data, (dict, list)):
                    key = eval(step)  # Evaluate step, e.g., [0], ['key']
                    data = data[key]
                else:
                    return None  # Can't traverse further if data is not list/dict

        return data

    def update_data_by_uuid(self, node_uuid, new_value):
        """
        Updates the data in the dataframe corresponding to the given UUID.
        """
        if self.id_df is None or self.id_df.empty:
            return False

        # Find the row in id_df matching the UUID
        row = self.id_df[self.id_df['uuid'] == node_uuid]
        if row.empty:
            return False

        # Extract the coordinates and path from the id_df
        cell_coords = row.iloc[0]['cell_coords']
        path = row.iloc[0]['path']
        
        # Retrieve the data from the DataFrame
        data = self._dataframe.iloc[cell_coords]
        
        # If the path is "(root)", we are dealing with the top-level data in the cell
        if path == "(root)":
            self._dataframe.iloc[cell_coords] = new_value
        else:
            # Remove "(root)" from the path
            path = path.replace("(root)", "", 1).strip()

            # Traverse the path to the parent of the target value
            parent = data
            if path:
                path_steps = path.split("][")  # Split on ][ and manually adjust the path parsing
                for step in path_steps[:-1]:  # Traverse all but the last step
                    step = step.strip("[]")  # Remove surrounding brackets
                    key = eval(step)
                    parent = parent[key]

                # Set the new value at the final step
                final_step = eval(path_steps[-1].strip("[]"))  # Strip and evaluate the final step
                parent[final_step] = new_value

        # Emit data changed signal
        self.dataChanged.emit(self.index(cell_coords[0], cell_coords[1]), self.index(cell_coords[0], cell_coords[1]))
        return True

    def rebuild_id_df(self):
        """
        Rebuild the entire id_df based on the current state of the DataFrame.
        This should be called after any structural modification to the DataFrame.
        """
        self.id_df = pd.DataFrame()  # Clear the existing id_df

        # Loop over all cells in the DataFrame and generate ids
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                self.generate_id_df(row, col)  # Rebuild id_df for each cell

    def get_valid_dtypes(self):
        """Returns the list of valid data types."""
        return self.VALID_DTYPES

    def delete_rows(self, selected_rows):
        """Deletes multiple rows based on selected rows."""
        if not selected_rows:
            return

        # Emit layoutAboutToBeChanged signal before modifying the DataFrame
        self.layoutAboutToBeChanged.emit()

        # Sort selected rows in reverse order to avoid index shift issues
        selected_rows.sort(reverse=True)

        for row_index in selected_rows:
            if 0 <= row_index < self.rowCount():
                self.beginRemoveRows(QModelIndex(), row_index, row_index)
                # Remove the row from the dataframe and reset the index
                self._dataframe = self._dataframe.drop(index=row_index).reset_index(drop=True)
                self.endRemoveRows()

        # Emit layoutChanged signal after rows are removed to update the view
        self.layoutChanged.emit()
        self.dataChanged.emit(QModelIndex(), QModelIndex())  # Emit signal to notify views

    def delete_columns(self, selected_columns):
        """Deletes multiple columns based on selected columns."""
        if not selected_columns:
            return

        # Emit layoutAboutToBeChanged signal before modifying the DataFrame
        self.layoutAboutToBeChanged.emit()

        # Sort the columns to delete in descending order (to avoid index shift problems)
        selected_columns.sort(reverse=True)

        for col_index in selected_columns:
            if 0 <= col_index < self.columnCount():
                self.beginRemoveColumns(QModelIndex(), col_index, col_index)
                # Drop the column from the dataframe
                self._dataframe.drop(self._dataframe.columns[col_index], axis=1, inplace=True)
                self.endRemoveColumns()

        # Emit layoutChanged signal after columns are removed to update the view
        self.layoutChanged.emit()
        self.dataChanged.emit(QModelIndex(), QModelIndex())  # Emit signal to notify views

    def add_column(self, column_name="New Column", column_data=None, dtype="object"):
        """Adds a new column with an optional data type."""
        if dtype not in self.VALID_DTYPES:
            raise ValueError(f"Invalid data type: {dtype}. Must be one of {self.VALID_DTYPES}.")

        # If the DataFrame is empty (no rows), initialize the column with one row
        if self.rowCount() == 0:
            # If no rows exist, initialize a default row (e.g., None for object type)
            if dtype == "int64":
                column_data = [0]  # Default to 0 for integer type
            elif dtype == "float64":
                column_data = [0.0]  # Default to 0.0 for float type
            else:
                column_data = [None]  # Default to None for object type

        else:
            # If rows exist, initialize the column with data matching the row count
            if column_data is None:
                if dtype == "int64":
                    column_data = [0] * self.rowCount()
                elif dtype == "float64":
                    column_data = [0.0] * self.rowCount()
                else:
                    column_data = [None] * self.rowCount()

        # Begin inserting the new column
        self.beginInsertColumns(QModelIndex(), self.columnCount(), self.columnCount())

        # Add the new column to the DataFrame
        self._dataframe[column_name] = pd.Series(column_data, dtype=dtype)

        # End the column insertion
        self.endInsertColumns()

    def set_column_dtype(self, column_index, new_dtype):
        """Attempts to change the data type of an existing column. If conversion fails, offers to clear problematic data."""
        if new_dtype not in self.VALID_DTYPES:
            raise ValueError(f"Invalid data type: {new_dtype}. Must be one of {self.VALID_DTYPES}.")

        if not (0 <= column_index < self.columnCount()):
            return  # Invalid column index

        column_name = self._dataframe.columns[column_index]

        try:
            # Attempt to convert the column to the new dtype
            self._dataframe[column_name] = self._dataframe[column_name].astype(new_dtype)

            # Notify the view of the data type change
            self.dataChanged.emit(
                self.index(0, column_index), 
                self.index(self.rowCount() - 1, column_index)
            )
            self.headerDataChanged.emit(Qt.Horizontal, column_index, column_index)

        except ValueError as e:
            clear = QMessageBox.question(
                None, "Type Conversion Error",
                f"Cannot convert column {column_name} to {new_dtype} due to invalid data.\n"
                "Would you like to clear the column's data and continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            if clear == QMessageBox.Yes:
                self.clear_column_data(column_index)

    def clear_column_data(self, column_index):
        """Clears the data in the specified column by setting all values to None."""
        if not (0 <= column_index < self.columnCount()):
            return  # Invalid column index

        column_name = self._dataframe.columns[column_index]
        self._dataframe[column_name] = [None] * self.rowCount()

        # Notify view that the data has changed
        self.dataChanged.emit(
            self.index(0, column_index), 
            self.index(self.rowCount() - 1, column_index)
        )

    def clear_selection(self, selection):
        """Clears the data in the selected cells."""
        for index in selection:
            row = index.row()
            col = index.column()
            self._dataframe.iloc[row, col] = None  # Set the selected cell to None
            self.dataChanged.emit(index, index, [Qt.EditRole])

    def add_row(self, row_data=None):
        """Adds a new row at the bottom. If row_data is provided, it should be a list or dict."""
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        if row_data is None:
            row_data = [None] * self.columnCount()
        new_row = pd.DataFrame([row_data], columns=self._dataframe.columns)
        self._dataframe = pd.concat([self._dataframe, new_row], ignore_index=True)
        self.endInsertRows()

    def move_row(self, row_index, direction):
        """Moves the row at row_index up or down. Direction should be -1 (up) or 1 (down).
        Returns the new row index of the moved row."""
        if direction not in [-1, 1] or not (0 <= row_index < self.rowCount()):
            return None  # Invalid direction or index

        target_index = row_index + direction
        if not (0 <= target_index < self.rowCount()):
            return None  # Can't move out of bounds

        # Swap the rows
        self._dataframe.iloc[[row_index, target_index]] = self._dataframe.iloc[[target_index, row_index]].values
        self.dataChanged.emit(self.index(row_index, 0), self.index(row_index, self.columnCount() - 1))
        self.dataChanged.emit(self.index(target_index, 0), self.index(target_index, self.columnCount() - 1))

        # Return the new row index to update selection
        return target_index

    def move_column(self, column_index, direction):
        """Moves the column at column_index left or right. Direction should be -1 (left) or 1 (right).
        Returns the new column index of the moved column."""
        if direction not in [-1, 1] or not (0 <= column_index < self.columnCount()):
            return None  # Invalid direction or index

        target_index = column_index + direction
        if not (0 <= target_index < self.columnCount()):
            return None  # Can't move out of bounds

        # Swap the columns
        columns = self._dataframe.columns.tolist()
        columns[column_index], columns[target_index] = columns[target_index], columns[column_index]
        self._dataframe = self._dataframe[columns]
        self.headerDataChanged.emit(Qt.Horizontal, min(column_index, target_index), max(column_index, target_index))
        self.layoutChanged.emit()  # Notify view to update

        # Return the new column index to update selection
        return target_index

    def sort_column(self, column_index):
        """Sorts the column in a cycle: original -> ascending -> descending."""
        if not (0 <= column_index < self.columnCount()):
            return

        column_name = self._dataframe.columns[column_index]
        if not hasattr(self, '_sort_states'):
            self._sort_states = {}

        current_state = self._sort_states.get(column_name, None)

        if current_state is None:
            self._dataframe.sort_values(by=column_name, ascending=True, inplace=True, ignore_index=True)
            self._sort_states[column_name] = 'asc'
        elif current_state == 'asc':
            self._dataframe.sort_values(by=column_name, ascending=False, inplace=True, ignore_index=True)
            self._sort_states[column_name] = 'desc'
        else:
            self._dataframe = self._dataframe.sort_index(ignore_index=True)
            self._sort_states[column_name] = None

        self.layoutChanged.emit()
