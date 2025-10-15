from src.application.services.job_orchestrator import JobOrchestrator
from src.infrastructure.adapters.blacklist_file_based import BlacklistFileBasedAdapter
from src.infrastructure.adapters.company_command_file_based import (
    CompanyCommandFileBasedAdapter,
)
from src.infrastructure.adapters.company_query_file_based import (
    CompanyQueryFileBasedAdapter,
)
from src.infrastructure.adapters.job_command_file_based import (
    JobCommandFileBasedAdapter,
)
from src.infrastructure.adapters.job_query_file_based import JobQueryFileBasedAdapter
from src.infrastructure.scrapers.company_scraper_manager import CompanyScraperManager
from src.infrastructure.scrapers.glassdoor_scraper import GlassdoorScraper
from src.infrastructure.scrapers.jobspy_scraper import JobspyScraper
from src.infrastructure.scrapers.kununu_scraper import KununuScraper
from src.utils.settings import COMPANY_BLACKLIST_FILENAME, JOB_BLACKLIST_FILENAME


def default_orchestrator():
    """
    Create a default JobOrchestrator with Glassdoor and Kununu scrapers.


    Returns:
        Configured JobOrchestrator
    """
    job_query_adapter = JobQueryFileBasedAdapter()
    job_command_adapter = JobCommandFileBasedAdapter()
    company_query_adapter = CompanyQueryFileBasedAdapter()
    company_command_adapter = CompanyCommandFileBasedAdapter()
    company_blacklist_adapter = BlacklistFileBasedAdapter(COMPANY_BLACKLIST_FILENAME)
    job_blacklist_adapter = BlacklistFileBasedAdapter(JOB_BLACKLIST_FILENAME)
    job_scraper_adapter = JobspyScraper()

    company_scraper = CompanyScraperManager([KununuScraper, GlassdoorScraper])

    orchestrator = JobOrchestrator(
        job_query_port=job_query_adapter,
        job_command_port=job_command_adapter,
        company_query_port=company_query_adapter,
        company_command_port=company_command_adapter,
        company_scraper=company_scraper,
        job_scraper_port=job_scraper_adapter,
        company_blacklist_port=company_blacklist_adapter,
        job_blacklist_port=job_blacklist_adapter,
    )
    return orchestrator
