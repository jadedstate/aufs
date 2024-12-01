from PySide6.QtCore import QObject, Signal
import pandas as pd
from datetime import datetime
from .aws_ec2_manager import AwsEC2Manager
from .dataframe_maintenance import no_nans_all_cols

class AwsDataManager:
    data_updated = Signal(str)  # Signal to notify when data is updated

    def __init__(self, details_to_add=None):
        self.data_frames = {}  # Key: 'object_region', Value: (df, last_updated, applied_details)
        self.update_threshold_minutes = 5  # Threshold for considering data as stale
        self.details_to_add = details_to_add if details_to_add else []
        self.meta_df = pd.DataFrame(columns=["Name", "LastUpdated", "AppliedDetails", "CreationTime"])

    def _get_meta_info(self, key):
        # Retrieve meta information for a given DataFrame key
        return self.meta_df[self.meta_df["Name"] == key].to_dict('records')

    def get_data(self, object_type, region, max_age_minutes=None, details_to_add=None, columns_to_return=None):
        details_to_add = details_to_add or self.details_to_add
        key = f"{object_type}_{region}"
        current_time = datetime.now()

        print(f"Fetching data for {object_type} in region {region} with max_age_minutes={max_age_minutes}")

        if key in self.data_frames:
            df, last_updated, applied_details = self.data_frames[key]
            age = (current_time - last_updated).total_seconds() / 60

            if max_age_minutes is not None and age <= max_age_minutes and set(details_to_add).issubset(set(applied_details)):
                if columns_to_return:
                    return df[columns_to_return]
                return df

        # Fetch fresh data if necessary
        new_df = self._fetch_data(object_type, region)
        print(f"Fetched data for {region}: {len(new_df)} rows")
        cleaned_df = no_nans_all_cols(new_df)

        # Apply additional details in a batch to avoid DataFrame fragmentation
        cleaned_df = self.apply_all_modifications(cleaned_df, details_to_add)

        # Print the DataFrame before filtering
        print(f"DataFrame before filtering: {cleaned_df.shape}")

        # Store the DataFrame and update metadata
        self.data_frames[key] = (cleaned_df, current_time, details_to_add)
        self._update_meta_df(key, current_time, details_to_add)

        # Return only the requested columns if specified
        if columns_to_return:
            return cleaned_df[columns_to_return]

        return cleaned_df

    def _update_meta_df(self, key, current_time, details_to_add):
        # Use pd.concat to avoid repeated append operations
        meta_row = pd.DataFrame({
            'DataFrame Name': [key],
            'Last Updated': [current_time],
            'Details Applied': [details_to_add]
        })

        if hasattr(self, 'meta_df'):
            self.meta_df = pd.concat([self.meta_df, meta_row], ignore_index=True)
        else:
            self.meta_df = meta_row

    def _fetch_data(self, object_type, region):
        manager = AwsEC2Manager(region=region)
        if object_type == 'ec2_instances':
            return manager.retrieve_ec2_instance_data()
        elif object_type == 'launch_templates':
            return manager.retrieve_ec2_launch_templates()
        elif object_type == 'instance_types':
            return manager.get_instance_type_details()
        else:
            raise ValueError(f"Unknown object type: {object_type}")

    def apply_all_modifications(self, df, details_to_add):
        """
        Applies all requested detail modifications in one go to avoid DataFrame fragmentation.

        Parameters:
            df (pd.DataFrame): The original DataFrame.
            details_to_add (list): List of detail methods to apply.

        Returns:
            pd.DataFrame: The modified DataFrame.
        """
        modifications = {}

        for detail_method in details_to_add:
            method = getattr(self, detail_method, None)
            if callable(method):
                modifications[detail_method] = method(df)

        # Combine all modifications into a new DataFrame and concatenate
        if modifications:
            mod_df = pd.concat(modifications.values(), axis=1)
            df = pd.concat([df, mod_df], axis=1)

        # Fill missing values if necessary
        df.fillna('', inplace=True)

        return df

    def set_update_threshold(self, minutes):
        self.update_threshold_minutes = minutes

    def get_active_dataframes_info(self):
        return self.meta_df

    def archive_or_flush_dataframes(self):
        pass

    def add_detail_status_check(self, df):
        status_check_summary = df.apply(self._calculate_status_check, axis=1)
        return pd.DataFrame({'StatusCheckSummary': status_check_summary})

    def _calculate_status_check(self, row):
        instance_check = row.get('InstanceStatus.Details', [])
        system_check = row.get('SystemStatus.Details', [])
        passed_checks = sum(1 for check in instance_check + system_check if check['Status'] == 'passed')
        return passed_checks

    def add_name(self, df):
        if 'Tags' in df.columns:  # Check if 'Tags' column exists
            names = df['Tags'].apply(self._extract_name)
        else:
            names = pd.Series([""] * len(df))  # Create an empty column if 'Tags' doesn't exist
        return pd.DataFrame({'Name': names})

    def _extract_name(self, tags):
        if isinstance(tags, list):
            for tag in tags:
                if tag.get('Key') == 'Name':
                    return tag.get('Value')
        return None

    def add_region(self, df):
        if 'Placement.AvailabilityZone' in df.columns:
            regions = df['Placement.AvailabilityZone'].str[:-1]
            return pd.DataFrame({'Region': regions})
        else:
            return pd.DataFrame({'Region': [""] * len(df)})

    def add_simple_state(self, df):
        if 'InstanceState.Name' in df.columns:
            states = df['InstanceState.Name']
            return pd.DataFrame({'State': states})
        else:
            return pd.DataFrame({'State': [""] * len(df)})

    def add_has_renderGroup_tag(self, df):
        if 'Tags' in df.columns:
            render_groups = df['Tags'].apply(self._extract_render_group)
        else:
            render_groups = pd.Series([""] * len(df))
        return pd.DataFrame({'RenderGroup': render_groups})

    def _extract_render_group(self, tags):
        if isinstance(tags, list):
            for tag in tags:
                if tag.get('Key') == 'renderGroup':
                    return tag.get('Value')
        return None

    def add_instance_family(self, df):
        if 'InstanceType' in df.columns:
            instance_families = df['InstanceType'].str.split('.', expand=True)
            return instance_families.rename(columns={0: 'InstanceFamily', 1: 'InstanceXlarge'})
        else:
            return pd.DataFrame({'InstanceFamily': [""] * len(df), 'InstanceXlarge': [""] * len(df)})

    def remove_terminated_instances(self, df):
        """
        Filters out terminated instances from the provided DataFrame.

        Parameters:
            df (pd.DataFrame): The DataFrame containing EC2 instance data.

        Returns:
            pd.DataFrame: The filtered DataFrame with terminated instances removed.
        """
        if 'State' in df.columns:
            df = df[df['State'] != 'terminated']
        return df

    def list_auto_scaling_groups(self):
        """
        Lists all Auto Scaling Groups (ASGs) in the current region.
        
        Returns:
            pd.DataFrame: DataFrame containing details of all ASGs.
        """
        try:
            response = self.asg_client.describe_auto_scaling_groups()
            asgs = response['AutoScalingGroups']
            
            # Flatten the data and extract relevant details
            data = []
            for asg in asgs:
                asg_data = {
                    'ASGName': asg['AutoScalingGroupName'],
                    'MinSize': asg['MinSize'],
                    'MaxSize': asg['MaxSize'],
                    'DesiredCapacity': asg['DesiredCapacity'],
                    'LaunchTemplateId': asg.get('LaunchTemplate', {}).get('LaunchTemplateId', ''),
                    'InstanceTypes': [override['InstanceType'] for override in asg.get('MixedInstancesPolicy', {}).get('LaunchTemplate', {}).get('Overrides', [])]
                }
                data.append(asg_data)

            df = pd.DataFrame(data)
            print(f"Retrieved {len(df)} Auto Scaling Groups in region {self.region}.")
            return df

        except Exception as e:
            print(f"Failed to list ASGs: {str(e)}")
            return pd.DataFrame()  # Return an empty DataFrame on failure

    def adjust_auto_scaling_group(self, asg_name, instance_types, target_number):
        """
        Adjusts the configuration of an existing Auto Scaling Group (ASG).
        
        Parameters:
            asg_name (str): The name of the ASG to adjust.
            instance_types (list): The list of allowed instance types.
            target_number (int): The target number of instances for the desired capacity.
        """
        try:
            # Update the ASG's instance types and target number
            self.asg_client.update_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                LaunchTemplate={'LaunchTemplateId': instance_types['LaunchTemplateId']},  # Assuming you pass this ID in instance_types
                MaxSize=target_number,
                DesiredCapacity=target_number,
                MinSize=target_number
            )
            print(f"ASG {asg_name} adjusted: MaxSize={target_number}, DesiredCapacity={target_number}, MinSize={target_number}")

        except Exception as e:
            print(f"Failed to adjust ASG {asg_name}: {str(e)}")
            raise

    def delete_auto_scaling_group(self, asg_name):
        """
        Deletes an existing Auto Scaling Group (ASG) and terminates all associated instances.
        
        Parameters:
            asg_name (str): The name of the ASG to delete.
        """
        try:
            # First, update the ASG to set desired, min, and max size to 0 to ensure all instances are terminated
            self.asg_client.update_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                MaxSize=0,
                DesiredCapacity=0,
                MinSize=0
            )
            print(f"ASG {asg_name} sizes set to 0. Instances terminating...")

            # Delete the ASG
            self.asg_client.delete_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                ForceDelete=True
            )
            print(f"ASG {asg_name} deleted successfully.")

        except Exception as e:
            print(f"Failed to delete ASG {asg_name}: {str(e)}")
            raise

    def create_auto_scaling_group(self, asg_name, launch_template_id, subnet_ids, instance_types, min_size=0, max_size=1, desired_capacity=0):
        """
        Creates an Auto Scaling Group (ASG) across all Availability Zones within specified subnets.
        
        Parameters:
            asg_name (str): The name of the Auto Scaling Group.
            launch_template_id (str): The ID of the launch template to use.
            subnet_ids (list): A list of subnet IDs to launch instances in.
            instance_types (list): A list of instance types to be used in the ASG.
            min_size (int): The minimum size of the ASG. Default is 0.
            max_size (int): The maximum size of the ASG. Default is 1.
            desired_capacity (int): The desired capacity of the ASG. Default is 0.
            
        Raises:
            Exception: If the ASG creation fails.
        """
        try:
            response = self.asg_client.create_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                LaunchTemplate={
                    'LaunchTemplateId': launch_template_id,
                    'Version': '$Latest'  # Always use the latest version of the launch template
                },
                MinSize=min_size,
                MaxSize=max_size,
                DesiredCapacity=desired_capacity,
                VPCZoneIdentifier=",".join(subnet_ids),  # All subnets to cover all availability zones
                MixedInstancesPolicy={
                    'LaunchTemplate': {
                        'LaunchTemplateSpecification': {
                            'LaunchTemplateId': launch_template_id,
                            'Version': '$Latest'
                        },
                        'Overrides': [{'InstanceType': itype} for itype in instance_types]  # Add all specified instance types
                    }
                },
                Tags=[
                    {
                        'Key': 'AutoScalingGroupName',
                        'Value': asg_name,
                        'PropagateAtLaunch': True
                    },
                ]
            )
            print(f"ASG {asg_name} created successfully in region {self.region}.")
        except Exception as e:
            print(f"Failed to create ASG {asg_name}: {str(e)}")
            raise
