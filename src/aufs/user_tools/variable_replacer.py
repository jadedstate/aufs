import os
import pandas as pd
from pathlib import Path

class ConfigReader:
    def __init__(self, config_path):
        self.config_path = config_path
        self.defaults_df = self._load_or_create_csv('packaging_defaults.csv')
        self.versions_df = self._load_or_create_csv('packaging_versions.csv')

    def _load_or_create_csv(self, file_name):
        file_path = os.path.join(self.config_path, file_name)
        if os.path.exists(file_path):
            return pd.read_csv(file_path)
        else:
            return pd.DataFrame()  # Return an empty DataFrame if the file doesn't exist

    def get_external_variables(self):
        if 'EXTERNALVARIABLES' in self.defaults_df.columns:
            return self.defaults_df['EXTERNALVARIABLES'].dropna().unique().tolist()
        return []

    def get_versions_info(self):
        return self.versions_df

class VariableReplacer:
    def __init__(self, config_reader, df):
        self.config_reader = config_reader
        self.df = df

    def replace_in_row(self, row):
        """This will be overridden by subclasses for specific replacement logic."""
        pass

    def replace_in_all(self):
        """Iterates through all rows and applies replacements."""
        for idx, row in self.df.iterrows():
            self.df.at[idx, 'DESTPREVIEW'] = self.replace_in_row(row)

class ExternalIteratedReplacer(VariableReplacer):
    def replace_in_row(self, row):
        """Handles external iterated replacements for each row."""
        dest_value = row['DEST']
        if not isinstance(dest_value, str):
            return dest_value

        # Iterate through external variables and replace them
        external_vars = self.config_reader.get_external_variables()
        for ext_var in external_vars:
            if f"${ext_var}" in dest_value:
                # Replace external variable with a placeholder for now
                dest_value = dest_value.replace(f"${ext_var}", "external_value")
        
        return dest_value

class ExternalBatchReplacer(VariableReplacer):
    def replace_in_all(self):
        """Handles external variables for batch replacement across all rows."""
        external_vars = self.config_reader.get_external_variables()
        for idx, row in self.df.iterrows():
            dest_value = row['DEST']
            if not isinstance(dest_value, str):
                continue
            
            # Replace in batch for all rows
            for ext_var in external_vars:
                if f"${ext_var}" in dest_value:
                    self.df.at[idx, 'DESTPREVIEW'] = dest_value.replace(f"${ext_var}", "external_value")

class InternalIteratedReplacer(VariableReplacer):
    def replace_in_row(self, row):
        """Handles internal iterated replacements for each row."""
        dest_value = row['DEST']
        if not isinstance(dest_value, str):
            return dest_value
        
        # Replace internal variables by matching to column headers
        for column in self.df.columns:
            if f"${column}" in dest_value:
                value = row[column]
                dest_value = dest_value.replace(f"${column}", str(value))

        return dest_value

class InternalBatchReplacer(VariableReplacer):
    def replace_in_all(self):
        """Handles internal variables for batch replacement across all rows."""
        for idx, row in self.df.iterrows():
            dest_value = row['DEST']
            if not isinstance(dest_value, str):
                continue
            
            # Replace internal variables in batch
            for column in self.df.columns:
                if f"${column}" in dest_value:
                    self.df.at[idx, 'DESTPREVIEW'] = dest_value.replace(f"${column}", str(row[column]))

class VersionReplacer(VariableReplacer):
    def __init__(self, config_reader, df, preview_mode):
        super().__init__(config_reader, df)
        self.preview_mode = preview_mode

    def replace_in_row(self, row):
        """Handles individual row versioning replacement for VERSION identifiers."""
        dest_value = row['DESTPREVIEW']
        if not isinstance(dest_value, str):
            return dest_value

        while 'VERSION' in dest_value:
            # Identify and process the version identifier (e.g., 'some_str_VERSION')
            version_pos = dest_value.find("VERSION")
            identifier_end = min(dest_value.find('/', version_pos), dest_value.find('.', version_pos))
            identifier_end = identifier_end if identifier_end != -1 else len(dest_value)

            # Extract the version identifier (string ending with '_VERSION' or '-VERSION')
            version_identifier = dest_value[:identifier_end].split('/')[-1]  

            # Check if version identifier exists in config and process it
            if version_identifier in self.config_reader.get_versions_info().columns:
                version_info = self.config_reader.get_versions_info()[version_identifier].iloc[0]
                new_version = self.apply_version_logic(version_info)

                # Replace this occurrence of VERSION with new version
                dest_value = dest_value.replace("VERSION", new_version, 1)

                # If not in preview mode, update the version file with the new version
                if not self.preview_mode:
                    self.update_version_file(version_identifier)

        return dest_value

    def apply_version_logic(self, version_info):
        """Creates the new version string from version_info."""
        last_used, date_entered, prefix, padding = version_info.split('-')
        new_version_number = str(int(last_used) + 1).zfill(int(padding))
        return f"{prefix}{new_version_number}"

    def update_version_file(self, version_identifier):
        """Updates the versions file by incrementing the current version."""
        versions_df = self.config_reader.get_versions_info()

        # Get current version info and increment it
        current_version_info = versions_df[version_identifier].iloc[0]
        last_used, date_entered, prefix, padding = current_version_info.split('-')
        new_version = int(last_used) + 1

        # Update the versions DataFrame with the new version and timestamp
        versions_df[version_identifier] = f"{new_version}-{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}-{prefix}-{padding}"
        
        # Save the updated DataFrame back to CSV
        versions_file_path = os.path.join(self.config_reader.config_path, 'packaging_versions.csv')
        versions_df.to_csv(versions_file_path, index=False)

    def replace_in_all(self):
        """Iterates through all rows and applies version replacements."""
        for idx, row in self.df.iterrows():
            self.df.at[idx, 'DESTPREVIEW'] = self.replace_in_row(row)

    def update_all_versions(self):
        """Updates all versions if required (only if not in preview mode)."""
        if not self.preview_mode:
            versions_df = self.config_reader.get_versions_info()
            versions_file_path = os.path.join(self.config_reader.config_path, 'packaging_versions.csv')
            versions_df.to_csv(versions_file_path, index=False)

class DuplicateHandler:
    def __init__(self, config_reader, df):
        self.df = df
        self.config_reader = config_reader

    def process_duplicates(self):
        """Processes rows with duplicate DEST values."""
        # Identify duplicate DEST values
        duplicate_rows = self.df[self.df.duplicated(subset=['DEST'], keep=False)]

        for dest_value, group_df in duplicate_rows.groupby('DEST'):
            # Sort based on the version extracted from SRC
            sorted_group = self._sort_by_src_version(group_df)
            
            # Process the first row to get the base version
            base_version_row = sorted_group.iloc[0]
            base_version_identifier = self._get_version_identifier_from_dest(base_version_row['DEST'])
            
            # Replace the version for the remaining rows
            self._replace_additional_versions(base_version_identifier, sorted_group)

    def _sort_by_src_version(self, group_df):
        """Sort the group of rows by the version number extracted from SRC."""
        group_df['src_version'] = group_df['SRC'].apply(self._extract_version_from_src)
        return group_df.sort_values(by='src_version')

    def _extract_version_from_src(self, src):
        """Extracts version from the SRC filename (e.g., file_v001 -> 1)."""
        filename = Path(src).stem.lower()
        if '_v' in filename:
            version_str = filename.split('_v')[-1]
            return int(''.join(filter(str.isdigit, version_str)))
        return 0

    def _get_version_identifier_from_dest(self, dest_value):
        """Extract the version identifier from the DEST path."""
        version_pos = dest_value.find("VERSION")
        identifier_end = min(dest_value.find('/', version_pos), dest_value.find('.', version_pos))
        identifier_end = identifier_end if identifier_end != -1 else len(dest_value)
        return dest_value[:identifier_end].split('/')[-1]  # Extract identifier

    def _replace_additional_versions(self, version_identifier, sorted_group):
        """Replace the version in the DEST field for rows after the first."""
        for idx, row in sorted_group.iterrows():
            # Increment the version and apply to additional rows
            if idx > 0:
                new_version = self._get_incremented_version(version_identifier)
                sorted_group.at[idx, 'DEST'] = row['DEST'].replace('VERSION', new_version)

        # Update the DEST fields in the original DataFrame
        self.df
