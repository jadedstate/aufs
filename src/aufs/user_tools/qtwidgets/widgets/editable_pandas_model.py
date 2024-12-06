# src/aufs/user_tools/editable_pandas_model.py

import pandas as pd
import json
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QMimeData
from PySide6.QtWidgets import QMessageBox, QComboBox, QTableView, QMenu, QAbstractItemView
import uuid  # To generate UUIDs

class EditablePandasModel(QAbstractTableModel):
    VALID_DTYPES = [ "object", "int64", "float64", "bool", "datetime64[ns]"]  # Re-added

    def __init__(self, dataframe: pd.DataFrame, value_options=None, editable=True, auto_fit_columns=False, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe if dataframe is not None else pd.DataFrame()
        self._editable = editable
        self.value_options = value_options if value_options is not None else {}
        self.auto_fit_columns = auto_fit_columns  # New flag for optional column auto-sizing
        
        # Precompute column widths only if auto_fit_columns is enabled
        if self.auto_fit_columns:
            self.column_widths = self.get_column_widths()
        else:
            self.column_widths = {}

    def get_column_widths(self):
        """Calculate and return optimal column widths."""
        if not self.auto_fit_columns:
            return {}

        column_widths = {}
        if not self._dataframe.empty:
            for column in range(self.columnCount()):
                # Get the column name
                column_name = self._dataframe.columns[column]

                # If column has dropdown values, only consider the first value (selected item)
                if column_name in self.value_options:
                    max_content_width = max(
                        len(str(value.split(", ")[0]))  # Only use the selected value (first item)
                        for value in self._dataframe[column_name]
                    )
                else:
                    # Default calculation for non-dropdown columns
                    max_content_width = max(
                        len(str(self._dataframe.iloc[row, column]))
                        for row in range(self.rowCount())
                    )

                # Include header width
                header_width = len(str(self._dataframe.columns[column]))
                optimal_width = max(max_content_width, header_width) * 8 + 10  # Scale and add padding
                column_widths[column] = optimal_width

        return column_widths

    def adjust_column_widths(self):
        """Recalculate column widths if auto_fit_columns is enabled."""
        if self.auto_fit_columns:
            self.column_widths = self.get_column_widths()

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False

        row = index.row()
        column = self._dataframe.columns[index.column()]

        # print(f"[setData] Attempting to update cell at row {row}, column '{column}' with value '{value}'")

        self._dataframe.iloc[row, index.column()] = value  # Keep the original logic

        # Debug current state of the DataFrame
        # print(f"[setData] DataFrame after update:\n{self._dataframe}")

        # Notify views that data has changed
        self.dataChanged.emit(QModelIndex(), QModelIndex(), [Qt.EditRole])
        return True

    def update_dataframe(self, new_dataframe: pd.DataFrame, view=None):
        """Updates the DataFrame and refreshes the model."""
        self.beginResetModel()
        self._dataframe = new_dataframe
        self._column_order = list(range(len(self._dataframe.columns)))  # Synchronize column order
        self.endResetModel()

        if view and isinstance(view, QTableView):
            self.apply_column_widths(view)

    def apply_column_widths(self, view):
        """
        Applies calculated column widths to the given QTableView if auto-fit is enabled.
        """
        if not self.auto_fit_columns:
            print("Auto-fit columns is disabled.")
            return

        if not view:
            print("Warning: No view provided for column resizing.")
            return

        column_widths = self.get_column_widths()
        for column, width in column_widths.items():
            print(f"Setting column {column} width to {width}.")
            view.setColumnWidth(column, width)

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

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            try:
                col = self._column_order[section] if self.dragNdrop else section
                return str(self._dataframe.columns[col])
            except IndexError:
                # Fallback in case of mismatch (debugging/logging can be added here)
                return str(self._dataframe.columns[section] if section < len(self._dataframe.columns) else "")
        return super().headerData(section, orientation, role)

    def get_dataframe(self):
        """Returns the current DataFrame being edited."""
        return self._dataframe

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
            self.dataChanged.emit(QModelIndex(), QModelIndex(), [Qt.EditRole])

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

    def add_column(self, column_name=None, dtype=None):
        """Add a new column to the DataFrame."""
        if column_name is None:
            column_name = f"Column {len(self._dataframe.columns)}"
        if dtype is None:
            dtype = 'object'

        # Add the new column with the specified data type
        self.layoutAboutToBeChanged.emit()

        self._dataframe[column_name] = pd.Series(dtype=dtype)

        # Update column order if drag-and-drop is enabled
        if self.dragNdrop:
            self._column_order.append(len(self._column_order))

        # Notify the view about the structure change
        self.layoutChanged.emit()
        self.dataChanged.emit(QModelIndex(), QModelIndex())  # Notify views

        # Optionally auto-fit column widths if enabled
        if self.auto_fit_columns:
            self.adjust_column_widths()

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
            self.dataChanged.emit(QModelIndex(), QModelIndex(), [Qt.EditRole])

    def add_row(self, row_data=None):
        """
        Adds a new row to the DataFrame.

        Args:
            row_data (list or dict, optional): Data for the new row.
                If None, fills with NaN. A dictionary should map column names to values.
        """
        # Emit layoutAboutToBeChanged signal before modifying the DataFrame
        self.layoutAboutToBeChanged.emit()

        if row_data is None:
            # Create a row filled with NaN if no data is provided
            row_data = {col: pd.NA for col in self._dataframe.columns}

        # Validate the data format
        if isinstance(row_data, dict):
            # Add the new row
            new_row = pd.DataFrame([row_data], columns=self._dataframe.columns)
            self._dataframe = pd.concat([self._dataframe, new_row], ignore_index=True)
        else:
            print("Invalid row_data format. Expected a dictionary.")

        # Emit layoutChanged signal after row addition
        self.layoutChanged.emit()
        self.dataChanged.emit(QModelIndex(), QModelIndex())  # Notify views

    def move_row(self, row_index, direction):
        """Moves the row at row_index up or down. Direction should be -1 (up) or 1 (down).
        Returns the new row index of the moved row."""

        self.layoutAboutToBeChanged.emit()

        if direction not in [-1, 1] or not (0 <= row_index < self.rowCount()):
            return None  # Invalid direction or index

        target_index = row_index + direction
        if not (0 <= target_index < self.rowCount()):
            return None  # Can't move out of bounds

        # Swap the rows
        self._dataframe.iloc[[row_index, target_index]] = self._dataframe.iloc[[target_index, row_index]].values
        self.dataChanged.emit(self.index(row_index, 0), self.index(row_index, self.columnCount() - 1))
        self.dataChanged.emit(self.index(target_index, 0), self.index(target_index, self.columnCount() - 1))

        # Emit layoutChanged signal after row addition
        self.layoutChanged.emit()
        self.dataChanged.emit(QModelIndex(), QModelIndex())  # Notify views

        # Return the new row index to update selection
        return target_index

    def move_column(self, column_index, direction):
        """Moves the column at column_index left or right. Direction should be -1 (left) or 1 (right).
        Returns the new column index of the moved column."""

        self.layoutAboutToBeChanged.emit()

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

        # Emit layoutChanged signal after row addition
        self.layoutChanged.emit()
        self.dataChanged.emit(QModelIndex(), QModelIndex())  # Notify views

        # Return the new column index to update selection
        return target_index

    def sort_column(self, column_index):
        """Sorts the column in a cycle: original -> ascending -> descending."""

        self.layoutAboutToBeChanged.emit()

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

        # Emit layoutChanged signal after row addition
        self.layoutChanged.emit()
        self.dataChanged.emit(QModelIndex(), QModelIndex())  # Notify views

    def supportedDropActions(self):
        """Allow move and copy actions during drop."""
        return Qt.CopyAction | Qt.MoveAction

    def dropMimeData(self, data, action, row, column, parent):
        """Handle MIME data dropped into the table."""
        if not data.hasText():
            return False

        try:
            import json
            payload = json.loads(data.text())
            dropped_text = payload.get("text", "N/A")

            # Use parent to infer drop location if row/column are invalid
            if row < 0 or column < 0:
                if parent and parent.isValid():
                    row = parent.row()
                    column = parent.column()
                    print(f"Inferring drop location from parent: row={row}, column={column}")
                else:
                    print("Unable to determine valid drop location.")
                    return False

            print(f"Dropped at row {row}, column {column} with data: {dropped_text}")

            # Add row if necessary
            if row >= len(self._dataframe):
                self._dataframe.loc[len(self._dataframe)] = [None] * len(self._dataframe.columns)

            # Add column if necessary
            if column >= len(self._dataframe.columns):
                self._dataframe[f"Column {len(self._dataframe.columns)}"] = None

            # Update the DataFrame
            self._dataframe.iloc[row, column] = dropped_text

            # Notify the view
            self.dataChanged.emit(
                self.index(row, column),
                self.index(row, column),
                [Qt.EditRole]
            )
            return True

        except Exception as e:
            print(f"Error in dropMimeData: {e}")
            return False

    def mimeTypes(self):
        """Define acceptable MIME types for dragging and dropping."""
        return ["text/plain"]

    def mimeData(self, indexes):
        """Package the selected data as MIME data."""
        if not indexes:
            return None
        
        # Collect the selected rows
        rows = sorted(set(index.row() for index in indexes))
        selected_data = self._dataframe.iloc[rows]
        
        # Convert selected rows to a CSV-like string
        mime_text = selected_data.to_csv(index=False, header=False).strip()
        
        # Package as MIME data
        mime_data = QMimeData()
        mime_data.setText(mime_text)
        return mime_data
    
    def flags(self, index):
        """Combine existing editable flags with drop support."""
        if not index.isValid():
            return Qt.NoItemFlags

        # Start with the default flags
        flags = super().flags(index)

        # Add editability if the model allows it
        if self._editable:
            flags |= Qt.ItemIsEditable

        # Add drop support
        flags |= Qt.ItemIsDropEnabled

        return flags


class EnhancedPandasModel(EditablePandasModel):
    def __init__(self, dataframe, value_options=None, editable=True,
                 auto_fit_columns=False, dragNdrop=False, ui_only=True, parent=None):
        super().__init__(dataframe, value_options, editable, auto_fit_columns, parent)
        self.dragNdrop = dragNdrop
        self.ui_only = ui_only
        self._column_order = list(range(len(self._dataframe.columns)))  # Initialize column order
        self._sort_states = {}
        self._original_index = self._dataframe.index.copy()  # Preserve the original row order
        self._original_dataframe = dataframe.copy()

    def sort_column(self, column_index):
        """Sorts the column in a cycle: original -> ascending -> descending."""
        print("using enhanced model sort")
        if not (0 <= column_index < self.columnCount()):
            return

        column_name = self._dataframe.columns[column_index]
        if not hasattr(self, '_sort_states'):
            self._sort_states = {}

        current_state = self._sort_states.get(column_name, None)

        if current_state is None:
            self._dataframe.sort_values(by=column_name, ascending=True, inplace=True, ignore_index=False)
            self._sort_states[column_name] = 'asc'
        elif current_state == 'asc':
            self._dataframe.sort_values(by=column_name, ascending=False, inplace=True, ignore_index=False)
            self._sort_states[column_name] = 'desc'
        else:
            self.reset_sort()
            self._sort_states[column_name] = None

        self.layoutChanged.emit()

    def sort_column_ascending(self, column_index):
        """Sort the column in ascending order."""
        if 0 <= column_index < self.columnCount():
            column_name = self._dataframe.columns[column_index]
            self._dataframe.sort_values(by=column_name, ascending=True, inplace=True)
            self._sort_states[column_name] = 'asc'
            self.layoutChanged.emit()

    def sort_column_descending(self, column_index):
        """Sort the column in descending order."""
        if 0 <= column_index < self.columnCount():
            column_name = self._dataframe.columns[column_index]
            self._dataframe.sort_values(by=column_name, ascending=False, inplace=True)
            self._sort_states[column_name] = 'desc'
            self.layoutChanged.emit()

    def reset_sort(self):
        """
        Resets the DataFrame's order to its original row index.
        """
        # print("PERFORMING RESET")
        # print(self._dataframe)
        self._dataframe = self._dataframe.sort_index().reset_index(drop=True)
        self.layoutChanged.emit()  # Notify the view of changes

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            col = self._column_order[index.column()] if self.dragNdrop else index.column()
            return str(self._dataframe.iloc[index.row(), col])
        return super().data(index, role)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            col = self._column_order[section] if self.dragNdrop else section
            return str(self._dataframe.columns[col])
        return super().headerData(section, orientation, role)

    def supportedDragActions(self):
        return Qt.MoveAction

    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeData(self, indexes):
        mime_data = QMimeData()
        if indexes:
            col = indexes[0].column()
            mime_data.setText(str(col))
        return mime_data

    def moveColumn(self, source_col, target_col):
        self.beginMoveColumns(QModelIndex(), source_col, source_col, QModelIndex(), target_col)
        col = self._column_order.pop(source_col)
        self._column_order.insert(target_col, col)
        self.endMoveColumns()

        if not self.ui_only:
            reordered_columns = [self._dataframe.columns[i] for i in self._column_order]
            self._dataframe = self._dataframe[reordered_columns]
        self.layoutChanged.emit()

class SortableTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Enable drag-and-drop for column reordering
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setDragEnabled(True)

        # Disable sorting on header clicks
        self.horizontalHeader().setSectionsClickable(False)

        # Enable header context menu
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.show_header_context_menu)

    def show_context_menu(self, position):
        """Context menu with explicit sort options."""
        index = self.indexAt(position)
        if index.isValid():
            column = index.column()
            menu = QMenu()
            menu.addAction("Sort Ascending", lambda: self.model().sort_column_ascending(column))
            menu.addAction("Sort Descending", lambda: self.model().sort_column_descending(column))
            menu.addAction("Reset Sort", lambda: self.model().reset_sort())
            menu.exec_(self.viewport().mapToGlobal(position))

    def show_header_context_menu(self, position):
        """Context menu with explicit sort options."""
        index = self.indexAt(position)
        if index.isValid():
            column = index.column()
            menu = QMenu()
            menu.addAction("Sort Ascending", lambda: self.model().sort_column_ascending(column))
            menu.addAction("Sort Descending", lambda: self.model().sort_column_descending(column))
            menu.addAction("Reset Sort", lambda: self.model().reset_sort())
            menu.exec_(self.viewport().mapToGlobal(position))

    def dropEvent(self, event):
        super().dropEvent(event)
        index = self.indexAt(event.pos())  # Get the index under the cursor
        if index.isValid():
            print(f"Dropped at row: {index.row()}, column: {index.column()}")
        else:
            print("Drop position invalid.")
