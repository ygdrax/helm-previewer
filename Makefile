.PHONY: install pre-commit lint clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install project dependencies including dev dependencies"
	@echo "  pre-commit  - Install pre-commit hooks"
	@echo "  lint        - Run code linting and formatting with ruff"
	@echo "  clean       - Remove Python cache files and build artifacts"
	@echo "  help        - Show this help message"

# Install project dependencies
install:
	@echo "Installing project dependencies..."
	uv sync --group dev
	@echo "Dependencies installed successfully"

# Install pre-commit hooks
pre-commit:
	@echo "Installing pre-commit hooks..."
	uv run pre-commit install
	@echo "Pre-commit hooks installed successfully"

# Run linting and formatting
lint:
	@echo "Running ruff linting and formatting..."
	uv run ruff check src/ tests/ --fix
	uv run ruff format src/ tests/
	@echo "Code linting and formatting completed"

# Clean Python cache files and build artifacts
clean:
	@echo "Cleaning Python cache files and build artifacts..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	@echo "Cleanup completed"
