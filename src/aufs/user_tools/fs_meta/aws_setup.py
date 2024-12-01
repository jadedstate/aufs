import os
import boto3

class AwsSetup:
    def __init__(self, region=None):
        self.credentials_file = os.path.expanduser("~/.aws/credentials")
        self.config_file = os.path.expanduser("~/.aws/config")
        self.region = region
        self.client = boto3.client('ec2', region_name=self.region)
        self.instance_data = None

    @classmethod
    def setup(cls, region=None):
        # Class method to check and set up AWS credentials
        instance = cls(region)
        instance._check_aws_credentials()
        if instance.region:
            instance.set_region(instance.region)

    def set_region(self, region):
        self.region = region
        self.client = boto3.client('ec2', region_name=self.region)

    def _check_aws_credentials(self):
        # Check if AWS credentials file exists or if env variables are set
        if not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
            if not os.path.isfile(self.credentials_file):
                self._setup_aws_credentials()
            else:
                with open(self.credentials_file, 'r') as file:
                    if '[default]' not in file.read():
                        self._setup_aws_credentials()

        # Set region from config file or environment
        if not self.region:
            self.region = os.getenv('AWS_DEFAULT_REGION')
            if not self.region and os.path.isfile(self.config_file):
                with open(self.config_file, 'r') as file:
                    for line in file:
                        if line.startswith('region'):
                            self.region = line.partition('=')[2].strip()

    def _setup_aws_credentials(self):
        # Prompt user for AWS credentials if not set in environment
        access_key = input("Enter AWS Access Key ID: ")
        secret_key = input("Enter AWS Secret Access Key: ")
        self.region = input("Enter AWS Default region (e.g., us-west-2): ")

        # Save credentials to file
        os.makedirs(os.path.dirname(self.credentials_file), exist_ok=True)
        with open(self.credentials_file, 'w') as file:
            file.write('[default]\n')
            file.write(f'aws_access_key_id = {access_key}\n')
            file.write(f'aws_secret_access_key = {secret_key}\n')

        # Save default region to config file
        with open(self.config_file, 'w') as file:
            file.write('[default]\n')
            file.write(f'region = {self.region}\n')
