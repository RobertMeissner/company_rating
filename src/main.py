from dataclasses import replace

import pandas as pd
import typer

from src.application.factories.default_orchestrator import default_orchestrator
from src.utils.settings import (
    COMPANIES_MISSING_RATING_FILENAME,
)

app = typer.Typer()


@app.command(name="daily")
def daily_chore():
    """
    Daily scrape of jobs.
    """
    orchestrator = default_orchestrator()
    orchestrator.scrape_jobs()
    orchestrator.filter_blacklisted_jobs()
    orchestrator.deduplicate_jobs()
    orchestrator.write()


@app.command(name="export")
def export_companies_without_ratings():
    """
    Export companies without ratings.
    """
    orchestrator = default_orchestrator()
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


@app.command(name="import")
def import_companies():
    """Import companies and add them to the system"""

    orchestrator = default_orchestrator()

    df = pd.read_csv(COMPANIES_MISSING_RATING_FILENAME)

    alternatives = {}
    for _, row in df.iterrows():
        if pd.notna(row["alternative_name"]) and row["alternative_name"].strip():
            alternatives[row["company_name"]] = row["alternative_name"].strip()

    updated_companies = []
    for company in orchestrator.companies():
        if company.name in alternatives:
            updated_company = replace(
                company, alternative_names=[alternatives[company.name]]
            )
            updated_companies.append(updated_company)
            print(f"Updated {company.name} -> {alternatives[company.name]}")
        else:
            updated_companies.append(company)

    orchestrator.set_companies(updated_companies)
    orchestrator.write()


@app.command(name="rescrape")
def rescrape_companies():
    """
    Rescrape companies without ratings
    """
    orchestrator = default_orchestrator()

    companies_to_scrape = [
        c for c in orchestrator.companies() if c.kununu_rating is None
    ]

    if companies_to_scrape:
        orchestrator.update_companies_incremental(
            companies_to_scrape, show_progress=True
        )
    else:
        print("No companies to scrape")

    # orchestrator.write()


if __name__ == "__main__":
    app()
