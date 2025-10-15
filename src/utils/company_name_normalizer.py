import re
import unicodedata

from src.domain.value_objects.company import Company

PHRASES_TO_REMOVE = [
    "- German Branch",
    "German Branch",
    "Deutschland",
    "Germany",
    "(Deutschland)",
    "(Germany)",
]


def normalize(name: str) -> str:
    """
    Normalize company name for comparison/deduplication.
    Returns lowercase, stripped version without special chars.
    """
    normalized = name.lower().strip()

    # Remove common phrases
    for phrase in PHRASES_TO_REMOVE:
        normalized = normalized.replace(phrase.lower(), "")

    normalized = (
        unicodedata.normalize("NFKD", normalized)
        .encode("ascii", "ignore")
        .decode("utf-8")
    )

    normalized = normalized.replace(" ", "-")

    normalized = normalized.replace("&", "").replace("+", "")

    # Remove all non-alphanumeric except hyphens
    normalized = re.sub(r"[^\w-]", "", normalized)

    # Remove multiple consecutive hyphens
    normalized = re.sub(r"-+", "-", normalized)

    # Normalize whitespace
    normalized = "-".join(normalized.split())

    return normalized.strip("-")


def normalized_company_name(company: Company) -> list[str]:
    """
    Generates multiple company name variations for scraping

    :param company: Company
    :return: list of possible names for scraping
    """
    names_to_try = set()
    names_to_try.update(company.alternative_names)
    names_to_try.add(normalize(company.name))

    return list(names_to_try)
