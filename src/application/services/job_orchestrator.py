import asyncio
from collections.abc import Callable
from dataclasses import asdict

import pandas as pd

from src.domain.entities.job import Job
from src.domain.ports.blacklist_port import BlacklistPort
from src.domain.ports.company_command_port import CompanyCommandPort
from src.domain.ports.company_query_port import CompanyQueryPort
from src.domain.ports.company_scraper_port import CompanyScraper
from src.domain.ports.job_command_port import JobCommandPort
from src.domain.ports.job_query_port import JobQueryPort
from src.domain.ports.job_scraper_port import JobScraper
from src.domain.value_objects.company import Company
from src.models.job_dict import JobDict
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
            self._jobs = self._job_query_port.get()

        return self._jobs

    def scrape_jobs(self) -> list[Job]:
        self._jobs = self._job_scraper_port.jobs()
        return self._jobs

    def companies(self) -> list[Company]:
        if not self._companies:
            self._companies = self._company_query_port.get()
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
        deduplicated_jobs = []
        seen_ids = set()

        for job in self.jobs():
            if job.job_id not in seen_ids:
                seen_ids.add(job.job_id)
                deduplicated_jobs.append(job)

        print(
            f"Before #jobs: {len(self.jobs())}. After deduplication #jobs: {len(deduplicated_jobs)}"
        )
        self._jobs = deduplicated_jobs

    def filter_blacklisted_jobs(self):
        """Remove jobs that are in the blacklist"""
        blacklist = self.job_blacklist()
        if not blacklist:
            print("No jobs in blacklist, skipping filter")
            return

        before_count = len(self._jobs)
        self._jobs = [job for job in self._jobs if job.job_id not in blacklist]
        filtered_count = before_count - len(self._jobs)

        print(
            f"Filtered {filtered_count} blacklisted jobs. Remaining: {len(self._jobs)}"
        )

    async def _scrape(self, companies: list[Company]) -> list[Company]:

        updated_companies = []
        async with self._company_scraper_port() as scraper:
            for company in companies:
                # Prefer alternative name if available, otherwise use company name
                name_to_scrape = (
                    company.alternative_names[0]
                    if company.alternative_names
                    else company.name.replace(" ", "-")
                )
                updated_company = await scraper.update(name_to_scrape)
                print(updated_company)
                updated_companies.append(updated_company)
        return updated_companies

    def update_companies(self):
        self._companies = asyncio.run(self._scrape(self.companies()))

    def export_to_csv(self):
        df = pd.DataFrame([asdict(c) for c in self.companies()])
        df.to_csv(FILTERED_COMPANIES_FILENAME)
        df = pd.DataFrame([asdict(c) for c in self.jobs()])
        df.to_csv(FILTERED_JOBS_FILENAME)

    def get_jobs_dataframe(
        self, min_rating: float = 0.0, apply_blacklist: bool = True
    ) -> pd.DataFrame:
        self.deduplicate_jobs()
        jobs_df = pd.DataFrame(
            [
                asdict(
                    JobDict(
                        job_id=job.job_id,
                        url=job.url,
                        company_name=job.company_name,
                        working_model=job.working_model,
                        salary=job.salary,
                        title=job.title,
                    )
                )
                for job in self.jobs()
            ]
        )
        companies_df = pd.DataFrame([asdict(c) for c in self.companies()])

        if jobs_df.empty:
            return pd.DataFrame()

        merged = pd.merge(
            jobs_df,
            companies_df[
                [
                    "name",
                    "kununu_rating",
                    "kununu_review_count",
                    "glassdoor_rating",
                    "glassdoor_review_count",
                    "location",
                ]
            ],
            left_on="company_name",
            right_on="name",
            how="left",
        ).drop(
            "name", axis=1
        )  # Remove duplicate 'name' column

        if apply_blacklist:
            company_blacklist = self._blacklist(self._company_blacklist_port)
            if company_blacklist:
                merged = merged[~merged["company_name"].isin(company_blacklist)]

            job_blacklist = self._blacklist(self._job_blacklist_port)
            if job_blacklist:
                merged = merged[~merged["job_id"].isin(job_blacklist)]

        if min_rating > 0.0:
            merged = merged[
                (merged["kununu_rating"] >= min_rating)
                | (merged["kununu_rating"].isna())
            ]

        return merged

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
