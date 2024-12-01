# src/rendering_utils/lib/aws_ec2_manager.py

from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import boto3

from .aws_setup import AwsSetup

class AwsEC2Manager:
    def __init__(self, region=None):
        AwsSetup.setup(region)
        self.region = region or AwsSetup(region).region
        self.client = boto3.client('ec2', region_name=self.region)
        self.asg_client = boto3.client('autoscaling', region_name=self.region)
        self.sqs_client = boto3.client('sqs', region_name=self.region)
        self.instance_data = None

    def set_region(self, region):
        self.region = region
        self.client = boto3.client('ec2', region_name=self.region)
        self.asg_client = boto3.client('autoscaling', region_name=self.region)
        self.sqs_client = boto3.client('sqs', region_name=self.region)

    def ensure_sqs_queue(self, queue_name):
        try:
            response = self.sqs_client.get_queue_url(QueueName=queue_name)
            queue_url = response['QueueUrl']
            print(f"SQS queue {queue_name} already exists: {queue_url}")
        except self.sqs_client.exceptions.QueueDoesNotExist:
            print(f"SQS queue {queue_name} does not exist, creating...")
            response = self.sqs_client.create_queue(QueueName=queue_name)
            queue_url = response['QueueUrl']
            print(f"SQS queue {queue_name} created: {queue_url}")
        return queue_url

    def asg_exists(self, asg_name):
        try:
            response = self.asg_client.describe_auto_scaling_groups(
                AutoScalingGroupNames=[asg_name]
            )['AutoScalingGroups']
            return len(response) > 0
        except Exception as e:
            print(f"Failed to validate ASG {asg_name}: {str(e)}")
            return False

    def initialize_auto_scaling_group(self, asg_name, launch_template_id, vpc_subnet_ids, instance_types):
        try:
            response = self.asg_client.create_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                LaunchTemplate={'LaunchTemplateId': launch_template_id},
                MinSize=0,
                MaxSize=len(instance_types),
                DesiredCapacity=0,
                VPCZoneIdentifier=",".join(vpc_subnet_ids),
                MixedInstancesPolicy={
                    'LaunchTemplate': {
                        'LaunchTemplateSpecification': {
                            'LaunchTemplateId': launch_template_id,
                            'Version': '$Latest'
                        },
                        'Overrides': [{'InstanceType': itype} for itype in instance_types]
                    }
                }
            )
            print(f"ASG {asg_name} created successfully.")
        except Exception as e:
            print(f"Failed to create ASG {asg_name}: {str(e)}")
            raise

    def set_max_then_desired_then_min(self, asg_name, max_size, desired_capacity, min_size):
        try:
            self.asg_client.update_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                MaxSize=max_size
            )
            print(f"ASG {asg_name} MaxSize set to {max_size}.")

            self.asg_client.update_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                DesiredCapacity=desired_capacity
            )
            print(f"ASG {asg_name} DesiredCapacity set to {desired_capacity}.")

            self.asg_client.update_auto_scaling_group(
                AutoScalingGroupName=asg_name,
                MinSize=min_size
            )
            print(f"ASG {asg_name} MinSize set to {min_size}.")
            
        except Exception as e:
            print(f"Failed to update ASG {asg_name}: {str(e)}")
            raise

    def update_asg_sizes_only(self, asg_name, max_size, desired_capacity, min_size):
        """
        Wrapper method to update only the size parameters of an ASG.
        
        :param asg_name: The name of the Auto Scaling Group.
        :param max_size: The maximum number of instances.
        :param desired_capacity: The desired number of instances.
        :param min_size: The minimum number of instances.
        """
        print(f"Updating ASG sizes: MaxSize={max_size}, DesiredCapacity={desired_capacity}, MinSize={min_size}")
        self.set_max_then_desired_then_min(asg_name, max_size, desired_capacity, min_size)

    def terminate_instance(self, formatted_data):
        results = {}

        for region, instances in formatted_data.items():
            self.set_region(region)
            instance_ids = [instance["InstanceId"] for instance in instances]

            try:
                response = self.client.terminate_instances(InstanceIds=instance_ids)
                terminated_instances = response.get('TerminatingInstances', [])
                results[region] = {
                    'terminated': [inst['InstanceId'] for inst in terminated_instances],
                    'success': True,
                }
            except Exception as e:
                results[region] = {
                    'terminated': [],
                    'error': str(e),
                    'success': False,
                }

        return results
    
    def describe_spot_placement_scores(self, instance_types):
        results = []
        for instance_type in instance_types:
            try:
                response = self.client.describe_spot_placement_scores(
                    InstanceTypes=[instance_type],
                    TargetCapacity=1,
                    SingleAvailabilityZone=True,
                    MaxResults=100
                )
                for score in response.get("SpotPlacementScores", []):
                    results.append({
                        "InstanceType": instance_type,
                        "Region": self.region,
                        "AvailabilityZone": score.get("AvailabilityZone"),
                        "Score": score.get("Score"),
                        "CapacityOptimized": score.get("CapacityOptimized"),
                    })
            except Exception as e:
                print(f"Error in region {self.region}: {str(e)}")
                continue
        
        return pd.DataFrame(results)
    
    def _fetch_spot_placement_scores(self, region, instance_types, target_capacity, max_results):
        """
        Helper method to fetch Spot Placement Scores for a specific region.

        Parameters:
        - region: AWS region to fetch scores for.
        - instance_types: List of instance types to check.
        - target_capacity: Number of instances you plan to launch.
        - max_results: Maximum number of results to return per request.

        Returns:
        - list: List of Spot Placement Scores.
        """
        region_client = boto3.client('ec2', region_name=region)
        try:
            response = region_client.describe_spot_placement_scores(
                InstanceTypes=instance_types,
                TargetCapacity=target_capacity,
                MaxResults=max_results
            )
            scores = response.get('SpotPlacementScores', [])
            # Annotate the scores with the region information
            for score in scores:
                score['Region'] = region
            return scores
        except Exception as e:
            print(f"Error in region {region}: {e}")
            return []

    def start_instance(self, formatted_data):
        results = {}

        for region, instances in formatted_data.items():
            self.set_region(region)
            instance_ids = [instance["InstanceId"] for instance in instances]

            try:
                response = self.client.start_instances(InstanceIds=instance_ids)
                starting_instances = response.get('StartingInstances', [])
                results[region] = {
                    'started': [inst['InstanceId'] for inst in starting_instances],
                    'success': True,
                }
            except Exception as e:
                results[region] = {
                    'started': [],
                    'error': str(e),
                    'success': False,
                }

        return results

    def stop_instance(self, formatted_data):
        results = {}

        for region, instances in formatted_data.items():
            self.set_region(region)
            instance_ids = [instance["InstanceId"] for instance in instances]

            try:
                response = self.client.stop_instances(InstanceIds=instance_ids)
                stopping_instances = response.get('StoppingInstances', [])
                results[region] = {
                    'stopped': [inst['InstanceId'] for inst in stopping_instances],
                    'success': True,
                }
            except Exception as e:
                results[region] = {
                    'stopped': [],
                    'error': str(e),
                    'success': False,
                }

        return results
    
    def retrieve_ec2_instance_data(self):
        instances = self.client.describe_instances()
        instance_data = []
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                flat_instance = {}
                for key, value in instance.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            flat_instance[f'{key}.{sub_key}'] = sub_value
                    else:
                        flat_instance[key] = value
                instance_data.append(flat_instance)

        instance_df = pd.DataFrame(instance_data)
        if instance_df.empty:
            print(f"No instance data retrieved for region {self.region}")
            return pd.DataFrame()

        # print(f"Initial Instance DataFrame for {self.region}:")
        # print(instance_df.head())

        status_response = self.client.describe_instance_status(IncludeAllInstances=True)
        status_data = status_response.get('InstanceStatuses', [])
        flat_status_data = []
        for status in status_data:
            flat_status = {'InstanceId': status['InstanceId']}
            for key, value in status.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        flat_status[f'{key}.{sub_key}'] = sub_value
                else:
                    flat_status[key] = value
            flat_status_data.append(flat_status)

        status_df = pd.DataFrame(flat_status_data)
        if status_df.empty:
            print(f"No status data retrieved for region {self.region}")
            return instance_df

        print(f"Status DataFrame for {self.region}:")
        print(status_df.head())

        for column in status_df.columns:
            if column not in instance_df.columns:
                instance_df[column] = ""

        for column in instance_df.columns:
            if column not in status_df.columns:
                status_df[column] = ""

        instance_df.fillna("", inplace=True)
        status_df.fillna("", inplace=True)

        merged_df = pd.merge(instance_df, status_df, on='InstanceId', how='left', suffixes=('', '_vSTATUS'))

        self.instance_data = merged_df
        return self.instance_data
    
    def retrieve_ec2_launch_templates(self):
        templates = self.client.describe_launch_templates()
        data = []
        for template in templates['LaunchTemplates']:
            template_data = {}
            for key, value in template.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        template_data[f'{key}.{sub_key}'] = sub_value
                else:
                    template_data[key] = value
            data.append(template_data)
        
        df = pd.DataFrame(data)
        df['THISDFSTATUS'] = 'fresh'

        return df

    def get_instance_type_details(self):
        paginator = self.client.get_paginator('describe_instance_types')
        instance_type_data = []

        for page in paginator.paginate():
            for instance_type in page['InstanceTypes']:
                flat_instance_type = {}
                for key, value in instance_type.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            flat_instance_type[f'{key}.{sub_key}'] = sub_value
                    else:
                        flat_instance_type[key] = value
                instance_type_data.append(flat_instance_type)

        instance_type_df = pd.DataFrame(instance_type_data)
        return instance_type_df

    def set_termination_protection(self, instance_id, enable=True):
        """
        Set termination protection for a specific EC2 instance.

        :param instance_id: The ID of the instance to modify.
        :param enable: Boolean flag to enable (True) or disable (False) termination protection.
        """
        try:
            self.client.modify_instance_attribute(
                InstanceId=instance_id,
                DisableApiTermination={'Value': enable}
            )
            action = "enabled" if enable else "disabled"
            print(f"Termination protection {action} for instance {instance_id}.")
        except Exception as e:
            print(f"Failed to set termination protection for instance {instance_id}: {str(e)}")
            raise