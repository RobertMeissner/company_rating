from dataclasses import replace

import pandas as pd
import typer
from pandas.errors import EmptyDataError

from src.application.factories.default_orchestrator import default_orchestrator
from src.domain.value_objects.company import Company
from src.models.scraper_model import SCRAPERS
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
    orchestrator.create_missing_companies()  # Create companies from jobs
    orchestrator.write()


@app.command(name="export")
def export_companies_without_ratings() -> None:
    """
    Export companies without ratings with their scraper identifiers.
    """
    orchestrator = default_orchestrator()
    companies_without_ratings = [
        {
            "company_name": c.name,
            "kununu_name": c.scraper_identifiers.get(SCRAPERS.KUNUNU.value, ""),
            "glassdoor_name": c.scraper_identifiers.get(SCRAPERS.GLASSDOOR.value, ""),
        }
        for c in orchestrator.companies_needing_scraping()
    ]

    pd.DataFrame(companies_without_ratings).to_csv(
        COMPANIES_MISSING_RATING_FILENAME, index=False
    )
    typer.echo(f"Export done. Exported {len(companies_without_ratings)} companies.")


@app.command(name="import")
def import_companies():
    """Import companies with updated scraper identifiers"""

    orchestrator = default_orchestrator()

    try:
        df = pd.read_csv(COMPANIES_MISSING_RATING_FILENAME)
    except EmptyDataError:
        typer.echo("No missing companies found")
        return

    # Build a map of company name to scraper identifiers
    scraper_identifier_updates = {}
    for _, row in df.iterrows():
        company_name = row["company_name"]
        scraper_identifiers = {}

        # Add kununu name if provided and different from empty string
        if pd.notna(row.get("kununu_name")) and str(row["kununu_name"]).strip():
            scraper_identifiers[SCRAPERS.KUNUNU.value] = str(row["kununu_name"]).strip()

        # Add glassdoor name if provided and different from empty string
        if pd.notna(row.get("glassdoor_name")) and str(row["glassdoor_name"]).strip():
            scraper_identifiers[SCRAPERS.GLASSDOOR.value] = str(
                row["glassdoor_name"]
            ).strip()

        # Always add to updates map (even if empty scraper_identifiers)
        scraper_identifier_updates[company_name] = scraper_identifiers

    # Track which companies from CSV were found in existing companies
    existing_company_names = {c.name for c in orchestrator.companies()}
    companies_to_create = (
        set(scraper_identifier_updates.keys()) - existing_company_names
    )

    # Update existing companies
    updated_companies = []
    updated_count = 0
    for company in orchestrator.companies():
        if company.name in scraper_identifier_updates:
            # Merge existing scraper identifiers with new ones
            updated_identifiers = {
                **company.scraper_identifiers,
                **scraper_identifier_updates[company.name],
            }
            updated_company = replace(company, scraper_identifiers=updated_identifiers)
            updated_companies.append(updated_company)
            logger.info(
                f"Updated scraper identifiers for {company.name}: {scraper_identifier_updates[company.name]}"
            )
            updated_count += 1
        else:
            updated_companies.append(company)

    # Create new companies from CSV that don't exist yet
    created_count = 0
    for company_name in companies_to_create:
        new_company = Company(
            name=company_name,
            scraper_identifiers=scraper_identifier_updates[company_name],
        )
        updated_companies.append(new_company)
        logger.info(
            f"Created new company: {company_name} with identifiers {scraper_identifier_updates[company_name]}"
        )
        created_count += 1

    orchestrator.set_companies(updated_companies)
    orchestrator.write()
    typer.echo(
        f"Import done. Updated {updated_count} companies, created {created_count} new companies."
    )


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
    companies = orchestrator.update_companies(orchestrator.companies_needing_scraping())
    orchestrator.set_companies(companies)
    orchestrator.write()

    typer.echo("Rescrape done")


if __name__ == "__main__":
    app()
