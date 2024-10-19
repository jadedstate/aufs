import pandas as pd
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import QMessageBox

class EditablePandasModel(QAbstractTableModel):
    # Class attribute for valid data types
    VALID_DTYPES = ["int64", "float64", "object", "bool", "datetime64[ns]"]

    def __init__(self, dataframe: pd.DataFrame, editable=True, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe if dataframe is not None else pd.DataFrame()  # Ensure it's not None
        self._editable = editable

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

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole or not self._editable:
            return False
        row = index.row()
        col = index.column()
        try:
            dtype = self._dataframe.dtypes[col]
            if dtype != object:
                value = dtype.type(value)  # Attempt to cast value to column's dtype
            self._dataframe.iloc[row, col] = value
            self.dataChanged.emit(index, index, [role])
            return True
        except ValueError:
            return False

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

    def update_dataframe(self, new_dataframe: pd.DataFrame):
        """Updates the DataFrame and refreshes the model."""
        self.beginResetModel()
        self._dataframe = new_dataframe
        self.endResetModel()

    def get_dataframe(self):
        """Returns the current DataFrame being edited."""
        return self._dataframe

    def get_valid_dtypes(self):
        """Returns the list of valid data types."""
        return self.VALID_DTYPES

    def add_column(self, column_name="New Column", column_data=None, dtype="object"):
        """Adds a new column with an optional data type."""
        if dtype not in self.VALID_DTYPES:
            raise ValueError(f"Invalid data type: {dtype}. Must be one of {self.VALID_DTYPES}.")

        self.beginInsertColumns(QModelIndex(), self.columnCount(), self.columnCount())
        if column_data is None:
            if dtype == "int64":
                column_data = [0] * self.rowCount()
            elif dtype == "float64":
                column_data = [0.0] * self.rowCount()
            else:
                column_data = [None] * self.rowCount()  # Default to None for object type
        self._dataframe[column_name] = pd.Series(column_data, dtype=dtype)
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
            # Conversion failed: Prompt to clear the data in the problematic column
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

        # Check current sort state of the column (store it in a dict)
        column_name = self._dataframe.columns[column_index]
        if not hasattr(self, '_sort_states'):
            self._sort_states = {}

        current_state = self._sort_states.get(column_name, None)

        if current_state is None:
            # Sort ascending
            self._dataframe.sort_values(by=column_name, ascending=True, inplace=True, ignore_index=True)
            self._sort_states[column_name] = 'asc'
        elif current_state == 'asc':
            # Sort descending
            self._dataframe.sort_values(by=column_name, ascending=False, inplace=True, ignore_index=True)
            self._sort_states[column_name] = 'desc'
        else:
            # Reset to original order
            self._dataframe = self._dataframe.sort_index(ignore_index=True)
            self._sort_states[column_name] = None

        # Notify the view to refresh
        self.layoutChanged.emit()
