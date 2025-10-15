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

logger = logging.getLogger(__name__)


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
        scraper_factories: list[Callable[[], CompanyScraperPort]],
    ):
        """
        Initialize the scraper manager.

        Args:
            scraper_factories: List of scraper factory functions (e.g., [KununuScraper, GlassdoorScraper])
        """
        self.scraper_factories = scraper_factories
        self.scrapers = []
        self.context_managers = []

    async def __aenter__(self):
        for factory in self.scraper_factories:
            scraper = factory()
            cm = await scraper.__aenter__()
            self.scrapers.append(cm)
            self.context_managers.append(scraper)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for cm in self.context_managers:
            await cm.__aexit__(exc_type, exc_val, exc_tb)

    async def update(self, company_name: str) -> Company:
        """
        Scrape company from all configured scrapers and merge results.

        Args:
            company_name: Name of company to scrape

        Returns:
            Company object with merged data from all scrapers
        """
        results = []

        # Execute all scrapers
        for i, scraper in enumerate(self.scrapers):
            scraper_name = self.scraper_factories[i].__name__
            try:
                logger.debug(f"Running {scraper_name} for {company_name}")
                result = await scraper.update(company_name)
                results.append((scraper_name, result))
                logger.debug(
                    f"{scraper_name} completed: "
                    f"kununu={result.kununu_rating}, glassdoor={result.glassdoor_rating}"
                )
            except Exception as e:
                logger.error(f"Error in {scraper_name} for {company_name}: {e}")

        if not results:
            logger.warning(f"No scrapers succeeded for {company_name}")
            return Company(name=company_name)
        return self._combined_scraper_results(company_name, results)

    async def get(self, company_name: str) -> Company:
        """Alias for update() to match CompanyScraper protocol."""
        return await self.update(company_name)

    @staticmethod
    def _is_meaningful_value(value) -> bool:
        return value not in (None, 0, "", [])

    def _combined_scraper_results(
        self, company_name: str, results: list[tuple[str, Company]]
    ) -> Company:
        """
        Merge strategy: Combine all non-empty fields from all scrapers.

        Priority: Later scrapers overwrite earlier ones for non-source-specific fields
        Source-specific fields (kununu_rating, glassdoor_rating) are preserved from their sources.

        Also captures scraped company names as alternative names for future scraping.
        """
        merged_dict = {"name": company_name}

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
        for scraper_name, company in results:
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
                    and "kununu" not in scraper_name.lower()
                ):
                    continue
                if (
                    "glassdoor" in field_name.lower()
                    and "glassdoor" not in scraper_name.lower()
                ):
                    continue

                # Use the value (later scrapers overwrite for non-source-specific fields)
                merged_dict[field_name] = value

        # Add scraped names to alternative_names (avoiding duplicates)
        existing_alternatives = merged_dict.get("alternative_names", []) or []
        for scraped_name in scraped_names:
            if (
                scraped_name not in existing_alternatives
                and scraped_name != company_name
            ):
                existing_alternatives.append(scraped_name)

        if existing_alternatives:
            merged_dict["alternative_names"] = existing_alternatives

        return Company(**merged_dict)

    def _merge_company_data(self, existing: Company, scraped: Company) -> Company:
        """
        Merge scraped company data with existing company data.
        Preserves non-empty fields from existing company when scraped fields are empty.
        Special handling for alternative_names: combines both lists instead of replacing.
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

        # Merge alternative_names: combine and deduplicate while preserving order
        merged["alternative_names"] = list(
            dict.fromkeys(scraped.alternative_names + existing.alternative_names)
        )

        return Company(**merged)

    def merge(self, existing: Company, scraped: Company) -> Company:
        return self._merge_company_data(existing, scraped)
