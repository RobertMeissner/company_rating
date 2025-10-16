"""
Company Scraper Manager - Orchestrates multiple scraping sources.

This manager enables:
1. Running multiple scrapers (Kununu, Glassdoor, etc.) for the same company
2. Merging results intelligently
3. Easy addition of new scrapers
4. Fallback strategies when one scraper fails
"""

import logging
from dataclasses import MISSING, asdict, fields
from typing import Callable

from src.domain.ports.company_scraper_port import CompanyScraperPort
from src.domain.value_objects.company import Company
from src.models.scraper_model import SCRAPERS
from src.utils.company_name_normalizer import normalized_company_name

logger = logging.getLogger(__name__)

SCRAPER_FACTORY_TYPE = dict[SCRAPERS : Callable[[], CompanyScraperPort]]


class CompanyScraperManager:
    """
    Manages multiple company scrapers and merges their results.

    - Accepts a list of scraper factory functions to be executed in sequence

    Example:
        manager = CompanyScraperManager([KununuScraper, GlassdoorScraper])
        async with manager as scraper:
            company = await scraper.update("SAP")
            # company now has both Kununu and Glassdoor data

    Implements CompanyScraperPort
    """

    def __init__(
        self,
        scraper_factories: SCRAPER_FACTORY_TYPE,
    ):
        """
        Initialize the scraper manager.

        Args:
            scraper_factories: dict of scraper factory functions (e.g., KununuScraper, GlassdoorScraper)
        """
        self.scraper_factories: SCRAPER_FACTORY_TYPE = scraper_factories

    async def update(self, current_company: Company) -> Company:
        """
        Scrape company from all configured scrapers and merge results.

        Args:
            :param current_company: company to (re)scrape

        Returns:
            Company object with merged data from all scrapers
        """
        results: dict[SCRAPERS:Company] = {}

        # Execute all scrapers with isolated browser contexts
        for scraper_type, factory in self.scraper_factories.items():
            try:
                # Use scraper-specific identifier if available, otherwise fall back to company name
                scraper_company_name = normalized_company_name(
                    current_company.scraper_identifiers.get(
                        scraper_type.value, current_company.name
                    )
                )

                logger.debug(f"Running {scraper_type} for {scraper_company_name}")

                async with factory() as scraper_instance:
                    result = await scraper_instance.update(scraper_company_name)
                    results.update({scraper_type: result})

                    logger.debug(
                        f"{scraper_type} completed: "
                        f"kununu={result.kununu_rating}, glassdoor={result.glassdoor_rating}"
                    )
            except Exception as e:
                logger.error(f"Error in {scraper_type} for {scraper_company_name}: {e}")

        return self._combined_scraper_results(current_company.name, results)

    async def get(self, company_name: str) -> Company:
        """Alias for update() to match CompanyScraper protocol."""
        return await self.update(company_name)

    @staticmethod
    def _is_meaningful_value(value) -> bool:
        return value not in (None, 0, "", [])

    def _combined_scraper_results(
        self, company_name: str, results: dict[SCRAPERS, Company]
    ) -> Company:
        """
        Merge strategy: Combine all non-empty fields from all scrapers.

        Priority: Later scrapers overwrite earlier ones for non-source-specific fields
        Source-specific fields (kununu_rating, glassdoor_rating) are preserved from their sources.

        Also captures scraped company names as alternative names for future scraping.
        """
        merged_dict: dict[str, str | dict[str, str]] = {"name": company_name}

        if results:

            for field in fields(Company):
                if field.name not in merged_dict:
                    if field.default_factory is not MISSING:  # has default_factory
                        merged_dict[field.name] = field.default_factory()
                    elif field.default is not MISSING:
                        merged_dict[field.name] = field.default
                    else:
                        merged_dict[field.name] = None

            # Collect scraped names for alternative_names
            scraped_names = []

            # Merge each scraper's results
            for scraper_name, company in results.items():
                company_dict = asdict(company)

                # Capture scraped name if different from provided name
                if company.name and company.name != company_name:
                    scraped_names.append(company.name)

                for field_name, value in company_dict.items():
                    # Always preserve the provided company name
                    if field_name == "name":
                        continue

                    # Skip empty values
                    if not self._is_meaningful_value(value):
                        continue

                    # For source-specific fields, only accept from the right source
                    if (
                        "kununu" in field_name.lower()
                        and SCRAPERS.KUNUNU != scraper_name
                    ) or (
                        "glassdoor" in field_name.lower()
                        and SCRAPERS.GLASSDOOR != scraper_name
                    ):
                        continue
                    merged_dict[field_name] = value

            kununu_name = (
                results[SCRAPERS.KUNUNU].name
                if SCRAPERS.KUNUNU in results
                else company_name
            )
            glassdoor_name = (
                results[SCRAPERS.GLASSDOOR].name
                if SCRAPERS.GLASSDOOR in results
                else company_name
            )
            merged_dict["scraper_identifiers"] = {
                SCRAPERS.KUNUNU.value: kununu_name,
                SCRAPERS.GLASSDOOR.value: glassdoor_name,
            }

        return Company(**merged_dict)

    def _merge_company_data(self, existing: Company, scraped: Company) -> Company:
        """
        Merge scraped company data with existing company data.
        Preserves non-empty fields from existing company when scraped fields are empty.
        Special handling for scraper_identifiers: merges both dicts, scraped overwrites existing.
        """
        # Build merged data field by field
        merged = {}
        for field in fields(Company):
            field_name = field.name
            scraped_value = getattr(scraped, field_name)
            if self._is_meaningful_value(scraped_value):
                merged[field_name] = scraped_value
            else:
                merged[field_name] = getattr(existing, field_name)

        merged["scraper_identifiers"] = {
            **existing.scraper_identifiers,
            **scraped.scraper_identifiers,
        }

        return Company(**merged)

    def merge(self, existing: Company, scraped: Company) -> Company:
        return self._merge_company_data(existing, scraped)
