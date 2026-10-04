.PHONY: build test lint typecheck format clean help venv venv-clean venv-activate venv-shell docs-style docs-coverage vet security-bandit security-audit security-check check check-strict-security shell

IMAGE_NAME := pydhcpcdparser
DOCKER_RUN := docker run --rm -v "$(PWD):/app" -w /app $(IMAGE_NAME)
PYTHON ?= python3
VENV_DIR ?= .venv
VENV_PYTHON := $(VENV_DIR)/bin/python

help: ## Show available targets
	@echo "List available targets"
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_.-]+:.*## / {printf "%-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build the Docker image
	@echo "Build Docker image $(IMAGE_NAME)"
	docker build -t $(IMAGE_NAME) .

venv: ## Create .venv and install project dependencies
	@echo "Create local virtual environment and install project"
	$(PYTHON) -m venv --clear $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e ".[dev]"

venv-clean: ## Remove local virtual environment
	@echo "Remove local virtual environment $(VENV_DIR)"
	rm -rf $(VENV_DIR)

venv-activate: ## Print the command to activate the local virtual environment
	@echo "Print activation command for local virtual environment"
	@echo "Run this in your shell: source $(VENV_DIR)/bin/activate"

venv-shell: venv ## Open an interactive shell with the venv activated
	@echo "Open interactive shell with local virtual environment activated"
	@$(SHELL) -i -c "source $(VENV_DIR)/bin/activate && exec $(SHELL) -i"

test: build ## Run pytest
	@echo "Run test suite with pytest"
	$(DOCKER_RUN) pytest -v

lint: build ## Run ruff linter and format check
	@echo "Run Ruff lint and format checks"
	$(DOCKER_RUN) ruff check src/ tests/
	$(DOCKER_RUN) ruff format --check src/ tests/

typecheck: build ## Run mypy type checker
	@echo "Run mypy type checks"
	$(DOCKER_RUN) mypy src/

docs-style: build ## Run docstring style checks (ruff pydocstyle rules)
	@echo "Run docstring style checks"
	$(DOCKER_RUN) ruff check src/pydhcpcdparser

docs-coverage: build ## Run docstring coverage checks
	@echo "Run docstring coverage checks"
	$(DOCKER_RUN) interrogate src/pydhcpcdparser

vet: build ## Run static quality checks (lint, mypy, docs checks)
	@echo "Run static quality gate (lint, mypy, docs checks)"
	$(DOCKER_RUN) ruff check src/ tests/
	$(DOCKER_RUN) ruff format --check src/ tests/
	$(DOCKER_RUN) mypy src/
	$(DOCKER_RUN) interrogate src/pydhcpcdparser

security-bandit: build ## Run Bandit security lint checks
	@echo "Run Bandit security lint checks"
	$(DOCKER_RUN) bandit -q -r src/pydhcpcdparser

security-audit: build ## Run dependency vulnerability audit (optional)
	@echo "Run dependency vulnerability audit"
	$(DOCKER_RUN) pip-audit || true

security-check: build ## Run security checks bundle
	@echo "Run security checks bundle"
	$(DOCKER_RUN) bandit -q -r src/pydhcpcdparser
	$(DOCKER_RUN) pip-audit || true

format: build ## Format code with ruff
	@echo "Format code and apply automatic Ruff fixes"
	$(DOCKER_RUN) ruff format src/ tests/
	$(DOCKER_RUN) ruff check --fix src/ tests/

check: build ## Run all verifications (lint, type checks, docs, security, tests)
	@echo "Run full verification suite"
	$(DOCKER_RUN) ruff check src/ tests/
	$(DOCKER_RUN) ruff format --check src/ tests/
	$(DOCKER_RUN) mypy src/
	$(DOCKER_RUN) interrogate src/pydhcpcdparser
	$(DOCKER_RUN) bandit -q -r src/pydhcpcdparser
	$(DOCKER_RUN) pip-audit || true
	$(DOCKER_RUN) pytest -v

check-strict-security: build ## Run all verifications and fail on dependency vulnerabilities
	@echo "Run strict verification suite (security audit enforced)"
	$(MAKE) check
	$(DOCKER_RUN) pip-audit

shell: build ## Open a shell in the container
	@echo "Open interactive shell in Docker container"
	docker run --rm -it -v "$(PWD):/app" -w /app $(IMAGE_NAME) bash

clean: ## Remove Docker image and caches
	@echo "Remove Docker image and local cache directories"
	docker rmi -f $(IMAGE_NAME) 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
