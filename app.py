## app.py
## Streamlit chat UI for the HAAS NWEA Data Agent.

import streamlit as st
import queryagent

st.title("NWEA Data Agent")

if "history" not in st.session_state:
    st.session_state.history = []
if "messages" not in st.session_state:
    # Each entry: {role, content, sql_queries}
    st.session_state.messages = []

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
