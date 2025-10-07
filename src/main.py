import csv

import pandas as pd

from src.application.services.job_orchestrator import JobOrchestrator
from src.infrastructure.adapters.blacklist_file_based import (
    BlacklistFileBasedAdapter,
)
from src.infrastructure.adapters.company_command_file_based import (
    CompanyCommandFileBasedAdapter,
)
from src.infrastructure.adapters.company_query_file_based import (
    CompanyQueryFileBasedAdapter,
)
from src.infrastructure.adapters.job_command_file_based import (
    JobCommandFileBasedAdapter,
)
from src.infrastructure.adapters.job_query_file_based import JobQueryFileBasedAdapter
from src.infrastructure.scrapers.jobspy_scraper import JobspyScraper
from src.infrastructure.scrapers.kununu_scraper import KununuScraper
from src.utils.settings import COMPANY_BLACKLIST_FILENAME, JOB_BLACKLIST_FILENAME


def outdated_main():
    df = pd.read_csv("data/jobs.csv")
    df.rename(columns={"company": "company_name"}, inplace=True)
    companies = pd.read_csv("data/output.csv")

    print(df.head())
    print(companies.head())

    print(len(df))

    consolidated = pd.merge(df, companies, how="left", on="company_name")

    filtered_df = consolidated[
        ["company_name", "rating", "title", "job_url"]
    ].drop_duplicates()
    print(filtered_df.head())
    null_ratings = filtered_df[filtered_df["rating"].isnull()]

    # Extract the 'company_rating' column values
    company_ratings = null_ratings["company_name"].drop_duplicates()

    # Write to a text file, one entry per line
    with open("data/null_ratings_output.txt", "w") as f:
        for rating in company_ratings:
            f.write(f"{rating}\n")

    filtered_df.to_csv(
        "data/filtered_jobs.csv",
        quoting=csv.QUOTE_NONNUMERIC,
        escapechar="\\",
        index=False,
    )


def bootstrap():
    orchestrator = job_orchestrator()
    print([job.title for job in orchestrator.jobs()])
    print(
        len(orchestrator.companies()),
        ":",
        [job.name for job in orchestrator.companies()],
    )
    orchestrator.sort_companies()
    orchestrator.deduplicate_companies()

    # orchestrator.write()
    # orchestrator.export_to_csv()

    # orchestrator.update_companies()
    # orchestrator.write()
    # orchestrator.export_to_csv()

    print([job.title for job in orchestrator.jobs()])
    orchestrator.scrape_jobs()
    print([job.title for job in orchestrator.jobs()])
    orchestrator.write()


def job_orchestrator():
    job_query_adapter = JobQueryFileBasedAdapter()
    job_command_adapter = JobCommandFileBasedAdapter()
    company_query_adapter = CompanyQueryFileBasedAdapter()
    company_command_adapter = CompanyCommandFileBasedAdapter()
    company_blacklist_adapter = BlacklistFileBasedAdapter(COMPANY_BLACKLIST_FILENAME)
    job_blacklist_adapter = BlacklistFileBasedAdapter(JOB_BLACKLIST_FILENAME)
    kununu_scraper = KununuScraper
    job_scraper_adapter = JobspyScraper()
    orchestrator = JobOrchestrator(
        job_query_port=job_query_adapter,
        job_command_port=job_command_adapter,
        company_query_port=company_query_adapter,
        company_command_port=company_command_adapter,
        company_scraper=kununu_scraper,
        job_scraper_port=job_scraper_adapter,
        company_blacklist_port=company_blacklist_adapter,
        job_blacklist_port=job_blacklist_adapter,
    )
    return orchestrator


def connect_company_to_jobs():
    orchestrator = job_orchestrator()
    df = orchestrator.get_jobs_dataframe()
    print(df.head())


def daily_chore():
    orchestrator = job_orchestrator()
    orchestrator.scrape_jobs()
    orchestrator.deduplicate_jobs()
    orchestrator.write()


if __name__ == "__main__":
    if False:
        bootstrap()
        connect_company_to_jobs()
    daily_chore()
