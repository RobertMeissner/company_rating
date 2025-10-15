import pandas as pd
from jobspy import scrape_jobs
from tqdm import tqdm

from src.domain.entities.job import Job
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JobspyScraper:
    """
    JobSpy scraper implementation with comprehensive data extraction.

    Extracts: salary, location, remote info, job details, company info, skills, etc.
    """

    search_terms = [
        "AI Engineer",
        "Fullstack developer",
        "AI Developer",
        "AI Software Engineer",
    ]
    _jobs: list[Job] = []

    @staticmethod
    def _job_from_row(row: tuple) -> Job:
        return Job(
            job_id=row.id,
            url=(
                row.job_url_direct
                if hasattr(row, "job_url_direct") and pd.notna(row.job_url_direct)
                else row.job_url
            ),
            company_name=row.company,
            title=row.title,
            # Salary information
            salary_min=(
                float(row.min_amount)
                if hasattr(row, "min_amount") and pd.notna(row.min_amount)
                else None
            ),
            salary_max=(
                float(row.max_amount)
                if hasattr(row, "max_amount") and pd.notna(row.max_amount)
                else None
            ),
            salary_currency=(
                row.currency
                if hasattr(row, "currency") and pd.notna(row.currency)
                else None
            ),
            salary_interval=(
                row.interval
                if hasattr(row, "interval") and pd.notna(row.interval)
                else None
            ),
            # Location and remote
            location=(
                row.location
                if hasattr(row, "location") and pd.notna(row.location)
                else None
            ),
            is_remote=(
                bool(row.is_remote)
                if hasattr(row, "is_remote") and pd.notna(row.is_remote)
                else None
            ),
            work_from_home_type=(
                row.work_from_home_type
                if hasattr(row, "work_from_home_type")
                and pd.notna(row.work_from_home_type)
                else None
            ),
            # Job details
            job_type=(
                row.job_type
                if hasattr(row, "job_type") and pd.notna(row.job_type)
                else None
            ),
            job_level=(
                row.job_level
                if hasattr(row, "job_level") and pd.notna(row.job_level)
                else None
            ),
            job_function=(
                row.job_function
                if hasattr(row, "job_function") and pd.notna(row.job_function)
                else None
            ),
            date_posted=(
                pd.to_datetime(row.date_posted)
                if hasattr(row, "date_posted") and pd.notna(row.date_posted)
                else None
            ),
            description=(
                row.description
                if hasattr(row, "description") and pd.notna(row.description)
                else None
            ),
            skills=(
                (
                    row.skills.split(",")
                    if isinstance(row.skills, str)
                    else list(row.skills)
                )
                if hasattr(row, "skills") and pd.notna(row.skills)
                else None
            ),
            # Company information
            company_industry=(
                row.company_industry
                if hasattr(row, "company_industry") and pd.notna(row.company_industry)
                else None
            ),
            company_num_employees=(
                row.company_num_employees
                if hasattr(row, "company_num_employees")
                and pd.notna(row.company_num_employees)
                else None
            ),
            company_revenue=(
                row.company_revenue
                if hasattr(row, "company_revenue") and pd.notna(row.company_revenue)
                else None
            ),
            company_description=(
                row.company_description
                if hasattr(row, "company_description")
                and pd.notna(row.company_description)
                else None
            ),
            company_url=(
                row.company_url_direct
                if hasattr(row, "company_url_direct")
                and pd.notna(row.company_url_direct)
                else (
                    row.company_url
                    if hasattr(row, "company_url") and pd.notna(row.company_url)
                    else None
                )
            ),
            # Legacy fields
            salary=0,
            working_model="",
        )

    def jobs(self) -> list[Job]:
        if not self._jobs:
            found_jobs = []

            # Create list of all scraping tasks
            sites = ["linkedin", "indeed"]
            total_tasks = len(self.search_terms) * len(sites)

            # Progress bar for overall scraping progress
            pbar = tqdm(
                total=total_tasks,
                desc="Scraping job boards",
                unit="search",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            )

            for search_term in self.search_terms:
                for site in sites:
                    # Update progress bar with current task
                    pbar.set_description(f"Scraping {site.capitalize()}: {search_term}")

                    try:
                        df_jobs = scrape_jobs(
                            site_name=site,
                            search_term=search_term,
                            google_search_term="AI engineer jobs near Münster, since last week",
                            location="Münster",
                            results_wanted=100,
                            hours_old=24 * 7,
                            country_indeed="germany",
                            linkedin_fetch_description=True,
                            # proxies=["208.195.175.46:65095", "208.195.175.45:65095", "localhost"],
                        )

                        jobs_found = len(df_jobs)
                        pbar.set_postfix_str(
                            f"Found {jobs_found} jobs | Total: {len(found_jobs)}"
                        )

                        found_jobs.extend(
                            [self._job_from_row(row) for row in df_jobs.itertuples()]
                        )
                    except Exception as e:
                        pbar.set_postfix_str(f"Error: {str(e)[:40]}")
                    finally:
                        pbar.update(1)

            pbar.close()
            logger.debug(f"Scraping complete! Found {len(found_jobs)} total jobs")
            self._jobs = found_jobs
        return self._jobs
