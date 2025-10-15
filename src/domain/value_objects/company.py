from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Company:
    """Company value object with comprehensive rating and profile information"""

    name: str
    location: str = ""

    # Overall ratings
    kununu_rating: Optional[float] = None
    kununu_review_count: Optional[int] = None
    glassdoor_rating: Optional[float] = None
    glassdoor_review_count: Optional[int] = None

    # Kununu sub-ratings (1-5 scale)
    kununu_career_rating: Optional[float] = None  # Career opportunities
    kununu_work_life_balance_rating: Optional[float] = None
    kununu_salary_benefits_rating: Optional[float] = None
    kununu_management_rating: Optional[float] = None  # Management/Leadership
    kununu_culture_rating: Optional[float] = None  # Company culture

    # Recommendation metrics
    kununu_recommend_percent: Optional[float] = None  # % who would recommend

    # Company details
    industry: Optional[str] = None
    company_size: Optional[str] = None  # e.g., "1001-5000 employees"
    founded_year: Optional[int] = None

    # URLs and identifiers
    alternative_names: list[str] = field(
        default_factory=list
    )  # in case depending on the platform, it has different names, spellings, ...
    url: str = ""  # Kununu profile URL
    website: str = ""  # Company's actual website
    linkedin_url: Optional[str] = None
    glassdoor_url: Optional[str] = None

    # Metadata
    description: Optional[str] = None
