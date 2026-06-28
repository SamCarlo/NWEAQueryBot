## app.py
## Streamlit chat UI for the HAAS NWEA Data Agent.

import streamlit as st
import queryagent

# Title 
st.title("NWEA Data Agent")

if "history" not in st.session_state:
    st.session_state.history = []
if "messages" not in st.session_state:
    # Each entry: {role, content, sql_queries}
    st.session_state.messages = []

# Instructions
st.info("""
### Welcome to the HAAS NWEA Testing Data Query App.
This is a tool to explore anonymous school testing data in plain English. 

**Current database: Winter SY 2025-2026**
**Last software update: 6/27/26**

Here are some starting prompts that you can copy/paste into the chat box to see it in action:
- What are the most vulnerable demographics between grades 6-10 in math? 
- Are there any sub-areas within Reading that are consistently low across all grades? 
- What are the academic strengths of each grade level? """,
        icon="💫")

# Render existing chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        for query in msg.get("sql_queries", []):
            st.code(query, language="sql")
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask about the data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        sql_queries = []
        response_text = None
        for event_type, content in queryagent.run(prompt, st.session_state.history):
            if event_type == "sql":
                st.code(content, language="sql")
                sql_queries.append(content)
            elif event_type == "response":
                response_text = content
                st.markdown(content)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "sql_queries": sql_queries,
    })
