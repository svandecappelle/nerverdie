# Nerverdie
Python monitor servers

## Development install
Requires Python 3.10 or later. Dependencies are declared in `pyproject.toml`
and pinned in `uv.lock`.

### With uv
Install [uv](https://docs.astral.sh/uv/) (for instance `python -m pip install --user uv`), then:
```
uv sync
```

* Run app:
  * In web service: ```uv run python start.py``` (options: `-H <host>`, `-P <port>`)
  * In console management: ```uv run python console.py```
  * Network discovery agent: ```uv run python agent.py -n 192.168.10.0/24``` (only on networks you are responsible for)
* Run the checks:
  * Tests: ```uv run pytest```
  * Lint: ```uv run ruff check .```
  * Known vulnerabilities in dependencies: ```uv run pip-audit```

## Users and security
There are no default credentials. Create an account before logging in:
```
uv run python manage.py create-user <username>
```
(`set-password`, `delete-user` and `list-users` are also available.)

Environment variables:
* `NEVERDIE_SECRET_KEY`: session signing key. If unset, a random key is generated once in `instance/secret_key` (git-ignored).
* `NEVERDIE_COOKIE_SECURE=1`: send the session cookie over HTTPS only. Set it as soon as the app is served behind TLS.
* `NEVERDIE_DB`: SQLite database path (default `db.sqlite`).

After 5 failed logins from one address within 5 minutes, further attempts are refused (HTTP 429).
