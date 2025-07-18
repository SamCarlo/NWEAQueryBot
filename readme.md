# NWEAQueryBot
## An AI-agent chat bot to help teachers explore their school testing data.

### Features as of 6/24/25

### Main purpose
This chat bot allows school faculty to perform high- to mid-level data analyses instantly using natural language, saving hours of work each year of manually creating reports. 

###Background

NWEA is a ubiquitous 3rd party formative testing service for K-12 schools. It allows teachers to trends in student learning, check if they are on track with national standards, and get a long-term view of their attained knowledge across many years. 

###Motivation for this app

 While NWEA's web tool "MAP" provides many data dashboards for teachers to explore, exploration of the website requires training, forethought, and development of data analysis skill. This tool can take vague prompts like "What should I teach in my class this year?" and end with a highly specified set of curriculum goals based on an analysis of student learning, guiding the user along the way about how to make their data analysis goals more specific. 

## Features
### Create a SQLite3 database from downloaded .csv
The program processes raw data from NWEA-MAP's "data export" module and stores it on a fast and reliable SQLite database.

### Data anonymization
The database must be scrubbed of personal identifying information (PII) before allowing a generative ai to query it. The data processing pipeline copies, redacts, and encrypts the database. When the AI model searches the database, it only sees names as "REDACTED" and id's as encrypted hexidecimal values. 

