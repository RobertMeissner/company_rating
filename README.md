<div align="center">

# WIP Company Rating Scraper

**Intelligent job search automation with company ratings integration**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A personal tool that automatically scrapes job listings from LinkedIn and Indeed, enriches them with Kununu company ratings, and provides an interactive dashboard for efficient job hunting.

BEWARE: This is a work in progress to test a number of assumptions. Everything can fail all the time.

[Features](#features) •
[Installation](#installation) •
[Usage](#usage) •
[Configuration](#configuration)

</div>

---

## 📋 Table of Contents

- [About](#about)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Daily Workflow](#daily-workflow)
  - [Dashboard](#dashboard)
  - [Alternative Company Names](#alternative-company-names)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Data Files](#data-files)

## 🎯 About

Company Rating Scraper automates the tedious process of job hunting by:
- Collecting job postings from multiple sources (LinkedIn, Indeed)
- Fetching company reputation data from Kununu
- Providing intelligent filtering and blacklisting
- Offering a clean, interactive dashboard for review

Built with a clean hexagonal architecture for maintainability and extensibility.

## ✨ Features

- 🔍 **Multi-Source Job Scraping** - Automated collection from LinkedIn and Indeed via JobSpy
- ⭐ **Company Ratings** - Enriches jobs with Kununu ratings and review counts
- 📊 **Interactive Dashboard** - Streamlit-based UI with real-time filtering
- 🚫 **Smart Blacklisting** - Hide unwanted companies or individual jobs
- 🔄 **Alternative Names** - Handle companies with different names across platforms
- 💾 **File-Based Storage** - Simple JSONL format, no database required
- 🎨 **Clean Architecture** - Ports & adapters pattern for easy testing and extension

## 🚀 Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd CompanyRating

# Install dependencies
uv sync

# Install Playwright browsers (required for Kununu scraping)
uv run playwright install chromium
```

## 📖 Usage

### Daily Workflow

**1. Scrape Jobs**

Run the daily scraping routine to fetch new jobs:

```bash
uv run src/main.py
```

This performs:
- Job scraping from LinkedIn and Indeed
- Blacklist filtering
- Deduplication
- Data persistence to `data/jobs.jsonl`

**2. Launch Dashboard**

```bash
make streamlit
```

Access the dashboard at `http://localhost:8501`

### Dashboard

The Streamlit interface provides:

- **Rating Filter**: Adjust minimum Kununu rating threshold via sidebar slider
- **Company Blacklist**: Multi-select dropdown to hide entire companies
- **Job Hiding**: Check individual jobs to add them to the blacklist
- **CSV Export**: Export filtered results for external analysis

### Alternative Company Names

Some companies appear with different names on job boards vs. rating sites:

```bash
# 1. Export companies without ratings
# Edit src/main.py: task = Tasks.EXPORT
uv run src/main.py

# 2. Edit data/companies_missing_ratings.csv
# Fill alternative_name column with correct Kununu names
# Use "void" for companies not on Kununu

# 3. Import and re-scrape
# Edit src/main.py: task = Tasks.IMPORT
uv run src/main.py
```

## ⚙️ Configuration

### Search Parameters

Edit `src/infrastructure/scrapers/jobspy_scraper.py`:

```python
search_terms = [
    "JOB TITLE 1",
    "Fullstack JOB TITLE 2",
    "AI JOB TITLE 3",
    "...",
]

location = "YOURPLACEOFWORK"
hours_old = 24 * 7  # Last 7 days
results_wanted = 100
```

### Task Selection

Edit `src/main.py` to change the execution task:

```python
task = Tasks.DAILY   # Daily job scraping
task = Tasks.EXPORT  # Export companies missing ratings
task = Tasks.IMPORT  # Import alternative names and re-scrape
```

## 📁 Project Structure

```
src/
├── domain/              # Core business logic
│   ├── entities/        # Job, Company entities
│   ├── ports/           # Interface definitions
│   └── value_objects/   # Immutable value objects
├── infrastructure/      # External integrations
│   ├── adapters/        # File storage, blacklist management
│   └── scrapers/        # Kununu (Playwright), JobSpy
├── application/         # Use cases
│   └── services/        # JobOrchestrator
├── presentation/        # User interfaces
│   └── streamlit_app.py # Interactive dashboard
└── main.py             # CLI entry point
```

## 💾 Data Files

All data stored in the `data/` directory:

| File | Purpose |
|------|---------|
| `companies.jsonl` | Company data with ratings |
| `jobs.jsonl` | Scraped job listings |
| `company_blacklist.txt` | Hidden companies |
| `job_blacklist.txt` | Hidden job IDs |
| `companies_missing_ratings.csv` | Manual name correction workflow |
| `filtered_*.csv` | Exported results |

## 🏗️ Architecture

Built with **Hexagonal Architecture** (Ports & Adapters):

- **Domain Layer**: Pure business logic, framework-agnostic
- **Application Layer**: Use cases and orchestration
- **Infrastructure Layer**: External concerns (file I/O, web scraping)
- **Presentation Layer**: User interfaces (Streamlit, CLI)

Benefits:
- Easy to test
- Swappable implementations (file storage → database)
- Clear separation of concerns

## 📝 Notes

- **Rate Limiting**: Kununu scraper includes 1-5s delays for respectful scraping
- **Stealth Mode**: Playwright uses anti-detection techniques
- **German Market**: Optimized for German job market (Indeed DE, Kununu)
- **Privacy**: All data stored locally, no external services required

---

<div align="center">
Made with ❤️ for efficient job hunting
</div>
