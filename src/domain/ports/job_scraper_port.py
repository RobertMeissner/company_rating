from typing import Iterable, Protocol

from src.domain.entities.job import Job


class JobScraper(Protocol):
    """Port for Job scraping"""

    def jobs(self) -> Iterable[Job]: ...
