import csv
from enum import Enum

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
from src.utils.settings import (
    COMPANIES_MISSING_RATING_FILENAME,
    COMPANY_BLACKLIST_FILENAME,
    JOB_BLACKLIST_FILENAME,
)


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
    orchestrator.filter_blacklisted_jobs()
    orchestrator.deduplicate_jobs()
    orchestrator.write()


def export_companies_without_ratings():
    orchestrator = job_orchestrator()
    companies_without_ratings = [
        {"company_name": c.name, "alternative_name": c.alternative_names}
        for c in orchestrator.companies()
        if (
            c.alternative_names
            and c.alternative_names[0] != "void"
            and c.kununu_rating is None
        )
        or (not c.alternative_names and c.kununu_rating is None)
    ]

    df = pd.DataFrame(companies_without_ratings)
    df.to_csv(COMPANIES_MISSING_RATING_FILENAME, index=False)


def import_alternative_names():
    from dataclasses import replace

    orchestrator = job_orchestrator()

    df = pd.read_csv(COMPANIES_MISSING_RATING_FILENAME)

    alternatives = {}
    for _, row in df.iterrows():
        if pd.notna(row["alternative_name"]) and row["alternative_name"].strip():
            alternatives[row["company_name"]] = row["alternative_name"].strip()

    # Update companies with alternative names
    updated_companies = []
    for company in orchestrator.companies():
        if company.name in alternatives:
            # Create new company with alternative name
            updated_company = replace(
                company, alternative_names=[alternatives[company.name]]
            )
            updated_companies.append(updated_company)
            print(f"Updated {company.name} -> {alternatives[company.name]}")
        else:
            updated_companies.append(company)

    orchestrator.set_companies(updated_companies)
    orchestrator.write()


def rescrape_companies():
    orchestrator = job_orchestrator()

    companies_to_scrape = [
        c
        for c in orchestrator.companies()
        if (
            c.alternative_names
            and c.alternative_names[0] != "void"
            and c.kununu_rating is None
        )
        or (not c.alternative_names and c.kununu_rating is None)
    ]

    if not companies_to_scrape:
        print("No companies with alternative names found")
        return

    # Temporarily set companies to only those we want to scrape
    all_companies = orchestrator.companies()
    orchestrator.set_companies(companies_to_scrape)
    orchestrator.update_companies()

    # Merge back updated companies
    updated_map = {c.name: c for c in orchestrator.companies()}
    orchestrator.set_companies([updated_map.get(c.name, c) for c in all_companies])

    orchestrator.write()


def rescrape_everything():
    orchestrator = job_orchestrator()
    orchestrator.update_companies()
    orchestrator.write()


class Tasks(Enum):
    DAILY = "daily"
    EXPORT = "export"
    IMPORT = "import"
    RESCRAPE = "rescrape"


if __name__ == "__main__":
    if False:
        bootstrap()
        connect_company_to_jobs()

    task = Tasks.DAILY

    match task:
        case Tasks.DAILY:
            daily_chore()
        case Tasks.EXPORT:
            export_companies_without_ratings()
        case Tasks.IMPORT:
            import_alternative_names()
            rescrape_companies()
        case Tasks.RESCRAPE:
            rescrape_everything()
