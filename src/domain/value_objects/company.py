from dataclasses import dataclass, field


@dataclass(frozen=True)
class Company:
    """Company value object"""

    name: str
    location: str = ""
    kununu_rating: float = 0
    glassdoor_rating: float = 0
    alternative_names: list[str] = field(
        default_factory=list
    )  # in case depending on the platform, it has different names, spellings, ...
    url: str = ""
