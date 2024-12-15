# src/aufs/user_tools/packaging/pandas_deep_data_editor.py

import os
import sys
import pandas as pd
import uuid
import random
import string
import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableView, QPushButton, QComboBox, QMessageBox, QInputDialog, QTreeWidgetItem, QTreeWidget,
    QLineEdit, QTextEdit, QLabel, QWidget, QStyledItemDelegate, QMenu, QAbstractItemView, QCheckBox, QToolBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.qtwidgets.widgets.editable_pandas_model import NestedDataTransformer, EnhancedPandasModel, SortableTableView

class DraggableTextInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)  # Enable accepting drops

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():  # Check if the drag data contains text
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            dropped_text = event.mimeData().text()  # Extract the text from the drop
            self.setText(dropped_text)  # Display it in the input box
            print(f"Dropped text: {dropped_text}")  # Debugging output
            event.accept()
        else:
            event.ignore()

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
                 nested_mode=False, preload=False, key_field='key', delimiter='/', parent=None, button_flags=None, auto_fit_columns=True):
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
                'search_replace': True,
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
                'exit': False
            }

        # === Main Layout ===
        self.main_layout = QVBoxLayout(self)

        # # In the __init__ method, add this widget to the UI
        # self.temp_drag_input = DraggableTextInput(self)
        # self.temp_drag_input.setPlaceholderText("Drop here to test drag-and-drop...")
        # self.main_layout.addWidget(self.temp_drag_input)

        # Initialize the transformer with desired configuration
        self.transformer = NestedDataTransformer(key_field=key_field, delimiter=delimiter)
        # Updated model to EnhancedPandasModel
        self.model = EnhancedPandasModel(
            self.dataframe_input if self.dataframe_input is not None else pd.DataFrame(),
            value_options=value_options,
            editable=True,
            dragNdrop=True,
            transformer=self.transformer,
            auto_fit_columns=self.auto_fit_columns
        )
        self.model.parent_editor = self
        self.model.dataChanged.connect(self.track_changes)
        self.model.dataChanged.connect(self.handle_data_change)

        # === Central Layout ===
        self.central_layout = QHBoxLayout()

        # === Left side vertical button layout ===
        self.left_button_layout = QVBoxLayout()

        self.search_replace_button = QPushButton("Search and Replace", self)
        self.search_replace_button.setEnabled(button_flags.get('search_replace', True))
        if not button_flags.get('add_row', True):
            self.search_replace_button.hide()
        self.left_button_layout.addWidget(self.search_replace_button)

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
        self.table_view = SortableTableView(self)
        self.table_view.setModel(self.model)
        delegate = CustomDelegate(value_options=value_options, parent=self.table_view)
        self.table_view.setItemDelegate(delegate)
        self.table_view.setDragEnabled(True)
        self.table_view.setAcceptDrops(True)
        self.table_view.setDropIndicatorShown(True)
        self.table_view.setDragDropMode(QAbstractItemView.DragDrop)
        self.table_view.setItemDelegate(CustomDelegate(value_options=value_options, parent=self.table_view))

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

        self.search_replace_button.clicked.connect(self.open_search_replace_dialog)
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

    def handle_data_change(self, top_left_index, bottom_right_index, roles):
        """
        Handle updates to the DataFrame when a cell is edited.
        Recalculates the entire PROVISIONEDLINK column after any edit.
        Ensures nested data is synchronized for edited cells.
        """
        if not roles or Qt.EditRole not in roles:
            return

        # Get the edited DataFrame
        df = self.model.get_dataframe()

        # Iterate over the edited range
        for row in range(top_left_index.row(), bottom_right_index.row() + 1):
            for col in range(top_left_index.column(), bottom_right_index.column() + 1):
                column_name = df.columns[col]

                # Ensure nested data exists for the column
                if "nested_data" not in df.attrs:
                    df.attrs["nested_data"] = {}
                if column_name not in df.attrs["nested_data"]:
                    df.attrs["nested_data"][column_name] = [[] for _ in range(len(df))]

                # Split the updated value into nested components
                updated_value = df.iat[row, col]
                df.attrs["nested_data"][column_name][row] = self.split_into_components(updated_value)

        # Recalculate PROVISIONEDLINK
        self.update_provisioned_links()

        # Emit layoutChanged to refresh the view
        self.model.layoutChanged.emit()

    def update_provisioned_links(self, delete=False):
        """
        Recalculates or cleans up the PROVISIONEDLINK column.
        When `delete` is True, ensures no references to deleted columns remain.
        """
        print("BOOO 1")
        df = self.model.get_dataframe()

        if delete:
            # If deleting, clean up `split_columns` and `nested_data` without creating new columns
            if "split_columns" in df.attrs:
                df.attrs["split_columns"] = [col for col in df.attrs["split_columns"] if col in df.columns]

            if "nested_data" in df.attrs:
                df.attrs["nested_data"] = {
                    col: nested for col, nested in df.attrs["nested_data"].items() if col in df.columns
                }

            # Ensure `PROVISIONEDLINK` is consistent with the remaining columns
            if "PROVISIONEDLINK" in df.columns:
                for row in range(len(df)):
                    provisioned_columns = df.columns[2:]  # Adjust as needed for your schema
                    joined_value = "/".join(
                        str(df.at[row, col]) for col in provisioned_columns if pd.notnull(df.at[row, col])
                    )
                    df.at[row, "PROVISIONEDLINK"] = joined_value

        else:
            # Regular recalculation logic (creation mode)
            self.create_nested_components()

            if "PROVISIONEDLINK" not in df.columns:
                df["PROVISIONEDLINK"] = None

            for row in range(len(df)):
                provisioned_columns = df.columns[2:]  # Adjust as needed
                joined_value = "/".join(
                    str(df.at[row, col]) for col in provisioned_columns if pd.notnull(df.at[row, col])
                )
                df.at[row, "PROVISIONEDLINK"] = joined_value

        # Notify the model of the changes
        self.model.layoutChanged.emit()

    def update_provisioned_link_for_row(self, row):
        """
        Updates the PROVISIONEDLINK value for a single row.
        Concatenates the values of all columns from the 3rd onward.
        """
        df = self.model.get_dataframe()
        provisioned_columns = df.columns[2:]  # Get columns from the 3rd column onward

        joined_value = "/".join(
            str(df.at[row, col]) for col in provisioned_columns if pd.notnull(df.at[row, col])
        )
        df.at[row, "PROVISIONEDLINK"] = joined_value  # Update the column for the given row

        print(f"Row {row}: PROVISIONEDLINK updated to {joined_value}")

    def create_nested_components(self):
        """
        Create nested lists for split columns in the DataFrame.
        """
        df = self.model.get_dataframe()
        split_columns = df.attrs.get("split_columns", [])

        # Generate split columns if not already present
        if not split_columns:
            split_data = df["PROVISIONEDLINK"].str.split("/", expand=True)
            split_columns = [f"Segment {i+1}" for i in range(split_data.shape[1])]
            df[split_columns] = split_data
            df.attrs["split_columns"] = split_columns

        # Embed nested lists
        self.embed_nested_lists(split_columns)

        # Reflect changes in the model
        self.model.update_dataframe(df)

    def embed_nested_lists(self, columns):
        """
        Embed nested lists into specified columns while keeping the main DataFrame intact.
        """
        df = self.model.get_dataframe()

        if "nested_data" not in df.attrs:
            df.attrs["nested_data"] = {}

        for column in columns:
            if column not in df.columns:
                raise ValueError(f"Column '{column}' not found in DataFrame.")

            # Generate nested components for each cell in the column
            nested_lists = df[column].apply(self.split_into_components).tolist()
            df.attrs["nested_data"][column] = nested_lists

        # Reflect changes in the model
        self.model.update_dataframe(df)

    def split_into_components(self, value):
        """
        Split a string value into nested components while retaining delimiters.
        """
        if pd.isnull(value) or not isinstance(value, str):
            return []
        return re.split(r'(_|-|\.)', value)

    def load_data(self):
        """Load data from a DataFrame or file."""
        if self.dataframe_input is not None and isinstance(self.dataframe_input, pd.DataFrame):
            self.load_from_dataframe(self.dataframe_input)
        elif self.file_path:
            self.load_file()

    def open_search_replace_dialog(self):
        """
        Opens the NestedEditor directly for search-and-replace functionality on the DataFrame.
        The editor will allow users to perform search-and-replace seamlessly.
        """
        try:
            # Pass the current DataFrame to the NestedEditor
            editor = NestedEditor(self.model.get_dataframe(), parent=self)
            editor.setWindowTitle("Search and Replace Editor")  # Optional: Customize window title
            editor.exec_()

            # Update the main DataFrame after the editor closes
            updated_dataframe = editor.get_dataframe()
            self.model.update_dataframe(updated_dataframe)

            QMessageBox.information(self, "Success", "Search and Replace completed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Search and Replace: {str(e)}")

    def load_from_dataframe(self, dataframe, create_embedded=False):
        """Load directly from an in-memory DataFrame."""
        self.create_embedded = create_embedded
        
        self.dataframe = dataframe
        self.model.update_dataframe(dataframe)

        # Reapply column resizing if enabled
        if self.auto_fit_columns:
            self.table_view.resizeColumnsToContents()

    def track_changes(self):
        """Track if any changes were made to the DataFrame."""
        self.changes_made = True

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
            # Move the column and get the new index
            new_col_index = self.model.move_column(index.column(), -1)
            if new_col_index is not None:
                # Update the selection to the new column
                self.table_view.setCurrentIndex(self.table_view.model().index(index.row(), new_col_index))
                # Update provisioned links after moving the column
                self.update_provisioned_links()
                # Keep the column selected
                self.table_view.selectColumn(new_col_index)

    def move_column_right(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            # Move the column and get the new index
            new_col_index = self.model.move_column(index.column(), 1)
            if new_col_index is not None:
                # Update the selection to the new column
                self.table_view.setCurrentIndex(self.table_view.model().index(index.row(), new_col_index))
                # Update provisioned links after moving the column
                self.update_provisioned_links()
                # Keep the column selected
                self.table_view.selectColumn(new_col_index)

    def add_row(self):
        self.model.add_row()

    def add_column(self):
        """Add a new column to the DataFrame, with an optional randomly generated column name."""
        # Generate a random column name
        random_column_name = f"Column_{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}"

        # Prompt the user for a column name, defaulting to the random name
        column_name, ok = QInputDialog.getText(
            self,
            "Add Column",
            "Column name (leave blank to use a randomly generated name):",
            text=random_column_name
        )

        if ok:
            column_name = column_name.strip() or random_column_name  # Fallback to random name if input is empty
            dtype, ok_type = QInputDialog.getItem(
                self,
                "Select Data Type",
                "Choose column data type:",
                self.model.get_valid_dtypes(),
                editable=False
            )
            if ok_type and dtype:
                # Add the column via the model
                self.model.add_column(column_name=column_name, dtype=dtype)

                # Initialize nested data for the new column
                df = self.model.get_dataframe()
                if "nested_data" not in df.attrs:
                    df.attrs["nested_data"] = {}
                df.attrs["nested_data"][column_name] = [[] for _ in range(len(df))]

                # Recalculate PROVISIONEDLINK to account for the new column
                self.update_provisioned_links()

                # Synchronize nested data structures
                self.sync_nested_data_with_columns()

                # Notify the model that the structure has changed
                self.model.layoutChanged.emit()

    def delete_selected_columns(self):
        selected_columns = sorted(set(index.column() for index in self.table_view.selectionModel().selectedColumns()), reverse=True)
        if selected_columns:
            # Get the current DataFrame
            df = self.model.get_dataframe()

            # Remove columns from `nested_data` if they exist
            if "nested_data" in df.attrs:
                for col in selected_columns:
                    column_name = df.columns[col]
                    if column_name in df.attrs["nested_data"]:
                        del df.attrs["nested_data"][column_name]

            # Perform the actual column deletion
            self.model.delete_columns(selected_columns)

            # Use the delete flag to clean up attributes
            self.update_provisioned_links(delete=True)

            # Track changes and notify the model
            self.track_changes()

    def sync_nested_data_with_columns(self):
        """Synchronize the nested data structure with the current column order."""
        df = self.model.get_dataframe()
        if "nested_data" in df.attrs:
            new_nested_data = {}
            for column in df.columns:
                if column in df.attrs["nested_data"]:
                    new_nested_data[column] = df.attrs["nested_data"][column]
            df.attrs["nested_data"] = new_nested_data

    def delete_selected_rows(self):
        selected_rows = sorted(set(index.row() for index in self.table_view.selectionModel().selectedRows()), reverse=True)
        if selected_rows:
            self.model.delete_rows(selected_rows)
            self.track_changes()

    def sort_column(self):
        index = self.table_view.currentIndex()
        if index.isValid():
            self.model.sort_column(index.column())

    def clear_selected_data(self):
        selection = self.table_view.selectionModel().selectedIndexes()
        self.model.clear_selection(selection)

    def preview_nested_data(self, row, column):
        """
        Extract the nested data for a given cell and return a single-row DataFrame for editing.
        """
        column_name = self.model._dataframe.columns[column]
        nested_data = self.model._dataframe.attrs.get("nested_data", {}).get(column_name, [])

        if not nested_data or row >= len(nested_data):
            QMessageBox.warning(self, "No Nested Data", "No nested data available for this cell.")
            return None

        # Create a single-row DataFrame for editing
        preview_df = pd.DataFrame([nested_data[row]], columns=[f"Component {i}" for i in range(len(nested_data[row]))])
        return preview_df

    def generate_preview(self, updated_components):
        """
        Generate the reassembled preview from the updated nested components.
        """
        return "".join(updated_components)  # Simply join components for now

    def show_preview_dialog(self, compiled_result, apply_callback):
        """
        Show a dialog to preview the reassembled result and allow the user to confirm or cancel.

        Args:
            compiled_result (str): The reassembled cell value.
            apply_callback (function): The function to call to apply changes.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Preview Changes")
        layout = QVBoxLayout(dialog)

        # Display the previewed value
        preview_label = QLabel(f"Preview of Compiled Result: {compiled_result}")
        layout.addWidget(preview_label)

        # Buttons to confirm or cancel
        button_layout = QHBoxLayout()
        confirm_button = QPushButton("Apply", dialog)
        cancel_button = QPushButton("Cancel", dialog)
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Connect buttons
        confirm_button.clicked.connect(lambda: (apply_callback(), dialog.accept()))
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def edit_nested_data(self, row, column):
        """Edit the nested data for a given cell."""
        preview_df = self.preview_nested_data(row, column)
        if preview_df is None:
            return  # No nested data to edit

        editor = NestedEditor(preview_df, self)
        editor.setAttribute(Qt.WA_DeleteOnClose)  # Allow the editor to run independently

        # Pass the current row and column context
        editor.set_context(row, column)

        editor.show()

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

        # Additional pass to update `PROVISIONEDLINK`
        provisioned_columns = df.columns[2:]  # Get columns from the 3rd column onward
        joined_value = "/".join(str(df.at[row, col]) for col in provisioned_columns if pd.notnull(df.at[row, col]))
        df.at[row, "PROVISIONEDLINK"] = joined_value  # Update `PROVISIONEDLINK`

        # Reflect changes in the UI
        self.model.layoutChanged.emit()
        QMessageBox.information(self, "Update Successful", f"Cell updated to: {new_value}\nPROVISIONEDLINK: {joined_value}")

    def show_context_menu(self, position):
        """Display a custom context menu for nested editing."""
        index = self.table_view.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self)
        nested_edit_action = QAction("Edit Nested Components", self)
        nested_edit_action.triggered.connect(lambda: self.edit_nested_data(index.row(), index.column()))
        menu.addAction(nested_edit_action)
        menu.exec(self.table_view.viewport().mapToGlobal(position))

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

        if editor.exec() == QDialog.Accepted:
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

        dialog.exec()

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

        dialog.exec()

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

        dialog.exec()

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

        if editor.exec() == QDialog.Accepted:
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
    def __init__(self, dataframe, parent=None, is_struct=False, struct_schema=None, auto_fit_columns=True):
        super().__init__(parent)
        self.setWindowTitle("Edit Nested Data" if not is_struct else "Edit Struct")
        self.resize(600, 400)
        self.parent_editor = parent  # Reference to the parent editor (DeepEditor)
        self.row = None
        self.column = None
        self.is_struct = is_struct
        self.struct_schema = struct_schema  # Schema for the struct, if available
        self.auto_fit_columns = auto_fit_columns  # Pass auto-fit behavior
        self.changes_made = False  # Track if any changes have been made

        # Handle empty or malformed DataFrames gracefully
        if not dataframe.empty:
            self.original_value = "".join(str(x) for x in dataframe.iloc[0].tolist() if x is not None)
        else:
            self.original_value = ""  # Fallback for empty DataFrame

        self.dataframe = dataframe

        # Enhanced Model for editing
        self.model = EnhancedPandasModel(
            self.dataframe, 
            editable=True, 
            auto_fit_columns=self.auto_fit_columns, 
            dragNdrop=True
        )
        self.model.dataChanged.connect(self.update_preview)

        # === Layout setup ===
        self.main_layout = QVBoxLayout(self)

        # Add Search-Replace Toolbar
        self.add_search_replace_toolbar()

        # Add a drag-and-drop test widget (for consistency with DeepEditor)
        self.temp_drag_input = DraggableTextInput(self)
        self.temp_drag_input.setPlaceholderText("Drop here to test drag-and-drop...")
        self.main_layout.addWidget(self.temp_drag_input)

        # === Live Preview Section ===
        self.preview_layout = QVBoxLayout()
        self.original_label = QLabel(f"Original: {self.original_value}", self)
        self.original_label.setStyleSheet("color: grey; font-size: 12px;")
        self.preview_label = QLabel(f"Preview: {self.original_value}", self)
        self.preview_label.setStyleSheet("color: black; font-size: 14px; font-weight: bold;")
        self.preview_layout.addWidget(self.original_label)
        self.preview_layout.addWidget(self.preview_label)
        self.main_layout.addLayout(self.preview_layout)

        # === Table View for Nested Data ===
        self.table_view = QTableView(self)
        self.table_view.setModel(self.model)
        self.table_view.setDragEnabled(True)
        self.table_view.setAcceptDrops(True)
        self.table_view.setDropIndicatorShown(True)
        self.table_view.setDragDropMode(QAbstractItemView.DragDrop)
        self.main_layout.addWidget(self.table_view)

        # Auto-fit columns if enabled
        if self.auto_fit_columns:
            self.table_view.resizeColumnsToContents()

        # === Add row/column controls ===
        self.control_layout = QHBoxLayout()

        self.add_column_button = QPushButton("Add Column", self)
        self.move_column_left_button = QPushButton("Move Column Left", self)
        self.move_column_right_button = QPushButton("Move Column Right", self)
        self.delete_column_button = QPushButton("Delete Column", self)
        self.control_layout.addWidget(self.add_column_button)
        self.control_layout.addWidget(self.move_column_left_button)
        self.control_layout.addWidget(self.move_column_right_button)
        self.control_layout.addWidget(self.delete_column_button)

        self.add_row_button = QPushButton("Add Row", self)
        self.delete_row_button = QPushButton("Delete Row", self)
        self.control_layout.addWidget(self.add_row_button)
        self.control_layout.addWidget(self.delete_row_button)

        self.move_row_up_button = QPushButton("Move Row Up", self)
        self.move_row_down_button = QPushButton("Move Row Down", self)
        self.control_layout.addWidget(self.move_row_up_button)
        self.control_layout.addWidget(self.move_row_down_button)
        self.main_layout.addLayout(self.control_layout)

        # === Save and Cancel buttons ===
        self.save_cancel_layout = QHBoxLayout()
        self.save_button = QPushButton("Save", self)
        self.cancel_button = QPushButton("Cancel", self)
        self.save_cancel_layout.addWidget(self.save_button)
        self.save_cancel_layout.addWidget(self.cancel_button)
        self.main_layout.addLayout(self.save_cancel_layout)

        # === Button Connections ===
        self.add_column_button.clicked.connect(self.add_column)
        self.move_column_left_button.clicked.connect(self.move_column_left)
        self.move_column_right_button.clicked.connect(self.move_column_right)
        self.delete_column_button.clicked.connect(self.delete_selected_columns)
        self.add_row_button.clicked.connect(self.add_row)
        self.delete_row_button.clicked.connect(self.delete_selected_rows)
        self.move_row_up_button.clicked.connect(self.move_row_up)
        self.move_row_down_button.clicked.connect(self.move_row_down)
        self.save_button.clicked.connect(self.save_changes)
        self.cancel_button.clicked.connect(self.close)

        # Auto-fit columns if enabled
        if self.auto_fit_columns:
            self.table_view.resizeColumnsToContents()

    def add_search_replace_toolbar(self):
        """Add a search-replace toolbar to the editor."""
        toolbar = QToolBar("Search and Replace", self)
        self.main_layout.addWidget(toolbar)

        # Search field
        toolbar.addWidget(QLabel("Search:", self))
        self.search_input = QLineEdit(self)
        toolbar.addWidget(self.search_input)

        # Replace field
        toolbar.addWidget(QLabel("Replace:", self))
        self.replace_input = QLineEdit(self)
        toolbar.addWidget(self.replace_input)

        # Options: Case-sensitive and Whole-word
        self.case_sensitive_checkbox = QCheckBox("Case Sensitive", self)
        toolbar.addWidget(self.case_sensitive_checkbox)

        self.whole_word_checkbox = QCheckBox("Whole Word", self)
        toolbar.addWidget(self.whole_word_checkbox)

        # Scope Selection
        self.scope_selector = QComboBox(self)
        self.scope_selector.addItems(["Selected Fields", "Entire Column", "Entire Row", "Entire Table"])
        toolbar.addWidget(QLabel("Scope:", self))
        toolbar.addWidget(self.scope_selector)

        # Execute button
        self.search_replace_button = QPushButton("Replace All", self)
        toolbar.addWidget(self.search_replace_button)

        # Connect the button to the search-replace method
        self.search_replace_button.clicked.connect(self.search_replace)

    def search_replace(self):
        """Perform search-and-replace on the DataFrame based on the selected scope."""
        search_term = self.search_input.text()
        replace_term = self.replace_input.text()
        case_sensitive = self.case_sensitive_checkbox.isChecked()
        whole_word = self.whole_word_checkbox.isChecked()
        scope = self.scope_selector.currentText()

        if not search_term:
            QMessageBox.warning(self, "Input Required", "Please enter a search term.")
            return

        flags = 0 if case_sensitive else re.IGNORECASE
        regex = rf"\b{re.escape(search_term)}\b" if whole_word else re.escape(search_term)

        def replace_func(value):
            if not isinstance(value, str):
                return value  # Skip non-string values
            return re.sub(regex, replace_term, value, flags=flags)

        # Determine scope and apply replacements
        try:
            if scope == "Selected Fields":
                indexes = self.table_view.selectionModel().selectedIndexes()
                for index in indexes:
                    row, col = index.row(), index.column()
                    self.dataframe.iat[row, col] = replace_func(self.dataframe.iat[row, col])

            elif scope == "Entire Column":
                indexes = self.table_view.selectionModel().selectedColumns()
                for index in indexes:
                    col = index.column()
                    self.dataframe.iloc[:, col] = self.dataframe.iloc[:, col].map(replace_func)

            elif scope == "Entire Row":
                indexes = self.table_view.selectionModel().selectedRows()
                for index in indexes:
                    row = index.row()
                    self.dataframe.iloc[row, :] = self.dataframe.iloc[row, :].map(replace_func)

            elif scope == "Entire Table":
                self.dataframe = self.dataframe.applymap(replace_func)

            # Update the model to reflect changes in the table view
            self.model.update_dataframe(self.dataframe)
            QMessageBox.information(self, "Success", "Search and replace completed.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to replace: {str(e)}")

    def save_changes(self):
        """Save changes to the parent or file."""
        self.accept()  # Close the editor

    def update_preview(self):
        """Update the live preview as edits are made."""
        current_value = "".join(str(x) for x in self.model.get_dataframe().iloc[0].tolist())
        self.preview_label.setText(f"Preview: {current_value}")

        # Update styles based on whether changes were made
        if current_value != self.original_value:
            self.preview_label.setStyleSheet("color: green; font-size: 14px; font-weight: bold;")
        else:
            self.preview_label.setStyleSheet("color: black; font-size: 14px; font-weight: bold;")
        self.changes_made = current_value != self.original_value

    def dragEnterEvent(self, event):
        print("Drag Enter Event triggered in NestedEditor!")
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        print("Drop Event triggered in NestedEditor!")
        super().dropEvent(event)

    def track_changes(self):
        """Mark that changes have been made to the data."""
        self.changes_made = True

    def update_preview(self):
        """Update the live preview as edits are made."""
        current_value = "".join(self.model.get_dataframe().iloc[0].tolist())
        self.preview_label.setText(f"Preview: {current_value}")

        # Update styles based on whether changes were made
        if current_value != self.original_value:
            self.preview_label.setStyleSheet("color: green; font-size: 14px; font-weight: bold;")
        else:
            self.preview_label.setStyleSheet("color: black; font-size: 14px; font-weight: bold;")
        self.changes_made = current_value != self.original_value

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

    def set_context(self, row, column):
        """Set the row and column context for updates."""
        self.row = row
        self.column = column

    def save_changes(self):
        """Save changes, update the parent, and close the editor."""
        updated_components = self.model.get_dataframe().iloc[0].tolist()

        # Push updates to the parent if context is set
        if self.row is not None and self.column is not None:
            self.parent_editor.apply_nested_updates(self.row, self.column, updated_components)

        self.changes_made = False  # Reset change tracking
        self.accept()  # Close the dialog

    def get_dataframe(self):
        """Return the edited DataFrame."""
        return self.model.get_dataframe()

    def add_row(self):
        """Adds a new row at the bottom."""
        self.model.add_row()

    def add_column(self):
        """Add a new column to the DataFrame, with an optional randomly generated column name."""
        # Generate a random column name
        random_column_name = f"Column_{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}"
        
        # Prompt the user for a column name, defaulting to the random name
        column_name, ok = QInputDialog.getText(
            self, 
            "Add Column", 
            "Column name (leave blank to use a randomly generated name):", 
            text=random_column_name
        )
        
        # Use the entered column name or the random name
        if ok:
            column_name = column_name.strip() or random_column_name  # Fallback to random name if input is empty
            dtype, ok_type = QInputDialog.getItem(
                self, 
                "Select Data Type", 
                "Choose column data type:",
                self.model.get_valid_dtypes(), 
                editable=False
            )
            if ok_type and dtype:
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

    def delete_row(self):
        """Delete the currently selected row (for lists or dicts only)."""
        if not self.is_struct:
            index = self.table_view.currentIndex()
            if index.isValid():
                self.model.delete_rows(index.row())

    def delete_column(self):
        """Delete the currently selected row (for lists or dicts only)."""
        if not self.is_struct:
            index = self.table_view.currentIndex()
            if index.isValid():
                self.model.delete_columns(index.row())

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

class SearchReplaceDialog(QDialog):
    def __init__(self, parent, dataframe):
        super().__init__(parent)
        self.parent_editor = parent
        self.dataframe = dataframe
        self.setWindowTitle("Search and Replace")
        self.resize(600, 400)

        # Main Layout
        layout = QVBoxLayout(self)

        # === Search/Replace Fields ===
        search_layout = QHBoxLayout()
        search_label = QLabel("Search for:", self)
        self.search_input = QLineEdit(self)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)

        replace_layout = QHBoxLayout()
        replace_label = QLabel("Replace with:", self)
        self.replace_input = QLineEdit(self)
        replace_layout.addWidget(replace_label)
        replace_layout.addWidget(self.replace_input)

        # === Options ===
        options_layout = QVBoxLayout()
        options_label = QLabel("Options:", self)
        self.case_sensitive_checkbox = QCheckBox("Case Sensitive", self)
        self.whole_word_checkbox = QCheckBox("Match Whole Word", self)
        self.delimiter_input = QLineEdit(self)
        self.delimiter_input.setPlaceholderText("Enter delimiters (comma-separated)")
        options_layout.addWidget(options_label)
        options_layout.addWidget(self.case_sensitive_checkbox)
        options_layout.addWidget(self.whole_word_checkbox)
        options_layout.addWidget(QLabel("Delimiters:", self))
        options_layout.addWidget(self.delimiter_input)

        # === Scope Selection ===
        scope_layout = QVBoxLayout()
        scope_label = QLabel("Apply to:", self)
        self.scope_selector = QComboBox(self)
        self.scope_selector.addItems(["Selected Fields", "Entire Column", "Entire Row", "Entire Table"])
        scope_layout.addWidget(scope_label)
        scope_layout.addWidget(self.scope_selector)

        # === Buttons ===
        button_layout = QHBoxLayout()
        preview_button = QPushButton("Preview", self)
        replace_button = QPushButton("Replace", self)
        cancel_button = QPushButton("Cancel", self)
        button_layout.addWidget(preview_button)
        button_layout.addWidget(replace_button)
        button_layout.addWidget(cancel_button)

        # === Assemble Layouts ===
        layout.addLayout(search_layout)
        layout.addLayout(replace_layout)
        layout.addLayout(options_layout)
        layout.addLayout(scope_layout)
        layout.addLayout(button_layout)

        # === Button Connections ===
        preview_button.clicked.connect(self.preview_changes)
        replace_button.clicked.connect(self.apply_changes)
        cancel_button.clicked.connect(self.reject)

    def preview_changes(self):
        """Preview changes based on search/replace options."""
        search_term = self.search_input.text()
        replace_term = self.replace_input.text()
        scope = self.scope_selector.currentText()
        case_sensitive = self.case_sensitive_checkbox.isChecked()
        whole_word = self.whole_word_checkbox.isChecked()
        delimiters = self.delimiter_input.text().split(",") if self.delimiter_input.text() else []

        if not search_term:
            QMessageBox.warning(self, "Input Required", "Please enter a search term.")
            return

        # Filter the DataFrame based on the selected scope
        if scope == "Selected Fields":
            indexes = self.parent().table_view.selectionModel().selectedIndexes()
            affected_df = self.extract_data_by_indexes(indexes)
        elif scope == "Entire Column":
            indexes = self.parent().table_view.selectionModel().selectedColumns()
            affected_df = self.extract_columns(indexes)
        elif scope == "Entire Row":
            indexes = self.parent().table_view.selectionModel().selectedRows()
            affected_df = self.extract_rows(indexes)
        else:  # Entire Table
            affected_df = self.dataframe.copy()

        # Log DataFrame state before processing
        print("Affected DataFrame before replacement:")
        print(affected_df)

        # Perform the replacement and show a preview in a NestedEditor
        modified_df = self.perform_search_replace(
            affected_df, search_term, replace_term, case_sensitive, whole_word, delimiters
        )

        # Log DataFrame state after processing
        print("Modified DataFrame:")
        print(modified_df)

        # Pass to NestedEditor
        try:
            nested_editor = NestedEditor(modified_df, parent=self)
            nested_editor.exec_()
        except Exception as e:
            print(f"Error initializing NestedEditor: {e}")
            QMessageBox.critical(self, "Error", f"Failed to preview changes: {e}")

    def apply_changes(self):
        """Apply the changes from the preview to the DataFrame."""
        
    def extract_data_by_indexes(self, indexes):
        """Extract data based on a set of selected indexes."""
        if not indexes:
            QMessageBox.warning(self, "No Selection", "No fields are selected.")
            return pd.DataFrame()  # Return an empty DataFrame if nothing is selected

        data = []
        for index in indexes:
            row, col = index.row(), index.column()
            value = self.dataframe.iloc[row, col]
            data.append([value])
        return pd.DataFrame(data, columns=["Value"])

    def extract_columns(self, indexes):
        """Extract data based on selected columns."""
        cols = [index.column() for index in indexes]
        return self.dataframe.iloc[:, cols]

    def extract_rows(self, indexes):
        """Extract data based on selected rows."""
        rows = [index.row() for index in indexes]
        return self.dataframe.iloc[rows, :]

    def perform_search_replace(self, dataframe, search_term, replace_term, case_sensitive, whole_word, delimiters):
        """Perform the search-replace operation with the specified options."""
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = rf"\b{re.escape(search_term)}\b" if whole_word else re.escape(search_term)

        def replace_func(x):
            if not isinstance(x, str):
                return x  # Skip non-string values
            if delimiters:
                for delimiter in delimiters:
                    parts = x.split(delimiter)
                    parts = [re.sub(regex, replace_term, part, flags=flags) for part in parts]
                    x = delimiter.join(parts)
                return x
            else:
                return re.sub(regex, replace_term, x, flags=flags)

        # Apply replacements element-wise
        try:
            return dataframe.applymap(replace_func)
        except Exception as e:
            print(f"Error during search-replace: {e}")
            raise

    @staticmethod
    def replace_with_delimiters(value, regex, replace_term, delimiters, flags):
        """Handle replacement with delimiters for whole-word matching."""
        if not isinstance(value, str):
            return value

        for delimiter in delimiters:
            parts = value.split(delimiter)
            parts = [re.sub(regex, replace_term, part, flags=flags) for part in parts]
            value = delimiter.join(parts)

        return value
