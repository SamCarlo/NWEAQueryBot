#type: ignore
# Open a spring csv and make an anon and a private DB. 

import pandas as pd
import sqlite3
import config
import shutil
import hashlib
import os

# Ensure that old db_paths are deleted.
for db_path in [config.priv_db_path, config.anon_db_path]:
    if os.path.exists(db_path):
        os.remove(db_path)

class DataPrepEngine:
    def __init__(self, *, fall_folder, spring_folder):
       
        self.fall_results_path = os.path.join(fall_folder, "AssessmentResults.csv")
        self.fall_students_path = os.path.join(fall_folder, "StudentsBySchool.csv")
        self.fall_teachers_path = os.path.join(fall_folder, "ClassAssignments.csv")
        self.spring_results_path = os.path.join(spring_folder, "AssessmentResults.csv")
        self.spring_students_path = os.path.join(spring_folder, "StudentsBySchool.csv")
        self.spring_teachers_path = os.path.join(spring_folder, "ClassAssignments.csv")
        self.results_metadata_path = "./data/results_metadata.csv"
        self.teachers_metadata_path = "./data/teachers_metadata.csv"
        self.students_metadata_path = "./data/student_metadata.csv"

        # Columns to REDACT when anonymizing
        self.redacted_cols = ["StudentFirstName",
                              "StudentLastName",
                              "TeacherName"]
        
        # A list of all csv paths to be read into pandas DataFrames.
        self.csv_paths = [
            self.fall_results_path,
            self.fall_students_path,
            self.fall_teachers_path,
            self.spring_results_path,
            self.spring_students_path,
            self.spring_teachers_path,
            self.results_metadata_path,
            self.teachers_metadata_path,
            self.students_metadata_path
        ]

        # Dict for iterating through df's in the sql upload process.
        self.df_kines = {
            "f_results": None, 
            "f_teachers": None, 
            "f_students": None, 
            "results_metadata": None,
            "teachers_metadata": None,
            "student_metadata": None,
            "s_results": None,
            "s_teachers": None,
            "s_students": None,
        }

        # Defines a csv uploaded to pd.DataFrame, preparing for push into SQLite database.
        self.students_fall_df = None
        self.students_spring_df = None

        self.results_fall_df = None
        self.results_spring_df = None

        self.teachers_fall_df = None
        self.teachers_spring_df = None

        self.results_meta_df = None
        self.teachers_meta_df = None
        self.students_meta_df = None

        # A placeholder for the upload process
        self._df = None

        # Lists the kinds of files that have already been fully pushed to 
        self.completed_uploads = []
        
        # A SQL database located in the filepath defined in config.py.
        self.priv_db_conn = sqlite3.connect(config.priv_db_path)

        # A SQL database that will be an anonymous copy of the priv db. 
        self.anon_db_conn = sqlite3.connect(config.anon_db_path)

    # Takes ALL self.csv_paths; --> assigns each to appropriate self.df
    def to_df(self):
        for path in self.csv_paths:
            print(f"to_df() : Reading {path} into a DataFrame...")
            df = pd.read_csv(path)
            df = df.dropna(how='all') # All rows must be NaN to drop them. 
            df = df.dropna(axis=1, how="all") # Drop all cols that are only null.

            # Determine fileType type based on the fileType name
            if "AssessmentResults" in path:
                if "fall" in path:
                    self.results_fall_df = df
                elif "spring" in path:
                    self.results_spring_df = df
            elif "ClassAssignments" in path:
                if "fall" in path:
                    self.teachers_fall_df = df
                elif "spring" in path:
                    self.teachers_spring_df = df
            elif "StudentsBySchool" in path:
                if "fall" in path:
                    self.students_fall_df = df
                elif "spring" in path:
                    self.students_spring_df = df
            elif "results_metadata" in path:
                self.results_meta_df = df
            elif "teachers_metadata" in path:
                self.teachers_meta_df = df
            elif "student_metadata" in path:
                self.students_meta_df = df
            else:
                raise ValueError("That is not a recognized NWEA MAP Data Export file. Keep the original file names given to all .csv files in the data export download package.")

        # If method successful, update the tables dict. 
        self.set_kines()

    # Takes ALL self.df's --> creates a .db table for each kine in self.df_kines
    # self Param conn        Either self.anon_db_conn or self.priv_db_conn
    def to_db(self):
        for kine, df in self.df_kines.items():
            if df is None:
                raise ValueError(f"At {kine} : DataFrame {df} has not been set yet.")
            else:
                print(f"to_db() : Uploading {kine} table to the db.")

            df.to_sql(name=kine, con=self.priv_db_conn, if_exists='replace', index=False)
            print(f"{kine} table uploaded to {config.priv_db_path}")

    # Takes self.teachers_df --> creates a new df with ID | Hashed ID
    # Run on the students_fall_df and students_spring_df DataFrames.
    # Returns a DataFrame with StudentID | HashStudentID
    @staticmethod
    def hash_student_ids(df):
        if df is None:
            raise ValueError("df not set yet. Run .to_df() on a students file before using this method.")
        
        # Create DF
        # Set initial columns based on student df
        student_key = pd.DataFrame({
            'StudentID': df['StudentID'],
            'StudentFirstName': df['StudentFirstName'],
            'StudentLastName': df['StudentLastName']
        })

        # Create hashed ID's
        # Create a hashed ID for each student. Append it to the student master key.
        student_key['HashStudentID'] = student_key['StudentID'].apply(
            lambda x: hashlib.sha256(str(x).encode()).hexdigest()
        )

        return student_key
    
    # Takes self.teachers_df --> creates a new df with ID | Hashed ID
    # Run on the teachers_fall_df and teachers_spring_df DataFrames.
    # Returns a DataFrame with TeacherName | HashTeacherName
    @staticmethod
    def hash_teacher_ids(df):
        if df is None:
            raise ValueError("Teacher DataFrame not set yet. Run .to_df() on a teachers file before using this method.")

        # Set initial columns based on teacher df
        teacher_key = pd.DataFrame({
            'TeacherName': df['TeacherName'],
        })

        # Create hashed names
        # Create a hashed name for each teacher. Append it to the teacher master key.
        teacher_key['HashTeacherName'] = teacher_key['TeacherName'].apply(
            lambda x: hashlib.sha256(str(x).encode()).hexdigest()
        )
        return teacher_key

    # Takes an existing priv_db connection --> Copies it, performs redactions on anon.
    # Must happen before merging hashed id's in main(). 
    def redact_db(self):

        ### Create a straight db file copy, with titles corresponding to config.py
        shutil.copyfile(config.priv_db_path, config.anon_db_path) # Copies to a new file
        print(f"{config.priv_db_path} copy created: {config.anon_db_path}")

        ### Redact the student and teacher names from the private db.
        conn = sqlite3.connect(config.anon_db_path)
        cursor = conn.cursor()
        for kine, _ in self.df_kines.items():
            if kine == "f_students":
                cursor.execute("UPDATE f_students SET StudentFirstName = 'REDACTED'")
                cursor.execute("UPDATE f_students SET StudentLastName = 'REDACTED'")
            elif kine == "s_students":
                cursor.execute("UPDATE s_students SET StudentFirstName = 'REDACTED'")
                cursor.execute("UPDATE s_students SET StudentLastName = 'REDACTED'")
            elif kine == "f_teachers":
                cursor.execute("UPDATE f_teachers SET TeacherName = 'REDACTED'")
            elif kine == "s_teachers":
                cursor.execute("UPDATE s_teachers SET TeacherName = 'REDACTED'")
  
        conn.commit()
        conn.close()

        print(f"Redacted student and teacher names in {config.anon_db_path}")
    
    # replaces ID's in anon_db tables with hash values.
    def merge_hashed_student_ids(self, key: pd.DataFrame, term_: str):

        if key is None:
            raise ValueError("key not set.")  
        
        cursor = self.anon_db_conn.cursor()

        ### Replace StudentID in students and teachers tables 
        for _, row in key.iterrows():

            cursor.execute(f"""
                UPDATE {term_}students
                SET StudentID = ?
                WHERE StudentID = ?
            """, (row['HashStudentID'], row['StudentID']))

            cursor.execute(f"""
                UPDATE {term_}teachers
                SET StudentID = ?
                WHERE StudentID = ?
            """, (row['HashStudentID'], row['StudentID'])) 

            cursor.execute(f"""
                UPDATE {term_}results
                SET StudentID = ?
                WHERE StudentID = ?
            """, (row['HashStudentID'], row['StudentID']))

        self.anon_db_conn.commit()

    def merge_hashed_teacher_names(self, key: pd.DataFrame, term_: str):
        ### Hash the teacher names
        #update teachers table for hashed teacher names
        if key is None:
            raise ValueError("key not set.")  
        
        cursor = self.anon_db_conn.cursor()

        for _, row in key.iterrows():
            cursor.execute(f"""
                UPDATE {term_}teachers
                SET TeacherID = ?
                WHERE TeacherID = ?
            """, (row['HashTeacherName'], row['TeacherName']))      
        self.anon_db_conn.commit()


    # Create tables in private.db for keys
    # Takes self.student_key and self.teacher_key and creates db table for each
    def keys_to_db(self, title, key):
        if key is None:
            raise ValueError("Key has not been set.")
        
        key.to_sql(name=f"{title}", con=self.priv_db_conn, if_exists='replace', index=False)
    
    # Sets the df_kines attribute based on the current DataFrames.
    def set_kines(self):
        self.df_kines = {
            "f_results": self.results_fall_df, 
            "f_teachers": self.teachers_fall_df,
            "f_students": self.students_fall_df,
            "s_results": self.results_spring_df,
            "s_teachers": self.teachers_spring_df,
            "s_students": self.students_spring_df,
            "results_metadata": self.results_meta_df,
            "teachers_metadata": self.teachers_meta_df,
            "student_metadata": self.students_meta_df,
        }

# Both a test and an implementation of DataPrepEngine class.
# Results in anon.db and private.db
def main():
    # Initialize Engine
    e = DataPrepEngine(fall_folder=config.fall_folder, spring_folder=config.spring_folder)

    # Create dfs
    print("MAIN: Creating df's...")
    e.to_df()
    e.set_kines()
    print("MAIN: DataFrames created.")

    # Create private db
    print("MAIN: Creating private db...")
    e.to_db()
    print("MAIN: Private db created.")

    # Hash IDs into dfs
    print("MAIN: Creating pandas.df of student IDs and teacher IDs...")
    s_student_key = e.hash_student_ids(e.students_spring_df) 
    f_student_key = e.hash_student_ids(e.students_fall_df)
    s_teacher_key = e.hash_teacher_ids(e.teachers_spring_df) 
    f_teacher_key = e.hash_teacher_ids(e.teachers_fall_df)

    # Create db: copy private.db into anon.db; redact student names
    print("MAIN: Creating anon.db...")
    e.redact_db()

    # Privatize anon.db's PII values
    print("MAIN: merging hashed values into anon.db...")
    e.merge_hashed_student_ids(s_student_key, "s_")
    e.merge_hashed_student_ids(f_student_key, "f_")
    e.merge_hashed_teacher_names(s_teacher_key, "s_")
    e.merge_hashed_teacher_names(f_teacher_key, "f_")

    # Create lookup tables in private.db
    print("MAIN: Creating student and teacher lookup tables in private.db...")
    e.keys_to_db("teacher_key", s_teacher_key)
    e.keys_to_db("student_key", s_student_key)

    print("MAIN: Data preparation complete. Databases created and populated.")

if __name__ == "__main__":
    main()