import sys
import threading
import boto3
import natsort
import pandas as pd
from datetime import datetime
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QHBoxLayout, QTreeWidgetItem, QTreeWidget, QLabel, QLineEdit, QListView, QPushButton, QCheckBox, QFrame, QSplitter, QListWidget, QListWidgetItem
from PySide6.QtCore import QStringListModel, Qt, Signal, QTimer
from PySide6.QtGui import QIntValidator
from lib.ec2_manager_boto3 import EC2Manager  # Retain the original manager
from lib.aws_data_manager import AwsDataManager  # Use the new data manager where appropriate

class SpotRequestApplication(QtWidgets.QWidget):
    update_status_signal = Signal(int, str)
    move_to_log_signal = Signal(str)

    def __init__(self, regions):
        super().__init__()
        self.ec2_manager = EC2Manager()
        self.ec2_manager.setup()
        self.regions = regions
        self.launch_templates = self._fetch_launch_templates()
        self.initUI()

        # Connect the selection change to sync checkboxes
        self.treeWidget.itemSelectionChanged.connect(self.sync_check_with_selection)
        self.update_status_signal.connect(self.update_top_info_pane)
        self.move_to_log_signal.connect(self.move_to_log_pane)
        
        # Cleaner timer setup
        self.cleaner_timer = QTimer(self)
        self.cleaner_timer.timeout.connect(self.clean_up_top_pane)
        self.cleaner_timer.start(5000)

    def initUI(self):
        self.setWindowTitle("Instance Launcher")
        self.resize(1000, 800)

        main_layout = QVBoxLayout(self)

        # Splitter setup
        splitter = QSplitter(Qt.Horizontal, self)
        main_layout.addWidget(splitter)

        # Left-side layout
        left_widget = QtWidgets.QWidget()
        left_layout = QHBoxLayout(left_widget)
        splitter.addWidget(left_widget)

        button_layout = QVBoxLayout()
        left_layout.addLayout(button_layout)

        self.okButton = QPushButton("GO", self)
        self.okButton.clicked.connect(self.confirm_and_launch_instances)
        self.okButton.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        button_layout.addWidget(self.okButton)

        form_layout = QVBoxLayout()
        left_layout.addLayout(form_layout)

        self.textLabel = QLabel("Name for SR listing:", self)
        self.textLabel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form_layout.addWidget(self.textLabel)

        self.textInput = QLineEdit(self)
        self.textInput.setText(self._generate_timestamp())
        self.textInput.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form_layout.addWidget(self.textInput)

        # Multi checkbox placed below listing name
        self.multiCheckbox = QCheckBox("Multi", self)
        self.multiCheckbox.stateChanged.connect(self.toggle_multi_mode)
        form_layout.addWidget(self.multiCheckbox)

        self.treeWidget = QTreeWidget(self)
        self.treeWidget.setHeaderLabels(["Region", "Launch Template"])
        self.treeWidget.setSelectionMode(QTreeWidget.SingleSelection)
        self.treeWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.treeWidget.installEventFilter(self)
        self.populate_tree_widget()
        form_layout.addWidget(self.treeWidget)

        self.list2Label = QLabel("Select an Instance Type", self)
        self.list2Label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form_layout.addWidget(self.list2Label)

        self.listView2 = QListView(self)
        self.listView2.setModel(QStringListModel(self._get_instance_types()))
        self.listView2.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.listView2.setMaximumHeight(100)  # Fixed height
        self.listView2.installEventFilter(self)
        form_layout.addWidget(self.listView2)

        self.intInputLabel = QLabel("Number of Instances:", self)
        self.intInputLabel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form_layout.addWidget(self.intInputLabel)

        self.intInput = QLineEdit(self)
        self.intInput.setValidator(QIntValidator(1, 9999))
        self.intInput.setText("15")
        self.intInput.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.intInput.installEventFilter(self)
        form_layout.addWidget(self.intInput)

        self.iterative_request = QCheckBox("Iterate requests", self)
        self.iterative_request.setChecked(True)
        self.iterative_request.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.iterative_request.installEventFilter(self)
        form_layout.addWidget(self.iterative_request)

        bottom_placeholder = QFrame(self)
        bottom_placeholder.setFrameShape(QFrame.NoFrame)
        bottom_placeholder.setFrameShadow(QFrame.Plain)
        bottom_placeholder.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        form_layout.addWidget(bottom_placeholder)

        # Right-side layout
        right_widget = QtWidgets.QWidget()
        right_layout = QVBoxLayout(right_widget)
        splitter.addWidget(right_widget)

        self.top_info_pane = QListWidget(self)
        right_layout.addWidget(self.top_info_pane)

        self.bottom_info_pane = QListWidget(self)
        right_layout.addWidget(self.bottom_info_pane)

        splitter.setSizes([400, 800])

        self.setLayout(main_layout)

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if source in (self.textInput, self.treeWidget, self.listView2, self.intInput, self.iterative_request):
                self.okButton.click()
                return True
        return super().eventFilter(source, event)

    def populate_tree_widget(self):
        self.treeWidget.clear()  # Clear existing items
        for region, templates in self.launch_templates.items():
            region_item = QTreeWidgetItem(self.treeWidget, [region])
            region_item.setFlags(region_item.flags() | Qt.ItemIsUserCheckable)  # Enable checkbox
            region_item.setCheckState(0, Qt.Unchecked)  # Default to unchecked
            for template in templates:
                template_item = QTreeWidgetItem(region_item, [template])
                template_item.setFlags(template_item.flags() | Qt.ItemIsUserCheckable)  # Enable checkbox
                template_item.setCheckState(0, Qt.Unchecked)  # Default to unchecked

        # Expand all items
        for i in range(self.treeWidget.topLevelItemCount()):
            self.treeWidget.topLevelItem(i).setExpanded(True)

        # Resize columns to fit content
        for i in range(self.treeWidget.columnCount()):
            self.treeWidget.resizeColumnToContents(i)

    def toggle_multi_mode(self, state):
        # Turn off all checkboxes and clear selections
        self.treeWidget.clearSelection()  # Deselect all selected items first
        for i in range(self.treeWidget.topLevelItemCount()):
            region_item = self.treeWidget.topLevelItem(i)
            region_item.setCheckState(0, Qt.Unchecked)  # Clear the checkbox for top-level items, if needed
            for j in range(region_item.childCount()):
                template_item = region_item.child(j)
                template_item.setCheckState(0, Qt.Unchecked)  # Clear the checkbox for child items

        # Then proceed with the rest of the toggle logic
        if state == Qt.Checked:
            self.treeWidget.setSelectionMode(QTreeWidget.MultiSelection)
        else:
            self.treeWidget.setSelectionMode(QTreeWidget.SingleSelection)

        # Ensure synchronization of checkboxes with selection state
        self.sync_check_with_selection()

    def sync_check_with_selection(self):
        # Always synchronize check state with selection
        selected_items = self.treeWidget.selectedItems()

        # Uncheck all items first
        for i in range(self.treeWidget.topLevelItemCount()):
            region_item = self.treeWidget.topLevelItem(i)
            for j in range(region_item.childCount()):
                template_item = region_item.child(j)
                template_item.setCheckState(0, Qt.Unchecked)

        # Check all selected items
        for item in selected_items:
            item.setCheckState(0, Qt.Checked)

    def confirm_and_launch_instances(self):
        text_value = self.textInput.text().strip()
        instance_type = self.listView2.model().data(self.listView2.currentIndex(), Qt.DisplayRole)
        count = int(self.intInput.text())

        if not text_value:
            QMessageBox.critical(self, "Validation Error", "Name for SR listing cannot be empty.")
            return
        if not instance_type:
            QMessageBox.critical(self, "Validation Error", "Please select an instance type.")
            return
        if count < 1:
            QMessageBox.critical(self, "Validation Error", "Number of instances must be at least 1.")
            return

        tags = {"renderGroup": text_value}
        use_iterative = self.iterative_request.isChecked()

        if self.multiCheckbox.isChecked():
            selected_items = []
            for i in range(self.treeWidget.topLevelItemCount()):
                region_item = self.treeWidget.topLevelItem(i)
                for j in range(region_item.childCount()):
                    template_item = region_item.child(j)
                    if template_item.checkState(0) == Qt.Checked:
                        selected_items.append((region_item.text(0), template_item.text(0)))

            if not selected_items:
                QMessageBox.critical(self, "Validation Error", "Please select at least one launch template.")
                return

            for region, launch_template_name in selected_items:
                self.launch_instances(region, launch_template_name, instance_type, count, tags, use_iterative)
        else:
            selected_item = self.treeWidget.currentItem()
            if not selected_item or not selected_item.parent():
                QMessageBox.critical(self, "Validation Error", "Please select a launch template.")
                return
            
            region = selected_item.parent().text(0)
            launch_template_name = selected_item.text(0)
            self.launch_instances(region, launch_template_name, instance_type, count, tags, use_iterative)

    def launch_instances(self, region, launch_template_name, instance_type, count, tags, use_iterative):
        timestamp = self._get_current_timestamp()
        list_item = QListWidgetItem(f"{timestamp}UTC - {region}: Launching {count}x {instance_type} in {region}")
        self.top_info_pane.addItem(list_item)
        item_index = self.top_info_pane.row(list_item)

        self.ec2_manager.set_region(region)
        launch_thread = threading.Thread(
            target=self.launch_instance_thread,
            args=(item_index, timestamp, launch_template_name, instance_type, count, tags, use_iterative, region)
        )
        launch_thread.start()

    def launch_instance_thread(self, item_index, timestamp, launch_template_name, instance_type, count, tags, use_iterative, region):
        if use_iterative:
            successful_launches = 0
            for i in range(1, count + 1):
                status_message = f"{timestamp}UTC - {region}: Running launch {i} of {count}x {instance_type}"
                self.update_status_signal.emit(item_index, status_message)
                response = self.ec2_manager.launch_instances_structured(launch_template_name, instance_type, 1, tags)
                if response['success']:
                    successful_launches += 1
                else:
                    status_message = f"{timestamp}UTC - {region}: Launch {i} of {count}x {instance_type} failed."
                    self.update_status_signal.emit(item_index, status_message)
                    break  # Stop launching on first failure
            final_message = f"{timestamp}UTC - {region}: {successful_launches} {instance_type} out of {count} instances launched successfully."
        else:
            status_message = f"{timestamp}UTC - {region}: Launching {count}x {instance_type}"
            self.update_status_signal.emit(item_index, status_message)
            response = self.ec2_manager.launch_instances_structured(launch_template_name, instance_type, count, tags)
            if response['success']:
                final_message = f"{timestamp}UTC - {region}: Launch of {count}x {instance_type} succeeded."
            else:
                final_message = f"{timestamp}UTC - {region}: Launch of {count}x {instance_type} failed."

        self.move_to_log_signal.emit(final_message)
        self.update_status_signal.emit(item_index, "")  # Mark completion in the top pane

    def update_top_info_pane(self, index, message):
        if message:
            item = self.top_info_pane.item(index)
            if item:
                item.setText(message)
        else:
            # Remove item from the list when the task is complete
            if index < self.top_info_pane.count():
                self.top_info_pane.takeItem(index)

    def move_to_log_pane(self, message):
        # Move final status message to the bottom info pane, at the top
        list_item = QListWidgetItem(message)
        self.bottom_info_pane.insertItem(0, list_item)

    def clean_up_top_pane(self):
        # Extract timestamps from the bottom info pane
        bottom_timestamps = set()
        for index in range(self.bottom_info_pane.count()):
            item_text = self.bottom_info_pane.item(index).text()
            timestamp = item_text.split(' - ')[0]
            bottom_timestamps.add(timestamp)

        # Remove items from the top info pane if their timestamps exist in the bottom pane
        for index in range(self.top_info_pane.count() - 1, -1, -1):  # Iterate in reverse to safely remove items
            item_text = self.top_info_pane.item(index).text()
            timestamp = item_text.split(' - ')[0]
            if timestamp in bottom_timestamps:
                self.top_info_pane.takeItem(index)

    def _get_launch_template_names(self):
        launch_templates = self.ec2_manager.get_launch_templates()
        return [template['LaunchTemplateName'] for template in launch_templates.get('LaunchTemplates', [])]

    def _fetch_launch_templates(self):
        templates_by_region = {}
        for region in self.regions:
            self.ec2_manager.set_region(region)
            templates = self.ec2_manager.get_launch_templates()
            templates_by_region[region] = [template['LaunchTemplateName'] for template in templates.get('LaunchTemplates', [])]
        return templates_by_region

    def _get_instance_types(self):
        instance_types = self.ec2_manager.describe_instance_type_families('m5')
        return instance_types

    def _generate_timestamp(self):
        return datetime.now().strftime("%H%M%S")

    def _get_current_timestamp(self):
        return datetime.now().strftime("[%Y-%m-%d %H:%M:%S %Z]")
