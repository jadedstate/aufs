import os
import sys
from PySide6.QtWidgets import QApplication, QMessageBox

# Add the `src` directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, '..', '..', '..', '..')  # Adjust to point to the `src` folder
sys.path.insert(0, src_path)

from src.aufs.user_tools.qtwidgets.widgets.custom_ec2_wrangling_confirmation_dialog_1 import ConfirmationDialog
from src.aufs.user_tools.fs_meta.aws_ec2_manager import AwsEC2Manager
import sys

class ASGManager:
    def __init__(self, region, data_manager):
        self.region = region
        self.data_manager = data_manager
        self.ec2_manager = AwsEC2Manager(region=region)

    def create_asg(self, asg_name, launch_template_id, subnet_ids, instance_types, min_size=0, max_size=1, desired_capacity=0):
        """
        Creates an Auto Scaling Group (ASG) in the specified region.
        
        Parameters:
            asg_name (str): The name of the ASG.
            launch_template_id (str): The ID of the launch template.
            subnet_ids (list): List of subnet IDs across which to deploy instances.
            instance_types (list): List of instance types for the ASG.
            min_size (int): Minimum size of the ASG. Default is 0.
            max_size (int): Maximum size of the ASG. Default is 1.
            desired_capacity (int): Desired capacity of the ASG. Default is 0.
        """
        try:
            self.ec2_manager.create_auto_scaling_group(
                asg_name=asg_name,
                launch_template_id=launch_template_id,
                subnet_ids=subnet_ids,
                instance_types=instance_types,
                min_size=min_size,
                max_size=max_size,
                desired_capacity=desired_capacity
            )
            QMessageBox.information(None, "ASG Creation", f"Auto Scaling Group {asg_name} created successfully in region {self.region}.")
        except Exception as e:
            QMessageBox.critical(None, "ASG Creation Failed", f"Failed to create ASG {asg_name}: {str(e)}")
    
    def list_asgs(self):
        """
        Lists all Auto Scaling Groups (ASGs) in the current region.
        
        Returns:
            pd.DataFrame: DataFrame containing details of all ASGs in the region.
        """
        try:
            asg_data = self.ec2_manager.list_auto_scaling_groups()
            if asg_data.empty:
                QMessageBox.information(None, "ASG List", f"No Auto Scaling Groups found in region {self.region}.")
            else:
                QMessageBox.information(None, "ASG List", f"Found {len(asg_data)} Auto Scaling Groups in region {self.region}.")
            return asg_data
        except Exception as e:
            QMessageBox.critical(None, "ASG List Failed", f"Failed to list ASGs: {str(e)}")
            return None

    def adjust_asg(self, asg_name, instance_types, target_number):
        """
        Adjusts the configuration of an existing Auto Scaling Group (ASG).
        
        Parameters:
            asg_name (str): The name of the ASG.
            instance_types (list): List of instance types to use.
            target_number (int): Desired capacity for the ASG.
        """
        try:
            self.ec2_manager.adjust_auto_scaling_group(
                asg_name=asg_name,
                instance_types=instance_types,
                target_number=target_number
            )
            QMessageBox.information(None, "ASG Adjustment", f"Auto Scaling Group {asg_name} adjusted successfully.")
        except Exception as e:
            QMessageBox.critical(None, "ASG Adjustment Failed", f"Failed to adjust ASG {asg_name}: {str(e)}")
    
    def delete_asg(self, asg_name):
        """
        Deletes an existing Auto Scaling Group (ASG) in the current region.
        
        Parameters:
            asg_name (str): The name of the ASG to delete.
        """
        try:
            self.ec2_manager.delete_auto_scaling_group(asg_name)
            QMessageBox.information(None, "ASG Deletion", f"Auto Scaling Group {asg_name} deleted successfully.")
        except Exception as e:
            QMessageBox.critical(None, "ASG Deletion Failed", f"Failed to delete ASG {asg_name}: {str(e)}")

class EC2Wrangler:
    def __init__(self, regions, data_manager):
        self.regions = regions
        self.data_manager = data_manager
        self.ec2_manager = AwsEC2Manager()  # Instantiate AwsEC2Manager here

    def object_list_formatter(self, instance_details, object_type):
        """
        Formats the details into a dictionary of lists grouped by region.
        Provides an example for users on how to structure data for EC2 instances and ASGs.
        
        Parameters:
            instance_details (list of tuples): List of tuples with object identifiers and their regions.
            object_type (str): Type of object, e.g., "ec2_instances" or "auto_scaling_groups".
        
        Returns:
            dict: Formatted dictionary with region as keys and lists of object identifiers.
        """
        formatted_data = {}

        if object_type == "ec2_instances":
            for instance_id, region in instance_details:
                if region not in formatted_data:
                    formatted_data[region] = []
                formatted_data[region].append({"InstanceId": instance_id})

        elif object_type == "auto_scaling_groups":
            for asg_name, region in instance_details:
                if region not in formatted_data:
                    formatted_data[region] = []
                formatted_data[region].append({"ASGName": asg_name})

        else:
            raise ValueError(f"Unsupported object type: {object_type}")

        print('Formatted data: ')
        print(formatted_data)

        return formatted_data

class EC2TerminationProcess:
    def __init__(self, instance_details, ec2_manager, object_list_formatter):
        self.instance_details = instance_details
        self.object_list_formatter = object_list_formatter
        self.ec2_manager = ec2_manager  # Instance of AwsEC2Manager

    def execute(self):
        # Initialize QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Format the instance details for termination
        formatted_data = self.object_list_formatter(self.instance_details, 'ec2_instances')

        # Confirmation Dialog
        dialog = ConfirmationDialog("Terminate Instances", formatted_data)
        if not dialog.get_confirmation():
            QMessageBox.information(None, "Termination Cancelled", "No instances were terminated.")
            return {'status': 'cancelled'}

        # Execute termination
        results = self.ec2_manager.terminate_instance(formatted_data)

        # Handle and display results
        summary = self.summarize_results(results)
        QMessageBox.information(None, "Termination Results", summary)
        return {'status': 'success', 'results': results}

    def summarize_results(self, results):
        summary_lines = []
        for region, result in results.items():
            if result['success']:
                summary_lines.append(f"Successfully terminated instances in {region}: {', '.join(result['terminated'])}")
            else:
                summary_lines.append(f"Failed to terminate instances in {region}: {result.get('error', 'Unknown error')}")
        return "\n".join(summary_lines)

class EC2StartProcess:
    def __init__(self, instance_details, ec2_manager, object_list_formatter):
        self.instance_details = instance_details
        self.object_list_formatter = object_list_formatter
        self.ec2_manager = ec2_manager  # Instance of AwsEC2Manager

    def execute(self):
        # Initialize QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        formatted_data = self.object_list_formatter(self.instance_details, 'ec2_instances')
        dialog = ConfirmationDialog("Start Instances", formatted_data)
        if not dialog.get_confirmation():
            QMessageBox.information(None, "Start Cancelled", "No instances were started.")
            return {'status': 'cancelled'}

        results = self.ec2_manager.start_instance(formatted_data)
        summary = self.summarize_results(results)
        QMessageBox.information(None, "Start Results", summary)
        return {'status': 'success', 'results': results}

    def summarize_results(self, results):
        summary_lines = []
        for region, result in results.items():
            if result['success']:
                summary_lines.append(f"Successfully started instances in {region}: {', '.join(result['started'])}")
            else:
                summary_lines.append(f"Failed to start instances in {region}: {result.get('error', 'Unknown error')}")
        return "\n".join(summary_lines)

class EC2StopProcess:
    def __init__(self, instance_details, ec2_manager, object_list_formatter):
        self.instance_details = instance_details
        self.object_list_formatter = object_list_formatter
        self.ec2_manager = ec2_manager  # Instance of AwsEC2Manager

    def execute(self):
        # Initialize QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        formatted_data = self.object_list_formatter(self.instance_details, 'ec2_instances')
        dialog = ConfirmationDialog("Stop Instances", formatted_data)
        if not dialog.get_confirmation():
            QMessageBox.information(None, "Stop Cancelled", "No instances were stopped.")
            return {'status': 'cancelled'}

        results = self.ec2_manager.stop_instance(formatted_data)
        summary = self.summarize_results(results)
        QMessageBox.information(None, "Stop Results", summary)
        return {'status': 'success', 'results': results}

    def summarize_results(self, results):
        summary_lines = []
        for region, result in results.items():
            if result['success']:
                summary_lines.append(f"Successfully stopped instances in {region}: {', '.join(result['stopped'])}")
            else:
                summary_lines.append(f"Failed to stop instances in {region}: {result.get('error', 'Unknown error')}")
        return "\n".join(summary_lines)

class EC2TerminationProtectionProcess:
    def __init__(self, instance_details, ec2_manager, object_list_formatter, enable=True):
        self.instance_details = instance_details
        self.object_list_formatter = object_list_formatter
        self.ec2_manager = ec2_manager  # Instance of AwsEC2Manager
        self.enable = enable

    def execute(self):
        # Initialize QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        action = "Enable" if self.enable else "Disable"
        formatted_data = self.object_list_formatter(self.instance_details, 'ec2_instances')
        dialog = ConfirmationDialog(f"{action} Termination Protection", formatted_data)
        if not dialog.get_confirmation():
            QMessageBox.information(None, f"{action} Protection Cancelled", f"No instances were modified.")
            return {'status': 'cancelled'}

        results = {}
        for region, instances in formatted_data.items():
            self.ec2_manager.set_region(region)
            for instance in instances:
                instance_id = instance['InstanceId']
                try:
                    self.ec2_manager.set_termination_protection(instance_id, self.enable)
                    results[instance_id] = {'success': True, 'message': f'Termination protection {action.lower()}d.'}
                except Exception as e:
                    results[instance_id] = {'success': False, 'error': str(e)}

        summary = self.summarize_results(results)
        QMessageBox.information(None, f"{action} Protection Results", summary)
        return {'status': 'success', 'results': results}

    def summarize_results(self, results):
        summary_lines = []
        for instance_id, result in results.items():
            if result['success']:
                summary_lines.append(f"Successfully {self.enable.lower()}d termination protection for instance {instance_id}.")
            else:
                summary_lines.append(f"Failed to {self.enable.lower()} termination protection for instance {instance_id}: {result.get('error', 'Unknown error')}")
        return "\n".join(summary_lines)
