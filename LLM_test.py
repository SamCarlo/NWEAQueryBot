# Test OpenAI o4-mini reactions to different inputs
# author: samuel carlos
# date: 7/17/25

from openai import OpenAI
import dotenv
import config
import tools
import os
import json


# A reasoning step
dotenv.load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

instructions = """
The user needs to understand patterns in their school's data, 
but is not a data analyst and doesn't know the structure
of their school's database. Help them develop a good question, and 
then use the declared functions to execute the necessary function calls 
and answer their question. 
"""

history = [{
            "role": "user", 
            "content": (
                "I need to prepare for my observation year by writing a paper"
                " about how I will plan to use data to drive my instruction."
            )
        }]

response = client.responses.create(
    model="o4-mini",
    reasoning={"effort": "medium"},
    instructions=instructions,
    tools=tools.openai_tools, #type: ignore
    input=history
)

# response.output[0]
print(response.output)

# Try to include reasoning
# ... per the "item ... of type 'function_call' was provided without its required 'reasoning' item"
for tool_call in response.output:
    if tool_call.type != "reasoning":
        continue
    id = tool_call.id

    history.append(tool_call)
    print(f"reasoning appended:{tool_call}")


#Handle the output - select only the function call
for tool_call in response.output:
    if tool_call.type != "function_call":
        continue
    
    name = tool_call.name
    args = json.loads(tool_call.arguments)

    sql_response = tools.get_schema(db_path=config.anon_db_path)
    history.append(tool_call)
    history.append({
        "type": "function_call_output",
        #"name": name,
        #"arguments": 
        "call_id": tool_call.call_id,
        "output": str(sql_response)
    })

# Next message
response = client.responses.create(
    model="o4-mini",
    reasoning={"effort": "medium"},
    instructions=instructions,
    tools=tools.openai_tools, #type: ignore
    input=history
)

print(response.output)