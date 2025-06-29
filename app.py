# type: ignore
## app to run sql-querying chatbot
# Sources: https://ai.google.dev/gemini-api/docs/function-calling?example=meeting
# and https://www.googlecloudcommunity.com/gc/Community-Blogs/Building-an-AI-powered-BigQuery-Data-Exploration-App-using/ba-p/716757?utm_source=chatgpt.com
# Date: 6/13/25
from google import genai
from google.genai import types
from google.genai.types import FunctionDeclaration, GenerateContentConfig, Part, Tool
import sqlite3
import config
import dotenv
from dotenv import load_dotenv
import os
import pandas as pd
import time
from QueryAgent import QueryAgent

# Instance of QueryBot
qb = QueryAgent()

# Starting prompt
prompt = ("""
          SYSTEM INSTRUCTIONS
          For all user questions, follow this flowchart of actions
          1) First, get the schema of the database with get_schema. Maintain it as context for future queries, calling it only as needed after the first look.
          2) Examine your function options. Choose one and return the function call if appropriate.
          3) Examine the results of the function call.
          4) Repeat steps 2 and 3 until a narrative response is appropriate.
          5) If asked to list names, use hashed ID's in place of names and pass your final narrative response to.
          6) If your narrative answer includes hashed values, you MUST use the template_response function call. 
          6) Be concise and completely true to the data in your narrative response. Explain where your answers came from in the database.
          \n
          """ 
          )


####### Setting up a chat with AI #########
# Source: https://ai.google.dev/gemini-api/docs/function-calling?example=meeting

try:
    chatting = True
    while chatting:
        userInput = input("What would you like to ask? (exit ='exit', help = 'help'): ")
        if userInput.lower() == 'exit':
            chatting = False
            break
        if userInput.lower() == 'help':
            print("Type exit to leave.")
        systemInput = prompt + userInput
        qb.raw_response = qb.chat.send_message(systemInput, config=qb.function_call_config)
        qb.response = qb.raw_response.candidates[0].content.parts[0]

        ## Function calling loop; AI talks with databse until narrative response necessary
        function_calling_in_process = True
        while function_calling_in_process:
            try:
                # Set params based on last AI response
                qb.params = {}
                for key, value in qb.response.function_call.args.items():
                    qb.params[key] = value

                # Log the response
                print("New params: ") 
                print(qb.params)

                if qb.response.function_call.name == "get_schema":
                    print("choosing get_schema")
                    qb.get_schema()
                    #print(qb.api_requests_and_responses[-1][2])

                if qb.response.function_call.name == "get_table":
                    print("Choosing get_table")
                    qb.get_table()

                if qb.response.function_call.name == "sql_query":
                    print("Choosing sql_query")
                    qb.sql_query()

                if qb.response.function_call.name == "template_response":
                    print("Choosing template_response")
                    composed_response = qb.template_response()
                    print(f"\n\ncomposed response:  {composed_response}")
                    function_calling_in_process = False

                #Form another response
                qb.send_api_response()                

                print("End of one loop.")
            # Will occur by design; allows narrative reply to end the function calling segment.
            except AttributeError:
                print(qb.response.text)
                print()
                print(qb.api_requests_and_responses[-1])
                function_calling_in_process = False

    print("\nExit chat loop.\n")
    print("Raw response: ")
    #print(qb.raw_response.candidates[0].content.parts[0].text)

except Exception as e:
    print("Final exception active")
    print(e)

## END CHAT LOOP ##
## Conditions for given AI function calls

