## Implements QueryAgent capabilities with OpenAI's API.
## Holds state: ai messages, user messages, and sql results.
## Accepts user input
## Drives a chat loop for sqlite3 querying

# Date: 7/14/25
# Author: Samuel Carlos

# type: ignore
import json
import os
import dotenv
import config
from openai import OpenAI
import tools

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

        ### PROMPT ###
        self.instructions = (
            "SYSTEM INSTRUCTIONS:" \
            "You have access to a sql database on one school year's worth of " 
            "standardized testing data. School administrators will need your help " 
            "to gain insights on that data because they aren't data analysts. " 
            "Start the conversation by helping the " 
            "user to set a clear goal for the analysis. Then, start drilling into " 
            "the database by using the functions available to you. Use the info gathered " 
            "to create a clear " 
            "and descriptive answer to the agreed upon goal."
            "The names in the database are redacted, so "
            "you will need to use the template_response to de-anonymize names."
            "Format lists of data as tables whenever appropriate."
            "Use double line breaks wherever line breaks are appropriate."
            "Users may refer to the Reading test as Language Arts and vice versa."
            "Get clarification on reading / language arts from the user it arises in convresation."

            """
            When formatting tables for Streamlit output, use GitHub-flavored Markdown with pipe (|) delimiters,
              a header row, and a separator row (e.g., |---|---|). Do not format tables as plain text or ASCII-style 
              unless explicitly requested.
            """
            )

        ### Client configuration ###
        self.my_config = {
            "model": "o4-mini",
            "instructions": self.instructions,
            "parallel_tool_calls": False,
            "temperature": 1.0,
            "tools": tools.openai_tools,
            "tool_choice": "auto",
            "reasoning": {"effort": "medium"},
        }

        ### PARAMS FROM AI ###
        # Accessible as response.output[n].arguments
        self.params = {}

        # Accessible as response.output[n].text
        self.output_text = ""

        #Store previous id from a response
        self.previous_id = None

    
    ### END OF __INIT__ ###

    #############################
    ### Send new chat message ###
    #############################

    def send_chat_message(self, input):
        print("In sent_chat_message")
        ## Add input text to the configuration for responses.create()
        self.my_config["input"] = input

        ### Add dummy function call to satiate model
        #func_call_found = False
        #for msg in input:
        #    for key, value in msg.items():
        #        if key == "function_call_output":
        #            func_call_found = True
        #            continue
        #if func_call_found == False:
        #    # dodge 'no tool output' error by forcing no tool call.
        #    self.my_config["tool_choice"] = "none" 

        ## Check if previous context exists
        if self.previous_id is None:
            print("No context yet. Creating response.")
            response = self.client.responses.create(**self.my_config)
            self.previous_id = response.id
        else:
            #print(f"Context provided. {self.previous_id}")
            #self.my_config["previous_response_id"] = self.previous_id
            response = self.client.responses.create(**self.my_config)
            self.previous_id = response.id
        print("QueryBot response created. Returning to UI.")
        return response
    
    ##########################
    ## Dispatch Switchboard ##
    ##########################
    # Call only when response.output[-1].type == "function_call"
    # param "name" = the function call name
    # param "arg" = the function call argument
    # return = the database's response, cleaned by the local functions already.
    def dispatch(self, name, arg=None):
        print("IN DISPATCH")
        if name == "get_schema":
            sql_response = tools.get_schema(db_path=config.anon_db_path)
        elif name == "get_table_info":
            print("Chose get_table_info")
            print(f"Args: {arg}")
            sql_response = tools.get_table_info(db_path=config.anon_db_path, table_id=arg)
        elif name == "sql_query":
            print("Chose sql_query")
            print(f"Args: {arg}")
            sql_response = tools.sql_query(db_path=config.anon_db_path, query=arg)
        elif name == "template_response":
            print("Chose template_response")
            print(f"Args: {arg}")
            sql_response = tools.template_response(encoded_response=arg)

        return sql_response




        