# Takes NWEA csv -> Pandas Dataframe -> anon.db 
# Author Samuel Carlos
# Date 04-10-26

import pandas as pd 
import sqlite3 
import hashlib

# Folder paths containing the complete NWEA folder contents. 
folder_path = "~/Documents/work/code/nweaAgent/data/26_nwea/"
results_path = folder_path + "AssessmentResults.csv"
students_path = folder_path + "StudentsBySchool.csv"
teachers_path = folder_path + "ClassAssignments.csv"

# Function to convert csv to dataframe
# param file    a string for the path to a csv file.
# Returns a Pandas Dataframe
def csv_to_df(file: str):
    df = pd.read_csv(file)
    df = df.dropna(how='all') # Drop all NaN rows
    return df 

# Function to hash a given value.
# param val     the value to hash.
def hash_id(val: int):
    return hashlib.sha256(str(val).encode()).hexdigest()

# Main function to convert csv files into a sqlite3 database.
def main():
    # Create a sqlite3 connection
    conn = sqlite3.connect("anon.db")
        
    # Convert all raw csv files into dataframes
    results_df = csv_to_df(results_path)
    students_df = csv_to_df(students_path)
    teachers_df = csv_to_df(teachers_path)

    # Make a list of all dfs to reduce further repetition
    df_list = [results_df, students_df, teachers_df]

    # Hash the Student ID's of the Dataframes 
    for df in df_list:
        df["StudentID"] = df["StudentID"].apply(hash_id)
    
    # Convert each df to a db 
    results_df.to_sql(name="results", con=conn, if_exists="replace", index=False) 
    students_df.to_sql(name="students", con=conn, if_exists="replace", index=False) 
    teachers_df.to_sql(name="teachers", con=conn, if_exists="replace", index=False) 

    print("All conversions from csv to db successful.")

    # Close sqlite3 connection
    conn.close()
    print("Connection closed.")

if __name__ == "__main__":
    main()
