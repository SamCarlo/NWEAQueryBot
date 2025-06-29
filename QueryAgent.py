# type: ignore
# Agent to act as a chat bot that can query a SQLite database using Gemini.

import dotenv
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
from google.genai.types import FunctionDeclaration, GenerateContentConfig, Part, Tool
import sqlite3
import config
import dotenv
import pandas as pd
import time
import config
import re
import json

class QueryAgent:
    """
    This class contains the function declarations for the Query Agent.
    It includes functions to get the schema, preview a table, execute SQL queries,
    and handle template responses and reverse lookups.
    """
    def __init__(self):
        
        # Declarations
        ## Function Declaration for returning .schema
        self.get_schema_declaration = FunctionDeclaration(
            name="get_schema",
            description="Use this function to get the full schema printout from the database. This will provide information about the different tables and views in the database, including the titles of tables, their data, and the datatypes.",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The name of this function, get_schema, to be used by the code. Always answer with get_schema."
                    },
                },
                "required": ["action"]
            }
        )

        ## Function declaration for returning detailed table information
        self.get_table_declaration = FunctionDeclaration(
            name="get_table",
            description="Use this function to get a full sql table from the db.",
            parameters={
                "type": "object",
                "properties": {
                    "table_id": {
                        "type": "string",
                        "description": (
                            "the exact name of the table that you want to find information about. "
                            "Always use fully qualified table names: the exact name of the table as it appears in the database schema."
                        )
                    },
                },
                "required": ["table_id"]
            }
        )

        ## Function declaration for sql_query
        self.sql_query_declaration = FunctionDeclaration(
            name="sql_query",
            description=(
                "Based on the information gathered in get_schema and preview_table, this function sends an ai-generated sql query to the database for execution and returns results that can answer the user's question."
            ),
            parameters={
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
                "required": ["query"]
            }
        )

        # A function to write a template response to be processed by hard-code in the reverse lookup function later. 
        self.template_response_declaration = FunctionDeclaration(
            name="template_response",
            description=(
                "If your final response includes at least one hashed value, "
                "use this function to create a structured response "
                "so that the program can look up the hashed value(s)."
                "Use only student or teacher hashes, but not both."
                "If a response requries both, explain that to the user as a narrative response."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "final_response": {
                        "type": "string",
                        "description": (
                            "Your final response that includes the literal hashed value(s) in context, as if those values are names. "
                            "Wrap those values in double curly braces, like this: {s{hash value}}. "
                            "As you can see, you must include a letter s or t between the first pair"
                            "of curly braces to indicate whether the person is a teacher or student."
                            "Examples: "
                            "'The students {s{12345}} and {s{67890}} are in cluster 3 for Math 6+.', "
                            "'The teacher {t{1f999ee01}} is doing well in the cluster analysis for Science 7.', "
                            "Here are the students in cluster 2 in {t{0912049012}}'s class: {s{a1b2c3d4e5}}, {s{f6g7h8i9j0}}.'"
                        )
                    },
                },
                "required": ["final_response"]
            }
        )
        
        # Chat persistence and logging
        self.backend_details = ""
        self.params = {}
        self.api_requests_and_responses = []
        self.raw_response = None
        self.response = None
        self.api_response = None

        # SQLite
        self.conn = sqlite3.connect(config.dest_path)  # Connect to the database
        self.cursor = self.conn.cursor()  # Create a cursor for executing SQL commands

        # Chat client and input
        self.sql_query_tools = Tool(
            function_declarations=[
            self.get_schema_declaration,
            self.get_table_declaration,
            self.sql_query_declaration,
            self.template_response_declaration #Chore : Write function for this
        ])

        self.function_call_config = GenerateContentConfig(
                temperature=0,
                tools=[self.sql_query_tools], # type: ignore
                automatic_function_calling={"disable": True}, # type: ignore
                tool_config={"function_calling_config": {"mode": "AUTO"}} # type: ignore
        )

        load_dotenv()
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.chat = self.client.chats.create(
            model="gemini-2.5-flash-preview-05-20", 
            config=self.function_call_config,
        )
        self.client = None
        self.prompt = ""

    def get_schema(self):
        schema = self.cursor.execute("SELECT sql FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()
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
                self.api_response = "\n\n".join(cleaned_response)
        
        # Append the API request and response for the next message to genai
        if self.api_response is None:
            raise ValueError("Could not get the schema from the SQL connection.")
        self.api_requests_and_responses.append([self.response.function_call.name, self.params, self.api_response]) 
    
    def get_table(self):
        if 'table_id' not in self.params:
            print("Failed to provide a table_id param.")
            raise ValueError("Missing required parameter table_id.")
        else:
            ai_table_id = self.params["table_id"]
            print(f"getting table {ai_table_id}")
        
        # Store API response for the chatbot
        self.api_response = self.cursor.execute(
            f"SELECT * FROM '{ai_table_id}';"
        ).fetchall()

        self.api_response = str(self.api_response)

        # store API response for the program
        self.cursor.execute(f"PRAGMA table_info('{ai_table_id}')")
        cols = [row[1] for row in self.cursor.fetchall()]
        columns_str = ", ".join(columns)
        
        self.api_requests_and_responses.append([self.response.function_call.name, self.params, columns_str]) #type: ignore
        print(f"API response: {self.api_response}")

    def template_response(self):
        print("IN TEMPLATE RESPONSE")
        secret_conn = sqlite3.connect(config.src_path)
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
                    f"SELECT StudentFirstName, StudentLastName FROM student_master_key WHERE student_master_key.HashStudentID = ?;",
                    (hash,) # has to be passed to sql as a tuple, thus (hash, )
                ).fetchall()
                print(f"{len(students)} NAMES FOUND")
                for first, last in students:
                    name_matches.append(f'{first} {last}')
            elif tag == "t":
                print("FOUND TEACHER TAG")
                teachers = secret_cursor.execute(
                    f"SELECT TeacherName FROM teacher_master_key WHERE HashTeacherName = ?;",
                    (hash,)
                ).fetchall()
                for _, teacher_name in teachers:
                    name_matches.append(teacher_name)
                    
        name_iter = iter(name_matches)
        def replace_with_name(match):
            return next(name_iter, match.group(0))
        
        filled_template = re.sub(r'\{[st]\{.*?\}\}', replace_with_name, final_response)

        self.api_requests_and_responses.append([self.response.function_call.name, self.params, self.api_response])
        return filled_template

    def send_api_response(self):
        new_raw_response = self.chat.send_message(
            Part.from_function_response(
                name=self.response.function_call.name,
                response={
                    "content": self.api_response
                }
            )
        )
        self.raw_response = new_raw_response
        self.response = new_raw_response.candidates[0].content.parts[0]

    def set_params(self):
        print("in set_params.")
        self.response = self.raw_response.candidates[0].content.parts[0]

        if self.response is None:
            raise ValueError("Response object is None. Cannot set parameters.")
        if hasattr(self.response, "function_call") and self.response.function_call and hasattr(self.response.function_call, "args"):
            for key, value in self.response.function_call.args.items():
                self.params[key] = value
            print("params set.")

    def get_params(self):
        return self.params

    def sql_query(self):
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
            self.api_response = self.cursor.execute(cleaned_query).fetchall()
            rows = str([dict(row) for row in self.api_response])  # Convert to list of dicts
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
    
    
    