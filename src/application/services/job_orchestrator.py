import asyncio
from collections.abc import Callable
from dataclasses import asdict

import pandas as pd

from src.domain.entities.job import Job
from src.domain.ports.company_command_port import CompanyCommandPort
from src.domain.ports.company_query_port import CompanyQueryPort
from src.domain.ports.company_scraper_port import CompanyScraper
from src.domain.ports.job_command_port import JobCommandPort
from src.domain.ports.job_query_port import JobQueryPort
from src.domain.ports.job_scraper_port import JobScraper
from src.domain.value_objects.company import Company
from src.utils.settings import FILTERED_COMPANIES_FILENAME, FILTERED_JOBS_FILENAME


class JobOrchestrator:
    _companies: list[Company] = []
    _jobs: list[Job] = []

    def __init__(
        self,
        job_query_port: JobQueryPort,
        job_command_port: JobCommandPort,
        company_query_port: CompanyQueryPort,
        company_command_port: CompanyCommandPort,
        company_scraper: Callable[[], CompanyScraper],
        job_scraper_port: JobScraper,
    ):
        self._job_query_port = job_query_port
        self._job_command_port = job_command_port
        self._company_query_port = company_query_port
        self._company_command_port = company_command_port
        self._company_scraper_port = company_scraper
        self._job_scraper_port = job_scraper_port

    def jobs(self) -> list[Job]:
        if not self._jobs:
            self._jobs = self._job_query_port.get()
        return self._jobs

    def scrape_jobs(self) -> list[Job]:
        self._jobs = self._job_scraper_port.jobs()
        return self._jobs

    def companies(self) -> list[Company]:
        if not self._companies:
            self._companies = self._company_query_port.get()
        return self._companies

    def write(self):
        self._company_command_port.write(self.companies())
        self._job_command_port.write(self.jobs())

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
        df.to_csv(FILTERED_COMPANIES_FILENAME)
        df = pd.DataFrame([asdict(c) for c in self._jobs])
        df.to_csv(FILTERED_JOBS_FILENAME)
