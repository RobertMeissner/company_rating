"""
POC script to match unsorted company names against existing companies.
"""

import sys
from difflib import SequenceMatcher
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.infrastructure.adapters.company_query_file_based import (
    CompanyQueryFileBasedAdapter,
)
from src.utils.settings import DATA_FOLDER


def normalize_name(name: str) -> str:
    """Normalize company name for better matching"""
    # Convert to lowercase
    normalized = name.lower().strip()

    # Remove common legal suffixes
    suffixes = [
        " gmbh",
        " gmbh & co. kg",
        " gmbh & co.kg",
        " gmbh & co kg",
        " ag",
        " se",
        " kg",
        " ohg",
        " gbr",
        " ug",
        " inc",
        " inc.",
        " corp",
        " corp.",
        " ltd",
        " ltd.",
        " llc",
        " llc.",
        " co.",
        " co",
        " group",
    ]

    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()

    # Remove special characters and extra spaces
    normalized = " ".join(normalized.split())

    return normalized


def similarity_score(name1: str, name2: str) -> float:
    """Calculate similarity score between two names (0.0 to 1.0)"""
    # Normalize both names
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    # Calculate similarity
    return SequenceMatcher(None, norm1, norm2).ratio()


def find_matches(
    unsorted_name: str, existing_companies: list, top_n: int = 3, threshold: float = 0.6
):
    """
    Find top N matching companies from existing companies.

    Args:
        unsorted_name: Name to match
        existing_companies: List of Company objects
        top_n: Number of top matches to return
        threshold: Minimum similarity score (0.0 to 1.0)

    Returns:
        List of tuples (company_name, score)
    """
    matches = []

    for company in existing_companies:
        score = similarity_score(unsorted_name, company.name)
        if score >= threshold:
            matches.append((company.name, score))

    # Sort by score (descending) and take top N
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:top_n]


def main():
    # Load existing companies
    print("Loading existing companies...\n")
    query_adapter = CompanyQueryFileBasedAdapter()

    try:
        existing_companies = query_adapter.get()
        print(f"Loaded {len(existing_companies)} existing companies\n")
    except FileNotFoundError:
        print("ERROR: No companies file found. Run the scraper first.")
        return

    # Read unsorted names from file
    unsorted_file = Path(DATA_FOLDER) / "beworben.txt"

    try:
        with open(unsorted_file, "r", encoding="utf-8") as f:
            unsorted_names = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"ERROR: File not found: {unsorted_file}")
        print("Please create data/beworben.txt with one company name per line.")
        return

    if not unsorted_names:
        print("ERROR: No company names found in beworben.txt")
        return

    print("=" * 80)
    print("COMPANY NAME MATCHING")
    print("=" * 80)
    print(f"\nMatching {len(unsorted_names)} company names...\n")
    print("-" * 80)

    # Match each unsorted name
    for unsorted_name in unsorted_names:
        matches = find_matches(
            unsorted_name, existing_companies, top_n=3, threshold=0.6
        )

        if matches:
            if matches[0][1] == 1.0:
                # Perfect match - just print the name
                print(matches[0][0])
            else:
                # Multiple candidates - print comma separated without scores
                candidates = ", ".join([name for name, score in matches])
                print(candidates)
        else:
            print("NO MATCH FOUND")

    print("-" * 80)
    print("\nOutput format:")
    print("  - Perfect match (100%): Company Name")
    print("  - Partial matches: Candidate1, Candidate2, Candidate3")
    print("  - No match: NO MATCH FOUND")


if __name__ == "__main__":
    main()
