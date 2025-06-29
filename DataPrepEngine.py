## Takes NWEA Data Export files and creates an anonymous database for AI use.

import pandas as pd
import sqlite3
import shutil
import hashlib

class DataPrepEngine: 
    def __init__(self, *, csv_file):
        self.file = csv_file

        ## Determine file type based on the file name
        if "AssessmentResults" in self.file:
            self.fileType = "results"
        elif "ClassAssignments" in self.file:
            self.fileType = "teachers"
        elif "StudentsBySchool" in self.file:
            self.fileType = "students"
        elif "metadata" in self.file:
            self.fileType = "metadata"
        
        if "fall" in self.file:
            self.season = "fall"
        elif "spring" in self.file:
            self.season = "spring"

    # Setter and getter for public db path
    def setPublicDbPath(self, path: str):
        self.public_db_path = path

    def getPublicDbPath(self) -> str:
        return self.public_db_path
    
    # Setter and getter for anonymous db path
    def setAnonymousDbPath(self, path: str):
        self.anonymous_db_path = path
        
    def getAnonymousDbPath(self) -> str:
        return self.anonymous_db_path

    ########## DATA INGESTION METHODS ########## 

    ## Function to read csv file and convert to pandas dataframe    
    def csvToDf(self) -> pd.DataFrame:
        df = pd.read_csv(self.file)
        return df
    
    ## Function to clean the data
    def cleanData(self) -> pd.DataFrame:
        ## Convert to df
        df = self.csvToDf()

        ## Drop NULL rows
        #df.dropna(inplace=True)

        ## Switch: If file is assessment results
        if self.fileType == "results":
            keepCols = ["TermName",
                        "StudentID", 
                        "Subject",
                        "Course",
                        "NormsReferenceData",
                        "GrowthMeasureYN", 
                        "TestName", 
                        "TestStartDate",
                        "TestStartTime",
                        "TestDuration"
                        "TestRITScore",
                        "TestStandardError",
                        "TestPercentile",
                        "AchievementQuintile",
                        "PercentCorrect",
                        "RapidGuessingPercentage",
                        "FallToFallProjectedGrowth",
                        "FallToFallObservedGrowth",
                        "FallToFallObservedGrowthSE",
                        "FallToFallMetProjectedGrowth",
                        "FalltoFallConditionalGrowthIndex",
                        "FalltoFallConditionalGrowthPercentile",
                        "FallToFallGrowthQuintile",
                        "FallToSpringProjectedGrowth",
                        "FallToSpringObservedGrowth",
                        "FallToSpringObservedGrowthSE",
                        "FallToSpringMetProjectedGrowth",
                        "FalltoSpringConditionalGrowthIndex",
                        "FalltoSpringConditionalGrowthPercentile",
                        "FallToSpringGrowthQuintile",
                        "SpringToSpringProjectedGrowth",
                        "SpringToSpringObservedGrowth",
                        "SpringToSpringObservedGrowthSE",
                        "SpringToSpringMetProjectedGrowth",
                        "SpringToSpringConditionalGrowthIndex",
                        "SpringToSpringConditionalGrowthPercentile",
                        "SpringToSpringGrowthQuintile",
                        "LexileScore",
                        "LexileMin",
                        "LexileMax",
                        "Goal1Name",
                        "Goal2Name",
                        "Goal3Name",
                        "Goal4Name",
                        "Goal5Name",
                        "Goal1RitScore",
                        "Goal2RitScore",
                        "Goal3RitScore",
                        "Goal4RitScore",
                        "Goal5RitScore",
                        "Goal1StdErr",
                        "Goal2StdErr",
                        "Goal3StdErr",
                        "Goal4StdErr",
                        "Goal5StdErr",
                        "Goal1Adjective",
                        "Goal2Adjective",
                        "Goal3Adjective",
                        "Goal4Adjective",
                        "Goal5Adjective",
                        "Goal1Range",
                        "Goal2Range",
                        "Goal3Range",
                        "Goal4Range",
                        "Goal5Range",
                        ]
            
            # Redefine DF to only contain the "keep" cols
            df = df[[col for col in keepCols if col in df.columns]]
            return df
        
        ## Switch: if file is Class Assignments (Gives teacher name)
        if self.fileType == "teachers":
            keepCols = ["TermName",
                        "StudentID",
                        "ClassName",
                        "TeacherName",
                        "TeacherID"]
            
            # Redefine DF to only contain the "keep" cols
            df = df[[col for col in keepCols if col in df.columns]]
            return df
        
        ## Switch: if file is StudentsBySchool (Gives student's full name)
        if self.fileType == "students":
            keepCols = ["StudentID",
                        "StudentLastName",
                        "StudentFirstName",
                        "Grade",
                        "NWEAStandard_EthnicGroup"]
            
            # Redefine DF to only contain the "keep" cols
            df = df[[col for col in keepCols if col in df.columns]]
            return df
        
        ##default
        return df

    ## Getter for file type
    def getFileType(self):
        return self.fileType
    
    ######### ANONYMIZATION METHODS #########

    @staticmethod
    def create_anonymous_db(src_path, dest_path):
        # Copy the public database file in the working folder and rename the copy '2024-2025_anonymous.db'
        shutil.copyfile(src_path, dest_path)
        print(f"copy of {src_path} created as {dest_path}")

        # Redact the student and teacher names from the private db.
        conn = sqlite3.connect(dest_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET StudentFirstName = 'REDACTED'")
        cursor.execute("UPDATE students SET StudentLastName = 'REDACTED'")
        #cursor.execute("UPDATE teachers SET TeacherName = 'REDACTED'")
        conn.commit()
        conn.close()
        print(f"Redacted student and teacher names in {dest_path}")

    # Method to update the anonymous database StudentID values with hashed IDs for students and teachers.
    @staticmethod
    def anonymize_database(*, anon_db_path, student_master_key, teacher_master_key):
        conn = sqlite3.connect(anon_db_path)
        cursor = conn.cursor()

        # Update students table
        for _, row in student_master_key.iterrows():
            cursor.execute("""
                UPDATE students
                SET StudentID = ?
                WHERE StudentID = ?
            """, (row['HashStudentID'], row['StudentID']))

        #update results table for hashed student IDs
        for _, row in student_master_key.iterrows():
            cursor.execute("""
                UPDATE results
                SET StudentID = ?
                WHERE StudentID = ?
            """, (row['HashStudentID'], row['StudentID']))

        # Update teachers table for hashed teacher names
        for _, row in teacher_master_key.iterrows():
            cursor.execute("""
                UPDATE teachers
                SET TeacherName = ?
                WHERE TeacherName = ?
            """, (row['HashTeacherName'], row['TeacherName']))
        
        # Update teachers table for hashed student IDs
        for _, row in teacher_master_key.iterrows():
            cursor.execute("""
                UPDATE teachers
                SET StudentID = ?
                WHERE StudentID = ?
            """, (row['HashStudentID'], row['StudentID']))

        conn.commit()
        conn.close()
        print(f"Anonymized StudentID and TeacherName in {anon_db_path}")

    # Create a new pandas df with anonymized id's
    @staticmethod
    def student_hash_table(*, public_db_path) -> pd.DataFrame:
        # Read the public database to get student names and IDs
        public_conn = sqlite3.connect(public_db_path)
        try:
            public_df_students = pd.read_sql_query("SELECT StudentID, StudentFirstName, StudentLastName FROM students", public_conn)
        except Exception as e:
            raise RuntimeError(f"Failed to read students table from {public_db_path}: {e}")
        
        public_conn.close()

        # Check for StudentID
        required_cols = {'StudentID', 'StudentLastName', 'StudentFirstName'}
        if not required_cols.issubset(public_df_students.columns):
            raise ValueError("students table must contain 'StudentID', 'StudentLastName', and 'StudentFirstName' columns.")    

        # Create a new DataFrame to hold student names and IDs
        student_master_key = pd.DataFrame({
            'StudentID': public_df_students['StudentID'],
            'StudentFirstName': public_df_students['StudentFirstName'],
            'StudentLastName': public_df_students['StudentLastName']
        })
        
        # Create a hashed ID for each student. Append it to the student master key.
        student_master_key['HashStudentID'] = student_master_key['StudentID'].apply(
            lambda x: hashlib.sha256(str(x).encode()).hexdigest()
        )

        return student_master_key
    
    @staticmethod
    def teacher_hash_table(*, public_db_path) -> pd.DataFrame:

        conn = sqlite3.connect(public_db_path)

        try:
            public_df_teachers = pd.read_sql_query("SELECT StudentID, TeacherName FROM teachers", conn)
        except Exception as e:
            raise RuntimeError(f"Failed to read teachers table from {public_db_path}: {e}")

        # Create a new DataFrame to hold teacher names and IDs. Also create a unique ID for each teacher.
        teacher_master_key = pd.DataFrame({
            'StudentID': public_df_teachers['StudentID'],
            'TeacherName': public_df_teachers['TeacherName']
        })

        # Create a hashed ID of each teacher's name and add corresponding column
        teacher_master_key['HashTeacherName'] = teacher_master_key['TeacherName'].apply(
            lambda x: hashlib.sha256(str(x).encode()).hexdigest()
        )

        # Create a hashed ID of each student id in the teachers key
        teacher_master_key['HashStudentID'] = teacher_master_key['StudentID'].apply(
            lambda x: hashlib.sha256(str(x).encode()).hexdigest()
        )

        return teacher_master_key
    
    # Method to reverse loopup from hash to ID
    # This will require a function declaration in app.
    # Will exist as separate function in app.
    @staticmethod
    def reverse_lookup(*, hashed_id: str, master_key: pd.DataFrame, lookup_column: str):
        if master_key is None:
            raise ValueError("Master key has not been created yet.")
        
        # Find the row with the matching hashed ID
        if lookup_column == 'StudentID':
            result = master_key[master_key['HashStudentID'] == hashed_id] #Understanding: [inner] = bool, outer[]=only rows where True.
            if not result.empty:
                return result['StudentID'].values[0]
        elif lookup_column == 'TeacherName':
            result = master_key[master_key['TeacherID'] == hashed_id]
            if not result.empty:
                return result['TeacherName'].values[0]

        else:
            print("A match for that hash ID was not found.")
            return None
    
    # Method to save the master key to a SQLite database
    # Set anon_db_path to a database that will not be passed to the AI.
    @staticmethod
    def save_master_keys(*, src_db_path, student_master_key, teacher_master_key):
        if student_master_key is None or teacher_master_key is None:
            raise ValueError("Master keys have not been created yet.")
        
        conn = sqlite3.connect(src_db_path)
        # Save student master key
        student_master_key.to_sql('student_master_key', conn, if_exists='replace', index=False)
        
        # Save teacher master key
        teacher_master_key.to_sql('teacher_master_key', conn, if_exists='replace', index=False)

        conn.close()
        
        print(f"student_master_key and teacher_master_key saved to {src_db_path}")
    
    # Method to validate that hashes are non-colliding
    @staticmethod
    def validate_hashes(key):
        if key is None:
            raise ValueError("Student master key has not been created yet.")
        
        # Check for duplicate hashes
        duplicate_hashes = key[key.duplicated('HashedID', keep=False)]
        if not duplicate_hashes.empty:
            raise ValueError("Duplicate hashes found in student master key.")
        else:
            print("All hashes are unique.")

    ###### UPLOADING DATABASE METHODS ########

    # Batch processing method
    @staticmethod
    def batch_to_sql(csv_files: dict, db_path: str):
        conn = sqlite3.connect(db_path)

        # For each table, write to the same db. 
        for key, path in csv_files.items():
            engine = DataPrepEngine(csv_file=path)
            df = engine.cleanData()

            table_name = f"{engine.fileType}"

            df.to_sql(name=table_name, con=conn, if_exists='replace', index=False)
            print(f"Wrote {table_name} to {db_path}")