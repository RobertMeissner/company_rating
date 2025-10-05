import csv

import pandas as pd

from src.kununu_scraper_poc import demo_scraping


def main():
    df = pd.read_csv("data/jobs.csv")
    df.rename(columns={"company": "company_name"}, inplace=True)
    companies = pd.read_csv("data/output.csv")

    print(df.head())
    print(companies.head())

    print(len(df))


    consolidated = pd.merge(df, companies, how="left", on="company_name")

    filtered_df = consolidated[["company_name", "rating","title", "job_url"]].drop_duplicates()
    print(filtered_df.head())
    null_ratings = filtered_df[filtered_df['rating'].isnull()]

    # Extract the 'company_rating' column values
    company_ratings = null_ratings['company_name'].drop_duplicates()

    # Write to a text file, one entry per line
    with open('data/null_ratings_output.txt', 'w') as f:
        for rating in company_ratings:
            f.write(f"{rating}\n")

    filtered_df.to_csv("data/filtered_jobs.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)





if __name__ == '__main__':
    main()
