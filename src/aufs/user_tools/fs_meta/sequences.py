# sequences.py
import pandas as pd
import itertools
import re

def seqs_tidyup(df):
    # Check for sequences that require work (more than one row with the same 'SEQUENCEFILENAME' and 'NUMBERPADDING')
    sequence_counts = df.groupby(['SEQUENCEFILENAME', 'NUMBERPADDING']).size()
    sequences_to_process = sequence_counts[sequence_counts > 1].reset_index()[['SEQUENCEFILENAME', 'NUMBERPADDING']]
    
    # Split the DataFrame into rows that need processing and rows that don't
    needs_processing = pd.merge(df, sequences_to_process, on=['SEQUENCEFILENAME', 'NUMBERPADDING'], how='inner')
    untouched = pd.merge(df, sequences_to_process, on=['SEQUENCEFILENAME', 'NUMBERPADDING'], how='outer', indicator=True).query('_merge == "left_only"').drop(columns=['_merge'])
    
    # Define the aggregation operations for necessary columns
    agg_operations = {
        'FIRSTFRAME': 'min',
        'LASTFRAME': 'max',
        'MISSINGFRAMES': lambda x: aggregate_missing_frames(x),
        'TOTALSIZE': 'sum',
        'CREATION_TIME': 'min'
    }
    
    # Group by 'SEQUENCEFILENAME' and 'NUMBERPADDING', and aggregate
    grouped = needs_processing.groupby(['SEQUENCEFILENAME', 'NUMBERPADDING'], as_index=False).agg(agg_operations)
    
    # Get the youngest row in each group as the base row
    youngest_rows = needs_processing.sort_values('CREATION_TIME').groupby(['SEQUENCEFILENAME', 'NUMBERPADDING'], as_index=False).last()
    
    # Merge the aggregated data with the youngest rows to get the final attributes
    final_processed = pd.merge(youngest_rows[['SEQUENCEFILENAME', 'NUMBERPADDING', 'SEQUENCE', 'MODIFICATION_TIME', 'TARGET', 'DOTEXTENSION']],
                        grouped[['SEQUENCEFILENAME', 'NUMBERPADDING', 'FIRSTFRAME', 'LASTFRAME', 'MISSINGFRAMES', 'TOTALSIZE']],
                        on=['SEQUENCEFILENAME', 'NUMBERPADDING'])
    
    # Combine the processed rows with the untouched rows
    final_df = pd.concat([final_processed, untouched], ignore_index=True)
    
    return final_df

def seqs_tidyup_v2(df):
    # Ensure CREATION_TIME is parsed as datetime
    df['CREATION_TIME'] = pd.to_datetime(df['CREATION_TIME'], errors='coerce')
    
    # Convert SEQUENCEPOSITION to a list of integers if they are digit strings, otherwise keep as None
    df['SEQUENCEPOSITION'] = df['SEQUENCEPOSITION'].apply(lambda x: [int(i) for i in x.split(',') if i.isdigit()] if pd.notnull(x) else x)

    # Check for sequences that require work (more than one row with the same 'SEQUENCENAME')
    sequence_counts = df.groupby('SEQUENCENAME').size()
    
    # If there are no sequences requiring processing, return the original dataframe
    if sequence_counts.max() <= 1:
        return df

    sequences_to_process = sequence_counts[sequence_counts > 1].reset_index()[['SEQUENCENAME']]
    
    # Split the DataFrame into rows that need processing and rows that don't
    needs_processing = df[df['SEQUENCENAME'].astype(bool)].copy()
    untouched = df[~df['SEQUENCENAME'].astype(bool)].copy()
    
    # Select one row per group to preserve all the identical values
    # This will be merged back after the aggregation
    base_rows = needs_processing.drop_duplicates(subset='SEQUENCENAME', keep='first')
 
    # Ensure FILESIZE is a numeric type
    needs_processing['FILESIZE'] = pd.to_numeric(needs_processing['FILESIZE'], errors='coerce')
    
    # Define the aggregation operations for necessary columns
    agg_operations = {
        'SEQUENCEPOSITION': lambda x: sorted(set([i for sublist in x for i in sublist])),  # flatten and sort
        'FILESIZE': 'sum',
        'CREATION_TIME': 'max'
    }
    
    # Group by 'SEQUENCENAME' and aggregate
    grouped = needs_processing.groupby('SEQUENCENAME', as_index=False).agg(agg_operations)
    # Merge the base rows to preserve all unaffected columns
    final_processed = pd.merge(base_rows.drop(columns=['SEQUENCEPOSITION', 'FILESIZE', 'CREATION_TIME']), grouped, on='SEQUENCENAME', how='left')

    # Update the 'FILE' column with 'SEQUENCENAME'
    final_processed['FILE'] = final_processed['SEQUENCENAME']
    
    # Extract the FIRST and LAST frames from SEQUENCEPOSITION
    final_processed['FIRSTFRAME'] = final_processed['SEQUENCEPOSITION'].apply(lambda x: str(x[0]) if x else '')
    final_processed['LASTFRAME'] = final_processed['SEQUENCEPOSITION'].apply(lambda x: str(x[-1]) if x else '')
    final_processed['FRAMERANGE'] = final_processed['SEQUENCEPOSITION'].apply(lambda x: format_ranges(x) if x else '')

    # Calculate the missing frames
    final_processed['MISSINGFRAMES'] = final_processed['SEQUENCEPOSITION'].apply(lambda x: calculate_missing_frames(x) if x else '')
    
    # Combine the processed rows with the untouched rows and retain all columns
    final_df = pd.concat([final_processed, untouched], ignore_index=True, sort=False)
    
    # Ensure all original columns are present, plus the new ones we've added
    final_df = final_df.reindex(columns=df.columns.tolist() + ['FIRSTFRAME', 'LASTFRAME', 'FRAMERANGE', 'MISSINGFRAMES'])
    # final_df = final_df.drop(['SEQUENCENAME', 'SEQUENCEPOSITION'], axis=1)
    
    return final_df

def parse_missing_frames(missing_frames_str):
    """Parse a MISSINGFRAMES string and return a set of individual missing frame numbers."""
    frame_set = set()
    for part in missing_frames_str.split(', '):
        if '-' in part:
            start, end = map(int, part.split('-'))
            frame_set.update(range(start, end + 1))
        else:
            frame_set.add(int(part))
    return frame_set

def aggregate_missing_frames(missing_frames_series):
    """Aggregate MISSINGFRAMES from a series of strings into a single string."""
    all_frames = set()
    for frames_str in missing_frames_series:
        all_frames.update(parse_missing_frames(frames_str))
    return format_ranges(sorted(all_frames))

def format_ranges(number_list):
    # Ensure all elements are integers
    cleaned_list = [int(x) for x in number_list if isinstance(x, int) or (isinstance(x, str) and x.isdigit())]
    ranges = []
    for k, g in itertools.groupby(enumerate(cleaned_list), lambda ix: ix[0] - ix[1]):
        group = list(map(lambda x: x[1], g))
        if len(group) > 1:
            ranges.append(f"{group[0]}-{group[-1]}")
        else:
            ranges.append(str(group[0]))
    return ", ".join(ranges)

def calculate_missing_frames(sequence_positions):
    """Calculate missing frames from a list of sequence positions."""
    if not sequence_positions:
        return ''
    
    full_range = set(range(sequence_positions[0], sequence_positions[-1] + 1))
    existing_frames = set(sequence_positions)
    missing_frames = sorted(full_range - existing_frames)
    
    return format_ranges(missing_frames)

def seqs_tidyup_v3(df):
    # Ensure CREATION_TIME is parsed as datetime
    df['CREATION_TIME'] = pd.to_datetime(df['CREATION_TIME'], errors='coerce')
    
    # Convert SEQUENCEPOSITION to a list of integers if they are digit strings, otherwise keep as None
    df['SEQUENCEPOSITION'] = df['SEQUENCEPOSITION'].apply(lambda x: [int(i) for i in x.split(',') if i.isdigit()] if pd.notnull(x) else x)

    # Count sequences to determine which need processing and which are single
    sequence_counts = df.groupby('SEQUENCENAME').size()


    # Identify single file sequences
    singles = sequence_counts[sequence_counts == 1].index
    print(singles)
    print("let's see if the singles get processed")
    
    # Clean up sequence metadata for singles
    if not singles.empty:
        singles_df = df[df['SEQUENCENAME'].isin(singles)].copy()
        print(singles_df)
        print("did we get our singles into a dataframe????")
        # Assuming FILE is formatted like 'filename.%04d.ext' and FIRSTFRAME is an integer
        singles_df['FILE'] = singles_df.apply(lambda row: '.'.join([row['FILE'].split('.')[0], str(row['FIRSTFRAME']), row['FILE'].split('.')[-1]]), axis=1)
        print(singles_df)
        print("did we get our single's names sorted????")
        singles_df.drop(['FIRSTFRAME', 'LASTFRAME', 'PADDING', 'MISSINGFRAMES'], axis=1, inplace=True)
    else:
        singles_df = pd.DataFrame()

    # Check for sequences that require work (more than one row with the same 'SEQUENCENAME')
    print(singles_df)
    if sequence_counts.max() <= 1:
        return pd.concat([singles_df, df[~df['SEQUENCENAME'].isin(singles)]], ignore_index=True, sort=False)

    sequences_to_process = sequence_counts[sequence_counts > 1].index
    print(sequences_to_process)
    
    # Split the DataFrame into rows that need processing and rows that don't
    needs_processing = df[df['SEQUENCENAME'].isin(sequences_to_process)].copy()
    untouched = df[~df['SEQUENCENAME'].isin(sequences_to_process) & ~df['SEQUENCENAME'].isin(singles)].copy()
    
    # Process sequences with more than one file
    needs_processing['FILESIZE'] = pd.to_numeric(needs_processing['FILESIZE'], errors='coerce')
    agg_operations = {
        'SEQUENCEPOSITION': lambda x: format_ranges(sorted(set([i for sublist in x for i in sublist]))),
        'FILESIZE': 'sum',
        'CREATION_TIME': 'max'
    }
    grouped = needs_processing.groupby('SEQUENCENAME', as_index=False).agg(agg_operations)
    base_rows = needs_processing.drop_duplicates(subset='SEQUENCENAME', keep='first')
    final_processed = pd.merge(base_rows.drop(columns=['SEQUENCEPOSITION', 'FILESIZE', 'CREATION_TIME']), grouped, on='SEQUENCENAME', how='left')
    
    # Combine all pieces back together
    final_df = pd.concat([final_processed, untouched, singles_df], ignore_index=True, sort=False)
    
    # Ensure all original columns are present, plus the new ones we've added
    final_df = final_df.reindex(columns=df.columns.tolist() + ['FIRSTFRAME', 'LASTFRAME', 'MISSINGFRAMES'])
    final_df = final_df.drop(['SEQUENCENAME', 'SEQUENCEPOSITION'], axis=1)
    
    return final_df

def expand_sequences(row):
    """Expands sequence rows into individual frame rows if applicable, preserving action_type."""
    # Normalize keys to expected format
    normalized_row = {
        'src': row.get('SRC') or row.get('src'),
        'dest': row.get('DEST') or row.get('dest'),
        'target': row.get('TARGET') or row.get('target'),
        'actiontype': row.get('ACTIONTYPE') or row.get('actiontype'),
        'numberofframes': int(row.get('NUMBEROFFRAMES') or row.get('numberofframes')),
        'inputfirstframe': int(row.get('INPUTFIRSTFRAME') or row.get('inputfirstframe')),
        'increment': int(row.get('INCREMENT') or row.get('increment', 1))
    }
    # print("Normalised row dest: ")
    # print(normalized_row['dest'])
    expanded_rows = []
    pattern = re.compile(r'%(\d*)d')
    for i in range(normalized_row['numberofframes']):
        frame = normalized_row['inputfirstframe'] + i * normalized_row['increment']
        def replacer(match):
            padding = match.group(1)
            format_str = f'{{:0{padding}d}}' if padding else '{}'
            return format_str.format(frame)
        
        src_formatted = pattern.sub(replacer, normalized_row['src'])
        dest_formatted = pattern.sub(replacer, normalized_row['dest'])
        target_formatted = pattern.sub(replacer, normalized_row['target'])
        
        expanded_rows.append({
            'src': src_formatted,
            'dest': dest_formatted,
            'target': target_formatted,
            'action_type': normalized_row['actiontype'],  # Ensure this matches the DataFrame column exactly
        })
        
    return expanded_rows

