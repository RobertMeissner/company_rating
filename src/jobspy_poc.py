import csv

import pandas as pd
from jobspy import scrape_jobs, Site


def found_jobs() -> pd.DataFrame:
    df = pd.DataFrame()
    search_terms = ["AI Engineer", "Fullstack developer", "AI Developer", "AI Software Engineer"]
    for search_term in search_terms:
        for site in Site:
            print(f"Scraping {site.name}")
            if site.name != Site.BDJOBS.name: # site.name == Site.LINKEDIN.name: #
                jobs = scrape_jobs(
                    site_name=site.name,
                    # not available in Europe: "zip_recruiter", bugs:  "bdjobs"
                    search_term=search_term,
                    google_search_term="AI engineer jobs near Münster, since last month",
                    location="Münster",
                    results_wanted=100,
                    hours_old=24 * 60,
                    country_indeed='germany',
                    linkedin_fetch_description=True  # gets more info such as description, direct job url (slower)
                    # proxies=["208.195.175.46:65095", "208.195.175.45:65095", "localhost"],
                )
                print(f"Found {len(jobs)} jobs")
                # print(jobs.head())
                df = pd.concat([df, jobs])
                print(len(df))

    return df


if __name__ == '__main__':
    df = found_jobs()

    print(f"Found {len(df)} jobs")
    print(df.head())
    df.to_csv("jobs.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)
