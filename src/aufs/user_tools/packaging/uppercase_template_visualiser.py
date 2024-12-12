# src/aufs/user_tools/packaging/uppercase_template_visualiser.py

import os
import sys
import pandas as pd
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTableWidget, QTreeWidgetItemIterator, 
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView, QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt

# --- Existing Functions ---
def decompose_file_paths(df, file_col='PROVISIONEDLINK'):
    """Decomposes file paths into hierarchical levels."""
    hierarchy_data = []

    for path in df[file_col]:
        
        if path.startswith("."):
            path = path[1:] 

        if not path.startswith("/"):
            path = "/" + path  # Ensure all paths have a leading slash

        # Split the normalized path
        parts = path.split(os.sep)
        # print("Path Parts: ")
        # print(parts)

        hierarchy = {file_col: path}  # Store the original file path

        # Decompose into hierarchy levels
        for i in range(1, len(parts) + 1):
            hierarchy[f'level_{i}'] = os.sep.join(parts[:i])

        hierarchy_data.append(hierarchy)

    # print("Hierarchy_data - this is where we're losing the non-slashed paths:")
    # print(hierarchy_data)

    # Convert to DataFrame
    decomposed_df = pd.DataFrame(hierarchy_data)

    # Fill NaNs with empty strings and ensure consistent types
    decomposed_df.fillna('', inplace=True)
    decomposed_df = decomposed_df.astype(str)
    # print("decomposed df raw: ")
    # print(decomposed_df)

    # Drop the normalized PROVISIONEDLINK
    decomposed_df.drop(columns=[file_col], inplace=True)

    # Add the original PROVISIONEDLINK column back
    decomposed_df.insert(0, file_col, df[file_col])
    # print("decomposed df after column replacement: ")
    # print(decomposed_df)

    return decomposed_df

def build_tree_structure(decomposed_df):
    """Builds unique parent-child relationships for the tree view."""
    tree_rows = []

    # Identify level columns (level_1, level_2, ...)
    level_cols = [col for col in decomposed_df.columns if col.startswith('level_')]

    # Iterate through levels starting from level_2 (since level_1 has no parent)
    for i in range(1, len(level_cols)):
        parent_col = level_cols[i - 1]
        child_col = level_cols[i]

        # Create parent-child pairs for this level
        level_relationships = (
            decomposed_df[[parent_col, child_col]]
            .drop_duplicates()
            .rename(columns={parent_col: "parent", child_col: "child"})
        )

        # Remove rows where child is empty (indicates end of hierarchy)
        level_relationships = level_relationships[level_relationships["child"] != ""]

        # Append these relationships to the tree_rows
        tree_rows.append(level_relationships)

    # Combine all levels into a single DataFrame
    tree_df = pd.concat(tree_rows, ignore_index=True)
    # print(tree_df)

    # Add computed columns
    tree_df['short_name'] = tree_df['child'].apply(lambda x: os.path.basename(x) if isinstance(x, str) and x else "")
    tree_df['is_expanded'] = False  # Default state
    tree_df['display_name'] = tree_df['short_name']  # Initial display name
    return tree_df

# --- Visualizer Implementation ---
class FileTreeVisualizer(QWidget):
    def __init__(self, df, tree_only=True):
        super().__init__()
        self.resize(1400, 650)
        self.df = df
        self.decomposed_df = decompose_file_paths(self.df)
        self.tree_df = build_tree_structure(self.decomposed_df)
        self.edited_df = None

        # If tree_only, skip initializing the table UI
        if tree_only:
            self.tree_window = TreeViewWidget(self.tree_df, parent_visualizer=self)
            self.tree_window.show()
        else:
            self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Table view
        self.table = QTableWidget()
        self.load_table(self.decomposed_df)
        layout.addWidget(self.table)

        # Button to show tree view
        self.tree_button = QPushButton("Show Tree View")
        self.tree_button.clicked.connect(self.show_tree_view)
        layout.addWidget(self.tree_button)

        # Set layout and window title
        self.setLayout(layout)
        self.setWindowTitle("File Tree Visualizer")

    def close_all(self):
        """Cleanly close the visualizer and any open windows."""
        if hasattr(self, "tree_window") and self.tree_window.isVisible():
            self.tree_window.close()
        self.close()

    def update_edited_df(self, edited_df):
        """Update the edited DataFrame."""
        self.edited_df = edited_df
        print("Updated edited_df:")
        print(self.edited_df)
        self.update_decomposed_df(self.edited_df)

    def load_table(self, df):
        """Load a DataFrame into the table view."""
        self.table.setColumnCount(len(df.columns))
        self.table.setRowCount(len(df))
        self.table.setHorizontalHeaderLabels(df.columns)
        
        for row_idx, row_data in df.iterrows():
            for col_idx, value in enumerate(row_data):
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

        # Resize columns to fit content
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def show_tree_view(self):
        """Launch the tree view window."""
        self.tree_window = TreeViewWidget(self.tree_df)
        self.tree_window.show()

    def update_decomposed_df(self, df):
        """Update the decomposed DataFrame and refresh views."""
        self.decomposed_df = decompose_file_paths(df)
        self.tree_df = build_tree_structure(self.decomposed_df)
        self.load_table(self.decomposed_df)

class TreeViewWidget(QWidget):
    def __init__(self, tree_df, parent_visualizer=None):
        super().__init__()
        self.tree_df = tree_df
        self.parent_visualizer = parent_visualizer  # Optional parent visualizer

        # Track whether all nodes are currently expanded
        self.all_expanded = False

        self.init_ui()

    def init_ui(self):
        self.resize(1550, 800)
        layout = QVBoxLayout()

        # Tree view widget
        self.tree_view = QTreeWidget()
        self.tree_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree_view.setHeaderLabel("File Hierarchy")
        layout.addWidget(self.tree_view)

        # Toggle button for expanding/collapsing all nodes
        self.toggle_button = QPushButton("Open All")
        self.toggle_button.clicked.connect(self.toggle_expand_collapse)
        layout.addWidget(self.toggle_button)

        # Checkbox to toggle between full path and node name
        self.checkbox = QCheckBox("Show Full Path")
        self.checkbox.stateChanged.connect(self.toggle_display_name)
        layout.addWidget(self.checkbox)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close_all)
        layout.addWidget(close_button)

        # Build tree
        self.build_tree()

        # Set layout and window title
        self.setLayout(layout)
        self.setWindowTitle("Tree View")

    def toggle_expand_collapse(self):
        """Toggle between expanding and collapsing all nodes."""
        # Flip the state
        self.all_expanded = not self.all_expanded

        # Update the button text
        self.toggle_button.setText("Close All" if self.all_expanded else "Open All")

        # Update the `is_expanded` column in the tree_df
        self.tree_df['is_expanded'] = self.all_expanded

        # Rebuild the tree to reflect the new state
        self.build_tree()

    def close_all(self):
        """Close the tree view and the parent visualizer if present."""
        if self.parent_visualizer:
            self.parent_visualizer.close_all()
        else:
            self.close()

    def toggle_display_name(self):
        """Toggle between showing full path and short name."""
        self.save_expanded_state()
        self.show_full_path = self.checkbox.isChecked()
        self.tree_df['display_name'] = self.tree_df['child'] if self.show_full_path else self.tree_df['short_name']
        self.build_tree()

    def build_tree(self):
        """Build the tree view from the DataFrame."""
        self.tree_view.clear()
        root_items = {}

        for _, row in self.tree_df.iterrows():
            parent_name = row['parent']
            child_name = row['child']
            display_name = row['display_name']
            is_expanded = row['is_expanded']

            # Handle root nodes (parent is empty)
            if parent_name == '':
                root_item = QTreeWidgetItem(self.tree_view, [display_name])
                root_item.setExpanded(is_expanded)
                root_items[child_name] = root_item
            else:
                parent_item = root_items.get(parent_name, None)
                if parent_item:
                    child_item = QTreeWidgetItem(parent_item, [display_name])
                    root_items[child_name] = child_item
                    child_item.setExpanded(is_expanded)

    def save_expanded_state(self):
        """Save expanded states directly into the DataFrame."""
        iterator = QTreeWidgetItemIterator(self.tree_view)
        while iterator.value():
            item = iterator.value()
            child_name = item.text(0)  # Match to the DataFrame's display name
            is_expanded = item.isExpanded()
            self.tree_df.loc[self.tree_df['display_name'] == child_name, 'is_expanded'] = is_expanded
            iterator += 1

        # Debugging: Check the updated DataFrame
        # print(self.tree_df)

    def file_col_rebuilder(self):
        """Rebuild the file_col (e.g., PROVISIONEDLINK) from tree_df."""
        filtered_df = self.tree_df[
            self.tree_df['child'].apply(lambda x: os.path.splitext(x)[1] != "")
        ]
        self.edited_df = filtered_df[['child']].rename(columns={'child': 'PROVISIONEDLINK'})
        print("Rebuilt file_col (edited_df):")
        print(self.edited_df)
        return self.edited_df

    def integrate_rebuilder(self):
        """Example integration to rebuild file_col."""
        rebuilt_df = self.file_col_rebuilder()
        parent_visualiser = FileTreeVisualizer
        parent_visualiser.update_edited_df(rebuilt_df)

# --- Main Method for Testing ---
def main():
    # Sample DataFrame
    # data = {'PROVISIONEDLINK': [
    #     '/root/folder1/file1.txt',
    #     '/root/folder1/file2.txt',
    #     '/root/folder2/subfolder1/file3.txt',
    #     '/root/folder2/subfolder1/file4.txt',
    #     '/groot/folder2/subfolder1/file3.txt'
    # ]}
    # df = pd.DataFrame(data)
    df = pd.read_csv("/Users/uel/.aufs/config/packaging/global/matchmove/aufs_pkg_matchmove.csv")
    # df = pd.read_csv("/Users/uel/.aufs/config/packaging/global/matchmove/aufs_pkg_matchmove_geo_only.csv")
    df = df[['PROVISIONEDLINK']]
    # print(df)

    app = QApplication(sys.argv)
    tree_only = False
    if not tree_only:
        visualizer = FileTreeVisualizer(df, tree_only=tree_only)
        visualizer.show()
    else:
        FileTreeVisualizer(df, tree_only=tree_only)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
