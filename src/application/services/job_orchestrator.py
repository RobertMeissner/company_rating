import asyncio
from collections.abc import Callable
from dataclasses import asdict

import pandas as pd

from src.domain.entities.job import Job
from src.domain.ports.company_command_port import CompanyCommandPort
from src.domain.ports.company_query_port import CompanyQueryPort
from src.domain.ports.company_scraper_port import CompanyScraper
from src.domain.ports.job_query_port import JobQueryPort
from src.domain.value_objects.company import Company
from src.utils.settings import FILTERED_JOBS_FILENAME


class JobOrchestrator:
    _companies: list[Company] = []

    def __init__(
        self,
        job_query_port: JobQueryPort,
        company_query_port: CompanyQueryPort,
        company_command_port: CompanyCommandPort,
        company_scraper: Callable[[], CompanyScraper],
    ):
        self._job_query_port = job_query_port
        self._company_query_port = company_query_port
        self._company_command_port = company_command_port
        self._company_scraper_port = company_scraper

    def jobs(self) -> list[Job]:
        return self._job_query_port.get()

    def companies(self) -> list[Company]:
        if not self._companies:
            self._companies = self._company_query_port.get()
        return self._companies

    def write(self):
        self._company_command_port.write(self.companies())

    def sort_companies(self):
        self._companies.sort(key=lambda c: c.name.lower())

    def deduplicate_companies(self):
        deduplicated_companies = []
        seen_names = set()

        for company in self.companies():
            name_key = company.name.lower()

            if name_key not in seen_names:
                seen_names.add(name_key)
                deduplicated_companies.append(company)

        print(f"Before #companies: {len(self.companies())}")
        print(f"After deduplication #companies: {len(deduplicated_companies)}")
        self._companies = deduplicated_companies

    async def _scrape(self, companies: list[Company]) -> list[Company]:

        updated_companies = []
        async with self._company_scraper_port() as scraper:
            for company in companies:
                updated_company = await scraper.update(company.name)
                print(updated_company)
                updated_companies.append(updated_company)
        return updated_companies

    def update_companies(self):
        self._companies = asyncio.run(self._scrape(self.companies()))

    def export_to_csv(self):
        df = pd.DataFrame([asdict(c) for c in self._companies])
        df.to_csv(FILTERED_JOBS_FILENAME)
