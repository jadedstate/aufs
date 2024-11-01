import pandas as pd

def no_nans_floats(df, whitelist=None):
    if whitelist is None:
        whitelist = []

    float_sentinel = 0.0  # Define a sentinel value for NaNs in float columns

    for col in df.columns:
        if col not in whitelist:
            df[col] = df[col].fillna('')  # Replace NaNs with an empty string
            # Directly convert to string without attempting to parse integers
            df[col] = df[col].astype(str)
        else:
            # Convert whitelisted columns to floats
            df[col] = df[col].astype(float).fillna(float_sentinel)

    return df

def no_nans_all_cols(df, whitelist=None):
    if whitelist is None:
        whitelist = []

    float_sentinel = 0.0  # Define a sentinel value for NaNs in float columns

    for col in df.columns:
        if col not in whitelist:
            df[col] = df[col].fillna('')  # Replace NaNs with an empty string
            # Directly convert to string without attempting to parse integers
            # df[col] = df[col].astype(str)
        else:
            # Convert whitelisted columns to floats
            df[col] = df[col].astype(float).fillna(float_sentinel)

    return df

def to_strings_then_conform_slashes(df, slash_conform_whitelist=None):
    """
    Converts all DataFrame elements to strings and conforms slashes according to a whitelist.

    Parameters:
    - df (pd.DataFrame): The DataFrame to process.
    - slash_conform_whitelist (list of str, optional): List of column headers to conform slashes. If None, applies to all columns.

    Returns:
    - pd.DataFrame: The processed DataFrame with all elements as strings and slashes conformed in specified columns.
    """
    # Convert entire DataFrame to strings
    df = df.astype(str)

    # If no whitelist is provided, conform slashes in all columns
    if slash_conform_whitelist is None:
        slash_conform_whitelist = df.columns

    # Conform slashes in whitelisted columns
    for col in slash_conform_whitelist:
        if col in df.columns:
            df[col] = df[col].str.replace("\\", "/", regex=False)

    return df

def conform_slashes_col_whitelist(df, slash_conform_whitelist):
    """
    Conforms slashes in specified columns of a DataFrame.

    Parameters:
    - df (pd.DataFrame): The DataFrame to process.
    - slash_conform_whitelist (list of str): List of column headers to conform slashes.

    Returns:
    - pd.DataFrame: The processed DataFrame with slashes conformed in specified columns.
    """
    for col in slash_conform_whitelist:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace("\\", "/", regex=False)

    return df

def remove_rows_with_value(df, column_name, value_to_remove):
    """
    Remove rows from a DataFrame where a specific column has a given value.
    
    Args:
        df (pd.DataFrame): The input DataFrame.
        column_name (str): The name of the column to check for the value.
        value_to_remove (any): The value to check for removal.

    Returns:
        pd.DataFrame: A DataFrame with the rows removed.
    """
    # Validate that the column exists in the DataFrame
    if column_name not in df.columns:
        raise ValueError(f"The specified column '{column_name}' does not exist in the DataFrame.")
    
    # Use `~` to invert the boolean series, so we keep rows that don't match the value
    df_cleaned = df[~(df[column_name] == value_to_remove)].copy()
    
    return df_cleaned

def remove_rows_with_values(df, column_name, values_to_remove):
    """
    Remove rows from a DataFrame where a specific column contains any of the given substrings.
    
    Args:
        df (pd.DataFrame): The input DataFrame.
        column_name (str): The name of the column to check for the values.
        values_to_remove (list): The substrings to check for removal.

    Returns:
        pd.DataFrame: A DataFrame with the rows removed.
    """
    # Start with a condition that is always False
    condition = df[column_name].str.contains(values_to_remove[0], regex=False, na=False) & False
    
    # Accumulate conditions for each substring to remove
    for value in values_to_remove:
        condition = condition | df[column_name].str.contains(value, regex=False, na=False)
    
    # Use the negated condition to filter rows
    df_cleaned = df[~condition].copy()
    
    return df_cleaned

