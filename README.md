# Nerverdie
Python monitor servers

## Development install
Requires Python 3.10 or later. Dependencies are declared in `pyproject.toml`
and pinned in `uv.lock`.

### With pip only (automatic virtual environment)
No tool to install besides Python:
```
python scripts/run.py
```
The first run creates `.venv`, installs the dependencies in it with pip (`pip install -e .`) and starts the web service; later runs start right away, and the dependencies are installed again only when `pyproject.toml` changes. The arguments go to `start.py` (`python scripts/run.py -P 8080`), unless the first one is another script: `python scripts/run.py manage.py create-user <username>`, `python scripts/run.py console.py`.

* `python scripts/bootstrap.py` only creates or updates `.venv`; `--dev` adds pytest, ruff and pip-audit, `--recreate` builds it again from scratch. `NEVERDIE_VENV` sets another directory.
* `make venv` (with the dev tools) and `make run` do the same. `make serve` uses `.venv` too when uv is not installed.
* On Debian or Ubuntu, Python needs its venv module: `sudo apt install python3-venv` (the script says so when it is missing).
* `pip install .` also works, to install the server package and its dependencies in an environment of your own.

### With uv
Install [uv](https://docs.astral.sh/uv/) (for instance `python -m pip install --user uv`), then:
```
uv sync
```

* Run the API and the UI together (development):
  ```
  make serve
  ```
  The API runs on http://127.0.0.1:5000 and the UI dev server on http://localhost:4200 (it forwards `/api` to the API); see [Configuration](#configuration-address-and-ports) to change the ports. Requires Node.js 22 or later; client dependencies are installed on first run. `make serve-api` starts the API only. Ctrl+C stops everything.
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

## Configuration (address and ports)
The web service listens on `127.0.0.1:5000` with 8 request threads by default. Each setting comes from, by priority:
1. the command line: `python start.py -H <host> -P <port> -t <threads>` (or `python scripts/run.py -P <port>`);
2. an environment variable: `NEVERDIE_HOST`, `NEVERDIE_PORT`, `NEVERDIE_THREADS`;
3. the configuration file `etc/neverdie.yml` (or the file named by `NEVERDIE_CONFIG`);
4. the default.

```yaml
server:
  host: 127.0.0.1   # 0.0.0.0: every interface
  port: 5000
  threads: 8
dev:
  ui_port: 4200     # Angular dev server of `make serve` (or NEVERDIE_UI_PORT)
```
Every setting of `etc/neverdie.yml` is commented out at first: uncomment the ones to change. A wrong value or an unknown setting stops the start with a message naming it. `python -m server.settings.config` prints the resulting values.

`make serve` follows the same configuration: the API starts on the configured port, the UI dev server on `dev.ui_port`, and its proxy forwards `/api` to the API port (`client/proxy.conf.mjs`, `NEVERDIE_API_URL`).

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

The *Per core* / *Overall* switch of the CPU chart shows one line per core or the overall load (the mean of the cores, like the system-wide CPU percent). The choice is saved with the dashboard layout.

The range and the refresh interval are kept in the URL (`/?from=now-6h&to=now&refresh=30s`), so a view can be bookmarked or shared.

*Customize* (next to the time range) opens the dashboard editor: show or hide each status tile and chart, reorder the charts (drag the rows or use the arrows), and set each chart to half or full width and to a small, medium or large height. The layout is saved in the browser; *Reset* brings the default one back (every chart at full width). Hidden charts are not loaded.

Long ranges are averaged by the server into about 1200 points per chart. History API (logged-in users): `GET /api/history/<cpu|memory|network>?from=<ms>&to=<ms>&points=<n>`, with `from`/`to` in epoch milliseconds (default: the last hour).

## Database size limit
The collector stores a sample every 3 seconds (CPU load per core, memory and network traffic), so the database grows forever by default. To cap it, open the administration screen (*Administration* in the toolbar, `/admin`), turn on *Limit the database size* and enter a limit in MB. The screen also shows the current size, the number of stored samples and their time range.

When the data reaches the limit, the oldest samples are deleted until 90 % of the limit is used, then the new samples fill the freed space: the history slides, keeping the most recent data. Users and settings are never deleted. A new limit is applied as soon as it is saved.

The limit applies to the data held in the database. Deleted rows leave free pages that SQLite reuses for new samples, so the file on disk does not shrink by itself: *Compact* (`VACUUM`) gives the free space back to the file system. It rewrites the whole file, so expect a short pause on large databases.

The same settings are available through the API (logged-in users): `GET /api/admin/storage`, `PUT /api/admin/storage` with `{"limit_mb": 500}` (`null` or `0`: unlimited) and `POST /api/admin/storage/compact`.

## Production deployment
### Automatic: `make install` (Linux, nginx, HTTPS)
On a Linux server with systemd (Debian, Ubuntu, Fedora, RHEL...), run as the user that will run Neverdie (not root, it asks for sudo when needed):
```
make install
```
(or `python scripts/install.py`). It:
1. creates or updates `.venv` and builds the UI (`npm ci`, `npm run build`; Node.js 22 or later, or `--skip-build` with a `client/dist` built elsewhere);
2. installs nginx when missing (apt, dnf, yum or zypper);
3. copies the built UI to `/var/www/neverdie`: nginx serves it, and forwards `/api` to the app on `127.0.0.1:<server.port>`;
4. creates the certificate in `/etc/neverdie/tls`: self-signed by default, for the server name, `localhost` and `127.0.0.1`, valid 825 days and renewed by `make install` 30 days before it expires;
5. writes the nginx site (`/etc/nginx/sites-available/neverdie`, or `conf.d/neverdie.conf`): HTTP redirects to HTTPS, TLS 1.2 and 1.3, the app's security headers plus HSTS, long caching of the build files. On Debian and Ubuntu the stock default site is turned off;
6. installs the systemd service `neverdie` (running `start.py` from `.venv` with `NEVERDIE_COOKIE_SECURE=1` and `NEVERDIE_TRUSTED_PROXIES=1`), starts it, and checks that the site answers over HTTPS.

Settings, in the `install` section of `etc/neverdie.yml` (or the variables in brackets):
```yaml
install:
  server_name: monitor.example.com  # (NEVERDIE_SERVER_NAME) one or more names / IP addresses, see below
  http_port: 80                     # (NEVERDIE_HTTP_PORT)
  https_port: 443                   # (NEVERDIE_HTTPS_PORT)
  certificate: self-signed          # (NEVERDIE_CERTIFICATE) or letsencrypt
  email: ops@example.com            # (NEVERDIE_LETSENCRYPT_EMAIL) Let's Encrypt notices, optional
```
* **Server names**: nginx shows Neverdie for links whose name is in `server_name`; a link with another name or address shows the *default site* of the port when nginx serves other sites. List every name and address used to open the monitor: `server_name: [monitor.example.com, 192.168.1.20]` (or `"monitor.example.com 192.168.1.20"`); the first one is the main name. When it is not set, `make install` uses the names and IPv4 addresses of the machine. It stops when another nginx site already uses one of these names, and tells which site answers the other links.
* **Self-signed** (default): browsers warn about the certificate until it is trusted on the computers that open the site (import `/etc/neverdie/tls/neverdie.crt`). Fine on a private network.
* **Let's Encrypt** (`certificate: letsencrypt`): a certificate trusted by browsers, for a public domain name that points to this server, with port 80 reachable from the Internet. certbot is installed when missing, asks you to accept the Let's Encrypt terms the first time, and renews the certificate by itself (nginx is reloaded after each renewal).

**Update** an installed Neverdie with:
```
make update
```
(or `python scripts/install.py --update`). It pulls the new version (`git pull --ff-only`, skipped with `--no-pull` or outside a git checkout), updates `.venv`, rebuilds the UI (running `npm ci` again when `package-lock.json` changed), publishes it to `/var/www/neverdie` and restarts the `neverdie` service, then checks that the site answers. It keeps the configuration as installed: the nginx site, the certificate, the systemd unit and `etc/neverdie.yml` are not changed (a local change to `etc/neverdie.yml` that the new version also changes stops `git pull`: keep your settings in a file outside the checkout with `NEVERDIE_CONFIG`). It refuses to go on when `server.host` or `server.port` changed since `make install` (nginx would forward the API to the old address), and tells when an `install` setting changed: run `make install` to apply those.

Run `make install` again to apply a new configuration. Options: `--dry-run DIR` writes the nginx site and the service to `DIR` and prints the commands without changing anything (works on any system), `--no-service` leaves the app out (nginx only), `--renew-certificate` makes a new self-signed certificate. `make uninstall` removes the service, the nginx site and `/var/www/neverdie` (it keeps nginx, the certificates, the database and `.venv`).

Logs: `journalctl -u neverdie -f`. With SELinux enforcing, `make install` allows nginx to connect to the app (`httpd_can_network_connect`).

### Manual
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
