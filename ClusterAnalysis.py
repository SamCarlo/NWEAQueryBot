# Class to run cluster analysis on student data. 
# Author: Samuel Carlos
# 6/18/25
from config import *
import sqlite3
import pandas as pd
import time
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass
from typing import Any
import numpy as np
from DataStructures import *

start_time= time.time()
from sklearn.cluster import KMeans
end_time = time.time()

print(f"Imported sklearn.cluster.KMeans for {end_time-start_time}")
# GOAL : Make new SQL Table. 
# Stucture: StudentID | TeacherID | Subject | Area1Cluster |...| Area4Cluster

# Tools to add a cluster analysis table to a database in-place.
class ClusterAnalysis():
    def __init__(self, *, db_path):
        # The str filepath to a results database
        self.db_path = db_path

        # A complete df copy of the db above.
        self.df = None
        self._make_dataframe()

        # The subject-filtered df created by one run of the analysis() method. 
        self.subject_df = None

        # subject_tree contains a nested dict map of subjects, courses, tests, and goal areas from the AssessmentResults csv.
        self.subject_tree = SubjectTree(df=self.df).get_subject_tree()
        
    # Load the Assessment Results from the database
    # a.k.a "initial df setter"
    def _make_dataframe(self):
        with sqlite3.connect(self.db_path) as conn:
            self.df = pd.read_sql_query(f"SELECT * FROM results", conn)
   
    # Runs cluster analysis on an AssessmentResults dataframe. 
    # Each subject is analyzed separately. Clusters are 3-4 dimensional, each dimension being a Goal Area RIT score.
    # Analyzed for 3 clusters. 
    # Param course:     The literal course title matching the AssessmentResults.csv names. (Math K-12, Science K-12, Reading, Language Usage)
    # Return            ClusterReport; custom data type with {testName, filtered df, centroid coordinates}. Returns one ClusterReport per TestName.
    # Source: https://realpython.com/k-means-clustering-python/
    def results_analysis(self, *, test):
        
        if self.df is None:
            raise ValueError("DataFrame has not been created yet. This should not have happened. Debug implementation of _make_dataframe() in __init__.")
        
        # Create a list of the 3-4 columns for cluster analysis, depending on number of goals in a test.
        _local_tree = SubjectTree(df=self.df)
        _local_tree.set_subject_tree()
        local_keys = _local_tree.get_test_path(test)
        print(f"\nlocal keys of {test}: {local_keys}\n")

        ## local_keys = {
        ##     "Subject": this_subject,
        ##     "Course": this_course,
        ##     "TestName": test,
        ##     "GoalScores": goal_scores_headings,
        ##     "GoalNames": goal_names_headings
        ## }

        goal_scores_cols = local_keys["GoalScores"]
        print(f"Selecting goal score columns: {goal_scores_cols}")

        # Define a full AssessmentResults df that is filtered by this test
        self.subject_df = self.df[self.df['TestName'] == test].copy()
        if len(self.subject_df) < 3:
            raise ValueError(f"Not enough data in this test's df. Have {len(self.subject_df)}, need 3.")
        print(f"\nCreated sliced version of df copy for the test:\n \'{self.subject_df.head()}\'\n")

        #Data frame of only this test's goal_n_RitScore columns 
        subject_data = self.subject_df[goal_scores_cols]
        print(f"\nData table for just this test: \n{subject_data.head()}\n")
                
        scaler = StandardScaler()
        print(f"Scaling data table features for test '{test}'")
        scaled_features = scaler.fit_transform(subject_data)
        kmeans_object = KMeans(
            init="random",
            n_clusters=3,
            n_init=10,
            max_iter=300,
            random_state=None
        )

        #Generate centroid array
        print(f"Creating centroid array for{test}")
        kmeans_object.fit(scaled_features)

        #Generate category labels
        print(".fit_predict(): create table labels")
        labels = kmeans_object.fit_predict(scaled_features)

        #attach labels to subject df
        print("Attaching labels to subject-only df copy.")
        self.subject_df.loc[subject_data.index, f'{local_keys["Course"]}_cluster'] = labels

        # Create the array of average centers
        print("Getting scaled cluster centers.")
        scaled_clusters = kmeans_object.cluster_centers_

        # Scaled back to be actual RIT numbers
        print("Inverse scaling cluster centers.")
        orig_clusters = scaler.inverse_transform(scaled_clusters)

        # Add a columns to orig_clutsers that contains the cluster number.
        #np.arange(len(orig_clusters)): creates an array [0, 1, 2, ..., n_clusters-1] (one cluster number for each row).
        # np.insert(array, 0, values, axis=1): inserts values as a new column at index 0 (the first column) along axis 1 (columns).
        orig_clusters = np.insert(orig_clusters, 0, np.arange(len(orig_clusters)), axis=1)

        # Create ClusterReport object for each and append to final list.
        print(f"Creating ClusterReport for test '{test}' with {len(orig_clusters)} clusters.\n")
        kmeans_result_analysis = ClusterReport(test=test, df=self.subject_df, cluster_array=orig_clusters, local_keys=local_keys)
        return kmeans_result_analysis
    
    ## Convert centroid array to df
    # Param         'report' is a ClusterReport object.
    # Returns       df of GoalAreaNames as cols, center of score cluster as rows
    @staticmethod
    def make_centroid_df(kmeans_analysis):
        print(f"\nCreating centroid df for test '{kmeans_analysis.test}'\n")
 
        test_goal_areas = kmeans_analysis.local_keys["GoalNames"].copy()
        test_goal_areas.insert(0, "cluster")
    
        # The numpy array of centroid coordinates
        centroid_array = kmeans_analysis.cluster_array

        # Create the df
        df = pd.DataFrame(centroid_array, columns=test_goal_areas)

        return df
        

    ## Getter for df
    def get_df(self):
        return self.df
    
    def get_subject_df(self):
        return self.subject_df
    
    ## Getter for subject tree
    def get_subject_tree(self):
        return self.subject_tree
    
    ## Get self.df length
    def get_len(self):
        if self.df is None:
            raise ValueError("Can't get_len for a None df.")
        return len(self.df)

# Example usage
def main():
    test_short = 'Reading 6+'
    test_long = TestTitles().get_long_title(test_short)
    cluster_engine = ClusterAnalysis(db_path = dest_path)
    results = cluster_engine.results_analysis(test=test_long)

    # Create a SubjectTree object to get local keys for this test
    local_keys = SubjectTree(df=results.df)
    local_keys.set_subject_tree()
    local_keys = local_keys.get_test_path(test_long)

    # Create a centroid df from the results
    centroid_df = cluster_engine.make_centroid_df(results)

    print(f"Test:\n {results.test}\n")
    print(f"df:\n {results.df.head()}\n")
    print(f"Centroid centers:\n {results.cluster_array}\n")
    print(f"Centroid df:\n {centroid_df}\n")


if __name__ == "__main__":  
    main()