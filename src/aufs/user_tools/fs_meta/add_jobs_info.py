import pandas as pd

def get_client_project_combos(all_jobs_info_df):

    df_alljobs = all_jobs_info_df
    unique_combos = df_alljobs[['CLIENT', 'PROJECT']].drop_duplicates().reset_index(drop=True)
    return unique_combos

def source_add_client_project(df, client, project):
    # Initialize CLIENT and PROJECT columns with empty strings
    df['CLIENT'] = ''
    df['PROJECT'] = ''
    df['SHOTNAME'] = ''
    
    mask = df['FILE'].str.contains(fr"\b{project}\b", case=True, na=False, regex=True)
    df.loc[mask, 'CLIENT'] = client
    df.loc[mask, 'PROJECT'] = project
    
    return df

def add_shot_names_to_df(df, shots_df):
    # Check if 'PROJECT' column exists and has any non-null, non-empty values
    if 'PROJECT' not in df.columns or df['PROJECT'].dropna().eq('').all():
        # print("No valid PROJECT values found; skipping shot name assignment.")
        return df  # Return early if no valid PROJECT values are found

    df_allshots = shots_df
    df['SHOTNAME'] = ''    
    unique_projects = df['PROJECT'].dropna().unique()
    
    for project in unique_projects:
        # Isolate the working frame for the current project
        project_frame = df[df['PROJECT'] == project]
        # Iterate through each unique shot within the project
        for _, shot_row in df_allshots.iterrows():
            shotname = shot_row['SHOTNAME']
            # Apply the mask for the current shotname within the project frame
            mask = project_frame['FILE'].str.contains(fr"{shotname}", case=True, na=False, regex=True)
            # Update SHOTNAME for matches
            df.loc[project_frame[mask].index, 'SHOTNAME'] = shotname

    return df

def add_shot_names_to_df_using_altshotnames(df, shots_df, ifNoName=True):
    df_allshots = shots_df
    
    # If ifNoName is True, only process rows with an empty SHOTNAME
    if ifNoName:
        # Apply the filter to limit processing to rows where SHOTNAME is empty
        df_filtered = df[df['SHOTNAME'] == '']
    else:
        df_filtered = df.copy()

    # Add the ALTSHOTNAME column with default empty values if it doesn't exist
    if 'ALTSHOTNAME' not in df.columns:
        df['ALTSHOTNAME'] = ''
    
    # Get the unique projects from the DataFrame
    unique_projects = df_filtered['PROJECT'].dropna().unique()
    if 'PROJECT' not in df_filtered.columns or df_filtered['PROJECT'].dropna().eq('').all():
        # print("No valid PROJECT values found; skipping shot name assignment.")
        return df_filtered  # Return early if no valid PROJECT values are found

    for project in unique_projects:
        # Isolate the working frame for the current project
        project_frame = df_filtered[df_filtered['PROJECT'] == project]

        # Iterate through each unique shot within the project
        for _, shot_row in df_allshots.iterrows():
            alt_shotname = shot_row.get('ALTSHOTNAME', None)
            shotname = shot_row['SHOTNAME']
            
            # Skip rows with no ALTSHOTNAME defined
            if pd.isna(alt_shotname):
                continue
            
            # Apply the mask for the current alt_shotname within the project frame (case-insensitive)
            mask = project_frame['FILE'].str.contains(fr"{alt_shotname}", case=False, na=False, regex=False)
            
            # Update SHOTNAME for matches
            df.loc[project_frame[mask].index, 'SHOTNAME'] = shotname
            # Mark rows in ALTSHOTNAME column with 'yes'
            df.loc[project_frame[mask].index, 'ALTSHOTNAME'] = 'yes'
    
    return df
