# type: ignore
## Run tests on each function within QueryAgent (OpenAI verison)
## Date: 7/15/25
## Author: Samuel Carlos

import QueryAgent
import json

def main():
    ## An agent to test
    agent = QueryAgent.QueryAgent()

    ## History
    input_messages = []

    ###############
    ## TEST CHAT ##
    ###############
    print()
    print("#" * 50)
    print("   TEST SEND_CHAT_MESSAGE   ".center(50, "#"))
    print("#" * 50)
    print()

    # Collect user message
    user_message = "What's in the database?"

    # Log user message
    input_messages.append({"role": "user", "content": user_message})

    # Send user message. Input currently holds one JSON item: the line above.
    response = agent.send_chat_message(input_messages)
    
    print(response.output)

    ###################
    ## TEST DISPATCH ##
    ###################
    print()
    print("#" * 50)
    print("   TEST DISPATCH   ".center(50, "#"))
    print("#" * 50)
    print()

    # Collect final (-1) response item; 
    # last output[] item will be a function call if any exist.
    reasoning = None
    tool_call = None
    message = None

    for output in response.output:
        if output.type == 'reasoning':
            reasoning = output
        elif output.type == 'function_call':
            tool_call = output
        elif output.type == 'message':
            message = output

    if tool_call and tool_call.type == 'function_call':
        # Parse apart response for name and args
        name = tool_call.name
        _arg = tool_call.arguments
        _arg = json.loads(_arg) # Now it's a dict
        print(_arg)
        for key, value in _arg.items():
            arg = value
        
        # Send to local model
        sql_response = agent.dispatch(name, arg)

        # Update the messages history
    else:
        print("Not a function call.")
        return

    print(sql_response)

    ##########################
    ## TEST SUBSEQUENT CALL ##
    ##########################
    print()
    print("#" * 50)
    print("   TEST SUBJSEQUENT CALL   ".center(50, "#"))
    print("#" * 50)
    print()

    input_messages.append({
        "type": "function_call_output",
        "call_id": tool_call.call_id,
        "output": sql_response
    })

    # Check the input_messages so far
    print("\n Input messages so far:", end="")
    print(len(input_messages))

    # Create a new response
    enlightened_response = agent.send_chat_message(input_messages)
    print("\nAI Response after reading sql response:")
    print(enlightened_response.output)

if __name__ == "__main__":
    main()



