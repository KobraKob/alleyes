.PHONY: up down migrate seed demo sim test lint format typecheck

up:
	docker compose up -d

down:
	docker compose down

migrate:
	alembic upgrade head

seed:
	python scripts/seed.py

demo:
	python scripts/demo.py

interactive:
	python scripts/interactive.py

sim:
	python scripts/simulate.py

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/
