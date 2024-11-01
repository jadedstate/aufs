# src/aufs/user_tools/fs_meta/fs_info_from_paths.py

import os
import time
import pandas as pd
from .parquet_get_fs_data_for_source import FileSystemScraper
from .add_jobs_info import source_add_client_project, add_shot_names_to_df, add_shot_names_to_df_using_altshotnames
from .parquet_tools import sequenceWork
from .dataframe_meta_work import (add_file_extension_column, format_file_size, add_ITEM_columns,
                                  add_strippeditemnames_itemversions, add_hashedfile_entrytime_columns_noRoot)
from .sequences import seqs_tidyup_v2
from .dataframe_maintenance import no_nans_floats, remove_rows_with_values, to_strings_then_conform_slashes


def file_details_df_from_path(paths, client, project, shots_df, output_csv, use_direct_process=False):
    print("Received paths for processing:", paths)
    scraper = FileSystemScraper()
    sequencer = sequenceWork.add_sequence_info_v4

    # client/project from UI
    # shotlist csv set automatically via client/project

    # Use the direct process_files method if the flag is true
    if use_direct_process:
        # Handle list of file paths directly
        new_data_df = scraper.process_files(paths)
        print("Directly processed files.")
    else:
        # Handle single directory processing
        new_data_df = scraper.scrape_directories(paths)
        print("Scraped directories.")
    
        # Check if the DataFrame is empty
    if new_data_df.empty:
        print("No update required: No files found in the supplied paths.")
        return

    # print(new_data_df)
    # print("scraped! first up is hashedfile and entrytime columns")
    # new_data_df = add_hashedfile_entrytime_columns_noRoot(new_data_df, 'FILE')
    # print("now adding any client-project info we can find")
    new_data_df = source_add_client_project(new_data_df, client, project)
    # print("client-project info in: ")
    # print(new_data_df)
    # print("Now for adding shot names...")
    new_data_df = add_shot_names_to_df(new_data_df, shots_df)
    # print("...and using altshotnames in case they're needed to get shot names.")
    new_data_df = add_shot_names_to_df_using_altshotnames(new_data_df, shots_df)
    # print("using sequencer is next up")
    new_data_df = sequencer(new_data_df)
    # print("sequenced, time to get dotextension filled")
    new_data_df = add_file_extension_column(new_data_df)
    # print("extensions added")
    # print(new_data_df)
    new_data_df = add_hashedfile_entrytime_columns_noRoot(new_data_df, 'FILE')
    # print("hashedFILE added, conform slashes next")
    new_data_df = to_strings_then_conform_slashes(new_data_df)
    # print(new_data_df)
    # new_data_df = new_data_df['MEMBERPACKAGES'] = [''] * len(df)
    
    # print(df)
    # This is where work to be done so we can update individual sequence information
    seqs_df = seqs_tidyup_v2(new_data_df)
    # print("did we sequence?")
    # print(seqs_df)
    seqs_df = remove_rows_with_values(seqs_df, 'FILE', ['~', '.db', '.tmp', 'Thumbs', '.autosave', 'DS_Store','Thumbnail'])
    seqs_df = no_nans_floats(seqs_df)
    # print("no NaNs no FLOAT.sss")
    seqs_df = format_file_size(seqs_df)
    # print("Made mega bytes")
    seqs_df = add_ITEM_columns(seqs_df, 'FILE')
    # print("added ITEM cols")
    # print(seqs_df['ITEMNAME'])
    seqs_df = add_strippeditemnames_itemversions(seqs_df)
    # print("done stripping and stuff")
    # print(seqs_df)
    
    seqs_df.to_csv(output_csv, index=False)  # Write to csv
    print("Written to the csv")
    
    return seqs_df