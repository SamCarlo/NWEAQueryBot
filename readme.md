# NWEA Data Agent
## Branch: gpt-5.4-mini

### Description
Chat in natural language with our school's database, rather than spending hours creating new tables in excel for one-off analyses. 

This is a barebones, one-database version of the NWEA data agent employing a faster model than those available last year. 

NWEA Data Agent allows non-technical users to browse an anonymized student testing database of the most recent HAAS NWEA testing data. It uses Winter data because our school's second NWEA test is in February. Growth data reflect progress of about 21 weeks of instruction.

### Features
- Model: ChatGPT 5.4 Mini 
- The AI model accesses the database using SQLite3 language. 
- Under the hood, the AI can access four tools for data exploration: 
  -- **get_schema**: Read the names of all the tables and their various columns.
  -- **get_table_info**: Look into the data types contained by each column. 
  -- **sql_query**: Dig into the database using the SQLite language. 
  Therefore, there is very low chance of hallucination; the answers to user questions come directly from values in the NWEA score database. 
