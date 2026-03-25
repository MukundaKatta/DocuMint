.PHONY: install dev test lint format clean docs

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=documint --cov-report=html --tb=short

lint:
	ruff check src/ tests/
	mypy src/documint/

format:
	black src/ tests/
	ruff check --fix src/ tests/

clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache .mypy_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

docs:
	documint generate src/documint/ -o docs/api
