from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class SCRAPERS(Enum):
    KUNUNU = "kununu"


@dataclass
class ScraperModel:
    """Container for scraping results"""

    company_name: str
    scraper: SCRAPERS
    company_location: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    profile_url: Optional[str] = None
    scraped_at: datetime = None
    success: bool = False
    error_message: Optional[str] = None
    scrape_duration: Optional[float] = None

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.now(timezone.utc)
