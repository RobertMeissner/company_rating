from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    """Company object"""

    name: str
    location: str
    kununu_rating: float
    glassdoor_rating: float
    alternative_names: list[
        str
    ]  # in case depending on the platform, it has different names, spellings, ...
