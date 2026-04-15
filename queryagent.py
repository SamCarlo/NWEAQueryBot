## queryagent.py
## A barebones OpenAI agent that queries a SQLite database.
##
## An agent is a loop that:
##   1. Sends a message to the model
##   2. Checks if the model wants to call a tool
##   3. Runs the tool and sends the result back
##   4. Repeats until the model gives a final text response

import os
import json
import dotenv
from openai import OpenAI
import tools
import config

dotenv.load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

INSTRUCTIONS = (
    "You have access to a SQL database of standardized testing data. "
    "Help school administrators gain insights from the data. "
    "For every user question, follow these steps in order:\n"
    "  1. Call get_schema to see all available tables.\n"
    "  2. Call get_table_info on any relevant tables to understand their columns.\n"
    "  3. Write and run sql_query calls as needed to answer the question.\n"
    "Do not skip steps or ask the user clarifying questions. "
    "Make reasonable assumptions and go straight to querying. "
    "Format results as GitHub-flavored Markdown tables where appropriate."
)

# 2. Dispatch — maps function names the model calls to actual Python functions
def dispatch(name, args):
    if name == "get_schema":
        return tools.get_schema(db_path=config.anon_db_path)
    elif name == "get_table_info":
        return tools.get_table_info(db_path=config.anon_db_path, table_id=args["table_id"])
    elif name == "sql_query":
        return tools.sql_query(db_path=config.anon_db_path, query=args["query"])
    else:
        return f"Unknown tool: {name}"

# 3. Agent loop — generator that yields ("sql", query) for each SQL query run,
# then yields ("response", final_text) when done.
# history is mutated in place so the caller retains context between turns.
def run(user_message, history=None):
    if history is None:
        history = []

    history.append({"role": "user", "content": user_message})
    input_messages = list(history)

    while True:
        response = client.responses.create(
            model="o4-mini",
            instructions=INSTRUCTIONS,
            tools=tools.openai_tools,
            input=input_messages,
            parallel_tool_calls=False,
            reasoning={"effort": "high"},
        )

        tool_calls = [item for item in response.output if item.type == "function_call"]

        # No tool calls means the model is done — yield the final response
        if not tool_calls:
            final_text = next(item.content[0].text for item in response.output if item.type == "message")
            history.append({"role": "assistant", "content": final_text})
            yield "response", final_text
            return

        # Execute each tool and yield SQL queries as they happen
        tool_results = []
        for call in tool_calls:
            args = json.loads(call.arguments)
            if call.name == "sql_query":
                yield "sql", args["query"]
            result = dispatch(call.name, args)
            tool_results.append({
                "type": "function_call_output",
                "call_id": call.call_id,
                "output": str(result),
            })

        # Feed tool results back in, keeping full history as prefix
        input_messages = input_messages + list(response.output) + tool_results
