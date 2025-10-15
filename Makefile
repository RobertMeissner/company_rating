
.PHONY: daily
daily:
	uv run python -m src.main daily

streamlit:
	uv run streamlit run src/presentation/streamlit_app.py

api:
	uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: frontend
frontend:
	cd frontend && npm run dev

frontend-install:
	cd frontend && npm install

scrape_jobs:
	uv run python -m src.main

# Docker Compose
docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker build -t company-rating-backend:latest -f Dockerfile.backend .

## Dev tooling

match_with_raw_company_names:
	uv run src/poc/match_company_names.py

.PHONY: pre-comit
pre-commit:
	uv run pre-commit run -a

.PHONY: pre-comit
pre-commit-manual:
	uv run pre-commit run -a --hook-stage manual

.PHONY: callgraph
callgraph:
	# WIP! Output is flaky at best
	uv run pycallgraph graphviz -- src/main.py
