from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class SCRAPERS(Enum):
    KUNUNU = "kununu"
    GLASSDOOR = "glassdoor"


@dataclass
class ScraperModel:
    """Container for scraping results with comprehensive company data"""

    company_name: str
    scraper: SCRAPERS
    company_location: Optional[str] = None

    # Overall ratings
    rating: Optional[float] = None
    review_count: Optional[int] = None

    # Kununu sub-ratings
    career_rating: Optional[float] = None
    work_life_balance_rating: Optional[float] = None
    salary_benefits_rating: Optional[float] = None
    management_rating: Optional[float] = None
    culture_rating: Optional[float] = None

    # Recommendation
    recommend_percent: Optional[float] = None

    # Company details
    industry: Optional[str] = None
    company_size: Optional[str] = None

    # URLs
    profile_url: Optional[str] = None
    company_website: Optional[str] = None

    # Metadata
    scraped_at: datetime = None
    success: bool = False
    error_message: Optional[str] = None
    scrape_duration: Optional[float] = None

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.now(timezone.utc)
