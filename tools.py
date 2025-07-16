# Holds declarations and functions for query bot
import sqlite3
import config
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
                "name": "get_table",
                "description": "Use this function to get a full sql table from the db.",
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
                        "final_response": {
                            "type": "string",
                            "description": (
                                "Your final response that includes the literal hashed value(s) in context, as if those values are names. "
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
                    "required": ["final_response"],
                    "additionalProperties": False
                },
                "strict": True
            }
        ]


##########################
### DECLARED FUNCTIONS ###
##########################
# Each run of these functions must update:                
# 1. self.previous_id = response.id (responsibility of app)
# 2. self.params = response.output[0].parameters (responsibility of app)
# 3. self.sql_response = <cleaned result of query> (done by these functions)
# 4. self.sql_requests_and_responses = [function call name, params, sql_response] (responsibility of app)

##################
### get_schema ###
##################
def get_schema(self):
    conn = sqlite3.connect(config.anon_db_path)
    cursor = conn.cursor()
    schema = cursor.execute("SELECT sql FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()
    #print(sql_response)
    cleaned_response = []
    for (sql,) in schema: ## This syntax unpacks tuples
        if sql: ## Skip if None (some rows in sqlite_master can have NULL)
            clean_schema = (
                sql
                .replace("\\n", "\n")
                .replace("\\", "") 
                .strip()
            )
            cleaned_response.append(clean_schema)
            self.sql_response = "\n\n".join(cleaned_response)
    conn.close()
    if self.api_response is None:
        raise ValueError("Could not get the schema from the SQL connection.")
    
#################    
### get_table ###
#################
def get_table(self):
    print("IN GET_TABLE")
    conn = sqlite3.connect(config.anon_db_path)
    cursor = conn.cursor()
    if 'table_id' not in self.params:
        print("Failed to provide a table_id param.")
        raise ValueError("Missing required parameter table_id.")
    else:
        ai_table_id = self.params["table_id"]
        print(f"getting table {ai_table_id}")
    
    # Store API response for the chatbot
    self.api_response = cursor.execute(
        f'SELECT * FROM "{ai_table_id}";'
    ).fetchall()
    self.api_response = str(self.api_response)
    print(f"Successfully retrieved: \n\n {self.api_response}")
    # Prepare shorter response for backend details
    print("Getting PRAGMA info for tidy appending to log")
    cursor.execute(f"PRAGMA table_info('{ai_table_id}')")
    columns = [row[1] for row in cursor.fetchall()]
    columns_str = ", ".join(columns)
    
    print("Closing SQL connection")
    conn.close()

#################
### sql_query ###
#################
def sql_query(self):
    conn = sqlite3.connect(config.anon_db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        # Make the genai-created query one line
        cleaned_query = (
                self.params["query"]
                .replace("\\n", " ")
                .replace("\n", "")
                .replace("\\", "")
                .strip()
            )
        # Send to SQLite db as function
        print(f"cleaned query: {cleaned_query}")
        self.api_response = cursor.execute(cleaned_query).fetchall()
        if self.api_response is None:
            self.api_response = "NONE - try again"
        elif isinstance(self.api_response, list):
            try:
                rows = str([dict(row) for row in self.api_response])  # Convert to list of dicts
            except TypeError as te:
                print("TypeError: Likely tried to convert a tuple to dict. Set conn.row_factory = sqlite3.Row.")
                print(te)
            except Exception as e:
                print("General error in row conversion")
                print(e)
        else:
            raise 
        sql_response_str = json.dumps(rows, indent=2)
        # Append to history
        self.api_requests_and_responses.append([self.response.function_call.name, self.params, sql_response_str]) #type: ignore
        self.api_response = sql_response_str
    except Exception as e:
                error_message = f"""
        We're having trouble running this SQL query. This
        could be due to an invalid query or the structure 
        of the data. Try rephrasing your question to help 
        the model generate a valid query for the database.
        """   

    conn.close()

#########################
### template_response ###
#########################
def template_response(self):
    print("IN TEMPLATE RESPONSE")
    secret_conn = sqlite3.connect(config.priv_db_path)
    secret_cursor = secret_conn.cursor()
    final_response = self.params["final_response"]
    self.api_response = final_response # Store api_response as the anonymous version
    hashes = re.findall(r"\{([st])\{(.*?)\}\}", final_response) #returns a tuple (st, hash)
    ## Make a list of names in order of appearance in the final response.
    name_matches = []
    for tag, hash in hashes: 
        if tag == "s":
            print("FOUND STUDENT TAG")
            students = secret_cursor.execute(
                f"SELECT StudentFirstName, StudentLastName FROM student_key WHERE student_key.HashStudentID = ?;",
                (hash,) # has to be passed to sql as a tuple, thus (hash, )
            ).fetchall()
            print(f"{len(students)} NAMES FOUND")
            for first, last in students:
                name_matches.append(f'{first} {last}')
        elif tag == "t":
            print("FOUND TEACHER TAG")
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
    
    filled_template = re.sub(r'\{[st]\{.*?\}\}', replace_with_name, final_response)
    self.api_requests_and_responses.append([self.response.function_call.name, self.params, self.api_response])
    return filled_template