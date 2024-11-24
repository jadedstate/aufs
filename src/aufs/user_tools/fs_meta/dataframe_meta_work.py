import pandas as pd
import os
import platform
import re
import math
import hashlib
from datetime import datetime
import pytz
from .config import F_root_path, loadConfigs

def add_packagerecipient_type003(df, package_name_column='PACKAGENAME', recipient_column='PACKAGERECIPIENT'):
    """
    Adds the 'PACKAGERECIPIENT' column to the DataFrame if it doesn't exist,
    and fills missing or empty values by extracting the recipient from 'PACKAGENAME'.
    
    Parameters:
    - df (pd.DataFrame): The DataFrame to modify.
    - package_name_column (str): The column name containing the package name (default 'PACKAGENAME').
    - recipient_column (str): The column name for the recipient (default 'PACKAGERECIPIENT').
    
    Returns:
    - pd.DataFrame: The modified DataFrame with 'PACKAGERECIPIENT' values.
    """
    
    # Check if the package name column exists
    if package_name_column not in df.columns:
        raise ValueError(f"Column '{package_name_column}' not found in DataFrame.")
    
    # Check if the recipient column exists, if not create it
    if recipient_column not in df.columns:
        df[recipient_column] = ''
        print(f"Added missing '{recipient_column}' column.")

    # Function to extract the recipient from PACKAGENAME
    def extract_recipient(package_name):
        if not isinstance(package_name, str):
            print(f"Invalid package name encountered: {package_name}")
            return None
        
        try:
            # Split by '-' and ensure there are at least 3 elements
            split_name = package_name.split('-')
            if len(split_name) < 3:
                print(f"Unexpected format for package name: {package_name}")
                return None

            # Take the 3rd element (index 2)
            third_element = split_name[2]

            # Split the 3rd element by '_'
            sub_parts = third_element.split('_')

            # Ensure there are more than 2 elements after the split
            if len(sub_parts) < 3:
                print(f"Unexpected format in 3rd element of package name: {package_name}")
                return None

            # Remove the last two elements and join the remaining ones with '_'
            recipient = '_'.join(sub_parts[:-2])

            # Return the recipient or None if it's invalid
            if recipient:
                return recipient
            else:
                print(f"Recipient extraction failed for package name: {package_name}")
                return None

        except Exception as e:
            print(f"Error extracting recipient from package name '{package_name}': {e}")
            return None

    # Iterate through each row in the DataFrame and fill missing recipient values
    for index, row in df.iterrows():
        current_recipient = row[recipient_column]
        package_name = row[package_name_column]

        # If recipient is empty or None, attempt extraction
        if not current_recipient or pd.isnull(current_recipient):
            new_recipient = extract_recipient(package_name)
            if new_recipient:
                df.at[index, recipient_column] = new_recipient
                print(f"Extracted recipient '{new_recipient}' for package '{package_name}' (row {index}).")
            else:
                print(f"Failed to extract recipient for row {index}, package name: '{package_name}'.")

    # Check if any rows still have missing recipients
    missing_recipients = df[df[recipient_column].isnull() | (df[recipient_column] == '')]
    if not missing_recipients.empty:
        print(f"Warning: The following rows could not have a recipient extracted:\n{missing_recipients[[package_name_column, recipient_column]]}")
    
    return df

def string_locate_row_and_return_field(df, search_term, search_column, return_column):
    """
    Locates a row in the DataFrame by searching for a string in a specified column and returns a value from another column.

    Args:
        df (pd.DataFrame): The DataFrame to search within.
        search_term (str): The search term to locate in the DataFrame.
        search_column (str): The name of the column to search for the term.
        return_column (str): The column from which to return the value if the search term is found.

    Returns:
        The value from the return_column of the located row, or None if no match is found.
    """
    # Convert the input search term and the search column values to strings for searching
    search_term_str = str(search_term)
    try:
        # Locate the row where the search column contains the search term
        matched_row = df[df[search_column].astype(str).str.contains(search_term_str, na=False)]
        if not matched_row.empty:
            # Return the value from the specified return column
            return matched_row.iloc[0][return_column]
        else:
            print(f"No match found for {search_term} in column {search_column}")
            return None
    except KeyError as e:
        print(f"Error: {e} - Check if the column names are correct.")
        return None

def format_file_size(df):
    """
    Formats the FILESIZE column in the DataFrame, converting file sizes from bytes
    to a more readable format (KB, MB, GB, etc.), and ensuring all output is in string format.
    Any non-positive values or values that can't be converted will default to "0 B".
    
    Args:
        df (pd.DataFrame): DataFrame containing the FILESIZE column.
    
    Returns:
        pd.DataFrame: Updated DataFrame with formatted FILESIZE column.
    """
    def bytes_to_best_unit(value):
        try:
            size_in_bytes = int(value)
        except (ValueError, TypeError):
            return "0 B"  # Default for problematic inputs
        
        if size_in_bytes <= 0:
            return "0 B"  # Default for non-positive values
        
        size_names = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
        i = int(math.floor(math.log(size_in_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_in_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    if 'FILESIZE' in df.columns:
        df['FILESIZE'] = df['FILESIZE'].apply(bytes_to_best_unit)
    else:
        raise KeyError("FILESIZE column not found in the DataFrame.")

    return df

def add_hashedfile_entrytime_columns_noRoot(df, column_name_for_hashing, noHashNonStringFields=True):
    # Generate the ENTRYTIME timestamp
    entry_time = datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
    
    # Add ENTRYTIME column with the generated timestamp
    df['ENTRYTIME'] = entry_time
    
    # Preprocess ENTRYTIME column to ensure compatibility
    datetime_format = '%Y-%m-%d %H:%M:%S %Z'
    default_datetime = pd.to_datetime('1970-01-01')
    df['ENTRYTIME'] = pd.to_datetime(df['ENTRYTIME'], errors='coerce', format=datetime_format).fillna(default_datetime)
    # print("Added entrytime....")
    # Check if the specified column exists
    if column_name_for_hashing in df.columns:
        # Create a temporary column for processing
        temp_column = df[column_name_for_hashing].copy()
        
        # Handle non-string fields based on noHashNonStringFields flag
        if temp_column.dtype != 'object' and noHashNonStringFields:
            print(f"The column '{column_name_for_hashing}' is not of type string. Marking as 'noHash'.")
            df['HASHEDFILE'] = 'noHash'
        else:
            # Convert column to string if it's not already a string type
            if temp_column.dtype != 'object':
                print(f"The column '{column_name_for_hashing}' is not of type string. Attempting to convert to string.")
                temp_column = temp_column.astype(str)

            # Remove all specified substrings
            substrings_to_remove = {}
            for substring in substrings_to_remove.values():
                temp_column = temp_column.apply(lambda x: x.replace(substring, ''))

            # Hash the processed temporary column's values
            def hash_value(value):
                try:
                    value = str(value).strip()  # Ensure value is a string and trim spaces
                    hash_obj = hashlib.sha256()  # Create a hash object
                    hash_obj.update(value.encode('utf-8'))
                    return hash_obj.hexdigest()
                except Exception as e:
                    return 'noHash'
            
            df['HASHEDFILE'] = temp_column.apply(hash_value)
            # print(df)
    else:
        print(f"Column '{column_name_for_hashing}' not found in DataFrame. HASHEDFILE column will not be created.")
        df['HASHEDFILE'] = 'noColumn'
    
    return df

def add_hashedfile_entrytime_columns_noRoot_noSlashes(df, column_name_for_hashing, noHashNonStringFields=True):
    # Generate the ENTRYTIME timestamp
    entry_time = datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
    
    # Add ENTRYTIME column with the generated timestamp
    df['ENTRYTIME'] = entry_time
    
    # Preprocess ENTRYTIME column to ensure compatibility
    datetime_format = '%Y-%m-%d %H:%M:%S %Z'
    default_datetime = pd.to_datetime('1970-01-01')
    df['ENTRYTIME'] = pd.to_datetime(df['ENTRYTIME'], errors='coerce', format=datetime_format).fillna(default_datetime)
    # print("Added entrytime....")
    # Check if the specified column exists
    if column_name_for_hashing in df.columns:
        # Create a temporary column for processing
        temp_column = df[column_name_for_hashing].copy()
        
        # Handle non-string fields based on noHashNonStringFields flag
        if temp_column.dtype != 'object' and noHashNonStringFields:
            print(f"The column '{column_name_for_hashing}' is not of type string. Marking as 'noHash'.")
            df['HASHEDFILE'] = 'noHash'
        else:
            # Convert column to string if it's not already a string type
            if temp_column.dtype != 'object':
                print(f"The column '{column_name_for_hashing}' is not of type string. Attempting to convert to string.")
                temp_column = temp_column.astype(str)

            # Remove all specified substrings
            substrings_to_remove = F_root_path(all=True)
            for substring in substrings_to_remove.values():
                temp_column = temp_column.apply(lambda x: x.replace(substring, ''))
                
            # Remove all slashes and backslashes, collapsing the text
            try:
                temp_column = temp_column.apply(lambda x: x.replace('/', '').replace('\\', ''))
            except Exception as e:
                print("Error removing slashes:", e)
                pass

            # Hash the processed temporary column's values
            def hash_value(value):
                try:
                    value = str(value).strip()  # Ensure value is a string and trim spaces
                    hash_obj = hashlib.sha256()  # Create a hash object
                    hash_obj.update(value.encode('utf-8'))
                    return hash_obj.hexdigest()
                except Exception as e:
                    return 'noHash'
            
            df['HASHEDFILE'] = temp_column.apply(hash_value)
            # print(df)
    else:
        print(f"Column '{column_name_for_hashing}' not found in DataFrame. HASHEDFILE column will not be created.")
        df['HASHEDFILE'] = 'noColumn'
    
    return df

def add_hashedfile_entrytime_columns(df, column_name_for_hashing, noHashNonStringFields=True):
    # Generate the ENTRYTIME timestamp
    entry_time = datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
    print(entry_time)
    
    # Add ENTRYTIME column with the generated timestamp
    df['ENTRYTIME'] = entry_time
    
    # Preprocess ENTRYTIME column to ensure compatibility
    datetime_format = '%Y-%m-%d %H:%M:%S %Z'  # adjust this format as needed
    default_datetime = pd.to_datetime('1970-01-01')  # default timestamp in case of parsing errors
    df['ENTRYTIME'] = pd.to_datetime(df['ENTRYTIME'], errors='coerce', format=datetime_format).fillna(default_datetime)

    # Check if the specified column exists
    if column_name_for_hashing in df.columns:
        # Handle non-string fields based on noHashNonStringFields flag
        if df[column_name_for_hashing].dtype != 'object' and noHashNonStringFields:
            print(f"The column '{column_name_for_hashing}' is not of type string. Marking as 'noHash'.")
            df['HASHEDFILE'] = 'noHash'
        else:
            if df[column_name_for_hashing].dtype != 'object':
                print(f"The column '{column_name_for_hashing}' is not of type string. Attempting to convert to string.")
                df[column_name_for_hashing] = df[column_name_for_hashing].astype(str)
            
            # Create HASHEDFILE column by hashing the specified column's values
            def hash_value(value):
                try:
                    # Ensure value is a string and trim spaces
                    value = str(value).strip()
                    # Create a hash object
                    hash_obj = hashlib.sha256()
                    hash_obj.update(value.encode('utf-8'))
                    return hash_obj.hexdigest()
                except Exception as e:
                    return 'noHash'
            
            df['HASHEDFILE'] = df[column_name_for_hashing].apply(hash_value)
    else:
        print(f"Column '{column_name_for_hashing}' not found in DataFrame. HASHEDFILE column will not be created.")
        df['HASHEDFILE'] = 'noColumn'
    
    return df

def add_shot_names_to_results(shot_data_df, results_df):
    """
    Adds SHOTNAME information to the working DataFrame based on matching file names,
    SEQUENCE, or LINK by checking against a modified version of the shot names
    (without the "THRG_" prefix) without altering any other column data.

    Parameters:
    - shot_data_df: A pandas DataFrame containing shot data, including a 'SHOTNAME' column.
    - results_df: The working pandas DataFrame to which 'SHOTNAME' information will be added.

    Returns:
    - The modified results_df with the 'SHOTNAME' column populated based on matches.
    """
    
    # Ensure that both shot_data_df and results_df are pandas DataFrame instances
    if not isinstance(shot_data_df, pd.DataFrame) or not isinstance(results_df, pd.DataFrame):
        raise ValueError("Both shot_data_df and results_df must be pandas DataFrame instances.")
    
    # Ensure the SHOTNAME column exists in results_df
    if 'SHOTNAME' not in results_df.columns:
        results_df['SHOTNAME'] = ''

    # Prepare a dictionary to map modified shot names back to their full SHOTNAME
    shot_name_mapping = {row['SHOTNAME'].replace("THRG_", ""): row['SHOTNAME'] for _, row in shot_data_df.iterrows()}

    # Define the columns to check for shot names
    check_columns = ['FILE', 'SEQUENCE', 'LINK']

    # Iterate over each row in results_df to look for matches in any of the specified columns
    for i, result_row in results_df.iterrows():
        for column in check_columns:
            if column in result_row:
                # Extract the part of the file path or sequence that may contain the shot name
                file_path_or_sequence = str(result_row[column])
                # Check against each modified shot name in shot_name_mapping
                for modified_shot_name, full_shot_name in shot_name_mapping.items():
                    if modified_shot_name in file_path_or_sequence:
                        # Assign the full SHOTNAME to the match
                        results_df.at[i, 'SHOTNAME'] = full_shot_name
                        break  # Stop checking once a match is found for this row

    return results_df

def add_who_info_to_files(df):
    """
    Updates the DataFrame by setting the 'WHOFROM' column based on the 'SEQUENCE' or 'FILE' columns.
    It normalizes slashes in paths, then looks for "/IN/" or "/OUT/" and finds the second part to the right.
    """
    # Initialize 'WHOFROM' column; assume it may already exist
    if 'WHOFROM' not in df.columns:
        df['WHOFROM'] = ''  # Initialize if not present

    # Function to normalize slashes and extract the specified part
    def normalize_and_extract(value):
        if pd.isna(value):
            return ''
        # Normalize slashes to forward slashes
        normalized_value = value.replace('\\', '/')
        parts = normalized_value.split('/')
        
        # Find and extract the second part to the right of "IN" or "OUT"
        for marker in ["IN"]:
            if marker in parts:
                marker_index = parts.index(marker)
                try:
                    # Return the part two places to the right of the marker
                    return parts[marker_index + 2]
                except IndexError:
                    # If there's no part two places to the right, return an empty string
                    return ''
        return ''  # Return empty string if neither "IN" nor "OUT" is found

    # Apply the extraction logic to each row for 'SEQUENCE' and 'FILE'
    for index, row in df.iterrows():
        sequence_extract = normalize_and_extract(row['SEQUENCE'])
        file_extract = normalize_and_extract(row['FILE'])
        # Prioritize 'SEQUENCE' column if it yields a result, else use 'FILE'
        df.at[index, 'WHOFROM'] = sequence_extract if sequence_extract else file_extract

    return df

def add_whofrom_info(df):
    """
    Updates the DataFrame by setting the 'WHOFROM' column based on the 'SEQUENCE' or 'FILE' columns.
    It normalizes slashes in paths, then looks for "/IN/" or "/OUT/" and finds the second part to the right.
    """
    # Initialize 'WHOFROM' column; assume it may already exist
    if 'WHOFROM' not in df.columns:
        df['WHOFROM'] = ''  # Initialize if not present
        # Function to replace backslashes with forward slashes in a given path
        def conform_slashes(path):
            return path.replace('\\', '/')
        
        # Process FILE for WHOFROM, conform slashes before processing
    for index, row in df.iterrows():
        if row['ISLINK'] == 'no':  # Only process rows representing links

            file_path = conform_slashes(row.get('FILE', ''))
            if 'IN' in file_path or 'OUT' in file_path:
                file_path_parts = file_path.split('/')
                try:
                    io_index = file_path_parts.index('IN') if 'IN' in file_path_parts else file_path_parts.index('OUT')
                    # Adjust to ensure it's the second part to the right of IN/OUT
                    df.at[index, 'WHOFROM'] = file_path_parts[io_index + 2] if io_index + 2 < len(file_path_parts) else ''
                except (ValueError, IndexError):
                    pass  # Do not set to 'local' or any default unless required

    return df

def add_whoto_info(df):

    df['WHOTO'] = ''

    # Function to replace backslashes with forward slashes in a given path
    def conform_slashes(path):
        return path.replace('\\', '/')

    for index, row in df.iterrows():
        if row['ISLINK'] != 'no':  # Only process rows representing links
            # Process TARGET for WHOTO, conform slashes before processing
            target_path = conform_slashes(row.get('TARGET', ''))
            if 'IN' in target_path or 'OUT' in target_path:
                target_parts = target_path.split('/')
                try:
                    io_index = target_parts.index('IN') if 'IN' in target_parts else target_parts.index('OUT')
                    # Adjust to ensure it's the second part to the right of IN/OUT
                    df.at[index, 'WHOFROM'] = target_parts[io_index + 2] if io_index + 2 < len(target_parts) else ''
                except (ValueError, IndexError):
                    pass  # Do not set to 'local' or any default unless required

            # Process FILE for WHOFROM, conform slashes before processing
            file_link_path = conform_slashes(row.get('FILE', ''))
            if 'IN' in file_link_path or 'OUT' in file_link_path:
                file_link_parts = file_link_path.split('/')
                try:
                    io_index = file_link_parts.index('IN') if 'IN' in file_link_parts else file_link_parts.index('OUT')
                    # Adjust to ensure it's the second part to the right of IN/OUT
                    df.at[index, 'WHOTO'] = file_link_parts[io_index + 2] if io_index + 2 < len(file_link_parts) else ''
                except (ValueError, IndexError):
                    pass  # Do not set to 'local' or any default unless required
    
    return df

def add_who_info_to_links(df):
    df['WHOFROM'] = ''
    df['WHOTO'] = ''

    # Function to replace backslashes with forward slashes in a given path
    def conform_slashes(path):
        return path.replace('\\', '/')

    for index, row in df.iterrows():
        # Process TARGET for WHOTO, conform slashes before processing
        target_path = conform_slashes(row.get('TARGET', ''))
        if 'IN' in target_path or 'OUT' in target_path:
            target_parts = target_path.split('/')
            try:
                io_index = target_parts.index('IN') if 'IN' in target_parts else target_parts.index('OUT')
                # Adjust to ensure it's the second part to the right of IN/OUT
                df.at[index, 'WHOTO'] = target_parts[io_index + 2] if io_index + 2 < len(target_parts) else ''
            except (ValueError, IndexError):
                pass  # Do not set to 'local' or any default unless required

        # Process SEQUENCE and LINK for WHOFROM, conform slashes before processing
        sequence_link_path = conform_slashes(row.get('SEQUENCE', '') + row.get('LINK', ''))
        if 'IN' in sequence_link_path or 'OUT' in sequence_link_path:
            sequence_link_parts = sequence_link_path.split('/')
            try:
                io_index = sequence_link_parts.index('IN') if 'IN' in sequence_link_parts else sequence_link_parts.index('OUT')
                # Adjust to ensure it's the second part to the right of IN/OUT
                df.at[index, 'WHOFROM'] = sequence_link_parts[io_index + 2] if io_index + 2 < len(sequence_link_parts) else ''
            except (ValueError, IndexError):
                pass  # Do not set to 'local' or any default unless required
    
    return df

def add_file_extension_column(df):
    """
    Adds a new column 'DOTEXTENSION' to the dataframe based on the 'FILE' column,
    extracting the file extension and filtering out extensions containing specific characters
    ("~", "#", "_", "-") or matching specific unwanted strings ('part', 'autosave', 'tmp').
    
    Parameters:
    - df (pd.DataFrame): The DataFrame to modify.
    
    Returns:
    - pd.DataFrame: The DataFrame with the added 'DOTEXTENSION' column.
    """
    # Characters to check in extensions for their presence
    forbidden_chars = {'~', '#', '_', '-'}
    # Exact string matches to filter out
    forbidden_strings = ['part', 'autosave', 'tmp']

    # Extract the extension and apply the filter
    def filter_extension(x):
        extension = x.split('.')[-1] if '.' in x else ''
        # Check if extension contains any forbidden character or matches any forbidden string
        if any(char in extension for char in forbidden_chars) or extension in forbidden_strings:
            return ''
        else:
            return extension

    df['DOTEXTENSION'] = df['FILE'].apply(filter_extension)

    return df

def add_hashedfile_column(df, column_name_for_hashing, noHashNonStringFields=True):
    if column_name_for_hashing in df.columns:
        # Handle non-string fields based on noHashNonStringFields flag
        if df[column_name_for_hashing].dtype != 'object' and noHashNonStringFields:
            print(f"The column '{column_name_for_hashing}' is not of type string. Marking as 'noHash'.")
            df['HASHEDFILE'] = 'noHash'
        else:
            if df[column_name_for_hashing].dtype != 'object':
                print(f"The column '{column_name_for_hashing}' is not of type string. Attempting to convert to string.")
                df[column_name_for_hashing] = df[column_name_for_hashing].astype(str)
            
            # Create HASHEDFILE column by hashing the specified column's values
            def hash_value(value):
                try:
                    # Ensure value is a string and trim spaces
                    value = str(value).strip()
                    # Create a hash object
                    hash_obj = hashlib.sha256()
                    hash_obj.update(value.encode('utf-8'))
                    return hash_obj.hexdigest()
                except Exception as e:
                    return 'noHash'
            
            df['HASHEDFILE'] = df[column_name_for_hashing].apply(hash_value)
    else:
        print(f"Column '{column_name_for_hashing}' not found in DataFrame. HASHEDFILE column will not be created.")
        df['HASHEDFILE'] = 'noColumn'
    
    return df

def add_ITEM_columns(df, column_name):
    # Initialize new columns with empty strings
    df['PARENTITEM'] = ''
    df['RAWITEMNAME'] = ''
    df['ITEMNAME'] = ''
    df['ITEMLOCATION'] = ''
    df['ITEMLOCATIONROOT'] = ''
    df['REMAPTYPE'] = ''
    
    # Function to parse each row
    def parse_row(value):
        try:
            # Step 1: Replace "\" with "/"
            value = value.replace("\\", "/")
            value_for_base_item_name = value
            # print("value for base item name: ", value_for_base_item_name)
            # Step 2: Find and remove all matches for "." followed by any %0d sequence notation, allow for 0-20
            value = re.sub(r'\.%0\d{1,2}d', '', value)  # Adjusted regex to correctly target sequence placeholders
            # Step 3: Split using "/"
            parts = value.split("/")
            base_parts = value_for_base_item_name.split("/")
            # Steps 4-6: Extract and assign parts to new columns
            remap_type = 'string'
            raw_item_name = base_parts[-1] if len(base_parts) > 0 else ''
            item_name = parts[-1] if len(parts) > 0 else ''
            item_location_root = parts[0] if len(parts) > 0 else ''
            item_location = '/'.join(parts[1:-1]) if len(parts) > 2 else ''
            return remap_type, raw_item_name ,item_name, item_location, item_location_root
        except Exception as e:
            # In case of error, return empty strings
            return '', '', ''

    # Apply parse_row function to each row in the specified column and assign the results to new columns
    df[['REMAPTYPE', 'RAWITEMNAME', 'ITEMNAME', 'ITEMLOCATION', 'ITEMLOCATIONROOT']] = df[column_name].apply(lambda x: parse_row(x)).tolist()

    return df

def add_strippeditemnames_itemversions(df):
    """
    Adds 'STRIPPEDITEMNAME' and 'ITEMVERSION' columns to the DataFrame by processing 'ITEMNAME' and 'SHOTNAME' columns.
    It strips the file extension from 'ITEMNAME', then checks for a 'SHOTNAME'. If 'SHOTNAME' is present,
    it removes this from the start of the 'ITEMNAME', along with any trailing "-" or "_".
    Then it attempts to find a version number in 'STRIPPEDITEMNAME', following specific rules, and adds it to 'ITEMVERSION'.

    Parameters:
    - df (pd.DataFrame): The DataFrame to modify.

    Returns:
    - pd.DataFrame: The DataFrame with the added 'STRIPPEDITEMNAME' and 'ITEMVERSION' columns.
    """
    for index, row in df.iterrows():
        # Initial setup
        item_version = ""
        item_base_name = row['ITEMNAME'].rsplit('.', 1)[0] if '.' in row['ITEMNAME'] else row['ITEMNAME']
        
        # Processing for STRIPPEDITEMNAME
        if pd.notna(row['SHOTNAME']) and row['SHOTNAME']:
            shot_name = row['SHOTNAME']
            if item_base_name.startswith(shot_name):
                stripped_name = item_base_name[len(shot_name):].lstrip('-_')
            else:
                stripped_name = item_base_name
        else:
            stripped_name = item_base_name
        
        df.at[index, 'STRIPPEDITEMNAME'] = stripped_name

        # Attempt to find version number in STRIPPEDITEMNAME
        parts = stripped_name.split('v') if 'v' in stripped_name else stripped_name.split('V') if 'V' in stripped_name else None
        if parts and len(parts) > 1:
            second_part = parts[1].split('.')[0]  # Take the part before the first dot, if any
            if second_part.isdigit() and len(second_part.strip('0')) > 0:  # Check if it's a padded number only
                item_version = f"v{second_part}"

        df.at[index, 'ITEMVERSION'] = item_version

    return df

def add_strippeditemname_column(df):
    """
    Adds a 'STRIPPEDITEMNAME' column to the DataFrame by processing 'ITEMNAME' and 'SHOTNAME' columns.
    It strips the file extension from 'ITEMNAME', then checks for a 'SHOTNAME'. If 'SHOTNAME' is present,
    it removes this from the start of the 'ITEMNAME', along with any trailing "-" or "_".

    Parameters:
    - df (pd.DataFrame): The DataFrame to modify.

    Returns:
    - pd.DataFrame: The DataFrame with the added 'STRIPPEDITEMNAME' column.
    """
    for index, row in df.iterrows():
        # Remove the file extension from 'ITEMNAME' to get the base name
        item_base_name = row['ITEMNAME'].rsplit('.', 1)[0] if '.' in row['ITEMNAME'] else row['ITEMNAME']
        # print(item_base_name)
        # Check if 'SHOTNAME' exists and is not empty
        if pd.notna(row['SHOTNAME']) and row['SHOTNAME']:
            shot_name = row['SHOTNAME']
            # Remove 'SHOTNAME' from the start of 'item_base_name', if present
            if item_base_name.startswith(shot_name):
                stripped_name = item_base_name[len(shot_name):].lstrip('-_')  # Remove any leading "-" or "_"
            else:
                stripped_name = item_base_name
        else:
            stripped_name = item_base_name
        
        # Assign the processed name to 'STRIPPEDITEMNAME'
        df.at[index, 'STRIPPEDITEMNAME'] = stripped_name

    return df

def add_thumbs_and_icons(df):
    # Step 1: Create a new column called 'THUMBNAME' with empty strings
    df['THUMBNAME'] = ''

    # Load thumb defaults from configuration
    configLoader = loadConfigs()
    thumb_defaults_df = configLoader.load_thumb_defaults()

    # Convert all DOTEXTENSION values in thumb_defaults_df to lowercase for case-insensitive matching
    thumb_defaults_df['DOTEXTENSION'] = thumb_defaults_df['DOTEXTENSION'].str.lower()

    # Create a dictionary from thumb_defaults_df for quick lookup
    thumb_defaults_dict = thumb_defaults_df.set_index('DOTEXTENSION').to_dict(orient='index')

    # Step 2: Iterate over rows in the dataframe
    for index, row in df.iterrows():
        dot_ext = row['DOTEXTENSION'].lower()  # Convert DOTEXTENSION in the dataframe to lowercase

        # Check if DOTEXTENSION exists in thumb_defaults_dict
        if dot_ext in thumb_defaults_dict:
            # Check THUMBNAILTYPE and act accordingly
            thumb_info = thumb_defaults_dict[dot_ext]
            if thumb_info['THUMBNAILTYPE'] == 'thumb':
                # Use existing naming pattern for thumbnails
                df.at[index, 'THUMBNAME'] = row['ITEMNAME'].replace(f'.{dot_ext}', '_thumbnail.png')
            elif thumb_info['THUMBNAILTYPE'] == 'icon':
                # Directly use DEFAULTTHUMBNAME from thumb_defaults
                df.at[index, 'THUMBNAME'] = thumb_info['DEFAULTTHUMBNAME']

    return df

def add_THUMBNAME(df):
    # Step 1: Create a new column called 'THUMBNAME' with empty strings
    df['THUMBNAME'] = ''
    
    # Step 2 and 3: Find rows with 'mov' or 'mp4' in 'DOTEXTENSION' and update 'THUMBNAME'
    for index, row in df.iterrows():
        if row['DOTEXTENSION'] in ['mov', 'mp4']:
            # Replace '.mov' or '.mp4' with '_thumbnail.png' in 'ITEMNAME' and assign to 'THUMBNAME'
            df.at[index, 'THUMBNAME'] = row['ITEMNAME'].replace('.mov', '_thumbnail.png').replace('.mp4', '_thumbnail.png')
        
        if row['DOTEXTENSION'] == 'nk':
            df.at[index, 'THUMBNAME'] = 'NukeApp256.png'

        if row['DOTEXTENSION'] == 'ma':
            df.at[index, 'THUMBNAME'] = 'ma.png'
            
        if row['DOTEXTENSION'] == 'mb':
            df.at[index, 'THUMBNAME'] = 'mb.png'
                        
    return df
