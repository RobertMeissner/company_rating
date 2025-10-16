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
from src.models.job_dict import JobDict
from src.utils.company_name_normalizer import normalized_company_name
from src.utils.logger import get_logger

logger = get_logger(__name__)


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

    def company(self, company_name: str) -> Company | None:
        for company in self.companies():
            if company_name == company.name:
                return company

            # more complicated, names could be similar, but need normalization
            seeking_names = normalized_company_name(name=company_name)
            current_names = normalized_company_name(company.name)

            if current_names == seeking_names:
                return company
        return None

    def companies_needing_scraping(self) -> list[Company]:
        return [c for c in self.companies() if c.kununu_rating is None]

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

        logger.debug(f"Before deduplication: {len(self.companies())} companies")
        logger.info(f"After deduplication: {len(deduplicated_companies)} companies")
        self.set_companies(deduplicated_companies)

    def deduplicate_jobs(self):
        initial_jobs = self.jobs()
        # dedup by job_id
        seen_ids = set()
        deduplicated_jobs = []
        for job in initial_jobs:
            if job.job_id not in seen_ids:
                seen_ids.add(job.job_id)
                deduplicated_jobs.append(job)

        intermediate_jobs = deduplicated_jobs

        # dedup by url
        seen_urls = set()
        deduplicated_jobs = []
        for job in intermediate_jobs:
            if job.url not in seen_urls:
                seen_urls.add(job.url)
                deduplicated_jobs.append(job)

        logger.debug(
            f"Jobs deduplication: {len(initial_jobs)} -> {len(deduplicated_jobs)}"
        )
        self.set_jobs(deduplicated_jobs)

    def create_missing_companies(self) -> None:
        """
        Create Company entries for companies in jobs that don't exist yet.

        Extracts unique company names from jobs and creates placeholder Company
        entries for any that aren't already in the companies list.
        """
        job_company_names = {
            job.company_name for job in self.jobs() if job.company_name
        }

        # Find missing companies
        missing_companies = []
        for company_name in job_company_names:
            if self.company(company_name.lower()) is None:
                # Create a new Company placeholder
                new_company = Company(
                    name=company_name,
                    location="",
                    kununu_rating=None,
                    glassdoor_rating=None,
                    scraper_identifiers={},
                )
                missing_companies.append(new_company)

        if missing_companies:
            logger.info(
                f"Creating {len(missing_companies)} new company entries from jobs"
            )
            updated_companies = self.companies() + missing_companies
            self.set_companies(updated_companies)
        else:
            logger.debug("No missing companies to create")

    def _scrape_company(self, company: Company) -> Company:
        """
        Rescrapes the company and merges with current one
        """
        updated_company: Company = asyncio.run(
            self._company_scraper_port.update(company)
        )

        return self._company_scraper_port.merge(
            existing=company, scraped=replace(updated_company, name=company.name)
        )

    def update(self, company: Company) -> Company:
        """
        Scrape a single company.

        Returns:
            The updated company with scraped data
        """
        scraped_company = self._scrape_company(company)
        company_map = {c.name: c for c in self.companies()}

        # Find existing company to get the correct key (handles name normalization)
        existing = self.company(company.name)
        if existing:
            # Update existing company using its exact name as the key
            company_map[existing.name] = scraped_company
        else:
            # Add new company if it doesn't exist
            company_map[company.name] = scraped_company

        self.set_companies(list(company_map.values()))
        self.write()
        return scraped_company

    def update_companies(self, companies: list[Company]) -> list[Company]:
        """
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
                logger.error(f"Error scraping {company.name}: {e}")
                updated_companies.append(company)  # Keep original if scraping fails

        return updated_companies

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
            merged = merged[~merged["company_name"].isin(self.company_blacklist())]
            merged = merged[~merged["job_id"].isin(self.job_blacklist())]

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
        self._company_blacklist_port.add(company_name)

    def remove_from_blacklist(self, company_name: str) -> None:
        self._company_blacklist_port.remove(company_name)

    def add_to_job_blacklist(self, job_id: str) -> None:
        self._job_blacklist_port.add(job_id)

    def remove_from_job_blacklist(self, job_id: str) -> None:
        self._job_blacklist_port.remove(job_id)
