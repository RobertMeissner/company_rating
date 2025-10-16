import re
import unicodedata

PHRASES_TO_REMOVE = [
    # Branch identifiers
    "- German Branch",
    "German Branch",
    "Deutschland",
    "Germany",
    "(Deutschland)",
    "(Germany)",
    # German legal forms - GmbH variations
    "GmbH",
    "Gmbh",
    "gmbh",
    "G.m.b.H.",
    "G.m.b.H",
    "mbH",
    "(GmbH)",
    "(Gmbh)",
    "(gmbh)",
    # GmbH & Co. KG combinations
    "GmbH & Co. KG",
    "GmbH & Co KG",
    "GmbH &Co. KG",
    "Gmbh & Co. KG",
    "gmbh & co. kg",
    "& Co. KG",
    "& Co KG",
    # Other German legal forms
    "AG",
    "A.G.",
    "(AG)",
    "SE",
    "S.E.",
    "KG",
    "K.G.",
    "OHG",
    "O.H.G.",
    "UG",
    "U.G.",
    "UG (haftungsbeschränkt)",
    "e.V.",
    "e. V.",
    "eV",
    # International legal forms
    "Inc.",
    "Inc",
    "LLC",
    "Ltd.",
    "Ltd",
    "Limited",
    "Corp.",
    "Corp",
    "Corporation",
    "Co.",
    "Company",
    # Common prefixes/suffixes
    "The",
]


def normalized_company_name(name: str) -> str:
    """
    Normalize company name for comparison/deduplication.
    Returns lowercase, stripped version without special chars.
    """

    normalized = name.strip()
    # Remove common phrases first, in case, e.g. "se" is inside the company name, too
    for phrase in PHRASES_TO_REMOVE:
        normalized = normalized.replace(phrase, "")

    normalized = normalized.lower().strip()

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
