import pandas as pd
from jobspy import scrape_jobs

from src.domain.entities.job import Job


class JobspyScraper:
    """

    Implements JobScraper

    """

    search_terms = [
        "AI Engineer",
        "Fullstack developer",
        "AI Developer",
        "AI Software Engineer",
    ]
    _jobs: list[Job] = []

    def jobs(self) -> list[Job]:
        if not self._jobs:
            found_jobs = []
            for search_term in self.search_terms:
                # not available in Europe: "zip_recruiter", bugs:  "bdjobs"
                for site in ["linkedin", "indeed"]:
                    print(f"Scraping {site}")
                    df_jobs = scrape_jobs(
                        site_name=site,
                        search_term=search_term,
                        google_search_term="AI engineer jobs near Münster, since last week",
                        location="Münster",
                        results_wanted=100,
                        hours_old=24 * 7,
                        country_indeed="germany",
                        linkedin_fetch_description=True,  # gets more info such as description, direct job url (slower)
                        # proxies=["208.195.175.46:65095", "208.195.175.45:65095", "localhost"],
                    )
                    print(f"Found {len(df_jobs)} jobs")
                    # print(jobs.head())

                    found_jobs.extend(
                        [
                            Job(
                                job_id=row.id,
                                url=(
                                    row.job_url_direct
                                    if hasattr(row, "job_url_direct")
                                    and pd.notna(row.job_url_direct)
                                    else row.job_url
                                ),
                                company_name=row.company,
                                title=row.title,
                                salary=0,
                                working_model="",
                            )
                            for row in df_jobs.itertuples()
                        ]
                    )
            self._jobs = found_jobs
        return self._jobs
