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

## Login security
Every login attempt is journaled for 90 days (time, user name, address, result). The *Login security* panel of the administration screen shows:
* the successful, failed and refused logins of the last 24 hours and the locked accounts,
* a chart of the connections over the last 24 hours, 7 days or 30 days,
* the last login attempts,
* the account lock policy, and every account with its failed logins and lock.

Lock policy: after a number of failed logins in a row (5 by default), an account is locked for a while (15 minutes by default) or until an administrator unlocks it. A successful login resets the count. While an account is locked, its logins are refused even with the right password (HTTP 423). The per address limit above still applies on top of it: the account lock also stops attempts spread over many addresses.

An administrator unlocks an account from the panel (*Unlock*), or from the command line, which also works when every administrator is locked out:
```
uv run python manage.py unlock-user <username>
```
(`set-password` unlocks the account too, and `list-users` shows the locked ones.)

The same is available through the API (logged-in users): `GET /api/admin/security`, `PUT /api/admin/security` with `{"max_attempts": 5, "lock_minutes": 15}` (`max_attempts` `null`: never lock, `lock_minutes` `0`: until unlocked), `POST /api/admin/security/unlock` with `{"username": "..."}` and `GET /api/admin/security/history?from=<ms>&to=<ms>`.

Every response carries security headers (Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Referrer-Policy), plus Strict-Transport-Security when `NEVERDIE_COOKIE_SECURE=1`. API responses are never cached.

## Dashboard time range
The dashboard charts the CPU load per core, the memory and the network traffic over a time range picked at the top right, the way Grafana does:
* the time range button opens quick ranges (*Last 5 minutes* to *Last 30 days*, with a search box) and an absolute range: *From* and *To* take a relative time like `now-6h` or a date like `2026-11-25 10:00:00`. The last absolute ranges used are listed under the form.
* the arrows move the range backward and forward by half its span, the magnifier zooms out (twice the span).
* drag over a chart to zoom into the selected span; double-click a chart to zoom out.
* the refresh button reloads the charts, and the menu next to it sets the auto-refresh interval (*Off* to *5m*).

The range and the refresh interval are kept in the URL (`/?from=now-6h&to=now&refresh=30s`), so a view can be bookmarked or shared.

*Customize* (next to the time range) opens the dashboard editor: show or hide each status tile and chart, reorder the charts (drag the rows or use the arrows), and set each chart to half or full width and to a small, medium or large height. The layout is saved in the browser; *Reset* brings the default one back (every chart at full width). Hidden charts are not loaded.

Long ranges are averaged by the server into about 1200 points per chart. History API (logged-in users): `GET /api/history/<cpu|memory|network>?from=<ms>&to=<ms>&points=<n>`, with `from`/`to` in epoch milliseconds (default: the last hour).

## Database size limit
The collector stores a sample every 3 seconds (CPU load per core, memory and network traffic), so the database grows forever by default. To cap it, open the administration screen (*Administration* in the toolbar, `/admin`), turn on *Limit the database size* and enter a limit in MB. The screen also shows the current size, the number of stored samples and their time range.

When the data reaches the limit, the oldest samples are deleted until 90 % of the limit is used, then the new samples fill the freed space: the history slides, keeping the most recent data. Users and settings are never deleted. A new limit is applied as soon as it is saved.

The limit applies to the data held in the database. Deleted rows leave free pages that SQLite reuses for new samples, so the file on disk does not shrink by itself: *Compact* (`VACUUM`) gives the free space back to the file system. It rewrites the whole file, so expect a short pause on large databases.

The same settings are available through the API (logged-in users): `GET /api/admin/storage`, `PUT /api/admin/storage` with `{"limit_mb": 500}` (`null` or `0`: unlimited) and `POST /api/admin/storage/compact`.

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
