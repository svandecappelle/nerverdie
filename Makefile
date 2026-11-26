ifeq ($(OS),Windows_NT)
PYTHON ?= python
else
PYTHON ?= python3
endif

.PHONY: serve serve-api venv run install update uninstall

## Production install on Linux: nginx with HTTPS serving the built UI, the app as a systemd service
install:
	$(PYTHON) scripts/install.py

## Update an installed Neverdie (git pull, .venv, UI) and restart its service; keeps the configuration
update:
	$(PYTHON) scripts/install.py --update

## Remove what make install added (keeps the certificates, the database and .venv)
uninstall:
	$(PYTHON) scripts/install.py --uninstall

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
