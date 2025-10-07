import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.domain.value_objects.company import Company
from src.infrastructure.adapters.company_command_file_based import (
    CompanyCommandFileBasedAdapter,
)
from src.infrastructure.adapters.company_query_file_based import (
    CompanyQueryFileBasedAdapter,
)
from src.utils.settings import DATA_FOLDER


def load_kununu_companies(csv_path: str) -> list[Company]:
    companies = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = Company(
                name=row["COMPANY_NAME"],
                kununu_rating=float(row["RATING"]),
                location="Münster",
                url=row["URL"],
                kununu_review_count=0,  # Not available in CSV
                glassdoor_rating=0,
                glassdoor_review_count=0,
                alternative_names=[],
            )
            companies.append(company)

    return companies


def merge_companies(
    existing_companies: list[Company], new_companies: list[Company]
) -> list[Company]:
    """Merge new companies with existing, avoiding duplicates by name"""
    existing_names = {c.name.lower() for c in existing_companies}
    merged = list(existing_companies)

    for company in new_companies:
        if company.name.lower() not in existing_names:
            merged.append(company)
            print(f"✓ Added: {company.name} (Rating: {company.kununu_rating})")
        else:
            print(f"⊘ Skipped duplicate: {company.name}")

    return merged


def main():
    csv_path = Path(DATA_FOLDER) / "kununu_companies.csv"

    print(f"Loading companies from {csv_path}...\n")

    # Load new companies from CSV
    new_companies = load_kununu_companies(str(csv_path))
    print(f"Found {len(new_companies)} companies in CSV\n")

    # Load existing companies
    query_adapter = CompanyQueryFileBasedAdapter()
    try:
        existing_companies = query_adapter.get()
        print(f"Found {len(existing_companies)} existing companies\n")
    except FileNotFoundError:
        print("No existing companies file found, starting fresh\n")
        existing_companies = []

    # Merge companies
    print("Merging companies...\n")
    print(f"  Total companies before: {len(existing_companies)}, {len(new_companies)}")
    merged_companies = merge_companies(existing_companies, new_companies)

    print(f"  Total companies: {len(merged_companies)}")
    # Save merged companies
    command_adapter = CompanyCommandFileBasedAdapter()
    command_adapter.write(merged_companies)

    print(f"  Total companies: {len(merged_companies)}")
    print(f"  New companies: {len(merged_companies) - len(existing_companies)}")


if __name__ == "__main__":
    main()
