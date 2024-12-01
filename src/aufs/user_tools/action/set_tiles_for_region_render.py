import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QPushButton, QSpinBox, QCheckBox,
    QHBoxLayout, QGroupBox, QSizePolicy, QComboBox
)
from .tile_placement import TilePlacement

class TileMatrixDialog(QDialog):
    def __init__(self, x_tiles=4, y_tiles=3, lock_tiles=False, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Tile Matrix Configuration')
        self.layout = QVBoxLayout(self)

        # X and Y input
        self.xy_layout = QHBoxLayout()

        self.x_input = QSpinBox(self)
        self.x_input.setMinimum(1)
        self.x_input.setValue(x_tiles)
        self.x_input.setPrefix('X: ')
        self.x_input.setFixedWidth(75)  # Fix the width to 75px
        if lock_tiles:
            self.x_input.setEnabled(False)  # Lock the X input

        self.y_input = QSpinBox(self)
        self.y_input.setMinimum(1)
        self.y_input.setValue(y_tiles)
        self.y_input.setPrefix('Y: ')
        self.y_input.setFixedWidth(75)  # Fix the width to 75px
        if lock_tiles:
            self.y_input.setEnabled(False)  # Lock the Y input

        self.xy_layout.addWidget(self.x_input)
        self.xy_layout.addWidget(self.y_input)
        self.xy_layout.addStretch()  # Justify left

        # Origin and Tile Order dropdowns
        self.ordering_layout = QHBoxLayout()

        self.origin_combo = QComboBox(self)
        self.origin_combo.addItems(["Top-Left", "Bottom-Left"])
        self.origin_combo.setCurrentIndex(0)  # Default to 'Top-Left'

        self.order_combo = QComboBox(self)
        self.order_combo.addItems(["Row-by-Row", "Column-by-Column", "Row-by-Row-Bounce", "Column-by-Column-Bounce"])
        self.order_combo.setCurrentIndex(1)  # Default to 'Column-by-Column'

        self.ordering_layout.addWidget(self.origin_combo)
        self.ordering_layout.addWidget(self.order_combo)
        self.ordering_layout.addStretch()  # Justify left

        self.check_submit_layout = QHBoxLayout()

        # Global toggle button
        self.global_toggle = QCheckBox('Toggle All', self)
        self.global_toggle.stateChanged.connect(self.toggle_all_tiles)

        # Submit and Cancel buttons
        self.submit_button = QPushButton('Submit', self)
        self.submit_button.clicked.connect(self.accept)
        
        self.check_submit_layout.addWidget(self.global_toggle)
        self.check_submit_layout.addWidget(self.submit_button)
        self.check_submit_layout.addStretch()  # Justify left

        # Grid layout for tiles inside a QGroupBox
        self.grid_groupbox = QGroupBox("Tile Grid")
        self.grid_layout = QGridLayout(self.grid_groupbox)
        self.grid_groupbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.cancel_button = QPushButton('Cancel', self)
        self.cancel_button.clicked.connect(self.reject)

        self.layout.addLayout(self.xy_layout)
        self.layout.addLayout(self.ordering_layout)  # Add the ordering dropdowns below the xy_layout
        self.layout.addLayout(self.check_submit_layout)
        self.layout.addWidget(self.grid_groupbox)  # Add the grid groupbox to the layout
        self.layout.addWidget(self.cancel_button)

        # Set the main layout
        self.setLayout(self.layout)

        # Initial tiles visualization
        self.visualize_tiles()

        # Connect X and Y inputs and dropdowns to the visualize function
        self.x_input.valueChanged.connect(self.visualize_tiles)
        self.y_input.valueChanged.connect(self.visualize_tiles)
        self.origin_combo.currentIndexChanged.connect(self.visualize_tiles)
        self.order_combo.currentIndexChanged.connect(self.visualize_tiles)

    def visualize_tiles(self):
        # Clear the existing grid
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget is not None: 
                widget.deleteLater()

        x_tiles = self.x_input.value()
        y_tiles = self.y_input.value()

        origin = self.origin_combo.currentText().lower().replace("-", "_")
        order = self.order_combo.currentText().lower().replace("-", "_")

        self.tile_checkboxes = []

        tile_placement = TilePlacement(x_tiles, y_tiles, origin=origin, traversal=order)
        placements = tile_placement.generate_tile_placements()

        for tile_number, row, column in placements:
            checkbox = QCheckBox(f'Tile_{tile_number}', self)
            self.grid_layout.addWidget(checkbox, row, column)  # Add checkbox to grid layout
            self.tile_checkboxes.append(checkbox)

    def toggle_all_tiles(self, state):
        for checkbox in self.tile_checkboxes:
            checkbox.setChecked(state)

    def get_result(self):
        """
        Returns the X, Y values and the selected tile indices.
        If all tiles are selected, returns just X, Y.
        Otherwise, returns X, Y, and a list of selected tile indices.
        """
        x_tiles = self.x_input.value()
        y_tiles = self.y_input.value()
        selected_tiles = [index for index, checkbox in enumerate(self.tile_checkboxes) if checkbox.isChecked()]

        if len(selected_tiles) == len(self.tile_checkboxes):
            return x_tiles, y_tiles
        else:
            return x_tiles, y_tiles, selected_tiles
