# src\lib\qtwidgets\widgets\custom_table_view6.py

import pandas as pd
from PySide6.QtWidgets import QTableView, QApplication, QHeaderView, QFileDialog, QMessageBox, QMenu, QDialog, QLineEdit, QVBoxLayout, QPushButton
from PySide6.QtCore import QModelIndex, Qt, QAbstractTableModel
from PySide6.QtGui import QKeySequence, QClipboard, QShortcut, QMouseEvent, QKeyEvent
from natsort import natsorted, natsort_keygen

from PySide6.QtWidgets import QHeaderView, QLineEdit, QStyle
from PySide6.QtCore import Qt, QRect, QSortFilterProxyModel

class EnhancedTableViewLite(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeader(EditableHeaderViewLite(Qt.Horizontal, self))
        self.setupTableView()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            self.deleteSelectedItems()
        else:
            super().keyPressEvent(event)

    def setupTableView(self):
        self.setEditTriggers(QTableView.DoubleClicked | QTableView.EditKeyPressed)
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectItems)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.horizontalHeader().setSectionsMovable(True)
        self.setClipboardCopySupport()
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.headerContextMenu)
        self.horizontalHeader().setSectionsClickable(True)
        editCellShortcut = QShortcut(QKeySequence(Qt.Key_F2), self)
        editCellShortcut.activated.connect(self.editSelectedCell)
        addRowShortcut = QShortcut(QKeySequence("Ctrl+R"), self)  # Example: Use Ctrl+N to add a new row
        addRowShortcut.activated.connect(self.addRow)
        duplicateRowShortcut = QShortcut(QKeySequence("Shift+Ctrl+R"), self)
        duplicateRowShortcut.activated.connect(self.duplicateSelectedRow)
        addColumnShortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        addColumnShortcut.activated.connect(self.addColumn)
        deleteShortcut = QShortcut(QKeySequence(Qt.Key_Backspace), self)
        deleteShortcut.activated.connect(self.deleteSelectedItems)
      
    def deleteSelectedItems(self):
        # Check for column selection
        selectedColumns = self.selectionModel().selectedColumns()
        if selectedColumns:
            for columnIndex in sorted(set(index.column() for index in selectedColumns), reverse=True):
                realIndex = self.model().mapToSource(self.model().index(0, columnIndex)).column()
                self.model().deleteColumn(realIndex)
        else:
            selectedIndexes = self.selectionModel().selectedRows()
            rows = sorted(set(self.model().mapToSource(index).row() for index in selectedIndexes), reverse=True)
            for row in rows:
                self.model().removeRow(row)
            self.model().invalidate()  # Refresh the proxy view

    def addColumn(self):
        try:
            if self.model():
                self.model().beginInsertColumns(QModelIndex(), self.model().columnCount(), self.model().columnCount())
                self.model().addColumn()
                self.model().endInsertColumns()
                self.resizeColumnsToContents()
        except Exception as e:
            print(f"Error adding column: {e}")  # Consider using a logging framework or QMessageBox for GUI feedback

    def duplicateSelectedRow(self):
        indexes = self.selectionModel().selectedRows()
        if indexes:
            rowIndex = indexes[0].row()
            self.model().duplicateRow(rowIndex)

    def addRow(self):
        if self.model():
            self.model().addRow()
            self.model().invalidate()  # Refresh the proxy view
            self.scrollToBottom()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        index = self.indexAt(event.pos())
        if index.isValid():
            self.edit(index)  # Initiates in-place editing
        else:
            super().mouseDoubleClickEvent(event)

    def editSelectedCell(self):
        index = self.currentIndex()
        if index.isValid():
            self.editCellDialog(index)

    def editCellDialog(self, index):
        dialog = QDialog(self)
        layout = QVBoxLayout(dialog)
        
        lineEdit = QLineEdit(dialog)
        current_value = self.model().data(index, Qt.DisplayRole)
        lineEdit.setText(current_value)
        layout.addWidget(lineEdit)
        
        # Adjust QLineEdit's width to fit its content
        metrics = lineEdit.fontMetrics()
        textWidth = metrics.boundingRect(lineEdit.text()).width()
        padding = 20  # Add some padding to the calculated text width
        minWidth = max(200, textWidth + padding)  # Ensure a minimum width for the dialog
        lineEdit.setMinimumWidth(minWidth)
        
        button = QPushButton("Update", dialog)
        update_action = lambda: [self.updateCellData(index, lineEdit.text()), dialog.close()]
        button.clicked.connect(update_action)
        layout.addWidget(button)
        
        # Close dialog on Enter press in QLineEdit
        lineEdit.returnPressed.connect(update_action)
        
        # Optionally, adjust the dialog's size to better fit the content
        dialog.adjustSize()
        
        dialog.setWindowTitle("Edit Cell")
        dialog.exec_()

    def updateCellData(self, index, value):
        if index.isValid():
            self.model().setData(index, value, Qt.EditRole)

    def setClipboardCopySupport(self):
        shortcut = QShortcut(QKeySequence.Copy, self)
        shortcut.activated.connect(self.copySelectionToClipboard)

    def copySelectionToClipboard(self):
        selection = self.selectedIndexes()
        if not selection:
            return

        rows = sorted(set(index.row() for index in selection))
        columns = sorted(set(index.column() for index in selection))
        clipboard_text = ""

        for row in rows:
            row_data = []
            for col in columns:
                if self.model().index(row, col) in selection:
                    row_data.append(str(self.model().data(self.model().index(row, col), Qt.DisplayRole)))
                else:
                    row_data.append('')
            clipboard_text += '\t'.join(row_data) + '\n'

        QApplication.clipboard().setText(clipboard_text)

    def headerContextMenu(self, position):
        menu = QMenu(self)
        actionHide = menu.addAction("Hide Selected Column(s)")
        actionShowAll = menu.addAction("Show All Columns")
        actionSortAscending = menu.addAction("Sort Ascending")
        actionSortDescending = menu.addAction("Sort Descending")
        action = menu.exec_(self.mapToGlobal(position))

        if action == actionHide:
            for col in self.getSelectedColumns():
                self.setColumnHidden(col, True)
        elif action == actionShowAll:
            for col in range(self.model().columnCount()):
                self.setColumnHidden(col, False)

    def getSelectedColumns(self):
        """
        Returns a list of unique selected column indexes.
        This considers both direct column selection and cell-based selection within columns.
        """
        selectedIndexes = self.selectionModel().selectedIndexes()
        selectedColumns = {index.column() for index in selectedIndexes}
        return list(selectedColumns)

class EditablePandasModelLite(QAbstractTableModel):
    def __init__(self, dataframe: pd.DataFrame, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe
        self.changesMade = False  # Flag to track changes

    def flags(self, index):
        """Return the flags for the item at the given index."""
        if not index.isValid():
            return Qt.NoItemFlags
        return super().flags(index) | Qt.ItemIsEditable
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._dataframe) if not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()):
        return len(self._dataframe.columns) if not parent.isValid() else 0

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):  # Ensure EditRole is handled
            value = self._dataframe.iloc[index.row(), index.column()]
            return str(value)
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])
            else:
                return str(section)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        row = index.row()
        col = index.column()
        try:
            # Attempt to convert the value to the dtype of the column
            dtype = self._dataframe.dtypes[col]
            if dtype != object:
                value = dtype.type(value)
            self._dataframe.iloc[row, col] = value
            self.changesMade = True
            self.dataChanged.emit(index, index, [role])  # Notify views and other interested parties
            return True
        except ValueError:
            # In case of a type conversion error, you might want to handle it (e.g., show a warning)
            return False

    def removeRow(self, row, parent=QModelIndex()):
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(parent, row, row)
            self._dataframe = self._dataframe.drop(self._dataframe.index[row]).reset_index(drop=True)
            self.endRemoveRows()
            self.changesMade = True
            return True
        return False

    def addRow(self):
        # Create a new row as a DataFrame with one row
        newRow = pd.DataFrame([{col: '' for col in self._dataframe.columns}], index=[len(self._dataframe)])
        # Use concat to add the new row
        self._dataframe = pd.concat([self._dataframe, newRow], ignore_index=True)
        self.layoutChanged.emit()

    def duplicateRow(self, rowIndex):
        # Check if the row index is valid
        if 0 <= rowIndex < self.rowCount():
            # Extract the row to duplicate
            rowToDuplicate = self._dataframe.iloc[[rowIndex]]
            # Use concat to insert the duplicated row
            self._dataframe = pd.concat([self._dataframe.iloc[:rowIndex+1], rowToDuplicate, self._dataframe.iloc[rowIndex+1:]]).reset_index(drop=True)
            self.layoutChanged.emit()

    def setHeaderData(self, section, orientation, value, role=Qt.EditRole):
        if role == Qt.EditRole and orientation == Qt.Horizontal:
            self._dataframe.columns.values[section] = value
            self.headerDataChanged.emit(orientation, section, section)
            return True
        return False

    def addColumn(self):
        # Determine a unique name for the new column
        baseName = "NewColumn"
        count = 1
        newName = f"{baseName}{count}"
        while newName in self._dataframe.columns:
            count += 1
            newName = f"{baseName}{count}"

        # Add the new column with default values (adjust as needed)
        self._dataframe[newName] = ''  # Assuming default empty string values for new column
        self.layoutChanged.emit()

    def deleteColumn(self, columnIndex):
        if 0 <= columnIndex < self.columnCount():
            # Remove the column
            columnName = self._dataframe.columns[columnIndex]
            self._dataframe.drop(columns=[columnName], inplace=True)
            self.layoutChanged.emit()

class EditableHeaderViewLite(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setSectionsClickable(True)
        self.sectionDoubleClicked.connect(self.onDoubleClick)
        self._lineEdit = None

    def onDoubleClick(self, logicalIndex):
        # print(f"Header double-clicked: {logicalIndex}")
        if self._lineEdit:
            return

        headerText = self.model().headerData(logicalIndex, self.orientation(), Qt.DisplayRole)
        
        self._lineEdit = QLineEdit(self)
        self._lineEdit.setFrame(False)
        self._lineEdit.setText(headerText)
        self._lineEdit.editingFinished.connect(self.finishEditing)
        
        # Calculate the rectangle for the section
        xPos = self.sectionViewportPosition(logicalIndex)
        yPos = 0
        width = self.sectionSize(logicalIndex)
        height = self.height()
        headerRect = QRect(xPos, yPos, width, height)
        
        self._lineEdit.setGeometry(headerRect)
        self._lineEdit.setFocus(Qt.OtherFocusReason)
        self._lineEdit.selectAll()
        self._lineEdit.show()  # Ensure the QLineEdit is shown

        self._currentLogicalIndex = logicalIndex

    def finishEditing(self):
        # Update model with new header text
        newText = self._lineEdit.text()
        model = self.model()
        if model:
            model.setHeaderData(self._currentLogicalIndex, self.orientation(), newText)

        # Clean up
        self._lineEdit.deleteLater()
        self._lineEdit = None
