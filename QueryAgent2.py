## Implements QueryAgent capabilities with OpenAI's API.
# Date: 7/14/25
# Author: Samuel Carlos

# type: ignore
import json
import os
import dotenv
import config
from openai import OpenAI


### Agent ###
# States: 
# previous_id : holds chat history
# api_response : holds sqlite3 result
# client : instance of gpt-4
# Tools: function declarations (4)
# params (literal): parameters passed from function call
class QueryAgent:
    def __init__(self):
        ### API CONNECTION ###
        dotenv.load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)

        ### CHAT HISTORY ###
        self.previous_id = None

        ### FUNCTION CALL RESPONSE ###
        self.sql_response = None

        ### FUNCTION CALL HISTORY ###
        self.sql_requests_and_responses = []

        ### PARAMS FROM AI ###
        # Accessible as response.output[0].arguments IF response.output[0].type == "function_call"
        self.params = {}

        ### TOOLS ###
        self.tools = config.openai_tools
        
        ### PROMPT ###
        self.instructions = """         
        SYSTEM INSTRUCTIONS
        For all user questions, follow this flowchart of actions
        1) First, you must get the schema of the database with get_schema. 
        2) Next, you must use get_table to read the descriptions of fields in the metadata tables for full context on the database.
        3) Consider asking the user for a clarifying question before moving onto database querying, using your new knowledge of the database to help guide the user prompt.
        4) Examine your function options. Choose one and return the function call if appropriate.
        5) Examine the results of the function call.
        6) Repeat steps 3 and 4 until a narrative response is appropriate.
        7) If asked to list names, use hashed ID's in place of names and pass your final narrative response to.
        8) If your narrative answer includes hashed values, you MUST use the template_response function call. 
        9) Be concise and completely true to the data in your narrative response. Explain where your answers came from in the database.
        \n
        """ 
    ### END OF __INIT__ ###

    #############################
    ### Send new chat message ###
    #############################

    # Iniitalizes response maker
    # Updates state: self.previous_id
    def send_chat_message(self, input):
        print("IN SEND MESSAGE")
        print(f"Previous id = {self.previous_id}")
        if self.previous_id is None:
            response = self.client.responses.create(
                model="gpt-4",
                instructions=self.instructions,
                input=[{"role": "user", "content": input}],
                tools=self.tools
            )
        else:
            response = self.client.responses.create(
            model="gpt-4",
            instructions=self.instructions,
            previous_response_id=self.previous_id,
            input=[{"role": "user", "content": input}],
            tools=self.tools,
        )
        return response

    ##########################
    ### DECLARED FUNCTIONS ###
    ##########################
    # Each run of these functions must update:                
    # 1. self.previous_id = response.id (responsibility of app)
    # 2. self.params = response.output[0].parameters (responsibility of app)
    # 3. self.sql_response = <cleaned result of query> (done by these functions)
    # 4. self.sql_requests_and_responses = [function call name, params, sql_response] (responsibility of app)

    ### get_schema ###
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

    ### get_table ###
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

    ### sql_query ###
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

    ### template_response ###
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


        