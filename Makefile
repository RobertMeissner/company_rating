## Local Development
.PHONY: dev
dev:
	@echo "Starting development servers with hot reload..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@$(MAKE) -j2 api frontend

.PHONY: api
api:
	uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: node
node:
	. ${HOME}/.nvm/nvm.sh use node

.PHONY: frontend
frontend: node
	cd frontend && bun run dev

frontend-install: node
	cd frontend && bun install

## Production
.PHONY: daily
daily:
	uv run python -m src.main daily

## Docker
.PHONY: docker
docker: docker-down docker-build docker-up

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
