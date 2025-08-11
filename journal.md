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
