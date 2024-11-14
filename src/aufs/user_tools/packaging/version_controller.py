import os
import csv
from datetime import datetime

class VersionController:
    def __init__(self, root_path, recipient, user=None, v_format="v", padding=4, working_versions=None):
        self.root_path = root_path
        self.recipient = recipient
        self.user = user or "system"
        self.v_format = v_format
        self.padding = padding
        self.working_versions = working_versions if working_versions is not None else {}

    def get_item_version_path(self, item):
        """Define path to the item’s versioning directory."""
        # print("ROOT PATH: ",self.root_path)
        # print("RECIPIENT: ", self.recipient)
        # print("ITEM: ", item)
        version_dir = os.path.join(self.root_path, self.recipient, "versioning", item)
        os.makedirs(version_dir, exist_ok=True)
        return version_dir

    def retrieve_working_version(self, item):
        """
        Retrieve or initialize the working version for an item, based on existing version files.
        Returns the formatted version ID and the current working_versions dictionary.
        """
        if item in self.working_versions:
            return self._format_version_id(self.working_versions[item]), self.working_versions

        # Initialize version if not in working_versions
        version_path = self.get_item_version_path(item)
        latest_file = self._get_latest_version_file(version_path)
        previous_version = 0

        if "YYYYMMDD_PKGVERSION3PADDED" in item:
            current_date = datetime.utcnow().strftime('%Y%m%d')
            if latest_file:
                with open(latest_file, 'r') as f:
                    last_entry = list(csv.reader(f))
                    last_entry_date, last_version = last_entry[-1][:2]
                    if last_entry_date == current_date:
                        previous_version = int(last_version)

        elif latest_file:
            with open(latest_file, 'r') as f:
                last_entry = list(csv.reader(f))
                previous_version = int(last_entry[-1][1])

        # Update working_versions and return
        self.working_versions[item] = previous_version + 1
        # print("working versions ARE: ")
        # print(self.working_versions)
        return self._format_version_id(self.working_versions[item]), self.working_versions

    def _get_latest_version_file(self, path):
        """Retrieve the latest timestamped CSV file in a given directory."""
        try:
            files = [f for f in os.listdir(path) if f.endswith('.csv')]
            if not files:
                return None
            # Sort files by timestamp embedded in filename and return the latest
            return os.path.join(path, sorted(files, key=lambda x: int(x.split('-')[-1].split('.')[0]))[-1])
        except Exception as e:
            print(f"Error retrieving latest version file: {e}")
            return None

    def _format_version_id(self, version_number):
        """Format the version ID based on the v_format and padding settings."""
        prefix = "v" if self.v_format == "v" else ("V" if self.v_format == "V" else "")
        return f"{prefix}{version_number:0{self.padding}d}"

    def log_version(self, item):
        """
        Log the version information for an item in a timestamped CSV file.
        If sub-items are associated, their versions are also updated.
        """
        version_path = self.get_item_version_path(item)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        log_path = os.path.join(version_path, f"{item}-{timestamp}.csv")
        
        version_id = self.working_versions[item]

        # Write the new version entry to a timestamped log file
        with open(log_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([datetime.utcnow().strftime('%Y%m%d'), version_id, self.user, item])

    def check_and_initialize_sub_items(self, item):
        """
        Load sub-items from thisitemsitems.csv. If empty, alert the user to populate it.
        Otherwise, load the list and ensure all sub-items are tracked.
        """
        sub_items_path = os.path.join(self.get_item_version_path(item), "thisitemsitems.csv")
        
        # Check if thisitemsitems.csv exists and is populated
        if not os.path.exists(sub_items_path):
            raise ValueError(f"No sub-items file found for '{item}'. Please populate 'thisitemsitems.csv'.")
        
        # Read and validate sub-items
        with open(sub_items_path, 'r') as csvfile:
            sub_items = [row[0] for row in csv.reader(csvfile) if row]
        
        if not sub_items:
            raise ValueError(f"Sub-items list for '{item}' is empty. Populate 'thisitemsitems.csv' to proceed.")
        
        return sub_items
