import config
import sqlite3
import pandas as pd
import time
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass
from typing import Any
import numpy as np
from ClusterAnalysis import ClusterAnalysis
import config
from DataStructures import *
from sklearn.cluster import KMeans

c = ClusterAnalysis(db_path=config.src_path)

# Prove df
df = c.get_df()
print(c.get_df().head()) # type: ignore

# Show test names
print(df[df['Course'] == 'Reading']['TestName'].unique())

# Create a Subject Tree
t = SubjectTree(df=c.get_df())
t_dict = t.get_subject_tree()
for key, value in t_dict.items():
   print(f"\n{key}, {value}\n")

# Run a results analysis of Reading 2-5
results = c.results_analysis(test='Growth: Reading 2-5 CCSS 2010 V4')
print(results.cluster_array)