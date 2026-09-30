.PHONY: install dev test train sample-data demo lint format docker-build docker-run compose-up compose-down clean

install:  ## Install the project and dev tools into the active environment
	python -m pip install -e ".[dev]"

dev:  ## Run the API locally with auto-reload
	uvicorn app.main:app --reload

test:  ## Run the test suite
	pytest -v

train:  ## Retrain and persist the model artifact
	python -m ml.train

sample-data:  ## Regenerate data/sample_transactions.json
	python scripts/generate_sample_transactions.py

demo:  ## Send sample transactions to a running local API
	python scripts/demo_client.py

lint:  ## Run static analysis
	ruff check app ml tests scripts

format:  ## Auto-fix lint/formatting issues
	ruff check --fix app ml tests scripts

docker-build:  ## Build the production container image
	docker build -t fraudpulse .

docker-run:  ## Run the production container image
	docker run --rm -p 8000:8000 fraudpulse

compose-up:  ## Build and start via docker compose
	docker compose up --build

compose-down:  ## Stop docker compose services
	docker compose down

clean:  ## Remove caches and local build artifacts
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
