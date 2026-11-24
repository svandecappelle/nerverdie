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

* Run the API and the UI together (development):
  ```
  make serve
  ```
  The API runs on http://127.0.0.1:5000 and the UI dev server on http://localhost:4200 (it forwards `/api` to the API). Requires Node.js 22 or later; client dependencies are installed on first run. `make serve-api` starts the API only. Ctrl+C stops everything.
  Without make (or on Windows without it, `scoop install make` / `choco install make`): ```python scripts/serve.py``` (`--no-ui` for the API only).
* Run app:
  * In web service: ```uv run python start.py``` (options: `-H <host>`, `-P <port>`, `-t <threads>`), served by the waitress WSGI server
  * In console management: ```uv run python console.py```
  * Network discovery agent: ```uv run python agent.py -n 192.168.10.0/24``` (only on networks you are responsible for)
* Run the checks:
  * Tests: ```uv run pytest```
  * Lint: ```uv run ruff check .```
  * Known vulnerabilities in dependencies: ```uv run pip-audit```

### Continuous integration
GitHub Actions (`.github/workflows/ci.yml`) runs on every push to `master`, on pull requests and weekly:
* ruff, pip-audit, and the tests with deprecation warnings treated as errors (Python 3.12);
* the tests on Linux and Windows with Python 3.10 and 3.14;
* for the Angular client (Node.js 24): npm audit, lint, unit tests, production build and Playwright end-to-end tests.

`uv sync --locked` fails when `uv.lock` is out of date with `pyproject.toml`: run `uv lock` and commit it.
Dependabot (`.github/dependabot.yml`) opens weekly update pull requests for the Python dependencies, the client npm packages (Angular major versions excluded: use `ng update`) and the actions.

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
* `NEVERDIE_TRUSTED_PROXIES`: number of reverse proxies in front of the app (default `0`). Set it to `1` behind a single proxy so that the client address and scheme are read from `X-Forwarded-For` / `X-Forwarded-Proto`. Leave it at `0` when clients connect directly, otherwise they could spoof their address.

After 5 failed logins from one address within 5 minutes, further attempts are refused (HTTP 429).

Every response carries security headers (Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Referrer-Policy), plus Strict-Transport-Security when `NEVERDIE_COOKIE_SECURE=1`. API responses are never cached.

## Production deployment
Keep the app listening on `127.0.0.1` (the default) and put a TLS reverse proxy in front of it. Example with [Caddy](https://caddyserver.com/), which obtains the certificate automatically:
```
monitor.example.com {
    reverse_proxy 127.0.0.1:5000
}
```
Equivalent nginx location (inside a `server` block configured for TLS):
```
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```
Then start the app with:
```
NEVERDIE_COOKIE_SECURE=1 NEVERDIE_TRUSTED_PROXIES=1 uv run python start.py
```
