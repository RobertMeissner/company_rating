import asyncio
from dataclasses import asdict, replace

import pandas as pd
from tqdm import tqdm

from src.domain.entities.job import Job
from src.domain.ports.blacklist_port import BlacklistPort
from src.domain.ports.company_command_port import CompanyCommandPort
from src.domain.ports.company_query_port import CompanyQueryPort
from src.domain.ports.company_scraper_port import CompanyScraperPort
from src.domain.ports.job_command_port import JobCommandPort
from src.domain.ports.job_query_port import JobQueryPort
from src.domain.ports.job_scraper_port import JobScraper
from src.domain.value_objects.company import Company
from src.utils.company_name_normalizer import normalized_company_name
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
        company_scraper: CompanyScraperPort,
        job_scraper_port: JobScraper,
        company_blacklist_port: BlacklistPort,
        job_blacklist_port: BlacklistPort,
    ):
        self._job_query_port = job_query_port
        self._job_command_port = job_command_port
        self._company_query_port = company_query_port
        self._company_command_port = company_command_port
        self._company_scraper_port = company_scraper
        self._job_scraper_port = job_scraper_port
        self._company_blacklist_port = company_blacklist_port
        self._job_blacklist_port = job_blacklist_port

    def jobs(self) -> list[Job]:
        if not self._jobs:
            self.set_jobs(self._job_query_port.get())
        return self._jobs

    def set_jobs(self, jobs: list[Job]):
        self._jobs = jobs

    def scrape_jobs(self) -> None:
        self.set_jobs(self._job_scraper_port.jobs())

    def companies(self) -> list[Company]:
        if not self._companies:
            self.set_companies(self._company_query_port.get())
        return self._companies

    def set_companies(self, companies: list[Company]):
        self._companies = companies

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

    def deduplicate_jobs(self):

        # dedup by job_id
        seen_ids = set()
        deduplicated_jobs = []
        for job in self.jobs():
            if job.job_id not in seen_ids:
                seen_ids.add(job.job_id)
                deduplicated_jobs.append(job)

        print(
            f"Before #jobs: {len(self.jobs())}. After dedup id's #jobs: {len(deduplicated_jobs)}"
        )
        self._jobs = deduplicated_jobs

        # dedup by url
        seen_urls = set()
        deduplicated_jobs = []
        for job in self._jobs:
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                deduplicated_jobs.append(job)

        print(
            f"Before #jobs: {len(self.jobs())}. After dedup url's #jobs: {len(deduplicated_jobs)}"
        )
        self._jobs = deduplicated_jobs

    def filter_blacklisted_jobs(self):
        """Remove jobs that are in the blacklist"""
        before_count = len(self._jobs)
        if blacklist := self.job_blacklist():
            self.set_jobs([job for job in self._jobs if job.job_id not in blacklist])
        print(
            f"Filtered {before_count - len(self._jobs)} blacklisted jobs. Remaining: {len(self._jobs)}"
        )

    async def _scrape_company(self, company: Company) -> Company:
        """
        Returns the first successful result with a rating.
        """
        async with self._company_scraper_port as scraper:
            updated_company = None

            # Try each name variation until we get a rating
            for name_to_scrape in normalized_company_name(company):
                result: Company = await scraper.update(name_to_scrape)

                rating = result.kununu_rating or result.glassdoor_rating
                if rating and rating > 0:
                    updated_company = replace(
                        result, alternative_names=[name_to_scrape]
                    )
                    break

                # Keep the last one, if nothing else is found
                updated_company = result

            return replace(updated_company, name=company.name)

    def update(self, company: Company) -> None:
        """
        Scrape a single company.
        """
        scraped_data = asyncio.run(self._scrape_company(company))

        merged_company = self._company_scraper_port._merge_company_data(
            company, scraped_data
        )
        company_map = {c.name: c for c in self.companies()}
        company_map[company.name] = merged_company
        self.set_companies(list(company_map.values()))

        self.write()

    def update_companies_incremental(self, companies: list[Company]) -> list[Company]:
        """
        Update multiple companies one at a time with immediate persistence.

        Args:
            companies: List of companies to scrape

        Returns:
            List of updated companies
        """
        updated_companies = []

        pbar = tqdm(companies, desc="Scraping companies", unit="company")
        for company in pbar:
            try:
                updated = self.update(company)
                updated_companies.append(updated)

                pbar.set_postfix_str(
                    f"Last: {company.name[:30]}... "
                    f"Rating: {updated.kununu_rating or 'N/A'}"
                )
            except Exception as e:
                print(f"Error scraping {company.name}: {e}")
                updated_companies.append(company)  # Keep original if scraping fails

        return updated_companies

    def export_to_csv(self):
        df = pd.DataFrame([asdict(c) for c in self.companies()])
        df.to_csv(FILTERED_COMPANIES_FILENAME)
        df = pd.DataFrame([asdict(c) for c in self.jobs()])
        df.to_csv(FILTERED_JOBS_FILENAME)

    def company_blacklist(self):
        return self._blacklist(self._company_blacklist_port)

    def job_blacklist(self):
        return self._blacklist(self._job_blacklist_port)

    def write_company_blacklist(self):
        self._company_blacklist_port.write(self.company_blacklist())

    def write_job_blacklist(self):
        self._job_blacklist_port.write(self.job_blacklist())

    def _blacklist(self, port: BlacklistPort) -> list[str]:
        return port.get()

    def add_to_blacklist(self, company_name: str) -> None:
        if self._company_blacklist_port:
            self._company_blacklist_port.add(company_name)

    def remove_from_blacklist(self, company_name: str) -> None:
        if self._company_blacklist_port:
            self._company_blacklist_port.remove(company_name)

    def add_to_job_blacklist(self, job_id: str) -> None:
        if self._job_blacklist_port:
            self._job_blacklist_port.add(job_id)

    def remove_from_job_blacklist(self, job_id: str) -> None:
        if self._job_blacklist_port:
            self._job_blacklist_port.remove(job_id)
