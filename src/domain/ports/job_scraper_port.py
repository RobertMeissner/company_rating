from typing import Protocol

from src.domain.entities.job import Job


class JobScraper(Protocol):
    """Port for Job scraping"""

    def jobs(self) -> list[Job]: ...
