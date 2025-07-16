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
    def __init__(self):
        # The fileType path of an AssessmentResults, ClassAssignments, StudentsBySchool, or metadata .csv fileType.
        self.csv_paths = [
            config.sp25_results_path,
            config.sp25_teachers_path,
            config.sp25_students_path,
            config.results_metadata,
            config.teachers_metadata,
            config.students_metadata
        ]

        # Columns to REDACT when anonymizing
        self.redacted_cols = ["StudentFirstName",
                              "StudentLastName",
                              "TeacherName"]
        
        # Defines a csv uploaded to pd.DataFrame, preparing for push into SQLite database.
        self.students_df = None
        self.results_df = None
        self.teachers_df = None
        self.results_meta_df = None
        self.teachers_meta_df = None
        self.students_meta_df = None

        self.df_kines = {
            "results": self.results_df, 
            "teachers": self.teachers_df, 
            "students": self.students_df, 
            "results_metadata": self.results_meta_df,
            "teachers_metadata": self.teachers_meta_df,
            "students_metadata": self.students_meta_df
        }

        # A placeholder for the upload process
        self._df = None

        # Lists the kinds of files that have already been fully pushed to 
        self.completed_uploads = []
        
        # A SQL database located in the filepath defined in config.py.
        self.priv_db_conn = sqlite3.connect(config.priv_db_path)

        # A SQL database that will be an anonymous copy of the priv db. 
        self.anon_db_conn = sqlite3.connect(config.anon_db_path)

        # A df to link real ID's to hashed ID's. To be pushed to anon_path.db later.
        self.student_key = None

        # A df to link real Teacher Names to hashed teacher names. To be pushed to anon.db later. 
        self.teacher_key = None

    # Takes ALL self.csv_paths; --> assigns each to appropriate self.df
    def to_df(self):
        for path in self.csv_paths:
            print(f"to_df() : Reading {path} into a DataFrame...")
            self._df = pd.read_csv(path)
            self._df = self._df.dropna(how='all') # All cols must be NaN to drop them. 

            # Determine fileType type based on the fileType name
            if "AssessmentResults" in path:
                print(f"to_df() : {path} is an results file.")
                self.results_df = self._df
            elif "ClassAssignments" in path:
                print(f"to_df() : {path} is a teachers file.")
                self.teachers_df = self._df
            elif "StudentsBySchool" in path:
                print(f"to_df() : {path} is a students file.")
                self.students_df = self._df
            elif "results_metadata" in path:
                print(f"to_df() : {path} is a results metadata file.") 
                self.results_meta_df = self._df
            elif "teachers_metadata" in path:
                print(f"to_df() : {path} is a teachers metadata file.")
                self.teachers_meta_df = self._df
            elif "students_metadata" in path:
                print(f"to_df() : {path} is a students metadata file.")
                self.students_meta_df = self._df
            else:
                raise ValueError("That is not a recognized NWEA MAP Data Export file. Keep the original file names given to all .csv files in the data export download package.")
            
        # Update self.df_kines dict
        self.set_kines()

    # Takes ALL self.df's --> creates a .db table for each kine in self.df_kines
    # self Param conn        Either self.anon_db_conn or self.priv_db_conn
    def to_db(self):
        for kine, df in self.df_kines.items():
            print(f"to_db() : Preparing to upload {kine} table to the database...")
            if df is None:
                raise ValueError(f"DataFrame {df} has not been set yet.")
            else:
                print(f"Uploading {kine} table to the db.")

            df.to_sql(name=kine, con=self.priv_db_conn, if_exists='replace', index=False)
            print(f"{kine} table uploaded to {config.priv_db_path}")

            self.completed_uploads.append(kine) # Add file type to completed uploads list

    # Takes self.teachers_df --> creates a new df with ID | Hashed ID
    def hash_student_ids(self):
        if self.students_df is None:
            raise ValueError("self.df not set yet. Run .to_df() on a students file before using this method.")
        
        # Set initial columns based on student df
        self.student_key = pd.DataFrame({
            'StudentID': self.students_df['StudentID'],
            'StudentFirstName': self.students_df['StudentFirstName'],
            'StudentLastName': self.students_df['StudentLastName']
        })

        # Create hashed ID's
        # Create a hashed ID for each student. Append it to the student master key.
        self.student_key['HashStudentID'] = self.student_key['StudentID'].apply(
            lambda x: hashlib.sha256(str(x).encode()).hexdigest()
        )
    
    # Takes self.teachers_df --> creates a new df with ID | Hashed ID
    def hash_teacher_ids(self):
        if self.teachers_df is None:
            raise ValueError("self.teachers_df not set yet. Run .to_df() on a teachers file before using this method.")
        
        # Set initial columns based on teacher df
        self.teacher_key = pd.DataFrame({
            'TeacherID': self.teachers_df['TeacherID'],
        })

        # Create hashed names
        # Create a hashed name for each teacher. Append it to the teacher master key.
        self.teacher_key['HashTeacherID'] = self.teacher_key['TeacherID'].apply(
            lambda x: hashlib.sha256(str(x).encode()).hexdigest()
        )   

    # Takes an existing priv_db connection --> Copies it, performs redactions on anon.
    def redact_db(self):

        ### Create a straight db file copy, with titles corresponding to config.py
        shutil.copyfile(config.priv_db_path, config.anon_db_path) # Copies to a new file
        print(f"{config.priv_db_path} copy created: {config.anon_db_path}")

        ### Redact the student and teacher names from the private db.
        conn = sqlite3.connect(config.anon_db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET StudentFirstName = 'REDACTED'")
        cursor.execute("UPDATE students SET StudentLastName = 'REDACTED'")
        cursor.execute("UPDATE teachers SET TeacherName = 'REDACTED'")
        conn.commit()
        conn.close()
        print(f"Redacted student and teacher names in {config.anon_db_path}")
    
    # replaces ID's in anon_db tables with hash values.
    def hash_dbs(self):
        cursor = self.anon_db_conn.cursor()

        ### Hash the student id's in students table
        #update results table for hashed student IDs
        if self.student_key is None:
            raise ValueError("student_key not set.")

        for _, row in self.student_key.iterrows():
            cursor.execute("""
                UPDATE students
                SET StudentID = ?
                WHERE StudentID = ?
            """, (row['HashStudentID'], row['StudentID'])) 
        self.anon_db_conn.commit()

        ### Hash StudentID in teachers table
        for _, row in self.student_key.iterrows():
            cursor.execute("""
                UPDATE teachers
                SET StudentID = ?
                WHERE StudentID = ?
            """, (row['HashStudentID'], row['StudentID'])) 
        self.anon_db_conn.commit()       

        ### Hash the teacher ids
        #update teachers table for hashed teacher names
        if self.teacher_key is None:
            raise ValueError("teacher_key not set.")  

        for _, row in self.teacher_key.iterrows():
            cursor.execute("""
                UPDATE teachers
                SET TeacherID = ?
                WHERE TeacherID = ?
            """, (row['HashTeacherID'], row['TeacherID']))      
        self.anon_db_conn.commit()

        ### Hash the results table for hashed student IDs
        if self.student_key is None:
            raise ValueError("student_key not set.")
        for _, row in self.student_key.iterrows():
            cursor.execute("""
                UPDATE results
                SET StudentID = ?
                WHERE StudentID = ?
            """, (row['HashStudentID'], row['StudentID']))
        self.anon_db_conn.commit()

    # Create tables in private.db for keys
    # Takes self.student_key and self.teacher_key and creates db table for each
    def keys_to_db(self):
        if self.student_key is None:
            raise ValueError("Student master key has not been set. Call hash_student_ids()")
        if self.teacher_key is None:
            raise ValueError("Teacher master key has not been set. Call hash_teacher_names()")
        
        self.student_key.to_sql(name="student_key", con=self.priv_db_conn, if_exists='replace', index=False)

        self.teacher_key.to_sql(name="teacher_key", con=self.priv_db_conn, if_exists='replace', index=False)
    
    # Sets the df_kines attribute based on the current DataFrames.
    def set_kines(self):
        self.df_kines = {
            "results": self.results_df, 
            "teachers": self.teachers_df, 
            "students": self.students_df, 
            "results_metadata": self.results_meta_df,
            "teachers_metadata": self.teachers_meta_df,
            "students_metadata": self.students_meta_df
        }

# Both a test and an implementation of DataPrepEngine class.
# Results in anon.db and private.db
def main():
    # Initialize Engine
    e = DataPrepEngine()

    # Create dfs
    print("MAIN: Creating df's...")
    e.to_df()
    print(f"MAIN: \n"
          f"results_df: {e.results_df.shape} \n"
          f"teachers_df: {e.teachers_df.shape} \n"
          f"students_df: {e.students_df.shape} \n"
          f"results_meta_df: {e.results_meta_df.shape} \n"
          f"teachers_meta_df: {e.teachers_meta_df.shape} \n"
          f"students_meta_df: {e.students_meta_df.shape}"
        ) 

    # Create private db
    print("MAIN: Creating private db...")
    e.to_db()

    # Hash IDs into dfs
    print("MAIN: Creating pandas.df of student IDs and teacher IDs...")
    e.hash_student_ids() #fills self.student_key -> pd.df
    e.hash_teacher_ids() #fills self.teacher_key -> pd.df

    # Create db: copy private.db into anon.db; redact student names
    print("MAIN: Redacting student names and teacher names in anon.db...")
    e.redact_db()

    # Update db: 
    print("MAIN: Hashing StudentID's and TeacherID's in anon.db...")
    e.hash_dbs()



    # Create lookup tables in private.db
    print("MAIN: Creating student and teacher lookup tables in private.db...")
    e.keys_to_db()
    print("MAIN: Data preparation complete. Databases created and populated.")

if __name__ == "__main__":
    main()