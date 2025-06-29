# Main method to run the data prep engine.
# Version 1.0 goal: only one school year

import pandas as pd
from DataPrepEngine import DataPrepEngine as dpr
from ClusterAnalysis import ClusterAnalysis as clus
from config import *
import time
from dataclasses import dataclass
from typing import Any
import DataStructures
import sqlite3

def main():
    # Batch process all files in the annum packet
    csv_files = {
        'results': sp25_results_path,
        'teachers': sp25_teachers_path,
        'students': sp25_students_path,
        'results_metadata': results_metadata,
    }

    # metadata files
    metadata_files = {
        'teachers_metadata' : teachers_metadata,
        'results_metadata' : results_metadata
    }

    # Batch process the files into one database to create src_path
    dpr.batch_to_sql(csv_files=csv_files, db_path=src_path)

    # Prepare an anonymous database copy
    dpr.create_anonymous_db(src_path=src_path, dest_path=dest_path)

    # Build master keys
    student_key = dpr.student_hash_table(public_db_path=src_path)
    teacher_key = dpr.teacher_hash_table(public_db_path=src_path)

    # Save master keys to the source db
    dpr.save_master_keys(
        src_db_path=src_path, 
        student_master_key=student_key, 
        teacher_master_key=teacher_key
        )
    
    # Anonymize the StudentIDs in the anonymous database
    dpr.anonymize_database( 
        anon_db_path=dest_path, 
        student_master_key=student_key, 
        teacher_master_key=teacher_key
        )

    ## Initialize cluster analysis capable object on dest_path, the anon path.
    # cluster_analysis_object = clus(db_path=dest_path)
    
    ## Iterate through a key of all titles to create all db's
    conn = sqlite3.connect(dest_path)
    cursor = conn.cursor()
    all_titles = DataStructures.TestTitles().get_titles()

    for key, value in all_titles.items():
        cluster_analysis_object = clus(db_path=dest_path)
        if cluster_analysis_object.get_df() is None:
            raise ValueError("That cluster analysis object doesn't have a df.")

        # If dataset is < 3 (or other failure), then skip cluster analysis.
        try:
            kmeans_results = cluster_analysis_object.results_analysis(test=value)
        except Exception as e:
            print(Exception)
            continue

        df = kmeans_results.df
        cluster_db = cluster_analysis_object.make_centroid_df(kmeans_results)

        if kmeans_results.local_keys is None:
            raise ValueError(f"No local keys found in {kmeans_results}.")
        
        full_title = kmeans_results.local_keys['TestName']
        short_title = DataStructures.TestTitles().get_short_title(full_title)

        if short_title is None:
            raise ValueError(f"Could not get short_title from {full_title}.")
        
        ## UPLOAD COURSE-FILTERED RESULTS TO DB ##
        df.to_sql(name=short_title, con=conn, if_exists='replace', index=False)
        print(f"Successfully saved {short_title} to the db.")

        ## UPLOAD CENTROID ARRAYS TO DB
        cluster_db.to_sql(name=f"{short_title}_clusters", con=conn, if_exists='replace', index=False)
        print(f"Successfully wrote {short_title}_clusters table to the db.")

    # Drop the keys from the anonymous db
    cursor.execute("DROP TABLE IF EXISTS teacher_master_key;")
    cursor.execute("DROP TABLE IF EXISTS student_master_key;")

    # Add metadata
    for key, value in metadata_files.items():
        df_m = pd.read_csv(value)
        print(f"Writing {key} to a metadata table.")
        df_m.to_sql(name=key, con=conn, if_exists='replace', index=False)

if __name__ == "__main__":
    main()