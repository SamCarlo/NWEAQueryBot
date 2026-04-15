## A non-OOP version of the 4-function chat agent
## From https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/

import sqlite3

# 1. Define a list of callable tools
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
            }]
            ## End of JSON function descriptions 

##################
### get_schema ###
##################
# Returns the schema, or overivew of data, of a given database. 
# param db_path     The string filepath of the sqlite database to explore
# returns           A string containing the schema. 
def get_schema(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    schema = cursor.execute("SELECT sql FROM sqlite_master").fetchall()
    return str(schema)

######################   
### get_table_info ###
######################
# Get the column names and data types for a given table. 
# param db_path     The string filepath to the database
# param table_id    The string table ID that the bot wants to explore
def get_table_info(db_path: str, table_id: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info('{table_id}')") # gets [(0, 'TermName', 'TEXT', 0, None, 0),....

    sql_response = ""
    for row in cursor.fetchall():
        sql_response += row[1] + row[2] + "\n" # Appends just the column name and data type

    conn.close()
    return sql_response

#################
### sql_query ###
#################
# queries the database and returns data in a list of dicts. 
def sql_query(db_path: str, query: str) -> list[dict]:
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row   # returns sqlite3.Row objects; can be turned into dicts easily.
        rows = conn.execute(query).fetchall() # List of sqlite3.Row objects
        row_list = []
        for row in rows:
            row_list.append(dict(row)) # row_list[n] = {"StudentID": "a1b2c3"}
        return row_list
    except Exception as e:
        return f"Query failed: {e}"




