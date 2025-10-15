from dataclasses import replace

import pandas as pd
import typer

from src.application.factories.default_orchestrator import default_orchestrator
from src.utils.logger import get_logger
from src.utils.settings import (
    COMPANIES_MISSING_RATING_FILENAME,
)

logger = get_logger(__name__)

app = typer.Typer()


@app.command(name="daily")
def daily_chore():
    """
    Daily scrape of jobs.
    """
    orchestrator = default_orchestrator()
    orchestrator.scrape_jobs()
    orchestrator.deduplicate_jobs()
    orchestrator.write()


@app.command(name="export")
def export_companies_without_ratings() -> None:
    """
    Export companies without ratings.
    """
    orchestrator = default_orchestrator()
    companies_without_ratings = [
        {"company_name": c.name, "alternative_name": c.alternative_names}
        for c in orchestrator.companies_needing_scraping()
    ]

    pd.DataFrame(companies_without_ratings).to_csv(
        COMPANIES_MISSING_RATING_FILENAME, index=False
    )
    typer.echo("Export done")


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
            logger.info(f"Updated {company.name} -> {alternatives[company.name]}")
        else:
            updated_companies.append(company)

    orchestrator.set_companies(updated_companies)
    orchestrator.write()
    typer.echo("Import done")


@app.command(name="rescrape")
def rescrape_company(name: str) -> None:
    """
    Rescrape one company
    """
    orchestrator = default_orchestrator()

    company = orchestrator.company(name)
    if company:
        orchestrator.update(company)
        typer.echo(f"Rescraping {name} done.")
    else:
        typer.echo(f"Rescraping {name} failed. Company not found.")


@app.command(name="rescrape_all")
def rescrape_companies():
    """
    Rescrape companies without ratings
    """
    orchestrator = default_orchestrator()

    orchestrator.update_companies_incremental(
        [c for c in orchestrator.companies_needing_scraping()]
    )

    typer.echo("Rescrape done")


if __name__ == "__main__":
    app()
