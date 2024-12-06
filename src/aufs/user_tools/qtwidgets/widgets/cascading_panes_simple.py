import sys
import os
import uuid
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QComboBox, QSizePolicy, QListWidgetItem, QScrollArea
)
from PySide6.QtGui import QDrag, QDragEnterEvent, QDropEvent, QFontMetrics
from PySide6.QtCore import Qt, QMimeData

class DraggableListWidget(QListWidget):
    def __init__(self, parent=None, is_sender=False, is_receiver=False, mime_type="text/plain"):
        super().__init__(parent)
        self.is_sender = is_sender
        self.is_receiver = is_receiver
        self.mime_type = mime_type
        self.setDragEnabled(self.is_sender)
        self.setAcceptDrops(self.is_receiver)

        # Set drag-and-drop mode for internal moves or external handling
        if self.is_sender and self.is_receiver:
            self.setDragDropMode(QListWidget.DragDrop)
        elif self.is_sender:
            self.setDragDropMode(QListWidget.DragOnly)
        elif self.is_receiver:
            self.setDragDropMode(QListWidget.DropOnly)

    def startDrag(self, supportedActions):
        """Start drag operation with robust MIME data handling."""
        current_item = self.currentItem()
        if not current_item:
            return

        drag = QDrag(self)
        mime_data = QMimeData()

        # Prepare MIME data
        item_text = current_item.text()
        item_index = self.row(current_item)
        # Add JSON-like structure to carry more information if needed
        mime_payload = {
            "text": item_text,
            "index": item_index,
            "source": "DraggableListWidget"
        }

        # Convert payload to a string or JSON format
        import json
        mime_data.setText(json.dumps(mime_payload))

        drag.setMimeData(mime_data)
        drag.exec_(supportedActions)

    def dragEnterEvent(self, event):
        """Handle the event when a drag enters the widget."""
        if self.is_receiver and event.mimeData().hasFormat(self.mime_type):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle the event when an item is dropped."""
        if self.is_receiver and event.mimeData().hasFormat(self.mime_type):
            dropped_text = event.mimeData().data(self.mime_type).data().decode("utf-8")  # Decode properly
            self.addItem(dropped_text)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Handle the event while dragging over the widget."""
        if self.is_receiver and event.mimeData().hasFormat(self.mime_type):
            event.accept()
        else:
            event.ignore()

class CascadingPaneManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cascading Panes Manager")
        self.resize(800, 400)

        self.dir_text_color = Qt.magenta  # Color for directory text
        self.file_text_color = Qt.cyan  # Color for file text

        # Pane tracking
        self.pane_order = []  # Ordered list of UUIDs
        self.cascade_state = {}
        self.pane_data = {}   # Mapping of UUID to DataFrame
        self.pane_display_data = {}  # Mapping of UUID to filtered DataFrame
        self.data_receiver = None  # Callback method for returned data

        # Root layout
        self.layout = QHBoxLayout(self)

    def set_data_receiver(self, receiver):
        """Set the method to receive data returned from the panes."""
        self.data_receiver = receiver

    def remove_panes_after(self, pane_uuid):
        """Remove panes to the right of the given pane."""
        # print("Pane removal happening now.")
        if pane_uuid not in self.pane_order:
            return

        # Determine the index of the specified pane
        index = self.pane_order.index(pane_uuid) + 1


        # Remove panes to the right of this pane
        for uuid_to_remove in self.pane_order[index:]:
            pane_to_remove = self.layout.itemAt(index).widget()
            if pane_to_remove:
                self.layout.removeWidget(pane_to_remove)
                pane_to_remove.deleteLater()
            del self.pane_data[uuid_to_remove]
        self.pane_order = self.pane_order[:index]

    def clear_downstream_panes(self, pane_uuid):
        """
        Clear all panes downstream of the given pane UUID using cascade_state.

        Args:
            pane_uuid (str): The UUID of the reference pane. 
        """
        # Find the index of the specified pane
        pane_index = self.cascade_state[pane_uuid]["pane_index"]

        # Collect UUIDs of panes to remove (those with a higher pane_index)
        uuids_to_remove = [
            uuid for uuid, info in self.cascade_state.items()
            if info["pane_index"] > pane_index
        ]

        # Remove the panes from layout and cascade_state
        for uuid in uuids_to_remove:
            widget = self.cascade_state[uuid]["widget"]
            if widget:
                self.layout.removeWidget(widget)
                widget.deleteLater()
            # Reset selection state in cascade_state
            del self.cascade_state[uuid]
            self.pane_order.remove(uuid)

    def display_pane(self, title, df, pane_type="list", is_sender=False, is_receiver=False, min_width=10, max_width=200):
        """Display a pane dynamically based on the DataFrame and pane type."""
        pane_uuid = self.create_pane_uuid()
        self.pane_order.append(pane_uuid)

        # Store DataFrame for this pane
        self.pane_data[pane_uuid] = df
        self.pane_display_data[pane_uuid] = df  # Initialize with the full DataFrame

        # Initialize tracking info for this pane early (without the widget)
        self.cascade_state[pane_uuid] = {
            "pane_index": len(self.pane_order) - 1,
            "selected_item": None,
            "selected_row_index": None,
            "title": title,
            "pane_type": pane_type,
            "widget": None,  # Widget reference will be added later
            "display_name": None,  # New field
        }

        # Clear downstream panes before creating the new one
        self.clear_downstream_panes(pane_uuid)
        self.remove_panes_after(pane_uuid)

        # Build the pane based on its type
        pane = None
        if pane_type == "list":
            pane = self.build_list_pane(title, df, pane_uuid, is_sender=is_sender)
        elif pane_type == "receiver":
            pane = self.build_receiver_pane(title, min_width, max_width)
        elif pane_type == "filterable_list":
            pane = self.build_filterable_list_pane(title, df, pane_uuid)
        elif pane_type == "basic_text":
            pane = self.build_basic_text_pane(title, df)

        if pane:
            # Add the pane to the layout
            self.layout.addWidget(pane)

            # Update the widget reference in cascade_state
            self.cascade_state[pane_uuid]["widget"] = pane

    def build_receiver_pane(self, title, min_width=10, max_width=200):
        """Build a resizable receiver pane."""
        pane = QWidget(self)
        pane_layout = QVBoxLayout(pane)
        pane.setLayout(pane_layout)

        # Add a title
        title_label = QLabel(title, pane)
        title_label.setAlignment(Qt.AlignCenter)
        pane_layout.addWidget(title_label)

        # Add the resizable receiver pane
        receiver = ResizableReceiverPane(pane, min_width=min_width, max_width=max_width)
        pane.receiver_widget = receiver  # Attach receiver to pane for future access
        pane_layout.addWidget(receiver)

        return pane

    def build_sender_pane(self, title, df, pane_uuid):
        """Build a sender pane."""
        pane = QWidget(self)
        pane_layout = QVBoxLayout(pane)
        pane.setLayout(pane_layout)

        # Add a title
        title_label = QLabel(title, pane)
        title_label.setAlignment(Qt.AlignCenter)
        pane_layout.addWidget(title_label)

        # Add the sender pane
        sender = SenderPane(pane)
        pane.sender_widget = sender  # Attach sender to pane for future access
        pane_layout.addWidget(sender)

        return pane

    def build_filterable_list_pane(self, title, df, pane_uuid, is_sender=False, is_receiver=False, mime_type="application/json"):
        """Build a pane with filtering capabilities and optional drag-and-drop."""
        pane = QWidget(self)
        pane_layout = QVBoxLayout(pane)
        pane.setLayout(pane_layout)

        # Add a title
        title_label = QLabel(title, pane)
        title_label.setAlignment(Qt.AlignCenter)
        pane_layout.addWidget(title_label)

        # Add a dropdown for filtering
        filter_dropdown = QComboBox(pane)
        filter_dropdown.addItems(["All", "Dirs only", "Files only"])
        filter_dropdown.setMinimumWidth(100)
        filter_dropdown.currentIndexChanged.connect(
            lambda index: self.apply_filter(index, pane_uuid)
        )
        pane_layout.addWidget(filter_dropdown)

        # Add a draggable and droppable list widget
        list_widget = DraggableListWidget(
            parent=pane, is_sender=is_sender, is_receiver=is_receiver, mime_type=mime_type
        )
        pane.list_widget = list_widget  # Attach list_widget to pane as an attribute
        pane_layout.addWidget(list_widget)

        # Populate the list widget with items from the DataFrame
        for idx, row in df.iterrows():
            display_text = (
                row["DISPLAYNAME"] if "DISPLAYNAME" in df.columns and pd.notna(row["DISPLAYNAME"])
                else row["Item"]
            )
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, idx)  # Store the DataFrame index as item data
            if row["OBJECTTYPE"] == "Directory":
                item.setForeground(self.dir_text_color)  # Set color for directories
            elif row["OBJECTTYPE"] == "File":
                item.setForeground(self.file_text_color)  # Set color for files
            list_widget.addItem(item)

        # Connect selection handling
        list_widget.itemClicked.connect(lambda item: self.handle_selection(item, pane_uuid))

        # Store the initial DataFrame for filtering later
        self.pane_display_data[pane_uuid] = df

        # Attach the pane to cascade_state for quick access in apply_filter
        self.cascade_state[pane_uuid]["widget"] = pane

        return pane

    def build_list_pane(self, title, df, pane_uuid, is_sender=False, is_receiver=False, mime_type="text/plain"):
        """Build a customizable list-based pane."""
        pane = QWidget(self)
        pane_layout = QVBoxLayout(pane)
        pane.setLayout(pane_layout)

        # Add a title
        title_label = QLabel(title, pane)
        title_label.setAlignment(Qt.AlignCenter)
        pane_layout.addWidget(title_label)

        # Add a custom list widget
        list_widget = DraggableListWidget(
            parent=pane, is_sender=is_sender, is_receiver=is_receiver, mime_type=mime_type
        )
        pane.list_widget = list_widget

        # Populate the list widget with items from the DataFrame
        for idx, row in df.iterrows():
            display_text = row.get("DISPLAYNAME", row["Item"])
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, idx)  # Store the DataFrame index as item data
            if row["OBJECTTYPE"] == "Directory":
                item.setForeground(self.dir_text_color)
            elif row["OBJECTTYPE"] == "File":
                item.setForeground(self.file_text_color)
            list_widget.addItem(item)

        # Connect selection handling
        list_widget.itemClicked.connect(lambda item: self.handle_selection(item, pane_uuid))
        pane_layout.addWidget(list_widget)

        return pane

    def create_pane_uuid(self):
        """Generate a unique UUID for a pane."""
        return str(uuid.uuid4())

    def apply_filter(self, filter_index, pane_uuid):
        """Apply a filter to the pane's display DataFrame."""
        # print(f"DEBUG: Applying filter {filter_index} on pane '{pane_uuid}'")

        # Retrieve the original DataFrame for the specified pane
        original_df = self.pane_data.get(pane_uuid)
        if original_df is None:
            print(f"DEBUG: No data found for pane '{pane_uuid}'.")
            return

        # Determine the filtered DataFrame based on the filter index
        if filter_index == 0:  # "All"
            filtered_df = original_df
        elif filter_index == 1:  # "Dirs only"
            filtered_df = original_df[original_df["OBJECTTYPE"] == "Directory"]
        elif filter_index == 2:  # "Files only"
            filtered_df = original_df[original_df["OBJECTTYPE"] == "File"]
        else:
            filtered_df = original_df  # Default to no filtering

        # Update the display DataFrame in cascade_state
        self.pane_display_data[pane_uuid] = filtered_df

        # Retrieve the pane's widget directly from cascade_state
        pane_info = self.cascade_state.get(pane_uuid)
        if not pane_info or not pane_info.get("widget"):
            print(f"DEBUG: Widget for pane '{pane_uuid}' not found.")
            return

        pane = pane_info["widget"]

        # Check for the presence of a list widget in the pane
        if not hasattr(pane, "list_widget"):
            print(f"DEBUG: Pane '{pane_uuid}' missing list widget.")
            return

        # Update the list widget with the filtered data
        list_widget = pane.list_widget
        list_widget.clear()  # Clear current items
        for idx, row in filtered_df.iterrows():
            item = QListWidgetItem(row["Item"])
            item.setData(Qt.UserRole, idx)  # Store the DataFrame index as item data
            if row["OBJECTTYPE"] == "Directory":
                item.setForeground(self.dir_text_color)  # Set color for directories
            elif row["OBJECTTYPE"] == "File":
                item.setForeground(self.file_text_color)  # Set color for files
            list_widget.addItem(item)

        # Reset selection state in cascade_state
        self.clear_downstream_panes(pane_uuid)        
        pane_info.update({"selected_item": None, "selected_row_index": None})

    def handle_selection(self, item, pane_uuid, refresh=False, replace_uuid="no"):
        """Handle user selection and pass the data to the receiver."""
        if replace_uuid == "no":
            self.selected_pane = pane_uuid
        elif replace_uuid != "1_before":
            self.selected_pane = self.find_another_pane_uuid(pane_uuid, flag=replace_uuid)
        elif replace_uuid != "1_after":
            self.selected_pane = self.find_another_pane_uuid(pane_uuid, flag=replace_uuid)

        # Get the current DataFrame for this pane
        current_df = self.pane_display_data.get(self.selected_pane)
        if current_df is None or current_df.empty:
            print(f"DEBUG: Current DataFrame for pane '{self.selected_pane}' is empty or not found.")
            return

        # Extract the selected item's text and associated row index
        if not refresh:
            selected_item = item.text()
            selected_row_index = item.data(Qt.UserRole)  # Retrieve the row index from the QListWidgetItem
        else:
            selected_item = self.cascade_state[self.selected_pane]["selected_item"]
            selected_row_index = self.cascade_state[self.selected_pane]["selected_row_index"]

        # Validate selected_row_index
        if selected_row_index is None or selected_row_index < 0 or selected_row_index >= len(current_df):
            print(f"DEBUG: Invalid selected_row_index: {selected_row_index}")
            return

        # Update the pane info
        self.cascade_state[self.selected_pane].update({
            "selected_item": selected_item,
            "selected_row_index": selected_row_index,
        })

        # Clear downstream panes
        self.clear_downstream_panes(self.selected_pane)
        # print("Current Pane setup: ")
        # print(self.cascade_state)

        # Remove panes to the right
        self.remove_panes_after(self.selected_pane)

        # Pass data to the receiver if required
        if self.data_receiver:
            self.data_receiver(current_df.iloc[[selected_row_index]])

    def find_pane_by_uuid(self, pane_uuid):
        """Find the pane widget by its UUID."""
        index = self.pane_order.index(pane_uuid) if pane_uuid in self.pane_order else -1
        if index >= 0:
            item = self.layout.itemAt(index)
            if item:
                return item.widget()
        print(f"DEBUG: Pane UUID '{pane_uuid}' not found.")
        return None

    def find_another_pane_uuid(self, pane_uuid, flag):
        """Find the UUID of another pane relative to the given pane's UUID.
        
        Args:
            pane_uuid (str): The UUID of the reference pane.
            flag (str): Determines the relative position to find. 
                        Options are '1_before', '1_after'.
        
        Returns:
            str: The UUID of the found pane or a default "xxxx-1111-xxxx" if not found.
        """
        default_uuid = "xxxx-1111-xxxx"

        # Ensure the pane_uuid exists in pane_order
        if pane_uuid not in self.pane_order:
            print(f"DEBUG: Pane UUID '{pane_uuid}' not found in pane_order.")
            return default_uuid

        index = self.pane_order.index(pane_uuid)

        if flag == "1_before":
            if index > 0:  # Check if there is a pane before
                return self.pane_order[index - 1]
            else:
                print(f"DEBUG: No pane before UUID '{pane_uuid}'. Returning default UUID.")
                return default_uuid

        elif flag == "1_after":
            if index < len(self.pane_order) - 1:  # Check if there is a pane after
                return self.pane_order[index + 1]
            else:
                print(f"DEBUG: No pane after UUID '{pane_uuid}'. Returning default UUID.")
                return default_uuid

        else:
            print(f"DEBUG: Invalid flag '{flag}' provided. Returning default UUID.")
            return default_uuid

    def build_basic_text_pane(self, title, df):
        """Build a pane to display basic text with a scrollable area."""
        pane = QWidget(self)
        pane_layout = QVBoxLayout(pane)
        pane.setLayout(pane_layout)

        # Set size policy for the pane
        pane.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Add a title
        title_label = QLabel(title, pane)
        title_label.setAlignment(Qt.AlignCenter)
        pane_layout.addWidget(title_label)

        # Create a scroll area for the text content
        scroll_area = QScrollArea(pane)
        scroll_area.setWidgetResizable(True)

        # Create a container widget for the text
        text_container = QWidget(scroll_area)
        text_layout = QVBoxLayout(text_container)
        text_container.setLayout(text_layout)

        # Add the text content
        text_label = QLabel(df.iloc[0]["Text"], text_container)
        text_label.setWordWrap(True)
        # text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        text_layout.addWidget(text_label)

        # Set the container as the scroll area's widget
        scroll_area.setWidget(text_container)
        pane_layout.addWidget(scroll_area)

        return pane

    def rebuild_panes(self):
        """Rebuild all panes from stored information."""
        self.clear_panes()

        for pane_uuid in self.pane_order:
            pane_info = self.cascade_state[pane_uuid]
            df = self.pane_data[pane_uuid]
            self.display_pane(
                pane_info["title"], df, pane_info["pane_type"]
            )

            # Restore selected item and row
            if pane_info["selected_item"] is not None:
                self.handle_selection(
                    pane_info["selected_item"],
                    pane_uuid,
                    refresh=True,
                )

    def clear_panes(self):
        """Clear all panes but keep data intact."""
        for uuid in self.pane_order:
            pane_to_remove = self.find_pane_by_uuid(uuid)
            if pane_to_remove:
                self.layout.removeWidget(pane_to_remove)
                pane_to_remove.deleteLater()
        self.pane_order = []

    def get_selected_item_and_path(self):
        """Return the current selection (item and path)."""
        if not self.selected_pane:
            return None, None

        selected_df = self.pane_data[self.selected_pane]
        selected_row = selected_df[selected_df["Item"] == self.selected_pane_selected_item]
        if not selected_row.empty:
            selected_path = selected_row.iloc[0]["Path"]
            return self.selected_pane_selected_item, selected_path
        return None, None

    @staticmethod
    def main():
        """Run the CascadingPaneManager for testing."""
        app = QApplication(sys.argv)

        # Example DataFrame
        example_df = pd.DataFrame({
            "Item": ["Option 1", "Option 2", "Option 3"],
            "Path": ["/path/to/option1", "/path/to/option2", "/path/to/option3"]
        })

        manager = CascadingPaneManager()
        manager.display_pane("Root Pane", example_df)
        manager.show()
        sys.exit(app.exec())

class ResizableReceiverPane(QLabel):
    def __init__(self, parent=None, min_width=10, max_width=200):
        super().__init__(parent)
        self.setText("Drop Here")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(min_width)
        self.max_width = max_width
        self.setStyleSheet("border: 1px solid black; background-color: #f0f0f0; padding: 5px;")
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept the drag if the MIME type is correct."""
        if event.mimeData().hasFormat("application/json"):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle the drop and resize the widget dynamically."""
        if event.mimeData().hasFormat("application/json"):
            # Decode the MIME data
            provenance_data = event.mimeData().data("application/json").data().decode()
            self.setText(provenance_data)  # Update the label text

            # Dynamically resize width to fit the text
            metrics = QFontMetrics(self.font())
            text_width = metrics.boundingRect(self.text()).width()
            self.setFixedWidth(min(max(text_width + 20, self.minimumWidth()), self.max_width))
            
            event.accept()
        else:
            event.ignore()

class SenderPane(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.add_sample_items()

    def add_sample_items(self):
        """Add some sample items to the sender pane."""
        sample_data = [
            {"name": "File A", "path": "/path/to/file_a", "type": "File"},
            {"name": "Directory B", "path": "/path/to/dir_b", "type": "Directory"},
        ]
        for item_data in sample_data:
            item = QListWidgetItem(item_data["name"])
            item.setData(Qt.UserRole, item_data)  # Store the metadata
            self.addItem(item)

    def startDrag(self, supportedActions):
        """Customize the drag operation to include provenance data."""
        item = self.currentItem()
        if item:
            drag = QDrag(self)
            mime_data = QMimeData()

            # Include detailed provenance and metadata in the MIME data
            provenance = {
                "name": item.text(),
                "metadata": item.data(Qt.UserRole),
                "environment": {
                    "timestamp": "2024-12-02T14:00:00Z",
                    "user": "John Doe",
                    "machine": "Workstation1",
                },
            }
            mime_data.setData("application/json", json.dumps(provenance).encode())

            drag.setMimeData(mime_data)
            drag.exec_(supportedActions)
