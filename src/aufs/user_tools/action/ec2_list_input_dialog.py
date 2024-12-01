import pandas as pd
import sys
import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.action.ec2_wrangler import EC2TerminationProcess
from src.aufs.user_tools.fs_meta.aws_ec2_manager import AwsEC2Manager
from src.aufs.user_tools.fs_meta.files_paths import set_a_render_root_for_os

class TextInputDialog(QDialog):
    def __init__(self, data_manager, regions, manage_ec2, object_list_formatter, mode='terminate', parent=None):
        super().__init__(parent)
        self.root_os = set_a_render_root_for_os('R:/')
        self.manage_ec2 = manage_ec2
        self.object_list_formatter = object_list_formatter
        self.mode = mode  # 'terminate' or 'cleanup'
        self.data_manager = data_manager
        self.regions = regions
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        self.label = QLabel("Paste from Deadline")
        layout.addWidget(self.label)

        self.textEdit = QTextEdit()
        layout.addWidget(self.textEdit)

        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.process_input_and_terminate)
        layout.addWidget(self.okButton)

        self.setWindowTitle("Text input")

    def process_input_and_terminate(self):
        deadline_instance_ids_and_regions = self.get_instance_ids_and_regions()

        if not deadline_instance_ids_and_regions:
            QMessageBox.information(self, "No Input", "No valid instance IDs or regions found.")
            return

        if self.mode == 'cleanup':
            deadline_instance_ids = {instance_id for instance_id, _ in deadline_instance_ids_and_regions}
            instances_to_terminate = self.get_instances_to_terminate(deadline_instance_ids)
        else:
            instances_to_terminate = deadline_instance_ids_and_regions

        if not instances_to_terminate:
            QMessageBox.information(self, "No Instances to Terminate", "No instances to terminate found.")
            self.reject()
            return

        termination_process = EC2TerminationProcess(instances_to_terminate, self.manage_ec2, self.object_list_formatter)
        termination_process.execute()
        
        self.accept()

    def get_instance_ids_and_regions(self):
        lines = self.textEdit.toPlainText().strip().split('\n')
        if not lines:
            return []

        headers = lines[0].split('\t')
        try:
            instance_id_index = headers.index('AWS Instance ID')
            availability_zone_index = headers.index('AWS Availability Zone')
        except ValueError:
            return []

        instance_region_pairs = []
        for line in lines[1:]:
            columns = line.split('\t')
            if len(columns) > max(instance_id_index, availability_zone_index):
                instance_id = columns[instance_id_index]
                availability_zone = columns[availability_zone_index]
                region = availability_zone[:-1]

                if instance_id.startswith('i-') and len(instance_id) > 18:
                    instance_region_pairs.append((instance_id, region))

        return instance_region_pairs

    def get_instances_to_terminate(self, deadline_instance_ids):
        fresh_instances = []
        
        # Use the same path as the DataProvider class
        parquet_file_path = os.path.join(self.root_os, 'dsvfx/render/main/ec2_instance_data.parquet')
        
        # Load the data from the Parquet file, similar to getData
        df = pd.read_parquet(parquet_file_path)

        # Apply the same column renaming logic
        if not df.empty:
            df.columns = df.columns.str.replace('.', '_')

            # Filter out rows where State is 'terminated'
            df = df[df['State_Name'] == 'running']

            # We can assume cleanup requires RenderGroup filtering
            df = df[df['RenderGroup'].apply(bool)]

        # Process each row in the filtered DataFrame
        for _, row in df.iterrows():
            instance_id = row['InstanceId']
            if isinstance(instance_id, pd.Series):
                instance_id = instance_id.iloc[0]  # Extract from the series if needed
            
            # Only add the instance if it has a valid RenderGroup
            if row['RenderGroup']:  
                fresh_instances.append({
                    "InstanceId": str(instance_id).strip(),  # Ensure InstanceId is a clean string
                    "Region": row['Region']  # Assuming Region is in the DataFrame
                })

        # Filter out instances that are in the deadline_instance_ids list
        instances_to_terminate = [
            (instance['InstanceId'], instance['Region']) 
            for instance in fresh_instances 
            if str(instance['InstanceId']) not in deadline_instance_ids
        ]

        return instances_to_terminate
