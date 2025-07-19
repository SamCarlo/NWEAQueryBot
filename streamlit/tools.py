# Holds declarations and functions for query bot
import sqlite3
import json
import re

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
                    "use this function to create a structured response "
                    "so that the program can look up the hashed value(s). "
                    "IF looking up a teacher name, PLEASE use HashTeacherName col, NOT TeacherID."
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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    schema = cursor.execute("SELECT sql FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()
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
    secret_conn = sqlite3.connect("private.db")
    secret_cursor = secret_conn.cursor()
    hashes = re.findall(r"\{([st])\{(.*?)\}\}", encoded_response) #returns a tuple (st, hash)
    ## Make a list of names in order of appearance in the final response.
    name_matches = []
    for tag, hash in hashes: 
        if tag == "s":
            students = secret_cursor.execute(
                f"SELECT StudentFirstName, StudentLastName FROM student_key WHERE student_key.HashStudentID = ?;",
                (hash,) # has to be passed to sql as a tuple, thus (hash, )
            ).fetchall()
            for first, last in students:
                name_matches.append(f'{first} {last}')
        elif tag == "t":
            teachers = secret_cursor.execute(
                f"SELECT TeacherName FROM teacher_key WHERE HashTeacherName = ?;",
                (hash,)
            ).fetchall()
            for _, teacher_name in teachers:
                name_matches.append(teacher_name)
    
    secret_conn.close()
    name_iter = iter(name_matches)
    def replace_with_name(match):
        return next(name_iter, match.group(0))
    
    filled_template = re.sub(r'\{[st]\{.*?\}\}', replace_with_name, encoded_response)
    return filled_template