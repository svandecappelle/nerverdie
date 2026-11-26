ifeq ($(OS),Windows_NT)
PYTHON ?= python
else
PYTHON ?= python3
endif

.PHONY: serve serve-api venv run

## Create or update .venv with pip (dependencies and dev tools)
venv:
	$(PYTHON) scripts/bootstrap.py --dev

## Start the web service from .venv (created on first run)
run:
	$(PYTHON) scripts/run.py

## Start the API (http://127.0.0.1:5000) and the UI dev server (http://localhost:4200)
serve:
	$(PYTHON) scripts/serve.py

## Start the API only
serve-api:
	$(PYTHON) scripts/serve.py --no-ui
