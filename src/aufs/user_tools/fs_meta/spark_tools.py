import os
import pandas as pd
import glob
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, max
from pyspark.sql.window import Window

def hashedfile_parquet_dedup_forIntranet(input_path):
    # Specify the path to the Python executable for Spark
    python_executable_path = "G:/dasein/data/sw/dev/apps/GitHub/utils/.venv/Scripts/python.exe"
    os.environ['PYSPARK_PYTHON'] = python_executable_path
    
    # Start Spark session
    spark = SparkSession.builder.appName("HashedParquetDeduplicationIntranet").getOrCreate()

    # Read your data into a DataFrame
    df = spark.read.parquet(input_path)

    # Deduplication logic
    window_spec = Window.partitionBy("HASHEDFILE")
    df_deduplicated = df.withColumn("max_ENTRYTIME", max("ENTRYTIME").over(window_spec)) \
                        .filter(col("ENTRYTIME") == col("max_ENTRYTIME")) \
                        .drop("max_ENTRYTIME")

    # Second deduplication stage based on "FILE" column
    df_deduplicated_final = df_deduplicated.dropDuplicates(["FILE"])

    # Convert the Spark DataFrame to a Pandas DataFrame
    pandas_df_deduplicated = df_deduplicated_final.toPandas()

    # Stop the Spark session
    spark.stop()

    # Return the deduplicated Pandas DataFrame
    return pandas_df_deduplicated

def hashedfile_parquet_dedup_forIntranet_pandas(input_path):
    # Construct the file pattern for matching
    file_pattern = input_path + "source_main*.parquet"
    # print(file_pattern)
    
    # Use glob to find all files matching the pattern
    files = glob.glob(file_pattern)
    # print("Files matched:", files)
    
    # Read each file into a DataFrame and concatenate them
    dfs = [pd.read_parquet(file) for file in files]
    df = pd.concat(dfs, ignore_index=True)
    # print("BOO-hassshhhhed")
    # print(df)

    # Deduplication logic, first focusing on "HASHEDFILE"
    df_sorted = df.sort_values(by=["HASHEDFILE", "ENTRYTIME"])
    df_deduplicated = df_sorted.drop_duplicates(subset=["HASHEDFILE"], keep='last')

    # Second deduplication stage based on "FILE" column, keeping the first occurrence
    df_deduplicated_final = df_deduplicated.drop_duplicates(subset=["FILE"], keep='first')

    # Return the deduplicated pandas DataFrame
    return df_deduplicated_final

def source_from_start_pandas_dedup(input_path):
    # print("INPUT PATH???? BOO!")
    # print(input_path)
    
    # Construct the file pattern for matching
    file_pattern = input_path + "*.parquet"
    # print(file_pattern)
    
    # Use glob to find all files matching the pattern
    files = glob.glob(file_pattern)
    # print("Files matched:", files)
    
    # Read each file into a DataFrame and concatenate them
    dfs = [pd.read_parquet(file) for file in files]
    df = pd.concat(dfs, ignore_index=True)
    # print("BOO-hassshhhhed")
    # print(df)

    # Deduplication logic, first focusing on "HASHEDFILE"
    df_sorted = df.sort_values(by=["HASHEDFILE", "ENTRYTIME"])
    df_deduplicated = df_sorted.drop_duplicates(subset=["HASHEDFILE"], keep='last')

    # Second deduplication stage based on "FILE" column, keeping the first occurrence
    df_deduplicated_final = df_deduplicated.drop_duplicates(subset=["FILE"], keep='first')

    # Return the deduplicated pandas DataFrame
    return df_deduplicated_final

def hashedfile_parquet_dedup_forIntranet_duckdb(input_path):
    con = duckdb.connect(database=':memory:')  # Use an in-memory database for processing

    # Construct the file pattern for matching Parquet files (DuckDB can handle wildcards in file paths)
    file_pattern = input_path + "source_main*.parquet"

    # Load all matching Parquet files into a DuckDB table
    df = con.execute(f"SELECT * FROM '{file_pattern}'").df()

    # Deduplication logic, first focusing on "HASHEDFILE"
    # Sort by HASHEDFILE and ENTRYTIME, then deduplicate keeping the last occurrence
    con.execute("""
    CREATE TEMPORARY VIEW dedup1 AS
    SELECT *, ROW_NUMBER() OVER (PARTITION BY HASHEDFILE ORDER BY ENTRYTIME DESC) as rn
    FROM df
    """)
    df_deduplicated = con.execute("SELECT * FROM dedup1 WHERE rn = 1").df()

    # Second deduplication stage based on "FILE" column, keeping the first occurrence
    con.execute("""
    CREATE TEMPORARY VIEW dedup2 AS
    SELECT *, ROW_NUMBER() OVER (PARTITION BY FILE ORDER BY ENTRYTIME ASC) as rn
    FROM df_deduplicated
    """)
    df_deduplicated_final = con.execute("SELECT * FROM dedup2 WHERE rn = 1").df()

    con.close()
    return df_deduplicated_final

def write_parquet_output(df, dest_pq, partition_base_dir=None, partition_cols=None):
    """
    Writes a Spark DataFrame to Parquet format. It writes a non-partitioned file to 'dest_pq' and, if requested,
    partitioned files into directories within 'partition_base_dir' named after 'dest_pq' and partition columns.

    Args:
    df (DataFrame): Spark DataFrame to write.
    dest_pq (str): Full path with filename for the main (non-partitioned) Parquet file.
    partition_base_dir (str or None): Base directory for partitioned output. Required if partition_cols is provided.
    partition_cols (list of str or None): Columns to partition the output by. Results in separate directories for each column.
    """
    # Write the DataFrame to a single Parquet file (non-partitioned)
    df.write.mode("overwrite").parquet(dest_pq)
    print(f"DataFrame written to {dest_pq}")

    # Write the DataFrame to partitioned Parquet files, if partition columns are provided
    if partition_cols and partition_base_dir:
        # Ensure partition_cols is a list
        if not isinstance(partition_cols, list):
            partition_cols = [partition_cols]

        # Extract the filename without extension to use in partitioned directory names
        dest_pq_filename = os.path.splitext(os.path.basename(dest_pq))[0]

        for col_name in partition_cols:
            partitioned_output_path = os.path.join(partition_base_dir, f"{dest_pq_filename}_{col_name}")
            df.write.partitionBy(col_name).mode("overwrite").parquet(partitioned_output_path)
            print(f"Partitioned Parquet files created in '{partitioned_output_path}' directory.")

def hashedfile_parquet_dedup(input_path):
    # Start Spark session
    spark = SparkSession.builder.appName("HashedParquetDeduplication").getOrCreate()

    # Read your data into a DataFrame
    df = spark.read.parquet(input_path)

    # Deduplication logic
    window_spec = Window.partitionBy("HASHEDFILE")
    df_deduplicated = df.withColumn("max_ENTRYTIME", max("ENTRYTIME").over(window_spec)) \
                        .filter(col("ENTRYTIME") == col("max_ENTRYTIME")) \
                        .drop("max_ENTRYTIME")
    
    # Convert the Spark DataFrame to a Pandas DataFrame
    pandas_df_deduplicated = df_deduplicated.toPandas()

    # Stop the Spark session
    spark.stop()

    # Return the deduplicated Pandas DataFrame
    return pandas_df_deduplicated

def intranet_delete_entries_from_source_main_simple(input_path, dest_pq, partition_base_dir, partition_cols, file_values_to_delete, seq_values_to_delete):
    spark = SparkSession.builder.appName("DeleteEntriesAndFinalize").getOrCreate()

    # Initial empty DataFrame for accumulating results
    final_df = spark.createDataFrame([], schema=spark.read.parquet(input_path).schema)

    unique_projects = spark.read.parquet(input_path).select("PROJECT").distinct().collect()

    for project_row in unique_projects:
        project = project_row.PROJECT
        unique_shotnames = spark.read.parquet(input_path).filter(col("PROJECT") == project).select("SHOTNAME").distinct().collect()

        for shotname_row in unique_shotnames:
            shotname = shotname_row.SHOTNAME
            
            # Path to the specific partition
            partition_path = f"{partition_base_dir}/PROJECT={project}/SHOTNAME={shotname}"
            partition_df = spark.read.parquet(partition_path)
            
            # Apply deletion criteria
            partition_df = partition_df.filter(~col("FILE").isin(file_values_to_delete) & ~col("SEQUENCENAME").isin(seq_values_to_delete))

            # Overwrite the updated partition
            partition_df.write.mode("overwrite").parquet(partition_path)

            # Accumulate the updated partitions into final_df
            final_df = final_df.union(partition_df)

    # After processing all partitions, use write_parquet_output to write final_df
    write_parquet_output(final_df, dest_pq, partition_base_dir, partition_cols)

    spark.stop()

    return dest_pq

def intranet_delete_entries_from_source_main_simple_PROJECT(df, dest_pq, partition_base_dir, partition_cols):
    print("df")
    print(df)
    print("dest_pq")
    print(dest_pq)
    print("base_dir")
    print(partition_base_dir)
    print("partition cols")
    print(partition_cols)
    print("now over to SPARK")
    spark = SparkSession.builder.appName("DeleteEntriesByProject").getOrCreate()
    spark.sparkContext.setLogLevel("INFO")


    final_df = spark.createDataFrame([], schema=df.schema)
    print("BOO2")
    print(final_df)

    unique_projects = df.select("PROJECT").distinct().collect()
    print("BOO3")
    print(unique_projects)

    for project_row in unique_projects:
        project = project_row.PROJECT
        
        # Identifying values to delete for this project
        file_values_to_delete = df.filter(df["PROJECT"] == project).select("FILE").rdd.flatMap(lambda x: x).collect()
        seq_values_to_delete = df.filter(df["PROJECT"] == project).select("SEQUENCENAME").rdd.flatMap(lambda x: x).collect()

        # Extract the base name of the dest_pq file (without the extension)
        dest_pq_basename = os.path.basename(dest_pq).replace('.parquet', '')

        # Construct the partition directory name by appending "_PROJECT" to the dest_pq base name
        partition_dir_name = f"{dest_pq_basename}_PROJECT"

        # Construct the full partition path
        partition_path = os.path.join(partition_base_dir, partition_dir_name, f"PROJECT={project}")

        print("Partition path:", partition_path)
        partition_df = spark.read.parquet(partition_path)

        partition_df = partition_df.filter(~col("FILE").isin(file_values_to_delete) & ~col("SEQUENCENAME").isin(seq_values_to_delete))

        partition_df.write.mode("overwrite").parquet(partition_path)

        final_df = final_df.union(partition_df)

    write_parquet_output(final_df, dest_pq, partition_base_dir, partition_cols)

    spark.stop()

    return dest_pq

def delete_unwanted_dt_entries_basic(df, dest_pq):
    try:
        print("Loading destination parquet file...")
        dest_df = pd.read_parquet(dest_pq)

        print("Initial count of entries in destination file:", len(dest_df))
        print(df)
        # print(dest_df)

        # Collect unique FILE and SEQUENCENAME from input DataFrame for matching
        files_to_remove = df['FILE'].dropna().unique()
        sequence_names_to_remove = df['SEQUENCENAME'].dropna().unique()

        # Print matches for FILE
        file_matches = dest_df[dest_df['FILE'].isin(files_to_remove)]
        # if not file_matches.empty:
        #     print("Entries to remove based on FILE match:")
        #     print(file_matches)

        # Remove entries where FILE matches
        dest_df = dest_df[~dest_df['FILE'].isin(files_to_remove)]

        # Print matches for SEQUENCENAME if no FILE matches were found
        if file_matches.empty:
            sequence_matches = dest_df[dest_df['SEQUENCENAME'].isin(sequence_names_to_remove)]
            # if not sequence_matches.empty:
            #     print("Entries to remove based on SEQUENCENAME match:")
            #     print(sequence_matches)

            # Remove remaining entries where SEQUENCENAME matches
            dest_df = dest_df[~dest_df['SEQUENCENAME'].isin(sequence_names_to_remove)]

        print("Count of entries after deletion:", len(dest_df))

        # Attempt to write the filtered DataFrame back to the parquet file
        # print("Writing the updated data back to the parquet file...")
        dest_df.to_parquet(dest_pq, index=False)

        print(f"Deletion completed successfully. {dest_pq}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return dest_pq

def intranet_delete_entries_from_source_main_simple_SHOTNAME(df, dest_pq, partition_base_dir, partition_cols):
    spark = SparkSession.builder.appName("DeleteEntriesByShotname").getOrCreate()

    final_df = spark.createDataFrame([], schema=df.schema)

    unique_shotnames = df.select("SHOTNAME").distinct().collect()

    for shotname_row in unique_shotnames:
        shotname = shotname_row.SHOTNAME
        
        # Identifying values to delete for this shotname
        file_values_to_delete = df.filter(df["SHOTNAME"] == shotname).select("FILE").rdd.flatMap(lambda x: x).collect()
        seq_values_to_delete = df.filter(df["SHOTNAME"] == shotname).select("SEQUENCENAME").rdd.flatMap(lambda x: x).collect()

        partition_path = f"{partition_base_dir}/SHOTNAME={shotname}"
        partition_df = spark.read.parquet(partition_path)

        partition_df = partition_df.filter(~col("FILE").isin(file_values_to_delete) & ~col("SEQUENCENAME").isin(seq_values_to_delete))

        partition_df.write.mode("overwrite").parquet(partition_path)

        final_df = final_df.union(partition_df)

    write_parquet_output(final_df, dest_pq, partition_base_dir, partition_cols)

    spark.stop()

    return dest_pq

def hashedfile_parquet_dedup_and_partition_write_main_plus_partitions(input_path, dest_pq, partition_base_dir, partition_cols):
    # Start Spark session
    spark = SparkSession.builder.appName("HashedParquetDeduplicationAndPartitioning").getOrCreate()

    # Read your data into a DataFrame
    df = spark.read.parquet(input_path)

    # Deduplication logic
    window_spec = Window.partitionBy("HASHEDFILE")
    df_deduplicated = df.withColumn("max_ENTRYTIME", max("ENTRYTIME").over(window_spec)) \
                        .filter(col("ENTRYTIME") == col("max_ENTRYTIME")) \
                        .drop("max_ENTRYTIME")
    
    # Example: Writing output using the modular function
    write_parquet_output(df_deduplicated, dest_pq, partition_base_dir, partition_cols)

    # Stop the Spark session
    spark.stop()

    return dest_pq

def temp_write(df):
    # Write the DataFrame to a temporary location
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "consolidated.parquet")
    df.write.mode('overwrite').parquet(output_path)
    
    # Return the path to the written parquet file
    return output_path
