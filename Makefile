

poc-file-resume:
	@echo "Example: make poc-file-resume FILE=data/companies.txt EXPORT=data/output.csv"

streamlit:
	uv run streamlit run src/presentation/streamlit_app.py


scrape_jobs:
	uv run src/jobspy_poc.py
