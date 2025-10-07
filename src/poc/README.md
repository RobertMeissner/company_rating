# Proof of Concept Scripts

Quick scripts for one-off data collection and import tasks.

## Scripts

### 1. `company_scraper.py` - Kununu Company Scraper

Scrapes companies from Kununu search results (filtered by location and rating).

**Usage:**
```bash
uv run src/poc/company_scraper.py
```

**Output:** `kununu_companies.csv` with columns:
- COMPANY_NAME
- RATING
- URL

**Configuration:**
Edit the `base_url` in the script to change search filters:
- Location
- Industry
- Rating range

### 2. `import_kununu_companies.py` - CSV Import Script

Imports companies from `kununu_companies.csv` into the main system.

**Usage:**
```bash
uv run src/poc/import_kununu_companies.py
```

**What it does:**
- Reads `kununu_companies.csv`
- Creates Company objects with:
  - name from CSV
  - kununu_rating from CSV
  - location = "Münster"
  - url from CSV
- Merges with existing companies (avoids duplicates)
- Writes to `data/companies.jsonl`

## Workflow

```bash
# 1. Scrape companies from Kununu
uv run src/poc/company_scraper.py

# 2. Import into main system
uv run src/poc/import_kununu_companies.py

# 3. Continue with normal workflow
uv run src/main.py  # Daily job scraping will now use these companies
```

## Notes

- These are POC scripts meant for initial data seeding
- For production use, prefer the main scraping infrastructure
- Always check the CSV output before importing
