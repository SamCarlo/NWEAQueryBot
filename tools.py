# Holds declarations and functions for query bot
import sqlite3
import config
import json
import re
import pandas as pd
from sklearn.cluster import KMeans
import os

###########################################
## Tool declarations and local functions ##
###########################################

## Purpose: provide functions ready for dispatch by query agent.
## Author: Samuel Carlos
## Date: 7/15/25

# Tools for OpenAI agents
openai_tools = [
            {
                "type": "function",
                "name": "get_schema",
                "description": "Use this function to get the full schema printout from the database. This will provide information about the different tables and views in the database, including the titles of tables, their data, and the datatypes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "The name of this function, get_schema, to be used by the code. Always answer with get_schema."
                        }
                    },
                    "required": ["action"],
                    "additionalProperties": False
                },
                "strict": True
            },
            {
                "type": "function",
                "name": "get_table_info",
                "description": "Use this function to get table info from a table in the db.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_id": {
                            "type": "string",
                            "description": (
                                "The exact name of the table that you want to find information about. "
                                "Always use fully qualified table names: the exact name of the table as it appears in the database schema."
                            )
                        }
                    },
                    "required": ["table_id"],
                    "additionalProperties": False
                },
                "strict": True
            },
            {
                "type": "function",
                "name": "sql_query",
                "description": (
                    "Based on the information gathered in get_schema and preview_table, this function sends an ai-generated sql query "
                    "to the database for execution and returns results that can answer the user's question."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "SQL query on a single line that will help give quantitative answers to the user's question when run on the given sql database. "
                                "In the SQL query, always use the fully qualified dataset and table names. Always wrap table names in quotes to avoid errors."
                            )
                        }
                    },
                    "required": ["query"],
                    "additionalProperties": False
                },
                "strict": True
            },
            {
                "type": "function",
                "name": "template_response",
                "description": (
                    "If your final response includes at least one hashed value, "
                    "always use this function to create a structured response "
                    "so that the program can look up the hashed value(s). "
                    "Always follow the regex format described in the properties of this function."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encoded_response": {
                            "type": "string",
                            "description": (
                                "Your final narrative response to the user's question about people, "
                                "except it includes the literal hashed value(s) in context, as if those values are names. "
                                "Wrap those values in double curly braces, like this: {s{hash value}}. "
                                "As you can see, you must include a letter s or t between the first pair "
                                "of curly braces to indicate whether the person is a teacher or student. "
                                "Examples: "
                                "'The students {s{12345}} and {s{67890}} are in cluster 3 for Math 6+.', "
                                "'The teacher {t{1f999ee01}} is doing well in the cluster analysis for Science 7.', "
                                "Here are the students in cluster 2 in {t{0912049012}}'s class: {s{a1b2c3d4e5}}, {s{f6g7h8i9j0}}.'"
                            )
                        }
                    },
                    "required": ["encoded_response"],
                    "additionalProperties": False
                },
                "strict": True
            },
            {
              "type": "function",
              "name": "clusters",
              "description": "Runs a cluster analysis on columns matching a pattern in the SQL query result. Returns a markdown table with cluster assignments for each row.",
              "parameters": {
                "type": "object",
                "properties": {
                  "sql_query": {
                    "type": "string",
                    "description": "A SQL query that returns a table with columns: StudentID, Subject, Course, and one or more columns containing 'growth' in their name for cluster analysis."
                  }
                },
                "required": ["sql_query"],
                "additionalProperties": False
              },
              "strict": True
            }
        ]


##########################
### DECLARED FUNCTIONS ###
##########################
# Each run of these functions must update:                
# 1. agent.previous_id = response.id (responsibility of app)
# 2. agent.params = response.output[0].parameters (responsibility of app)
# 3. agent.sql_response = <cleaned result of query> (done by these functions)
# 4. agent.sql_requests_and_responses = [function call name, params, sql_response] (responsibility of app)

##################
### get_schema ###
##################
def get_schema(db_path: str) -> str:
    expected_path = os.path.realpath(os.path.abspath(db_path))
    print(f"in tools->get_schema ... expected path = {expected_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    schema = cursor.execute("SELECT sql FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()
    print(f"in tools->get_schema ... schema type = {type(schema)}, len = {len(schema)}")
    sql_response = None
    #print(sql_response)
    _digest_response = []
    for (sql,) in schema: ## This syntax unpacks tuples
        if sql: ## Skip if None (some rows in sqlite_master can have NULL)
            clean_schema = (
                sql
                .replace("\\n", "\n")
                .replace("\\", "") 
                .strip()
            )
            _digest_response.append(clean_schema)
            sql_response = "\n\n".join(_digest_response)
    conn.close()
    if sql_response is None:
        raise ValueError("Could not get the schema from the SQL connection.")
    else:
        return sql_response
    
######################   
### get_table_info ###
######################
def get_table_info(db_path, table_id):
    print("IN get_table_info_INFO")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Prepare shorter response for backend details
    print("Getting PRAGMA info for tidy appending to log...")
    cursor.execute(f"PRAGMA table_info('{table_id}')")
    columns = [row[1] for row in cursor.fetchall()]
    sql_response = ", ".join(columns)

    conn.close()

    return sql_response

#################
### sql_query ###
#################
def sql_query(db_path: str, query: str) -> str:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:

        # Send to SQLite db as function
        print(f"cleaned query: {query}")
        sql_response = cursor.execute(query).fetchall()
        conn.close()

        if sql_response is None:
            sql_response = "That query didn't work. Try again with a different one."
            return sql_response
        elif isinstance(sql_response, list):
            try:
                print("sql_response is list. Trying to turn into rows. ")
                rows = [dict(row) for row in sql_response]  # Convert to list of dicts
                sql_response = json.dumps(rows, indent=2)
            except TypeError as te:
                print("TypeError: Likely tried to convert a tuple to dict. Set conn.row_factory = sqlite3.Row.")
                print(te)
            except Exception as e:
                print("General error in row conversion")
                print(e)
        else:
            raise ValueError(f"sql_response did not return as a list. It was type={type(sql_response)} instead.")
        
    except Exception as e:
        error_message = f"""
        We're having trouble running this SQL query. This
        could be due to an invalid query or the structure 
        of the data. Try rephrasing your question to help 
        the model generate a valid query for the database.
        """
        sql_response = error_message
        print(e)
        return sql_response

    return sql_response # type: ignore


#########################
### template_response ###
#########################
def template_response(encoded_response):
    # Define Pattern object
    CAP = re.compile(r'\{([st])\{([^}]+)\}\}')

    # Parse out code blobs from the full string --> Get [(s, 2309hf984), (t, 23fh9h942h9283), ...]
    hashes = CAP.findall(encoded_response) #returns a tuple (st, hash)
    # print(f"hashes: \n\n {hashes}\n\n")

    # Sort into types (to avoid N searches -> run max 2 searches {one each for s and t} instead)
    teacher_vals = []
    student_vals = []
    for tag, hashval in hashes:
        if tag == "t":
            teacher_vals.append(hashval)
        elif tag == "s":
            student_vals.append(hashval)
    print(teacher_vals)
    # Create DB connection
    secret_conn = sqlite3.connect(config.priv_db_path)
    secret_cursor = secret_conn.cursor()

    # Run one query for each name type
    # Build dict keys of names:hashvals
    student_key = {}
    teacher_key = {}

    for v in student_vals:
        row = secret_cursor.execute(
            "SELECT StudentFirstName, StudentLastName FROM student_key WHERE student_key.HashStudentID = ?;",
            (v,)
        ).fetchone()
        
        if row:
            first, last = row
            student_key[v] = f"{first} {last}"
        else:
            student_key[v] = f"{{s{{{v}}}}}"

    for v in teacher_vals:
        row = secret_cursor.execute(
            "SELECT TeacherName FROM teacher_key WHERE HashTeacherName = ?;",
            (v,)
        ).fetchone()

        #select 'Last, First' from tuple "row" using row[0]
        parts = row[0].split(", ")
        if len(parts) == 2:
            last, first = parts
            teacher_key[v] = (f"{first} {last}")
        else:
            teacher_key[v] = row
    
    secret_conn.close()

    #print("student key:")
    #for key, value in student_key.items():
    #    print(f"{key} -> {value}")
    #print("Teacher key")
    #for key, value in teacher_key.items():
    #    print(f"{key} -> {value}")
    
    # Update encoded response
    lookup = {'s': student_key, 't': teacher_key}
    unknown = {'s': '[unknown student]', 't': '[unknown teacher]'}
    missing = {'s': [], 't': []}
    leave_unresolved = False

    # text outside of the {{}} match
    out = []
    
    # pos
    pos = 0

    #Pattern.finditer() is an iterator of re.Match objects.
    # A re.Match object contains:
        # group(0) => a whole regex statement
        # group(1) => captured group 1 in regex, in this case 's' or 't'
        # group(2) => captured group 2 in regex, in this case the hash value
        # group(3) => span: a tuple of indeces showing where in the original string the regex starts and ends. 
    # a re.Match object also contains methods that make it easy to pull properties like these:
        # re.Match.start() returns the start index of a whole group
        # re.Match.end() you can guess
        # re.Match.span() (start, end) pair
    for m in CAP.finditer(encoded_response):
        out.append(encoded_response[pos:m.start()])

        tag, hashval = m.group(1), m.group(2)

        # dict lookup for name given hashval
        name = lookup[tag].get(hashval)

        if name is None:
            missing[tag].append(hashval)
            out.append(m.group(0) if leave_unresolved else unknown[tag])
        else:
            out.append(name)
        
        pos = m.end() # sets pos to index of char after last match
    
    # Tail of text after the last match
    out.append(encoded_response[pos:])

    # out is a list of string chunks. join them
    filled_text = "".join(out)

    return filled_text  

#######################
### Cluster Analysis ##
#######################
# param sql_query: a query that returns table of studentID | Subject | Course | goalAreaNGrowth
def clusters(sql_query: str, cluster_pattern: str = "cluster"):
    secret_conn = sqlite3.connect(config.anon_db_path)
    secret_cursor = secret_conn.cursor()
    secret_cursor.execute(sql_query)
    rows = secret_cursor.fetchall()
    for r in range(min(5, len(rows))):
        print(rows[r])
    # Get column names
    columns = [desc[0] for desc in secret_cursor.description]

    # Create dataframe
    df = pd.DataFrame(rows, columns=columns)

    # Select columns for cluster analysis based on pattern
    cluster_cols = df.filter(like=cluster_pattern).columns
    print(f"Cluster columns = {cluster_cols}")
    X = df[cluster_cols]

    # Drop rows with any NaN in clustering columns
    mask = X.notna().all(axis=1)
    X = X[mask]
    df_clean = df[mask].copy()

    # DEBUG
    print("X shape:", X.shape)
    print("X head:\n", X.head())

    # Check if X is empty
    if X.empty:
        return "No data available for clustering after cleaning NaN values."

    # Perform k-means cluster analysis
    kmeans = KMeans(n_clusters=3, random_state=42)
    df_clean['cluster'] = kmeans.fit_predict(X)

    # Convert ID columns to string to avoid scientific notation
    for col in df_clean.columns:
        if "id" in col.lower():
            df_clean[col] = df_clean[col].astype(str)

    # Return cluster table as a string
    df_text = df_clean.to_markdown(index=False)
    return df_text