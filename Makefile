.PHONY: up down test lint

up:
	docker compose up --build

down:
	docker compose down -v

test:
	cd backend && python -m pytest ../tests/ -v
	cd frontend && npm test -- --watchAll=false

lint:
	cd backend && flake8 .
	cd ml_service && flake8 .
	cd document_parser && flake8 .
	cd frontend && npx eslint src/
