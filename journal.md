# 8/10/25
- Start 10:00am
- Beginning of "aim domain" project
- Building additional functions to create downloadable reports for pay
- Reports: 
    -- Find learning gaps by grade through cluster analysis and write a learning plan
    -- Find teaching gaps among whole school, analyzed at subject-level and goal-level
- Necessary functions: 
    -- Cluster analysis
    -- Data across whole school year
    -- For teaching gaps: calculate conditional growth scaled by months of instruction
        -- Researching if this is possible...
        -- YES, just scale linearly by ((norm expected growth by 32 weeks) / 32) * (((Test date - Start of year) / 7) - # of weeks of break)
        -- Z = (observed growth - mean growth) / St Dev
        -- Edit data prep engine

- Trying to run streamlit from thumb drive... Done. 
- Goal: make button function for identifying learning gaps. Drop down menu by grade and subject. 
- first, make cluster analysis function in tools.py

- Added first attempt at cluster analysis function for growth
- Added pandas as requirements.txt for the cluster analysis
- Added sklearn to requirements.txt
- Error: numpy depricated version; ran pip install --upgrade scikit-learn
- Fixed dependency issue by removing and resetting the venv. Also caused an error with renaming the folder part way thru. 
- Got uploaded to github. 
- Added tabulate to requirements.txt; was needed for markdown line in cluster_test.

- Cluster test successful. Appending function to tools.py. Writing function declaration. 
- Push to main.
- End: 4:00pm with a couple of hours of break


# 8/13/25
Start 8:44am
- Chrystel just changed the number of weeks for conditional growth calculations from 32 to 26. Should make a difference. 
- In order to compare, it would be nice to create a "data selection" page on the streamlit--a page that appears before the chat agent. Or a data selection button that restarts the chat if manipulated. 
- For now, here are just some comparision tables... Downloaded to PastConversations
- Attempting to fix bug at line 217 of data prep engine: writing over a readonly db. 
-- Will need to do it later.. will require all functions to be re-written so that the sql connection isn't opened by the __init__ but by each function that uses it. 
-- Try: just deleting the old db's
End: 10:30am

# 8/15/25
Start 10:45am
- I am continuing to work on an individual teacher report. Cluster analysis was part of this idea. 
- Next: Create the basis for a method to give a teacher their relative "rank" among the school as measured by whole-subject RIT growth. 
- Associated functionality: Per Class Assignment (e.g. Kukui ELA) and Subject (Reading, Science, Math), calculate the average growth percentile within that subject for all students in that class. 
- UI: will appear as 4 menus: Class Assignment, Subject, and School Year.  Season calculated will default to Spring because it will be based on Fall->Spring conditional growth. 
- First task: try to create a table of: Class Assignment (teachers table) | Subject | Conditional Growth Percentile
- First error: my DataPrepEngine Redacts but does not hash teacher names. Not a priority, but will have to fix eventually. 
- End 11:22a
- Start 2:40p
- Fixing teacher hash error....
  - Changed merge_hashed_teacher_names, set "TeacherID" -> now is "TeacherName"
  - Commented out the part o redact_db() that sets TeacherName to REDACTED
  - Run test: ERROR: 'sql_response' referenced before assignment. I fixed this before by setting sql_response to none in  queryagent.py. 
  - Added try / except with traceback in the exception within the dispatch()method in queryagent.py. This showed that the error is actually in tools.py at line 160, which is inside of get_schema: "if sql_response is None". THis is a reference before assignment. So, I added a sql_response = None before the meat of the method. 
  - The error was not syntax, though sloppy syntax made it harder to find. The real error was that the anon.db file in the working directory was 1byte for some reason. I re-copied and pasted the .db files from my temporary desktop folder that I used to run the new DataPrepEngine and now it works. 
  - New error: in template_response: "not enough values to unpack (expected 2, got 1)"
  - Fixed by re-writing the whole template_response function. Added notes as comments based on learning. Biggest thing that will take more practice is regex objects. Method to loop over re.Match iterator is clever and I want it to be intuitive in the future. But no need to commit to heart now. 
  - Updating tools for new template_response method...Done and uploaded. 
  - Still has errors in template response behavior. Test and try to fix later. 
  - End: 6:45pm
  - 
- Start 8:15pm
- Try to fix the template response... fixed... maybe. Had been updating the name variables incorrectly in template_response. 
- UPdating changes to tools.py.
- Fixed 'last, first' in teacher names in template_response.
- Fixed tuple parsing error in template_response. 
- Fixed ugly backend printing -> clean sql now. 
Stop 9:00pm

# 8/16/25
- Start 7:15am
- Created tables to give overview of calculated subject area growth within a single school year, and grouped by Class (TeacherID). Made them for all grades. 
- Grouping by teacher ID will be the basis of creating whole-school and teacher reports. 
- End 8:30am

# 4/10/26
- Start 8:00pm
- We are back baby
- Two and a half semesters of classes have changed my perspective on OOP. 
- My old data prep engine is so silly. 
- new goal: follow "Do one thing well" principle in all levels.
- Created new branch docker-redesign.
- Wrote dataPrepLite.py, which reduces the engine from over 300 lines to under 60!
- Goal is to make a simpler chatbot that does not do reverse lookup; just does really fast data analysis. Be able to ask questions like: "How did reading growth stack up across grades this year?"
- End 11:28pm

# 4/11/26
- Start 9:30pm
- Edited data prep lite: now removes PII and illegible ethnicity column. 
- Cleaned up printout. 
- Claude coded explorer.py, a dope TUI to explore NWEA data. 
- End 11:19pm
