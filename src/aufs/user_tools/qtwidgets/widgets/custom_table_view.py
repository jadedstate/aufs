import pandas as pd
from PyQt5.QtWidgets import QTableView, QApplication, QHeaderView, QFileDialog, QMessageBox, QShortcut, QMenu
from PyQt5.QtCore import QModelIndex, Qt, QAbstractTableModel
from PyQt5.QtGui import QKeySequence, QClipboard
from natsort import natsorted, natsort_keygen

class PandasModel(QAbstractTableModel):
    """A model to interface a Qt view with a pandas DataFrame."""
    def __init__(self, dataframe: pd.DataFrame, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._dataframe) if not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._dataframe.columns) if not parent.isValid() else 0

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None

        value = self._dataframe.iloc[index.row(), index.column()]
        if isinstance(value, float) and value.is_integer():
            # Convert float that represents an integer to an int before converting to string
            return str(int(value))
        return str(value)


    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])
            else:
                return str(self._dataframe.index[section])
        return None

class EnhancedTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupTableView()

    def setupTableView(self):
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectItems)  # Allows selection of individual items
        self.setSelectionMode(QTableView.ExtendedSelection)  # Allows multiple items to be selected
        self.horizontalHeader().setSectionsMovable(True)
        self.setClipboardCopySupport()
        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.headerContextMenu)
        deleteRowShortcut = QShortcut(QKeySequence("Del"), self)
        deleteRowShortcut.activated.connect(self.deleteSelectedRows)
        editCellShortcut = QShortcut(QKeySequence("F2"), self)
        editCellShortcut.activated.connect(self.editSelectedCell)

    def deleteSelectedRows(self):
        selectedIndexes = self.selectionModel().selectedRows()
        rows = sorted(set(index.row() for index in selectedIndexes), reverse=True)
        for row in rows:
            self.model().removeRow(row)

    def editSelectedCell(self):
        index = self.currentIndex()
        if index.isValid():
            self.editCellDialog(index)

    def editCellDialog(self, index):
        dialog = QDialog(self)
        layout = QVBoxLayout(dialog)
        
        lineEdit = QLineEdit(dialog)
        lineEdit.setText(self.model().data(index, Qt.DisplayRole))
        layout.addWidget(lineEdit)
        
        button = QPushButton("Update", dialog)
        button.clicked.connect(lambda: self.updateCellData(index, lineEdit.text()))
        layout.addWidget(button)
        
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

        # Organize selected indexes by row and then by column to ensure correct order
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
        # Updated action text to reflect the possibility of hiding multiple columns
        actionHide = menu.addAction("Hide Selected Column(s)")
        actionShowAll = menu.addAction("Show All Columns")
        action = menu.exec_(self.mapToGlobal(position))

        if action == actionHide:
            # Hide all selected columns
            for col in self.getSelectedColumns():
                self.setColumnHidden(col, True)
        elif action == actionShowAll:
            # Show all columns
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

class EditablePandasModel(PandasModel):
    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.EditRole:
            self._dataframe.iat[index.row(), index.column()] = value
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def removeRow(self, row, parent=QModelIndex()):
        self.beginRemoveRows(QModelIndex(), row, row)
        self._dataframe.drop(self._dataframe.index[row], inplace=True)
        self.endRemoveRows()
        return True