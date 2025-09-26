.PHONY: help run resume export test test-specific debug clean install setup demo demo-export poc-company poc-test poc-file poc-file-export poc-file-resume

# Default target
help:
	@echo "Company Rating Scraper - Available commands:"
	@echo ""
	@echo "Basic Usage:"
	@echo "  run          Run full scraping pipeline"
	@echo "  resume       Resume interrupted run"
	@echo "  export       Export results to CSV"
	@echo "  test-company Test specific company (use COMPANY=name)"
	@echo ""
	@echo "POC Commands:"
	@echo "  demo         Run demo with 5 test companies"
	@echo "  demo-export  Run demo and export to CSV"
	@echo "  poc-company  Test specific company with POC (use COMPANY=name)"
	@echo "  poc-test     Run POC tests"
	@echo "  poc-file     Scrape companies from text file (use FILE=path)"
	@echo "  poc-file-export  Scrape from file and export (use FILE=path)"
	@echo "  poc-file-resume  Resume scraping with incremental saves"
	@echo ""
	@echo "Development:"
	@echo "  test         Run all tests"
	@echo "  test-kununu  Run Kununu scraper tests"
	@echo "  debug        Run with debug logging (limited to 5 companies)"
	@echo ""
	@echo "Setup:"
	@echo "  install      Install dependencies"
	@echo "  setup        Create data directory structure"
	@echo "  clean        Clean up generated files"

# Basic Usage Commands
run:
	python src/main.py --input data/companies.csv --output data/results.db

resume:
	python src/main.py --resume

export:
	python src/main.py --export data/results.csv

test-company:
ifndef COMPANY
	@echo "Usage: make test-company COMPANY=\"Company Name\""
	@echo "Example: make test-company COMPANY=\"SAP\""
else
	python src/main.py --test "$(COMPANY)"
endif

# Development Commands
test:
	pytest tests/ -v

test-kununu:
	python -m pytest tests/test_kununu.py::test_scrape_sap -v

debug:
	python src/main.py --debug --limit 5

# Setup Commands
install:
	pip install -r requirements.txt

setup:
	mkdir -p data tests src/scrapers src/models src/utils
	touch data/companies.csv

# POC Commands
demo:
	python src/kununu_scraper_poc.py --demo

demo-export:
	python src/kununu_scraper_poc.py --demo --export results.csv

poc-company:
ifndef COMPANY
	@echo "Usage: make poc-company COMPANY=\"Company Name\""
	@echo "Example: make poc-company COMPANY=\"SAP\""
else
	python src/kununu_scraper_poc.py --company "$(COMPANY)"
endif

poc-test:
	python src/kununu_scraper_poc.py --test

# Input file commands
poc-file:
ifndef FILE
	@echo "Usage: make poc-file FILE=path/to/companies.txt"
	@echo "Example: make poc-file FILE=data/companies.txt"
else
	python src/kununu_scraper_poc.py --input "$(FILE)"
endif

poc-file-export:
ifndef FILE
	@echo "Usage: make poc-file-export FILE=path/to/companies.txt [EXPORT=output.csv]"
	@echo "Example: make poc-file-export FILE=data/companies.txt EXPORT=results.csv"
else
ifndef EXPORT
	python src/kununu_scraper_poc.py --input "$(FILE)" --export results.csv
else
	python src/kununu_scraper_poc.py --input "$(FILE)" --export "$(EXPORT)"
endif
endif

poc-file-resume:
ifndef FILE
	@echo "Usage: make poc-file-resume FILE=path/to/companies.txt EXPORT=output.csv"
	@echo "Example: make poc-file-resume FILE=data/companies.txt EXPORT=data/output.csv"
else
ifndef EXPORT
	@echo "EXPORT parameter required for resume mode"
	@echo "Usage: make poc-file-resume FILE=companies.txt EXPORT=results.csv"
else
	python src/kununu_scraper_poc.py --input "$(FILE)" --export "$(EXPORT)" --resume
endif
endif

clean:
	rm -f data/results.db data/failed_lookups.csv results.csv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete