import pandas as pd
import sqlite3
import config
from sklearn.cluster import KMeans

# param sql_query: a query that returns table of studentID | Subject | Course | goalAreaGrowth
def growth_clusters(sql_query: str):
    secret_conn = sqlite3.connect(config.anon_db_path)
    secret_cursor = secret_conn.cursor()
    secret_cursor.execute(sql_query)
    rows = secret_cursor.fetchall()
    for r in range(5):
        print(rows[r])
    # Get column names
    columns = [desc[0] for desc in secret_cursor.description]

    # Create dataframe
    df = pd.DataFrame(rows, columns=columns)

    # Select cols for cluster analysis
    growth_cols = df.filter(like='growth').columns
    print(f"growth cols = {growth_cols}")
    X = df[growth_cols]

    # Drop rows with any NaN in clustering columns
    mask = X.notna().all(axis=1)
    X = X[mask]
    df_clean = df[mask].copy()

    # DEBUG
    print("X shape:", X.shape)
    print("X head:\n", X.head())

    # Perform k-means cluster analysis
    kmeans = KMeans(n_clusters=3, random_state=42)
    df_clean['cluster'] = kmeans.fit_predict(X)

    # Return cluster table as a string
    if 'StudentID' in df_clean.columns:
        df_clean['StudentID'] = df_clean['StudentID'].astype(str)

    df_text = df_clean.to_markdown(index=False)
    df_text = df_clean.to_markdown(index=False)
    return df_text


def main():
    QUERY = """
        SELECT
      f."StudentID",
      (s."Goal1RitScore" - f."Goal1RitScore") AS growth_Goal1,
      (s."Goal2RitScore" - f."Goal2RitScore") AS growth_Goal2,
      (s."Goal3RitScore" - f."Goal3RitScore") AS growth_Goal3,
      (s."Goal4RitScore" - f."Goal4RitScore") AS growth_Goal4
    FROM "f_results" AS f
    JOIN "s_results" AS s
      ON f."DistrictName" = s."DistrictName"
      AND f."SchoolName"   = s."SchoolName"
      AND f."StudentID"    = s."StudentID"
      AND f."Subject"      = s."Subject"
    WHERE f."Subject" = 'Mathematics';"""
    output = growth_clusters(QUERY)

    print(output)

if __name__ == "__main__":
    main()