# type: ignore
## Run tests on each function within QueryAgent (OpenAI verison)
## Date: 7/15/25
## Author: Samuel Carlos

import queryagent
import json
import streamlit as st
import time

## Persist via st.session_state
if "agent" not in st.session_state:
    st.session_state.agent = queryagent.QueryAgent()
if "input_messages" not in st.session_state:
    st.session_state.input_messages = []

## Set Streamlit page config
st.set_page_config(
    page_title="HAAS NWEA Data Agent",
    page_icon=None,
    layout="wide",
)
st.subheader("HAAS NWEA Data Agent")

## Starting prompts
with st.expander("Read me", expanded=False):
    st.write(
        """
        This is an AI agent run on OpenAI's "o4-mini" Large Language Model.
        It is connected to the HAAS NWEA testing data for Spring 2024-2025. \n

        All data will be output in its encrypted format until the school
        signs a Data Processing Addendum with a secure cloud storage provider. 

        ⚠️ Please note ⚠️ \n
        **Any names or id's you enter into the chat field are not protected.**
        Entering any student PII into the user chat box is a violation of FERPA. 
    """
    )
with st.expander("Sample prompts", expanded=False):
    st.write(
    """
    - Explain what's in the database.
    - Which 7th grade students deserve a reward for their achievements in each subject?
    - I'm curious about math proficiency gaps in 5th grade. What are they, specifically?
    - Make a table that shows how vocabulary and geometry scores relate to overall Science RIT.
    - I want to improve 3rd-grade reading outcomes. What should I do?
    - Set classroom performance objectives for each of the 5 lowest-scoring 6th graders in Reading.  
    - Write a 1-page reoprt using this data to create learning pods for an Earth and Space unit in 8th grade science.
    """
    )

###############################
######## CHAT INSTANCE  #######
###############################
# for logging continuous stream of messages
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# For logging data LLM action cycle; refresh after each prompt
st.session_state.action_history = ""

# Init anon_response to avoid "not defined" error upon comparison
anon_response = ""

## Wait for the user to respond to "Type your question..."
## Store response in userInput
if userInput := st.chat_input("Type your question..."):

    # Append user input to the message stream
    st.session_state.input_messages.append({"role": "user", "content": userInput})
    st.session_state.chat_history.append({"role": "user", "content": userInput})

    # Show the user message
    with st.chat_message("user"):
        st.markdown(userInput)

    # Call the ai to make a decision
    try:
        print("Sending first message...")
        #for msg in st.session_state.input_messages:
        #    print(msg)
        with st.chat_message("assistant"):
            st.markdown("Awaiting bot response...")
        response = st.session_state.agent.send_chat_message(st.session_state.input_messages)
        with st.chat_message("assistant"):
            st.markdown("Bot response received. Processing further...")
        print("got response.")

        #### ENTER FUNCTION CALLING LOOP ####
        function_calling = True
        while function_calling:
            ## Initialize the types of outputs to be collected
            reasoning = None
            tool_call = None
            message = None

            # Sort out and store the kinds of outputs in the response
            i = 0

            ## Store reasoning tool calls in history
            reasoning_tool_call = []
            function_tool_call = []
            message_call = []

            for tool_call in response.output:
                if tool_call.type == "reasoning":
                    reasoning_tool_call.append(tool_call)
                elif tool_call.type == "function_call":
                    function_tool_call.append(tool_call)
                elif tool_call.type == "message":
                    message_call.append(tool_call)
            
            # Append reasoning
            if function_tool_call and reasoning_tool_call:
                for r in reasoning_tool_call:
                    st.session_state.input_messages.append({
                        "type":               "reasoning",
                        "id":                  r.id,
                        "summary":             r.summary,
                        "encrypted_content":   r.encrypted_content,
                    })
                for fc in function_tool_call:
                    st.session_state.input_messages.append({
                        "type": "function_call",
                        "name": fc.name,
                        "call_id": fc.call_id,
                        "arguments": fc.arguments,
                        "id": fc.id,
                    })
            if function_tool_call and not reasoning_tool_call:
                for fc in function_tool_call:
                # Append function_call
                    st.session_state.input_messages.append({
                        "type": "function_call",
                        "name": fc.name,
                        "call_id": fc.call_id,
                        "arguments": fc.arguments,
                        "id": fc.id,
                    })

            # Function_call_output gets appended below.
            # Complete message is appended at the end of the loop. 

            # Render response immedietally if no function_call
            if not function_tool_call:
                print("No function call...")
                function_calling = False
                ######### BREAK OUT OF LOOP ########


            ######### IF FUNCTION CALL #########
            if function_tool_call:
                print("Got a tool call...")
                ######### STORE AS VARIABLES AND HISTORY #########
                # Parse apart response for name and args
                for tool_call in function_tool_call:
                    print(tool_call)
                    name = tool_call.name
                    _arg = tool_call.arguments
                    _arg = json.loads(_arg) # Now it's a dict

                    arg = None
                    if "query" in _arg:
                        arg = _arg.get("query") 
                        arg = arg.strip()
                    elif "table_id" in _arg:
                        arg = _arg.get("table_id")
                    elif "encoded_response" in _arg:
                        arg = _arg.get("encoded_response")
                                            # Now it's a string
                    print(f"Argument cleaned and parsed: {arg}") 

                    # Send to local model
                    print(f"Dispatching {name} with argument {arg}...")
                    sql_response = st.session_state.agent.dispatch(name, arg)

                    # Show arguments
                    if arg:
                        _arg_key = next(iter(_arg)) # gets just the first key from the dict object
                        st_arg = f":material/database: :small[{arg}]"
                        query_msg = _arg_key + " " + st_arg
                        with st.chat_message("Actions", avatar="🚀"):
                            st.markdown(query_msg)

                    # Check for anon output fist
                    if name == "template_response":
                        st.session_state.input_messages.append({
                            "type": "function_call_output",
                            "call_id": tool_call.call_id,
                            "output": "action complete; thank you!",
                        })
                        anon_response += sql_response
                        function_calling = False

                    else:   
                        st.session_state.input_messages.append({
                            "type": "function_call_output",
                            "call_id": tool_call.call_id,
                            "output": str(sql_response),
                        })

                #### SEND SQL RESULTS TO AGENT ######
                response = st.session_state.agent.send_chat_message(st.session_state.input_messages)
                # response will be checked for new content at top of loop again

        #### END OF FUNCTION CALLING LOOP ###
        print("End of func call loop")
        time.sleep(1)

        ## Collect the narrative response from the final output
        full_response = ""

        ## Check if final response was an anon format
        if anon_response:
            full_response += anon_response

        else:
            msg_found = False
            for item in response.output:
                if item.type == "message":
                    msg_found = True
                    full_response = item.content[0].text
                else:
                    full_response = str(item)
            if msg_found == False:
                st.error("A narrative message was not produced. Here is the last model output...")

        ## Store the narrative response in input_messages
        st.session_state.input_messages.append({"role": "assistant", "content": full_response,})
        st.session_state.chat_history.append({"role": "assistant", "content": full_response,})
        
        # Render a container and populate with text. 
        with st.chat_message("assistant"):
            st.markdown(full_response)

    ##### END OF TRY #######
    except Exception as e:
        print(e)
        error_message = f"""
        Something went wrong! We encountered an unexpected error while
        trying to process your request. Please try rephrasing your
        question. Details:

        {str(e)}"""
        st.error(error_message)
        # st.session_state.input_messages.append({
        #     "role": "assistant",
        #     "content": error_message,
        # })

    for item in st.session_state.input_messages:
        print(item)


