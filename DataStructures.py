## Holds ubiquitous classes for future tool building. 
from dataclasses import dataclass
import numpy as np
import pandas as pd
from typing import Optional

# Builds a nested dictionary of Subjects, Courses, Tests, and Goal Areas
# Param: AssessmentResults file as a pandas database
class SubjectTree:
    def __init__(self, *, df):
        self.df = df
        self.subject_tree = {}
    
    def set_subject_tree(self):
        if self.df is None:
            raise ValueError("self.df not set yet.")
        k = 0
        for _, row in self.df.iterrows():
            subject = row['Subject']
            course = row['Course']
            test = row['TestName']
            if subject not in self.subject_tree:
                self.subject_tree[subject] = {}
            if course not in self.subject_tree[subject]:
                self.subject_tree[subject][course] = {}
            if test not in self.subject_tree[subject][course]:
                k += 1
                print(f"k = {k}")
                print(f"Adding test {test} under course {course} under subject {subject}")
                self.subject_tree[subject][course][test] = {}
                for i in range(1, 8):
                    goal_name_col = f'Goal{i}Name'
                    goal_score_col = f'Goal{i}RitScore'
                    if goal_name_col in row and pd.notna(row[goal_name_col]):
                        if goal_name_col not in self.subject_tree[subject][course][test]:
                            self.subject_tree[subject][course][test][goal_name_col] = row[f'Goal{i}Name']
                        if goal_score_col not in self.subject_tree[subject][course][test]:
                            self.subject_tree[subject][course][test][goal_score_col] = row[f'Goal{i}RitScore']

    def get_subject_tree(self):
        self.set_subject_tree()
        if self.subject_tree is None:
            raise ValueError("subject_tree has not been set yet. Upload a valid df and run self.set_subject_tree().")
        return self.subject_tree
    
    # Param test:       A TestName, literal based on AssessmentResults.csv
    # Return:           the Subject, Course, TestName, Goal_N_Scores, and Goal_N_Names
    def get_test_path(self, test):
        goal_scores_headings = []
        goal_names_headings = []
        this_course = None
        this_subject = None

        if self.subject_tree is None:
            raise ValueError("subject_tree has not been set yet. Upload a valid df and run self.set_subject_tree().")
        
        for subject in self.subject_tree:
            for course in self.subject_tree[subject]:
                if test in self.subject_tree[subject][course]:
                    # Store the found subject and courses titles for later titling
                    this_course = course
                    this_subject = subject

                    for key, value in self.subject_tree[subject][course][test].items():
                        if key.endswith('RitScore'):
                            goal_scores_headings.append(key)
                        elif key.endswith('Name'):
                            goal_names_headings.append(value)
        if this_course is None or this_subject is None:
            raise ValueError(f"Test '{test}' not found in subject tree.")
        local_keys = {
            "Subject": this_subject,
            "Course": this_course,
            "TestName": test,
            "GoalScores": goal_scores_headings,
            "GoalNames": goal_names_headings
        }

        return local_keys

# Holds the resulting objects of interest from kmeans analysis.
@dataclass
class ClusterReport:
    test: str
    df: pd.DataFrame
    cluster_array: np.ndarray
    local_keys: Optional[dict]

class TestTitles:
    def __init__(self):
        self.titles = {
            'Algebra 2': 'Growth: Algebra 2 CCSS 2010',
            'Language Use': 'Growth: Language 2-12 CCSS 2010 V2',
            'Math 2-5': 'Growth: Math 2-5 CCSS 2010 V2',
            'Math 6+': 'Growth: Math 6+ CCSS 2010 V2',
            'Math K-2': 'Growth: Math K-2 CCSS 2010 V2',
            'Reading 2-5': 'Growth: Reading 2-5 CCSS 2010 V4',
            'Reading 6+': 'Growth: Reading 6+ CCSS 2010 V4',
            'Reading K-2': 'Growth: Reading K-2 CCSS 2010',
            'Science 3-5': 'Growth: Science 3-5: for use with NGSS 2013',
            'Science 6-8': 'Growth: Science 6-8: for use with NGSS 2013',
            'Science 9-12 Life Science': 'Growth: Science 9-12 Life Science: for use with NGSS 2013 1.1',
            'Science 9-12': 'Growth: Science 9-12: for use with NGSS 2013'
        }
    def get_short_title(self, full_title):
        for short_title, long_title in self.titles.items():
            if long_title == full_title:
                return short_title
        print(f"Title '{full_title}' not found in the test titles dictionary.")
        return None
    
    def get_long_title(self, short_title):
        for _short, long_title in self.titles.items():
            if _short == short_title:
                return long_title
        raise ValueError("That title could not be found in the dictionary.")
    

    def get_titles(self):
        return self.titles