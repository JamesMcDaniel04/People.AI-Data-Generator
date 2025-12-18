.PHONY: install install-dev clean test format lint help

help:
	@echo "Available commands:"
	@echo "  make install      - Install the package in development mode"
	@echo "  make install-dev  - Install with development dependencies"
	@echo "  make clean        - Remove generated files and caches"
	@echo "  make test         - Run tests"
	@echo "  make format       - Format code with black"
	@echo "  make lint         - Run linting with ruff"
	@echo "  make dry-run      - Run a dry-run with example config"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test:
	pytest tests/ -v

format:
	black src/ tests/

lint:
	ruff check src/ tests/

dry-run:
	@if [ ! -f demo.yaml ]; then \
		echo "Creating demo.yaml from example..."; \
		cp demo.example.yaml demo.yaml; \
	fi
	demo-gen dry-run -c demo.yaml
