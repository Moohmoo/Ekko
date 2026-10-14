.PHONY: all install dev test test-backend test-e2e lint build clean

# Default target
all: install

## install: Install all backend (uv) and frontend (npm) dependencies
install:
	uv sync
	cd clients/desktop-electron && npm install

## dev: Launch the desktop application and supervised daemon in development mode
dev:
	cd clients/desktop-electron && npm run dev

## test: Run the complete test suite (Pytest backend + Playwright E2E)
test: test-backend test-e2e

## test-backend: Run Python backend unit and integration tests
test-backend:
	uv run pytest

## test-e2e: Run Playwright desktop end-to-end test suite
test-e2e:
	cd clients/desktop-electron && npm run test:e2e

## lint: Run ruff linter on Python code and verify TypeScript compilation
lint:
	uvx ruff check .
	cd clients/desktop-electron && npm run build

## build: Build the production Electron renderer and main bundles
build:
	cd clients/desktop-electron && npm run build

## clean: Remove build artifacts, test output, and Python cache directories
clean:
	rm -rf clients/desktop-electron/dist clients/desktop-electron/dist-electron clients/desktop-electron/test-results .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
