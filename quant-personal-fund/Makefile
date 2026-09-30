.PHONY: test lint clean init-data-dirs help

# Default target
help:
	@echo "quant-personal-fund — Makefile targets"
	@echo ""
	@echo "  make test           Run all unit and integration tests"
	@echo "  make lint           Run flake8 linting on source code"
	@echo "  make clean          Remove __pycache__ and .pytest_cache"
	@echo "  make init-data-dirs Create data directory structure for raw downloads"

test:
	pytest core/tests/ data/pipelines/tests/ -v --tb=short

lint:
	flake8 core/ signals/ portfolio/ risk/ backtest/ execution/ monitoring/ data/pipelines/ --max-line-length=120

clean:
	@echo "Cleaning __pycache__ and .pytest_cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Done."

init-data-dirs:
	@echo "Creating data download directories..."
	mkdir -p data/raw/yahoo/daily
	mkdir -p data/raw/fred
	@echo "Done."