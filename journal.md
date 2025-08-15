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
