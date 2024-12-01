import asyncio
import pandas as pd
import os
import tempfile
from aiohttp import ClientSession  # Only if you are using aiohttp for other requests
from concurrent.futures import ThreadPoolExecutor  # For running sync code in async
from lib.aws_data_manager import AwsDataManager  # Your existing AwsDataManager
from lib.parquet_tools import df_write_to_pq, concat_df_to_existing_pq as concat_to_pq

class EC2DataFetcher:
    def __init__(self, regions, details_to_add=None):
        """
        Initializes the EC2DataFetcher with a list of AWS regions and optional details to add.
        """
        self.regions = regions
        self.details_to_add = details_to_add if details_to_add else []
        self.aws_data_manager = AwsDataManager(details_to_add=self.details_to_add)
        self.executor = ThreadPoolExecutor()  # Executor to run blocking code

    async def fetch_instance_data_for_region(self, region):
        """
        Asynchronously fetches EC2 instance data for a specific region by running the blocking code in an executor.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.aws_data_manager.get_data,
            'ec2_instances',
            region,
            self.details_to_add
        )

    async def fetch_instance_data(self):
        """
        Asynchronously fetches EC2 instance data from the specified regions.
        """
        tasks = [self.fetch_instance_data_for_region(region) for region in self.regions]
        all_data = await asyncio.gather(*tasks)

        # Filter out any None responses and concatenate the dataframes
        all_data = [df for df in all_data if df is not None]

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()  # Return an empty DataFrame if no data is retrieved

    def append_df_to_parquet(self, df, file_path):
        """
        Appends the DataFrame to an existing Parquet file.
        If the file or directory doesn't exist, creates them.
        """
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        if os.path.exists(file_path):
            concat_to_pq(df, file_path)
        else:
            df_write_to_pq(df, file_path)

    async def get_ec2_data_file(self, file_path=None):
        """
        Retrieves EC2 data from the specified regions asynchronously and appends it to a Parquet file.
        """
        ec2_data = await self.fetch_instance_data()
        if ec2_data.empty:
            raise ValueError("No EC2 data retrieved from the specified regions.")
        
        if file_path is None:
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, 'ec2_data.parquet')

        self.append_df_to_parquet(ec2_data, file_path)
        return file_path

    async def schedule_fetch(self, interval, file_path=None):
        """
        Runs the EC2 data fetching on a schedule.
        """
        while True:
            try:
                await self.get_ec2_data_file(file_path)
            except Exception as e:
                print(f"Error during fetch: {e}")
            
            if interval == 0:
                break
            
            await asyncio.sleep(interval)

