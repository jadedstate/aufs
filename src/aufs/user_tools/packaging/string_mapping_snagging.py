# src/aufs/user_tools/packaging/string_mapping_snagging.py

import os
import sys
import pandas as pd
from rapidfuzz import fuzz
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QTableView, QMessageBox, QComboBox, QStyledItemDelegate, 
    QStyle, QStyleOptionComboBox, QCheckBox, QAbstractItemView
    )
from PySide6.QtCore import Qt

current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')
sys.path.insert(0, src_path)

from src.aufs.user_tools.editable_pandas_model import EditablePandasModel, EnhancedPandasModel, SortableTableView

class CustomEditorDelegate(QStyledItemDelegate):
    def __init__(self, model, dropdown_column, parent_widget, parent=None):
        super().__init__(parent)
        self.model = model
        self.dropdown_column = dropdown_column
        self.parent_widget = parent_widget  # Explicit reference to the parent widget
        self.dropdown_options = {}

    def setModelData(self, editor, model, index):
        """Saves the editor's data back to the working_df and updates STATUS."""
        if isinstance(editor, QComboBox):
            selected_value = editor.currentText()

            # Retrieve and update the dropdown values
            collapsed_df = self.model.get_dataframe()
            dropdown_values = collapsed_df.iloc[index.row()][self.dropdown_column].split(", ")
            if selected_value in dropdown_values:
                new_values = [selected_value] + [v for v in dropdown_values if v != selected_value]
                self.model.setData(index, ", ".join(new_values), Qt.EditRole)

            # Update working_df STATUS
            dedupe_value = collapsed_df.iloc[index.row()][self.parent_widget.dedupe_column]
            working_df = self.parent_widget.working_df
            duplicate_rows = working_df[working_df[self.parent_widget.dedupe_column] == dedupe_value].index

            for row in duplicate_rows:
                working_df.at[row, "STATUS"] = "valid" if working_df.at[row, self.dropdown_column] == selected_value else "invalid"

            self.parent_widget.working_df = working_df.copy()
        else:
            super().setModelData(editor, model, index)

    def commit_and_close_editor(self, editor):
        """
        Commit the editor's data and close it, triggering a repaint.
        """
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)

    def paint(self, painter, option, index):
        """
        Custom paint method to display the selected value in the dropdown cell.
        """
        if not index.isValid():
            return

        # Get the current column name
        column_name = self.model.get_dataframe().columns[index.column()]

        if column_name == self.dropdown_column:
            # Retrieve the current value for the cell
            current_value = self.model.get_dataframe().iloc[index.row(), index.column()]
            if not isinstance(current_value, str):  # Guard against non-string values
                current_value = str(current_value)

            # Split the dropdown values and get the selected value
            dropdown_values = current_value.split(", ")
            selected_value = dropdown_values[0] if dropdown_values else ""  # Default to first item if available

            # Use QStyle to render the dropdown
            combo_box_option = QStyleOptionComboBox()
            combo_box_option.rect = option.rect
            combo_box_option.currentText = selected_value
            
            combo_box_option.state = option.state | QStyle.State_Enabled

            style = option.widget.style()
            style.drawComplexControl(QStyle.CC_ComboBox, combo_box_option, painter)

            # Render the text inside the dropdown
            text_rect = style.subControlRect(
                QStyle.CC_ComboBox, combo_box_option, QStyle.SC_ComboBoxEditField, option.widget
            )
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, selected_value)
        else:
            super().paint(painter, option, index)

    def createEditor(self, parent, option, index):
        """Creates the dropdown editor for the dropdown column."""
        column_name = self.model.get_dataframe().columns[index.column()]
        if column_name == self.dropdown_column:
            combo_box = QComboBox(parent)

            # Retrieve preordered dropdown values directly from collapsed_df
            collapsed_df = self.model.get_dataframe()
            dropdown_values = collapsed_df.iloc[index.row()][column_name].split(", ")

            # Populate the QComboBox with the preordered values
            combo_box.addItems(dropdown_values)

            # Trigger commit and repaint when a selection is made
            combo_box.activated.connect(lambda: self.commit_and_close_editor(combo_box))
            return combo_box

        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        """Populates the editor with the current value."""
        collapsed_df = self.model.get_dataframe()
        dropdown_values = collapsed_df.iloc[index.row()][self.dropdown_column].split(", ")

        # Assume the first value in the collapsed list is the prioritized value
        valid_value = dropdown_values[0]

        if isinstance(editor, QComboBox):
            current_index = editor.findText(valid_value)
            if current_index >= 0:
                editor.setCurrentIndex(current_index)
        else:
            super().setEditorData(editor, index)

class StringRemappingSnaggingWidget(QWidget):
    def __init__(self, dataframe, dedupe_column, dropdown_column=None, remove_double_dupes=True, show_only_dupes=True, parent=None):
        super().__init__(parent)

        # Validate deduplication column
        if dedupe_column not in dataframe.columns:
            raise ValueError(f"Deduplication column '{dedupe_column}' not found in DataFrame.")

        if dropdown_column is None:
            dropdown_column = dedupe_column

        if dropdown_column not in dataframe.columns:
            raise ValueError(f"Dropdown column '{dropdown_column}' not found in DataFrame.")

        self.dedupe_column = dedupe_column
        self.dropdown_column = dropdown_column
        self.show_only_dupes = show_only_dupes

        # Initialize working and updated DataFrames
        self.working_df = dataframe.copy()  # Starts as a copy of the input DataFrame
        self.original_df = dataframe.copy()
        self.updated_dataframe = None  # Will hold the finalized result

        # Add STATUS column if missing
        if "STATUS" not in self.working_df.columns:
            self.working_df["STATUS"] = "pending"

        # Remove double-dupes if the option is enabled
        if remove_double_dupes:
            self.remove_double_dupes()

        # Initialize STATUS column in working_df
        self.initialize_status_column()

        # Detect duplicates and prepare collapsed DataFrame
        self.collapsed_dataframe = self.collapse_duplicates(self.working_df, self.dedupe_column)

        # Apply initial filtering to show only duplicates if enabled
        if self.show_only_dupes:
            self.collapsed_dataframe = self.filter_only_duplicates(self.collapsed_dataframe)

        # Model setup
        self.model = EnhancedPandasModel(
            dataframe=self.collapsed_dataframe,
            value_options={self.dropdown_column: dataframe[self.dropdown_column].unique()},
            editable=True,
            auto_fit_columns=True,  # Enable this explicitly for testing the feature
            dragNdrop=True,
            ui_only=True
        )

        # Create UI
        # Use SortableTableView
        self.table_view = SortableTableView()
        self.table_view.setModel(self.model)
        self.table_view.setSelectionBehavior(SortableTableView.SelectRows)

        # Enable drag-and-drop for column reordering
        self.table_view.setDragDropMode(QAbstractItemView.InternalMove)
        self.table_view.setDragEnabled(True)
        self.table_view.setAcceptDrops(True)

        # Connect header clicks for sorting
        header = self.table_view.horizontalHeader()
        header.sectionClicked.connect(self.handle_header_click)

        # Apply column widths if auto_fit_columns is enabled
        if self.model.auto_fit_columns:
            self.apply_resizing_to_views()

        # Install custom delegate
        delegate = CustomEditorDelegate(self.model, self.dropdown_column, parent_widget=self)
        self.table_view.setItemDelegate(delegate)

        # Buttons
        self.save_button = QPushButton("Save and Return")
        self.reset_button = QPushButton("Reset")
        self.cancel_button = QPushButton("Cancel")

        # Checkbox to toggle showing all rows or only duplicates
        self.show_all_checkbox = QCheckBox("Show All Rows")
        self.show_all_checkbox.setChecked(not self.show_only_dupes)  # Reflect initial state
        self.show_all_checkbox.stateChanged.connect(self.toggle_row_visibility)

        # Connect buttons
        self.save_button.clicked.connect(self.return_dataframe)
        self.reset_button.clicked.connect(self.reset_dataframe)
        self.cancel_button.clicked.connect(self.close)

        # Layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.cancel_button)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.show_all_checkbox)  # Add the checkbox to the layout
        main_layout.addWidget(self.table_view)
        main_layout.addLayout(button_layout)

        # Set widget properties
        self.setLayout(main_layout)
        self.setWindowTitle("String Remapping Utility")

    def handle_header_click(self, column_index):
        print(f"Header clicked: column {column_index}")
        self.model.sort_column(column_index)
        
    def apply_resizing_to_views(self):
        """
        Iterates over all models and views in the application, applying column resizing where enabled.
        """
        model_view_pairs = [
            (self.model, self.table_view)
        ]

        for model, view in model_view_pairs:
            if isinstance(model, EditablePandasModel):
                model.apply_column_widths(view)

    def filter_only_duplicates(self, dataframe):
        """
        Filters the collapsed dataframe to include only duplicates based on the dedupe_column.
        """
        duplicate_groups = self.working_df.groupby(self.dedupe_column).size()
        duplicate_keys = duplicate_groups[duplicate_groups > 1].index
        return dataframe[dataframe[self.dedupe_column].isin(duplicate_keys)].reset_index(drop=True)

    def toggle_row_visibility(self, state):
        """Toggles between showing all rows and only duplicates."""
        if self.show_all_checkbox.isChecked():
            self.collapsed_dataframe = self.collapse_duplicates(self.working_df, self.dedupe_column)
        else:
            self.collapsed_dataframe = self.filter_only_duplicates(
                self.collapse_duplicates(self.working_df, self.dedupe_column)
            )

        self.model.update_dataframe(self.collapsed_dataframe, view=self.table_view)

    def remove_double_dupes(self):
        """
        Removes rows from working_df where both the dedupe_column and dropdown_column
        have identical duplicate values.
        """
        dedupe_col = self.dedupe_column
        dropdown_col = self.dropdown_column

        # Find double-dupes
        duplicates = self.working_df.duplicated(subset=[dedupe_col, dropdown_col], keep='first')
        
        # Remove double-dupes from working_df
        self.working_df = self.working_df.loc[~duplicates].reset_index(drop=True)

        # Debugging
        # print("working_df after removing double-dupes:", self.working_df)

    def initialize_status_column(self):
        """
        Ensures the STATUS column in working_df is initialized properly.
        """
        valid_status_values = ["pending", "valid", "invalid"]

        # Ensure missing or invalid STATUS values are set to "pending"
        self.working_df["STATUS"] = self.working_df["STATUS"].apply(
            lambda x: x if x in valid_status_values else "pending"
        )

        # Group by the dedupe column and set STATUS appropriately for "pending" rows only
        duplicate_groups = self.working_df.groupby(self.dedupe_column)
        for name, group in duplicate_groups:
            # Find indices of rows with STATUS == "pending"
            pending_indices = group[group["STATUS"] == "pending"].index

            if len(group) > 1:
                # For duplicates, set pending rows to "invalid"
                self.working_df.loc[pending_indices, "STATUS"] = "invalid"
            else:
                # For non-duplicates, set pending rows to "valid"
                self.working_df.loc[pending_indices, "STATUS"] = "valid"

    def collapse_duplicates(self, dataframe, dedupe_column):
        """
        Create a collapsed DataFrame purely for display purposes, ensuring dropdown values are ordered.
        """
        dataframe["STATUS"] = dataframe["STATUS"].fillna("pending").astype(str).str.strip()


        duplicate_groups = dataframe.groupby(dedupe_column)
        collapsed_rows = []

        for name, group in duplicate_groups:
            # Separate valid and other rows
            valid_rows = group[group["STATUS"] == "valid"]
            other_rows = group[group["STATUS"] != "valid"]

            # Collect dropdown values
            valid_values = list(valid_rows[self.dropdown_column])  # Valid rows first
            other_values = list(other_rows[self.dropdown_column])  # Non-valid rows

            # Apply fuzzy matching to reorder "other" values
            if other_values:
                other_values = self.apply_fuzzy_sorting(other_values, name)

            # Combine valid values (always on top) with fuzzy-sorted other values
            dropdown_values = valid_values + other_values

            # Store dropdown values as a comma-separated string
            collapsed_row = {
                dedupe_column: name,
                self.dropdown_column: ", ".join(dropdown_values),  # Dropdown options
            }

            collapsed_rows.append(collapsed_row)

        return pd.DataFrame(collapsed_rows)

    def apply_fuzzy_sorting(self, dropdown_values, dedupe_key):
        """
        Reorder dropdown values based on fuzzy similarity to the dedupe key.
        """
        # Define a function to calculate similarity scores
        def similarity(value):
            return fuzz.partial_ratio(value.lower(), dedupe_key.lower())

        # Sort dropdown values by similarity (descending order)
        sorted_values = sorted(dropdown_values, key=similarity, reverse=True)
        return sorted_values

    def reset_dataframe(self):
        """
        Resets the working DataFrame to match the original DataFrame.
        """
        confirmation = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset all changes?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirmation == QMessageBox.Yes:
            self.working_df = self.original_df.copy()
            self.collapsed_dataframe = self.collapse_duplicates(self.working_df, self.dedupe_column)
            self.model.update_dataframe(self.collapsed_dataframe)

    def return_dataframe(self):
        """Updates the working DataFrame and returns it to the caller."""
        self.updated_dataframe = self.working_df.copy()
        # print("Updated working DataFrame returned:", self.updated_dataframe)  # Debugging
        self.close()

    def get_result(self):
        """
        Returns the final DataFrame.
        """
        return getattr(self, "updated_dataframe", None)

    def update_model(self):
        """Refresh the model with the latest collapsed_df."""
        self.collapsed_dataframe = self.collapse_duplicates(self.working_df, self.dedupe_column)
        
        # Debug: Confirm collapsed_df is being passed to the model
        print("Updating model with collapsed_df:")
        print(self.collapsed_dataframe)
        
        self.model.update_dataframe(self.collapsed_dataframe)

if __name__ == "__main__":
    # Example DataFrame
    data = {
        "Name": ["Alice", "Bob", "Alice", "Charlie", "Bob", "Eve", "Alice"],
        "Prize": ["90", "20", "10", "30", "60", "40", "78"],
        "STATUS": [None, None, None, None, None, None, None],
    }

    df = pd.DataFrame(data)

    app = QApplication(sys.argv)
    widget = StringRemappingSnaggingWidget(dataframe=df, dedupe_column="Name", dropdown_column="Prize")
    widget.show()
    app.exec()

    # Get the updated DataFrame
    updated_df = widget.get_result()
    print(updated_df)