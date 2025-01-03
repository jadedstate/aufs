# 

import os
import sys
import pandas as pd
import uuid
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableView, QPushButton, QComboBox, QMessageBox, QInputDialog, QTreeWidgetItem, QTreeWidget,
    QLineEdit, QTextEdit, QLabel, QWidget, QStyledItemDelegate, QMenu
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.editable_pandas_model import EditablePandasModel, EnhancedPandasModel, SortableTableView

class CustomDelegate(QStyledItemDelegate):
    def __init__(self, value_options=None, parent=None):
        super().__init__(parent)
        # Set default as an empty dictionary, making options truly optional
        self.value_options = value_options or {}

    def createEditor(self, parent, option, index):
        """Create a ComboBox editor if value options exist for the column; otherwise, use a default LineEdit."""
        column_name = index.model()._dataframe.columns[index.column()]

        # Check if the column has specific dropdown options
        if column_name in self.value_options:
            combo_box = QComboBox(parent)
            combo_box.addItems(self.value_options[column_name])
            return combo_box

        # Default to LineEdit for non-dropdown columns
        return QLineEdit(parent)

    def setEditorData(self, editor, index):
        """Populate the editor with the current value."""
        value = index.model().data(index, Qt.EditRole)

        if isinstance(editor, QComboBox):
            current_index = editor.findText(str(value))
            if current_index >= 0:
                editor.setCurrentIndex(current_index)
        elif isinstance(editor, QLineEdit):
            editor.setText(str(value))

    def setModelData(self, editor, model, index):
        """Store the edited value back in the model."""
        value = editor.currentText() if isinstance(editor, QComboBox) else editor.text()
        model.setData(index, value, Qt.EditRole)

class DeepEditor(QWidget):
    def __init__(self, file_path=None, dataframe_input=None, value_options=None, file_type='parquet', 
                 nested_mode=False, preload=False, parent=None, button_flags=None, auto_fit_columns=True):
        super().__init__(parent)
        self.preload = preload
        self.current_tree_dialog = None
        self.current_row = None
        self.current_col = None
        self.auto_fit_columns = auto_fit_columns        
        # Save the file path and type if provided
        self.file_path = file_path
        self.file_type = file_type
        
        # Allow DataFrame input (new functionality)
        self.dataframe_input = dataframe_input
        self.dataframe = None
        
        self.nested_mode = nested_mode
        self.changes_made = False  # Track if changes were made

        # Set window title depending on whether we're editing a file or a DataFrame
        if file_path:
            self.setWindowTitle(f"Editing: {file_path}")
        else:
            self.setWindowTitle(f"Editing DataFrame")

        self.resize(3000, 800)

        # Initialize button flags if not provided
        if button_flags is None:
            button_flags = {
                'add_row': True,
                'delete_row': True,
                'move_row_up': True,
                'move_row_down': True,
                'add_column': True,
                'delete_column': True,
                'move_column_left': True,
                'move_column_right': True,
                'sort_column': True,
                'clear_selection': True,
                'set_column_type': True,
                'dtype_dropdown': True,
                'reload': True,
                'save': True,
                'exit': True
            }

        # === Main Layout ===
        self.main_layout = QVBoxLayout(self)

        # === Initialize EditablePandasModel ===
        self.model = EditablePandasModel(self.dataframe, value_options=value_options, editable=True, parent=self)
        self.model.dataChanged.connect(self.track_changes)

        # === Central Layout ===
        self.central_layout = QHBoxLayout()

        # === Left side vertical button layout ===
        self.left_button_layout = QVBoxLayout()

        # Add Row button
        self.add_row_button = QPushButton("Add Row", self)
        self.add_row_button.setEnabled(button_flags.get('add_row', True))
        if not button_flags.get('add_row', True):
            self.add_row_button.hide()
        self.left_button_layout.addWidget(self.add_row_button)

        # Delete Row button
        self.delete_row_button = QPushButton("Delete Row", self)
        self.delete_row_button.setEnabled(button_flags.get('delete_row', True))
        if not button_flags.get('delete_row', True):
            self.delete_row_button.hide()
        self.left_button_layout.addWidget(self.delete_row_button)

        # Move Row Up/Down buttons
        self.move_row_up_button = QPushButton("Move Row Up", self)
        self.move_row_up_button.setEnabled(button_flags.get('move_row_up', True))
        if not button_flags.get('move_row_up', True):
            self.move_row_up_button.hide()
        self.move_row_down_button = QPushButton("Move Row Down", self)
        self.move_row_down_button.setEnabled(button_flags.get('move_row_down', True))
        if not button_flags.get('move_row_down', True):
            self.move_row_down_button.hide()
        self.left_button_layout.addWidget(self.move_row_up_button)
        self.left_button_layout.addWidget(self.move_row_down_button)

        # Add the left button layout to the central layout
        self.central_layout.addLayout(self.left_button_layout)

        # === TableView for displaying the DataFrame ===
        self.table_view = QTableView(self)
        self.table_view.setModel(self.model)
        delegate = CustomDelegate(value_options=value_options, parent=self.table_view)
        self.table_view.setItemDelegate(delegate)
        self.central_layout.addWidget(self.table_view)

        # Apply auto-fitting of columns if enabled
        if self.auto_fit_columns:
            self.table_view.resizeColumnsToContents()
            
        # === Top button layout (use QVBox and QHBox to replace QGridLayout) ===
        self.top_button_layout = QVBoxLayout()  # Using QVBoxLayout for vertical stacking

        # Create a horizontal layout to group similar buttons together
        button_row_1 = QHBoxLayout()  # First row of buttons
        self.add_column_button = QPushButton("Add Column", self)
        self.add_column_button.setEnabled(button_flags.get('add_column', True))
        if not button_flags.get('add_column', True):
            self.add_column_button.hide()
        button_row_1.addWidget(self.add_column_button)

        self.delete_column_button = QPushButton("Delete Column", self)
        self.delete_column_button.setEnabled(button_flags.get('delete_column', True))
        if not button_flags.get('delete_column', True):
            self.delete_column_button.hide()
        button_row_1.addWidget(self.delete_column_button)


        # Second row of buttons
        button_row_2 = QHBoxLayout()  # Another horizontal row of buttons
        self.move_column_left_button = QPushButton("Move Column Left", self)
        self.move_column_left_button.setEnabled(button_flags.get('move_column_left', True))
        if not button_flags.get('move_column_left', True):
            self.move_column_left_button.hide()
        button_row_2.addWidget(self.move_column_left_button)

        self.move_column_right_button = QPushButton("Move Column Right", self)
        self.move_column_right_button.setEnabled(button_flags.get('move_column_right', True))
        if not button_flags.get('move_column_right', True):
            self.move_column_right_button.hide()
        button_row_2.addWidget(self.move_column_right_button)


        # Sort Column button in a separate horizontal row
        button_row_3 = QHBoxLayout()
        self.sort_column_button = QPushButton("Sort Column", self)
        self.sort_column_button.setEnabled(button_flags.get('sort_column', True))
        if not button_flags.get('sort_column', True):
            self.sort_column_button.hide()
        button_row_1.addWidget(self.sort_column_button)

        # Clear Selected Data and Dropdown Layout
        button_row_4 = QHBoxLayout()
        self.clear_selection_button = QPushButton("Clear Selected Data", self)
        self.clear_selection_button.setEnabled(button_flags.get('clear_selection', True))
        if not button_flags.get('clear_selection', True):
            self.clear_selection_button.hide()
        button_row_1.addWidget(self.clear_selection_button)

        # Clear Selected Data and Dropdown Layout
        button_row_5 = QHBoxLayout()
        
        self.dtype_dropdown = QComboBox(self)
        self.dtype_dropdown.addItems(self.model.get_valid_dtypes())
        if not button_flags.get('dtype_dropdown', True):
            self.dtype_dropdown.hide()

        self.set_column_type_button = QPushButton("Set Column Type", self)
        self.set_column_type_button.setEnabled(button_flags.get('set_column_type', True))
        if not button_flags.get('set_column_type', True):
            self.set_column_type_button.hide()
        button_row_1.addWidget(self.set_column_type_button)
        button_row_1.addWidget(self.dtype_dropdown)

        self.top_button_layout.addLayout(button_row_1) # add/delete col
        self.top_button_layout.addLayout(button_row_3) # sort col
        self.top_button_layout.addLayout(button_row_5) # change col data type
        self.top_button_layout.addLayout(button_row_4) # clear selected cells
        self.top_button_layout.addLayout(button_row_2) # move col left/right
        
        # Add top button layout to the main layout
        self.main_layout.addLayout(self.top_button_layout)
        self.main_layout.addLayout(self.central_layout)

        # === Footer buttons ===
        self.footer_layout = QHBoxLayout()
        self.reload_button = QPushButton("Reload", self)
        self.reload_button.setEnabled(button_flags.get('reload', True))
        if not button_flags.get('reload', True):
            self.reload_button.hide()
        self.footer_layout.addWidget(self.reload_button)

        self.save_button = QPushButton("Save", self)
        self.save_button.setEnabled(button_flags.get('save', True))
        if not button_flags.get('save', True):
            self.save_button.hide()
        self.exit_button = QPushButton("Exit", self)
        self.exit_button.setEnabled(button_flags.get('exit', True))
        if not button_flags.get('exit', True):
            self.exit_button.hide()
        self.footer_layout.addWidget(self.save_button)
        self.footer_layout.addWidget(self.exit_button)

        self.main_layout.addLayout(self.footer_layout)

        # === Button Connections ===
        self.add_row_button.clicked.connect(self.add_row)
        self.delete_row_button.clicked.connect(self.delete_selected_rows)
        self.add_column_button.clicked.connect(self.add_column)
        self.delete_column_button.clicked.connect(self.delete_selected_columns)
        self.move_row_up_button.clicked.connect(self.move_row_up)
        self.move_row_down_button.clicked.connect(self.move_row_down)
        self.move_column_left_button.clicked.connect(self.move_column_left)
        self.move_column_right_button.clicked.connect(self.move_column_right)
        self.sort_column_button.clicked.connect(self.sort_column)
        self.clear_selection_button.clicked.connect(self.clear_selected_data)
        self.set_column_type_button.clicked.connect(self.set_column_type)
        self.reload_button.clicked.connect(self.reload_file)
        self.save_button.clicked.connect(self.save_file)
        self.exit_button.clicked.connect(self.close)

        if self.nested_mode:
            self.enable_nested_mode()

        self.load_data()

    def load_data(self):
        """Load data from a DataFrame or file."""
        if self.dataframe_input is not None and isinstance(self.dataframe_input, pd.DataFrame):
            self.load_from_dataframe(self.dataframe_input)
        elif self.file_path:
            self.load_file()

    def load_from_dataframe(self, dataframe):
        """Load directly from an in-memory DataFrame."""
        self.dataframe = dataframe
        self.model.update_dataframe(dataframe)

        # Reapply column resizing if enabled
        if self.auto_fit_columns:
            self.table_view.resizeColumnsToContents()

    def track_changes(self):
        """Track if any changes were made to the DataFrame."""
        self.changes_made = True

    def closeEvent(self, event):
        """Prompt the user to save changes before closing."""
        if self.changes_made:
            reply = QMessageBox.question(self, 'Save Changes?',
                                         "You have unsaved changes. Do you want to save before closing?",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                         QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_file()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()  # Close without saving
            else:
                event.ignore()  # Cancel closing
        else:
            event.accept()

    def load_file(self):
        """Load the file based on its type ('parquet' or 'csv')."""
        if self.file_path:
            if self.file_type == 'parquet':
                self.load_parquet(preload=self.preload)
            elif self.file_type == 'csv':
                self.load_csv(preload=self.preload)

    def reload_file(self):
        """Reload the file, discarding any unsaved changes."""
        if self.file_path:
            reply = QMessageBox.question(self, 'Confirm Reload', 
                                         "Are you sure you want to reload the file? All unsaved changes will be lost.", 
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.load_file()

    def load_parquet(self, preload=False):
        """Load the Parquet file into a Pandas DataFrame."""
        try:
            if os.path.exists(self.file_path):
                dataframe = pd.read_parquet(self.file_path)

                if preload:
                    # Treat as user-passed DataFrame
                    self.dataframe_input = dataframe
                    self.load_from_dataframe(dataframe)  # Reuse existing method for direct DataFrame loading
                else:
                    # Original behavior
                    self.dataframe = dataframe
                    self.model.update_dataframe(dataframe)
                    self.table_view.setModel(self.model)
                    if self.auto_fit_columns:
                        self.table_view.resizeColumnsToContents()
            else:
                QMessageBox.warning(self, "File Not Found", f"{self.file_path} does not exist.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load Parquet file: {str(e)}")

    def load_csv(self, dtype_mapping=None, preload=False):
        """Load the CSV file into a Pandas DataFrame with specified column data types."""
        try:
            if os.path.exists(self.file_path):
                if dtype_mapping is None:
                    dtype_mapping = {'PADDING': str, 'FIRSTFRAME': str, 'LASTFRAME': str}
                dataframe = pd.read_csv(self.file_path, dtype=dtype_mapping)
                print("Read: ", self.file_path)
                
                if preload:
                    # Treat as user-passed DataFrame
                    self.dataframe_input = dataframe
                    self.load_from_dataframe(dataframe)  # Reuse existing method for direct DataFrame loading
                else:
                    # Original behavior
                    self.dataframe = dataframe
                    self.model.update_dataframe(dataframe)
                    self.table_view.setModel(self.model)
                    if self.auto_fit_columns:
                        self.table_view.resizeColumnsToContents()
            else:
                QMessageBox.warning(self, "File Not Found", f"{self.file_path} does not exist.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load CSV file: {str(e)}")

    def delete_selected_rows(self):
        """Deletes the currently selected rows."""
        selected_rows = sorted(set(index.row() for index in self.table_view.selectionModel().selectedRows()), reverse=True)
        if selected_rows:
            self.model.delete_rows(selected_rows)
            self.track_changes()  # Track changes after modifying rows

    def delete_selected_columns(self):
        """Deletes the currently selected columns."""
        selected_columns = sorted(set(index.column() for index in self.table_view.selectionModel().selectedColumns()), reverse=True)
        if selected_columns:
            self.model.delete_columns(selected_columns)
            self.track_changes()  # Track changes after modifying columns

    def open_context_menu(self, position):
        """Handle right-click event and directly show the nested structure."""
        index = self.table_view.indexAt(position)
        if index.isValid():
            self.current_row, self.current_col = index.row(), index.column()

            # Generate id_df for the right-clicked cell only
            self.model.generate_id_df(self.current_row, self.current_col)

            # Display the tree view based on the id_df
            self.show_tree_view()

    def enable_nested_mode(self):
        """Enable additional nested mode features, like the tree view and nested editor."""
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)

    def preview_nested_data(self, row, column):
        """
        Extract the nested data for a given cell and display in a preview buffer.

        Args:
            row (int): The row index of the selected cell.
            column (int): The column index of the selected cell.

        Returns:
            pd.DataFrame: The preview buffer containing the nested components.
        """
        column_name = self.model._dataframe.columns[column]
        nested_data = self.model._dataframe.attrs.get("nested_data", {}).get(column_name, [])

        if not nested_data or row >= len(nested_data):
            QMessageBox.warning(self, "No Nested Data", "No nested data available for this cell.")
            return None

        # Create a DataFrame preview buffer for the nested components
        preview_df = pd.DataFrame({"Components": nested_data[row]})
        return preview_df

    def edit_nested_data(self, row, column):
        """
        Edit the nested data for a given cell.

        Args:
            row (int): The row index of the selected cell.
            column (int): The column index of the selected cell.
        """
        # Extract nested data into a preview buffer
        preview_df = self.preview_nested_data(row, column)
        if preview_df is None:
            return  # No nested data to edit

        # Launch the editor
        editor = NestedEditor(preview_df, self)
        if editor.exec_() == QDialog.Accepted:
            # Retrieve updated nested data from the editor
            updated_df = editor.get_dataframe()
            updated_components = updated_df["Components"].tolist()

            # Apply changes back to the main DataFrame
            self.apply_nested_updates(row, column, updated_components)

    def apply_nested_updates(self, row, column, updated_components):
        """
        Apply updates to the nested data and reflect changes in the main DataFrame.

        Args:
            row (int): The row index of the cell.
            column (int): The column index of the cell.
            updated_components (list): The updated list of nested components.
        """
        column_name = self.model._dataframe.columns[column]
        df = self.model._dataframe

        # Update the nested data stored in `attrs`
        if "nested_data" not in df.attrs:
            df.attrs["nested_data"] = {}
        if column_name not in df.attrs["nested_data"]:
            df.attrs["nested_data"][column_name] = [[] for _ in range(len(df))]

        df.attrs["nested_data"][column_name][row] = updated_components

        # Recompute the main cell value by joining the components
        new_value = "".join(updated_components)
        df.at[row, column_name] = new_value  # Update the main DataFrame cell value

        # Reflect changes in the UI
        self.model.layoutChanged.emit()
        QMessageBox.information(self, "Update Successful", f"Cell updated to: {new_value}")

    def show_context_menu(self, position):
        """Display a custom context menu for nested editing."""
        index = self.table_view.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self)
        nested_edit_action = QAction("Edit Nested Components", self)
        nested_edit_action.triggered.connect(lambda: self.edit_nested_data(index.row(), index.column()))
        menu.addAction(nested_edit_action)
        menu.exec_(self.table_view.viewport().mapToGlobal(position))

    def save_file(self, partition_cols=None):
        """Save the DataFrame to a file based on file type."""
        if self.file_path:
            try:
                if self.file_type == 'parquet':
                    self.save_parquet(partition_cols)
                elif self.file_type == 'csv':
                    self.save_csv()
                QMessageBox.information(self, "Success", "Changes saved successfully.")
                self.changes_made = False  # Reset changes tracking after saving
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
        else:
            # If no file path, return the edited DataFrame
            return self.dataframe

    def save_parquet(self, partition_cols=None):
        """Save the DataFrame to a Parquet file."""
        try:
            if partition_cols:
                self.dataframe.to_parquet(self.file_path, partition_cols=partition_cols)
            else:
                self.dataframe.to_parquet(self.file_path)
        except Exception as e:
            raise IOError(f"Failed to save Parquet file: {str(e)}")

    def save_csv(self):
        """Save the DataFrame to a CSV file."""
        try:
            dataframe = self.model.get_dataframe()  # Ensure we get the updated DataFrame
            dataframe.to_csv(self.file_path, index=False)
            QMessageBox.information(self, "Success", f"CSV saved successfully: {self.file_path}")
            self.changes_made = False  # Reset the changes tracking
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save CSV: {str(e)}")

    def reload_csv(self):
        """Reload the CSV file and discard any unsaved changes."""
        reply = QMessageBox.question(self, 'Confirm Reload', 
                                     "Are you sure you want to reload the file? All unsaved changes will be lost.", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.load_csv()
            self.model.update_dataframe(self.dataframe)

    def add_row(self):
        """Adds a new row at the bottom."""
        self.model.add_row()

    def add_column(self):
        column_name, ok = QInputDialog.getText(self, "Add Column", "Column name:")
        if ok and column_name:
            # Optionally, you can also ask for the data type if needed
            dtype, ok_type = QInputDialog.getItem(
                self, "Select Data Type", "Choose column data type:", ["object", "int64", "float64"], editable=False
            )

            if ok_type and dtype:
                # Add the new column to the model
                self.model.add_column(column_name=column_name, dtype=dtype)

    def move_row_up(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            new_row_index = self.model.move_row(index.row(), -1)
            if new_row_index is not None:
                # Update the selection to the new row
                self.table_view.selectRow(new_row_index)

    def move_row_down(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            new_row_index = self.model.move_row(index.row(), 1)
            if new_row_index is not None:
                # Update the selection to the new row
                self.table_view.selectRow(new_row_index)

    def move_column_left(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            new_col_index = self.model.move_column(index.column(), -1)
            if new_col_index is not None:
                # Update the selection to the new column
                self.table_view.setCurrentIndex(self.table_view.model().index(index.row(), new_col_index))

    def move_column_right(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            new_col_index = self.model.move_column(index.column(), 1)
            if new_col_index is not None:
                # Update the selection to the new column
                self.table_view.setCurrentIndex(self.table_view.model().index(index.row(), new_col_index))

    def sort_column(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            self.model.sort_column(index.column())

    def clear_selected_data(self):
        """Clear the data in the currently selected cells."""
        selection_model = self.table_view.selectionModel()
        selected_indexes = selection_model.selectedIndexes()
        self.model.clear_selection(selected_indexes)

    def set_column_type(self):
        """Sets the column's data type based on the dropdown selection."""
        index = self.table_view.currentIndex()
        if index.isValid():
            selected_dtype = self.dtype_dropdown.currentText()
            self.model.set_column_dtype(index.column(), selected_dtype)

    def show_tree_view(self):
        """Display the tree view built from the id_df directly."""
        if self.current_tree_dialog is not None:
            self.current_tree_dialog.close()

        self.current_tree_dialog = QDialog(self)
        self.current_tree_dialog.setWindowTitle("Cell Content Tree")
        self.current_tree_dialog.resize(400, 400)

        layout = QVBoxLayout(self.current_tree_dialog)
        tree = QTreeWidget(self.current_tree_dialog)

        # Request id_df from the model for the selected cell
        self.model.generate_id_df(self.current_row, self.current_col)

        # Recursively add nodes to the tree
        self.add_tree_nodes(tree.invisibleRootItem(), self.model.id_df)

        tree.expandAll()
        layout.addWidget(tree)

        # Add buttons below the tree
        tv_button_layout = QHBoxLayout()
        edit_button = QPushButton("Edit", self.current_tree_dialog)
        nest_button = QPushButton("Nest", self.current_tree_dialog)
        delete_button = QPushButton("Delete Selected", self.current_tree_dialog)

        tv_button_layout.addWidget(edit_button)
        tv_button_layout.addWidget(nest_button)
        tv_button_layout.addWidget(delete_button)
        layout.addLayout(tv_button_layout)

        edit_button.clicked.connect(lambda: self.edit_node(tree.currentItem()))
        nest_button.clicked.connect(lambda: self.nest_node(tree.currentItem()))
        delete_button.clicked.connect(lambda: self.delete_node(tree.currentItem(), tree))

        self.current_tree_dialog.setLayout(layout)
        self.current_tree_dialog.show()

    def add_tree_nodes(self, parent, id_df):
        """Recursively add tree nodes from the id_df."""
        grouped = id_df.groupby('path')
        for path, group in grouped:
            # For each unique path, create a tree node
            node = QTreeWidgetItem(parent, [group.iloc[0]['data_type']])
            node.setData(0, Qt.UserRole + 1, group.iloc[0]['uuid'])  # Store UUID in user role data
            # Recursively handle nested nodes if needed
            if len(group) > 1:
                self.add_tree_nodes(node, group)

    def edit_node(self, item):
        """Edit the selected node."""
        node_uuid = item.data(0, Qt.UserRole + 1)
        data_package = self.model.get_data_by_uuid(node_uuid)

        if data_package is None:
            QMessageBox.warning(self, "Error", "Failed to retrieve data for editing.")
            return

        value, data_type = data_package, type(data_package).__name__

        if data_type == 'str':
            self.show_text_editor(value, item)
        elif data_type in ['list', 'dict']:
            self.show_nested_editor(value)
        elif data_type == 'ndarray':
            self.show_ndarray_editor(value)
        else:
            QMessageBox.information(self, "Non-Editable Node", f"The type {data_type} is not editable.")

    def show_ndarray_editor(self, ndarray):
        """Open the NestedEditor dialog for editing numpy ndarrays."""
        import numpy as np

        # Convert the ndarray to a DataFrame for editing
        if ndarray.ndim == 1:
            # 1D array: Treat as a list
            df = pd.DataFrame({'Array Element': ndarray})
        else:
            # Multi-dimensional array: Convert to DataFrame
            df = pd.DataFrame(ndarray)

        # Show the NestedEditor with the converted DataFrame
        editor = NestedEditor(df, self)

        if editor.exec_() == QDialog.Accepted:
            # Convert the edited DataFrame back to an ndarray
            new_ndarray = editor.model.get_dataframe().to_numpy()

            # Do something with the updated ndarray
            # e.g., update the model or save the result
            self.model.update_data_by_uuid(self.current_row, self.current_col, new_ndarray)

            self.refresh_views()

    def nest_node(self, item):
        """Add a sub-node (nested data) to the selected node if it is a list or dict, or offer to convert."""
        node_uuid = item.data(0, Qt.UserRole + 1)
        data_package = self.model.get_data_by_uuid(node_uuid)

        # Check if the node contains a list or dict
        if isinstance(data_package, (list, dict)):
            # Display a dialog to allow the user to choose where to nest
            self.show_nesting_dialog(data_package, node_uuid)
        elif isinstance(data_package, str) or isinstance(data_package, object):
            # Offer to convert the string/object to a list or dict
            self.offer_conversion(item, data_package, node_uuid)
        else:
            QMessageBox.information(self, "Nesting Unavailable",
                                    "You can only nest data inside lists or dictionaries at this time.")

    def show_nesting_dialog(self, data_package, node_uuid):
        """Display a dialog to allow the user to select where and what to nest."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Nest Data")
        layout = QVBoxLayout(dialog)

        # Label: Choose where to nest
        layout.addWidget(QLabel("Select where to nest the new data:"))

        # List existing elements (for dicts: show keys, for lists: show indices)
        existing_items_combo = QComboBox(dialog)

        if isinstance(data_package, dict):
            existing_items_combo.addItems(data_package.keys())  # Add dict keys
        elif isinstance(data_package, list):
            for i in range(len(data_package)):
                existing_items_combo.addItem(f"Index {i}")  # Add list indices

        layout.addWidget(existing_items_combo)

        # Option to add a new item/key
        add_new_item_button = QPushButton("Add New Item", dialog)
        layout.addWidget(add_new_item_button)

        # Label: Choose what type of data to nest
        layout.addWidget(QLabel("Select the type of data to nest:"))

        # Dropdown for data type selection
        data_type_combo = QComboBox(dialog)
        data_type_combo.addItems(["String", "Integer", "List", "Dict"])  # Types for now
        layout.addWidget(data_type_combo)

        # Buttons for confirmation
        ne_conf_button_layout = QHBoxLayout()
        save_button = QPushButton("Nest", dialog)
        cancel_button = QPushButton("Cancel", dialog)
        ne_conf_button_layout.addWidget(save_button)
        ne_conf_button_layout.addWidget(cancel_button)
        layout.addLayout(ne_conf_button_layout)

        # Connect the buttons
        save_button.clicked.connect(lambda: self.confirm_nesting(existing_items_combo, data_type_combo, data_package, node_uuid, dialog))
        cancel_button.clicked.connect(dialog.reject)

        # Add new item logic
        add_new_item_button.clicked.connect(lambda: self.add_new_item_to_list_or_dict(existing_items_combo, data_package))

        dialog.exec_()

    def offer_conversion(self, item, data_package, node_uuid):
        """Offer to convert a string/object to a list or dict for nesting."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Convert Data for Nesting")

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("The selected data is not a list or dictionary. Would you like to convert it?"))

        # Offer conversion options
        oc_button_layout = QHBoxLayout()
        convert_to_list_button = QPushButton("Convert to List", dialog)
        convert_to_dict_button = QPushButton("Convert to Dictionary", dialog)
        cancel_button = QPushButton("Cancel", dialog)
        
        oc_button_layout.addWidget(convert_to_list_button)
        oc_button_layout.addWidget(convert_to_dict_button)
        oc_button_layout.addWidget(cancel_button)

        layout.addLayout(oc_button_layout)

        # Connect the buttons
        convert_to_list_button.clicked.connect(lambda: self.convert_data_and_nest(item, "list", node_uuid, dialog))
        convert_to_dict_button.clicked.connect(lambda: self.convert_data_and_nest(item, "dict", node_uuid, dialog))
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec_()

    def convert_data_and_nest(self, item, target_type, node_uuid, dialog):
        """Convert the current data to a list or dict, then proceed with nesting."""
        # Retrieve the data again (in case it's changed)
        data_package = self.model.get_data_by_uuid(node_uuid)
        
        # Convert the data based on user choice
        if target_type == "list":
            new_data = [data_package] if data_package else []  # Wrap current data in a list or create empty list
        elif target_type == "dict":
            new_data = {"original_data": data_package} if data_package else {}  # Wrap in dict or create empty dict
        
        # Update the data in the DataFrame
        success = self.model.update_data_by_uuid(node_uuid, new_data)

        if success:
            # Regenerate id_df and proceed with nesting
            self.model.generate_id_df(self.current_row, self.current_col)
            dialog.accept()  # Close the conversion dialog

            # Now, continue with the nesting dialog
            self.show_nesting_dialog(new_data, node_uuid)

    def add_new_item_to_list_or_dict(self, existing_items_combo, data_package):
        """Allow the user to add a new item to the list or dict."""
        if isinstance(data_package, dict):
            new_key, ok = QInputDialog.getText(self, "Add New Key", "Enter the new key for the dictionary:")
            if ok and new_key:
                existing_items_combo.addItem(new_key)
                data_package[new_key] = None  # Placeholder for new key
        elif isinstance(data_package, list):
            existing_items_combo.addItem(f"Index {len(data_package)}")
            data_package.append(None)  # Add new element to the list

    def confirm_nesting(self, existing_items_combo, data_type_combo, data_package, node_uuid, dialog):
        """Confirm the nesting operation and update the model."""
        selected_location = existing_items_combo.currentText()  # The key (for dict) or index (for list)
        selected_data_type = data_type_combo.currentText()  # The type of data to nest

        # Determine what kind of data to nest based on the selected type
        if selected_data_type == "String":
            new_data = "New String"
        elif selected_data_type == "Integer":
            new_data = 0
        elif selected_data_type == "List":
            new_data = []
        elif selected_data_type == "Dict":
            new_data = {}

        # Perform nesting based on data type (list or dict)
        if isinstance(data_package, dict):
            data_package[selected_location] = new_data
        elif isinstance(data_package, list):
            index = int(selected_location.replace("Index ", ""))
            data_package.insert(index, new_data)  # Insert at the selected index

        # Update the model with the new data
        success = self.model.update_data_by_uuid(node_uuid, data_package)

        if success:
            # Regenerate the id_df for the current cell and refresh views
            self.model.generate_id_df(self.current_row, self.current_col)
            self.refresh_views()

        dialog.accept()

    def delete_node(self, item, tree):
        """Delete the selected node after confirmation."""
        node_uuid = item.data(0, Qt.UserRole + 1)
        
        # Confirmation dialog
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this item and all its nested data?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.model.update_data_by_uuid(node_uuid, None)  # Clear the data for the node
            if success:
                # Remove item from tree
                (item.parent() or tree.invisibleRootItem()).removeChild(item)
                self.refresh_views()

    def show_text_editor(self, value, item):
        """Open a text editor for string values."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Text")

        layout = QVBoxLayout(dialog)
        text_box = QTextEdit(dialog)
        text_box.setText(value)
        layout.addWidget(text_box)

        ste_button_layout = QHBoxLayout()
        save_button = QPushButton("Save", dialog)
        cancel_button = QPushButton("Cancel", dialog)
        ste_button_layout.addWidget(save_button)
        ste_button_layout.addWidget(cancel_button)

        layout.addLayout(ste_button_layout)
        dialog.setLayout(layout)

        save_button.clicked.connect(lambda: self.confirm_edit(item, text_box.toPlainText(), dialog))
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec_()

    def confirm_edit(self, item, new_value, dialog):
        """Confirm the edit and update the model."""
        node_uuid = item.data(0, Qt.UserRole + 1)
        success = self.model.update_data_by_uuid(node_uuid, new_value)

        if success:
            # Regenerate id_df for the current cell after data is modified
            self.model.generate_id_df(self.current_row, self.current_col)
            self.refresh_views()

        dialog.accept()

    def show_nested_editor(self, nested_data):
        """Open the NestedEditor dialog for editing lists, dicts, or arrays."""
        if isinstance(nested_data, list) or isinstance(nested_data, dict):
            df = pd.DataFrame({'List Element': nested_data} if isinstance(nested_data, list)
                            else list(nested_data.items()), columns=['Key', 'Value'])
        else:
            df = pd.DataFrame(nested_data)

        editor = NestedEditor(df, self)

        if editor.exec_() == QDialog.Accepted:
            # Get the updated DataFrame and convert it back to the original structure
            updated_df = editor.get_dataframe()
            if isinstance(nested_data, list):
                updated_data = updated_df['List Element'].tolist()
            elif isinstance(nested_data, dict):
                updated_data = dict(zip(updated_df['Key'], updated_df['Value']))
            else:
                updated_data = updated_df.to_numpy()

            # Update the model with the edited data
            self.model.update_data_by_uuid(self.current_row, self.current_col, updated_data)

            self.refresh_views()

    def refresh_views(self):
        """Refresh both the table view and tree view when data changes."""
        self.model.layoutChanged.emit()  # Notify the table that the data has changed
        if self.current_tree_dialog is not None:
            self.show_tree_view()  # Redisplay the tree for the current cell

    def recurse_struct(self, struct_data, path_str):
        for field_name, value in struct_data.items():
            field_type = type(value).__name__
            unique_id = str(uuid.uuid4())
            self.id_df.append({
                "uuid": unique_id,
                "data_type": field_type,
                "path": f"{path_str}.{field_name}",
                "cell_coords": (row, col)
            })
            # Recursively handle nested structs or lists inside fields
            if isinstance(value, dict):  # Struct fields
                self.recurse_struct(value, f"{path_str}.{field_name}")
            elif isinstance(value, list):  # Arrays inside struct fields
                self.recurse_list(value, f"{path_str}.{field_name}")

class NestedEditor(QDialog):
    def __init__(self, dataframe, parent=None, is_struct=False, struct_schema=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Nested Data" if not is_struct else "Edit Struct")
        self.resize(600, 400)
        self.is_struct = is_struct
        self.struct_schema = struct_schema  # Schema for the struct, if available
        self.changes_made = False  # Track if any changes have been made
        
        # Layout setup
        layout = QVBoxLayout(self)
        self.model = EditablePandasModel(dataframe, editable=True)
        self.table_view = QTableView(self)
        self.table_view.setModel(self.model)
        layout.addWidget(self.table_view)
        
        # Add row/column controls
        ne_button_layout = QHBoxLayout()
        if not self.is_struct:  # Allow adding rows for lists/dicts, but not for structs
            self.add_row_button = QPushButton("Add Row", self)
            self.delete_row_button = QPushButton("Delete Row", self)
            ne_button_layout.addWidget(self.add_row_button)
            ne_button_layout.addWidget(self.delete_row_button)
        
        self.move_row_up_button = QPushButton("Move Row Up", self)
        self.move_row_down_button = QPushButton("Move Row Down", self)
        ne_button_layout.addWidget(self.move_row_up_button)
        ne_button_layout.addWidget(self.move_row_down_button)
        layout.addLayout(ne_button_layout)

        # Add Save and Cancel buttons
        save_cancel_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        save_cancel_layout.addWidget(self.save_button)
        save_cancel_layout.addWidget(self.cancel_button)
        layout.addLayout(save_cancel_layout)

        # Button connections
        self.add_row_button.clicked.connect(self.add_row)
        self.delete_row_button.clicked.connect(self.delete_row)
        self.move_row_up_button.clicked.connect(self.move_row_up)
        self.move_row_down_button.clicked.connect(self.move_row_down)
        self.save_button.clicked.connect(self.save_changes)
        self.cancel_button.clicked.connect(self.close)
        
        # Track changes when editing
        self.model.dataChanged.connect(self.track_changes)

    def track_changes(self):
        """Mark that changes have been made to the data."""
        self.changes_made = True

    def closeEvent(self, event):
        """Prompt the user to save changes when closing."""
        if self.changes_made:
            reply = QMessageBox.question(self, 'Save Changes?',
                                         "You have unsaved changes. Do you want to save before closing?",
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                         QMessageBox.Cancel)
            if reply == QMessageBox.Yes:
                self.save_changes()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()  # Cancel closing
        else:
            event.accept()

    def save_changes(self):
        """Save changes and close the editor."""
        self.changes_made = False  # Reset the changes tracking
        self.accept()  # Close the dialog
        self.parent().track_changes()  # Notify the parent that changes were made

    def add_row(self):
        """Add a new row (for lists or dicts only)."""
        if not self.is_struct:
            self.model.add_row()

    def delete_row(self):
        """Delete the currently selected row (for lists or dicts only)."""
        if not self.is_struct:
            index = self.table_view.currentIndex()
            if index.isValid():
                self.model.delete_row(index.row())

    def move_row_up(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            new_row_index = self.model.move_row(index.row(), -1)
            if new_row_index is not None:
                # Update the selection to the new row
                self.table_view.selectRow(new_row_index)

    def move_row_down(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            new_row_index = self.model.move_row(index.row(), 1)
            if new_row_index is not None:
                # Update the selection to the new row
                self.table_view.selectRow(new_row_index)

    def get_dataframe(self):
        """Return the edited DataFrame."""
        return self.model.get_dataframe()
