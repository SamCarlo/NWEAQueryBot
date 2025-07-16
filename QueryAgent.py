## Implements QueryAgent capabilities with OpenAI's API.
# Date: 7/14/25
# Author: Samuel Carlos

# type: ignore
import json
import os
import dotenv
import config
from openai import OpenAI
import re


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



        