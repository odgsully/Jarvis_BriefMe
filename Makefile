.PHONY: install run email test lint clean

# Python interpreter
PYTHON := python3

# Virtual environment
VENV := venv
VENV_ACTIVATE := . $(VENV)/bin/activate

# Install dependencies and create virtual environment
install:
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "Installing dependencies..."
	$(VENV_ACTIVATE) && pip install --upgrade pip
	$(VENV_ACTIVATE) && pip install -r requirements.txt
	@echo "Installation complete!"

# Run the application without email (dry run)
run:
	@echo "Running Jarvis BriefMe (no email)..."
	$(VENV_ACTIVATE) && $(PYTHON) -m src.main --dry-run

# Run the application with email
email:
	@echo "Running Jarvis BriefMe with email..."
	$(VENV_ACTIVATE) && $(PYTHON) -m src.main --email

# Run tests with coverage
test:
	@echo "Running tests with coverage..."
	$(VENV_ACTIVATE) && pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=90

# Run linter
lint:
	@echo "Running ruff linter..."
	$(VENV_ACTIVATE) && ruff check .

# Clean up generated files and cache
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete!"

# Development helpers
dev-install: install
	$(VENV_ACTIVATE) && pip install ipython

# Check environment
check-env:
	@echo "Checking environment variables..."
	@test -f .env || (echo "ERROR: .env file not found!" && exit 1)
	@echo "Environment check passed!"

# Full pipeline test (no actual email)
test-pipeline: check-env
	$(VENV_ACTIVATE) && $(PYTHON) -m src.main --dry-run

# Help
help:
	@echo "Available commands:"
	@echo "  make install      - Create venv and install dependencies"
	@echo "  make run          - Generate files without sending email"
	@echo "  make email        - Generate files and send email"
	@echo "  make test         - Run tests with coverage"
	@echo "  make lint         - Run ruff linter"
	@echo "  make clean        - Clean up cache and generated files"
	@echo "  make dev-install  - Install with development tools"
	@echo "  make check-env    - Verify .env file exists"
	@echo "  make help         - Show this help message"