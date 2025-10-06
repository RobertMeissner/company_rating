import csv

import pandas as pd

from src.application.services.job_orchestrator import JobOrchestrator
from src.infrastructure.adapters.company_command_file_based import (
    CompanyCommandFileBasedAdapter,
)
from src.infrastructure.adapters.company_query_file_based import (
    CompanyQueryFileBasedAdapter,
)
from src.infrastructure.adapters.job_query_file_based import JobQueryFileBasedAdapter
from src.infrastructure.scrapers.kununu_scraper import KununuScraper


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


def main():
    job_query_adapter = JobQueryFileBasedAdapter()
    company_query_adapter = CompanyQueryFileBasedAdapter()
    company_command_adapter = CompanyCommandFileBasedAdapter()
    kununu_scraper = KununuScraper
    orchestrator = JobOrchestrator(
        job_query_port=job_query_adapter,
        company_query_port=company_query_adapter,
        company_command_port=company_command_adapter,
        company_scraper=kununu_scraper,
    )
    print([job.title for job in orchestrator.jobs()])
    print(
        len(orchestrator.companies()),
        ":",
        [job.name for job in orchestrator.companies()],
    )
    orchestrator.sort_companies()
    orchestrator.deduplicate_companies()

    orchestrator.write()
    orchestrator.export_to_csv()

    orchestrator.update_companies()
    orchestrator.write()
    orchestrator.export_to_csv()


if __name__ == "__main__":
    main()
