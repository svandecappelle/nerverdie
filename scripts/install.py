#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Install Neverdie for production on Linux: nginx in front, over HTTPS.

    make install                              # or: python scripts/install.py
    python scripts/install.py --dry-run out   # write the files to out/, change nothing
    make uninstall                            # or: python scripts/install.py --uninstall

Run it as the user that will run Neverdie (not root): it asks for sudo when
needed. It:
1. creates or updates .venv (scripts/bootstrap.py) and builds the UI (npm);
2. installs nginx (and certbot for Let's Encrypt) when missing;
3. copies the built UI to /var/www/neverdie, served by nginx, which forwards
   /api to the app on 127.0.0.1;
4. creates the certificate: self-signed (default) or Let's Encrypt;
5. writes the nginx site (HTTP redirected to HTTPS) and a systemd service
   for the app, then starts both and checks that the site answers.

Settings: the `install` and `server` sections of etc/neverdie.yml, or the
NEVERDIE_SERVER_NAME, NEVERDIE_HTTPS_PORT... variables (see README). Run it
again after an update (git pull): it rebuilds the UI and restarts the app.
"""

import argparse
import getpass
import ipaddress
import json
import os
import re
import shlex
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS)
from bootstrap import ROOT, ensure_venv  # noqa: E402

sys.path.insert(0, ROOT)
from server.settings.security import SECURITY_HEADERS  # noqa: E402  (standard library only)

CLIENT = os.path.join(ROOT, 'client')
DIST = os.path.join(CLIENT, 'dist')
WEB_ROOT = '/var/www/neverdie'
ACME_ROOT = '/var/lib/neverdie/acme'
ETC = '/etc/neverdie'
TLS_DIR = ETC + '/tls'
STATE = ETC + '/install.json'
SERVICE_NAME = 'neverdie'
SERVICE_FILE = '/etc/systemd/system/neverdie.service'
SITES_AVAILABLE = '/etc/nginx/sites-available'
SITES_ENABLED = '/etc/nginx/sites-enabled'
CONF_D = '/etc/nginx/conf.d'
LETSENCRYPT_LIVE = '/etc/letsencrypt/live'
CERT_DAYS = 825
RENEW_BEFORE_SECONDS = 30 * 86400
# NEVERDIE_* variables of the install passed on to the service (not the secret key:
# the unit file is world readable; the app keeps its key in instance/secret_key).
SERVICE_VARIABLES = ('NEVERDIE_CONFIG', 'NEVERDIE_DB', 'NEVERDIE_INSTANCE_DIR',
                     'NEVERDIE_HOST', 'NEVERDIE_PORT', 'NEVERDIE_THREADS')
PATH_VARIABLES = ('NEVERDIE_CONFIG', 'NEVERDIE_DB', 'NEVERDIE_INSTANCE_DIR')
HSTS = 'max-age=31536000; includeSubDomains'
# Mozilla "intermediate" TLS profile.
CIPHERS = ('ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:'
           'ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305')
PACKAGE_MANAGERS = (
    ('apt-get', ['apt-get', 'install', '-y'], ['apt-get', 'update']),
    ('dnf', ['dnf', 'install', '-y'], None),
    ('yum', ['yum', 'install', '-y'], None),
    ('zypper', ['zypper', '--non-interactive', 'install'], None),
)


class InstallError(Exception):
    pass


def say(message):
    print('install: ' + message, flush=True)


# --- pure helpers (unit tested) -------------------------------------------------

def is_ip(name):
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        return False


def certificate_names(server_name):
    """Names of the self-signed certificate: the server name, then localhost."""
    names = []
    for name in (server_name, 'localhost', '127.0.0.1', '::1'):
        if name and name not in names:
            names.append(name)
    return names


def subject_alt_names(names):
    return ','.join(('IP:%s' if is_ip(name) else 'DNS:%s') % name for name in names)


def parse_nginx_version(output):
    """(1, 24, 0) from `nginx -v` output ("nginx version: nginx/1.24.0 (Ubuntu)"), or None."""
    match = re.search(r'nginx/(\d+)\.(\d+)\.(\d+)', output or '')
    return tuple(int(part) for part in match.groups()) if match else None


def site_url(server_name, https_port):
    host = '[%s]' % server_name if ':' in server_name else server_name
    return 'https://%s%s/' % (host, '' if https_port == 443 else ':%d' % https_port)


def backend_url(host, port):
    """Address nginx forwards /api to (the app listens on host:port)."""
    if host in ('0.0.0.0', '', '*'):  # noqa: S104 (connecting to it)
        host = '127.0.0.1'
    elif host == '::':
        host = '::1'
    if ':' in host:
        host = '[%s]' % host
    return 'http://%s:%d' % (host, port)


def _headers(indent, cache=None):
    lines = ['add_header %s "%s" always;' % (name, value) for name, value in SECURITY_HEADERS.items()]
    lines.append('add_header Strict-Transport-Security "%s" always;' % HSTS)
    if cache:
        lines.append('add_header Cache-Control "%s" always;' % cache)
    return ''.join('%s%s\n' % (indent, line) for line in lines)


def render_nginx(settings, certificate, key, nginx_version=None, ipv6=True):
    """nginx site: HTTP redirected to HTTPS, the UI from WEB_ROOT, /api forwarded to the app."""
    name = settings['server_name']
    http_port, https_port = settings['http_port'], settings['https_port']
    modern_http2 = nginx_version is None or nginx_version >= (1, 25, 1)
    listen_http = ['listen %d;' % http_port] + (['listen [::]:%d;' % http_port] if ipv6 else [])
    ssl_suffix = ' ssl' if modern_http2 else ' ssl http2'
    listen_https = ['listen %d%s;' % (https_port, ssl_suffix)]
    if ipv6:
        listen_https.append('listen [::]:%d%s;' % (https_port, ssl_suffix))
    if modern_http2:
        listen_https.append('http2 on;')
    redirect = 'https://$host%s$request_uri' % ('' if https_port == 443 else ':%d' % https_port)
    backend = backend_url(settings['host'], settings['port'])
    indent = ' ' * 8
    return """\
# Neverdie, written by scripts/install.py (make install): run it again rather than
# editing this file, which it overwrites.

server {
%(listen_http)s
    server_name %(name)s;
    server_tokens off;

    # Let's Encrypt HTTP challenge.
    location /.well-known/acme-challenge/ {
        root %(acme)s;
    }

    location / {
        return 301 %(redirect)s;
    }
}

server {
%(listen_https)s
    server_name %(name)s;
    server_tokens off;

    ssl_certificate %(certificate)s;
    ssl_certificate_key %(key)s;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers %(ciphers)s;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:NeverdieTLS:10m;
    ssl_session_tickets off;

    client_max_body_size 1m;
    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;

    # The built UI (client/dist), copied by make install.
    root %(web_root)s;
    index index.html;

    # The API: the app on %(backend)s (systemd service neverdie). It sends its own
    # security headers. ^~: no regex location below applies to /api/ URLs.
    location ^~ /api/ {
        proxy_pass %(backend)s;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_read_timeout 60s;
    }

    location = /api {
        return 404;
    }

    # File names of the build carry a hash of their content: cache them for good.
    location ~* \\.(?:js|css)$ {
        try_files $uri =404;
        expires 1y;
%(headers_immutable)s    }

    location /media/ {
        try_files $uri =404;
        expires 1y;
%(headers_immutable)s    }

    # Everything else is a page of the single page application.
    location / {
        try_files $uri $uri/ /index.html;
%(headers_page)s    }
}
""" % {
        'listen_http': ''.join('    %s\n' % line for line in listen_http).rstrip('\n'),
        'listen_https': ''.join('    %s\n' % line for line in listen_https).rstrip('\n'),
        'name': name,
        'acme': ACME_ROOT,
        'redirect': redirect,
        'certificate': certificate,
        'key': key,
        'ciphers': CIPHERS,
        'web_root': WEB_ROOT,
        'backend': backend,
        'headers_immutable': _headers(indent, 'public, max-age=31536000, immutable'),
        'headers_page': _headers(indent, 'no-cache'),
    }


def systemd_path(text):
    """A path written as is in a unit file (WorkingDirectory=): only specifiers need escaping."""
    if '\n' in text or '\r' in text:
        raise InstallError('a value for the systemd service contains a line break: %r' % text)
    return text.replace('%', '%%')


def systemd_quote(text):
    """A value inside double quotes in a unit file (Environment=, ExecStart=)."""
    return systemd_path(text).replace('\\', '\\\\').replace('"', '\\"')


def service_environment(environ, cwd):
    """Environment of the service: behind a TLS proxy, plus the NEVERDIE_* settings of the install."""
    env = {'NEVERDIE_COOKIE_SECURE': '1', 'NEVERDIE_TRUSTED_PROXIES': '1', 'PYTHONUNBUFFERED': '1'}
    for name in SERVICE_VARIABLES:
        value = environ.get(name, '').strip()
        if value:
            env[name] = os.path.abspath(os.path.join(cwd, value)) if name in PATH_VARIABLES else value
    return env


def render_service(user, python, env):
    environment = ''.join('Environment="%s=%s"\n' % (name, systemd_quote(value)) for name, value in env.items())
    return """\
# Neverdie, written by scripts/install.py (make install).
[Unit]
Description=Neverdie server monitoring
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=%(user)s
WorkingDirectory=%(root)s
%(environment)sExecStart="%(python)s" "%(start)s"
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full

[Install]
WantedBy=multi-user.target
""" % {
        'user': user,
        'root': systemd_path(ROOT),
        'environment': environment,
        'python': systemd_quote(python),
        'start': systemd_quote(os.path.join(ROOT, 'start.py')),
    }


def check_letsencrypt(settings):
    name = settings['server_name']
    if is_ip(name) or '.' not in name or name.endswith(('.local', '.localhost', '.lan', '.internal')):
        raise InstallError('Let\'s Encrypt needs a public domain name in install.server_name '
                           '(NEVERDIE_SERVER_NAME), pointing to this machine; got %r. Use certificate: '
                           'self-signed otherwise.' % name)
    if settings['http_port'] != 80:
        raise InstallError('Let\'s Encrypt checks the domain over HTTP on port 80: install.http_port must be 80.')


# --- system actions --------------------------------------------------------------

class Installer(object):
    def __init__(self, dry_run=None):
        self.dry_run = os.path.abspath(dry_run) if dry_run else None
        if self.dry_run:
            os.makedirs(self.dry_run, exist_ok=True)

    def run(self, command, check=True, capture=False, **kwargs):
        """Runs a command as this user."""
        result = subprocess.run(command, text=True, capture_output=capture, **kwargs)
        if check and result.returncode != 0:
            details = ('\n' + (result.stderr or result.stdout).strip()) if capture else ''
            raise InstallError('%s failed (exit %d)%s' % (shlex.join(command), result.returncode, details))
        return result

    def root(self, command, check=True, capture=False):
        """Runs a command as root (through sudo); only printed in a dry run."""
        if self.dry_run:
            print('  would run: %s' % shlex.join(command))
            return subprocess.CompletedProcess(command, 0, '', '')
        prefix = [] if os.geteuid() == 0 else ['sudo']
        return self.run(prefix + command, check=check, capture=capture)

    def put(self, content, destination, mode='644'):
        """Writes a root owned file; in a dry run, into the dry run directory."""
        if self.dry_run:
            path = os.path.join(self.dry_run, os.path.basename(destination))
            with open(path, 'w', encoding='utf-8', newline='\n') as file:
                file.write(content)
            print('  would write %s (see %s)' % (destination, path))
            return
        with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', suffix='.neverdie') as file:
            file.write(content)
        try:
            self.root(['install', '-D', '-m', mode, '-o', 'root', '-g', 'root', file.name, destination])
        finally:
            os.unlink(file.name)

    def root_file_exists(self, path):
        if self.dry_run:
            return os.path.exists(path)
        return self.root(['test', '-e', path], check=False).returncode == 0


def find_program(name):
    for path in (shutil.which(name), '/usr/sbin/' + name, '/usr/bin/' + name, '/sbin/' + name):
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def install_packages(installer, packages):
    for manager, install, update in PACKAGE_MANAGERS:
        if find_program(manager):
            say('installing %s (%s)...' % (', '.join(packages), manager))
            if update:
                installer.root(update)
            installer.root(install + packages)
            return
    raise InstallError('no known package manager: install %s yourself, then run again.' % ', '.join(packages))


def ensure_program(installer, name, package=None):
    path = find_program(name)
    if not path:
        if installer.dry_run:
            print('  would install the %s package' % (package or name))
            return name
        install_packages(installer, [package or name])
        path = find_program(name)
        if not path:
            raise InstallError('%s is still missing after installing %s.' % (name, package or name))
    return path


def ipv6_available():
    if not socket.has_ipv6:
        return False
    try:
        socket.socket(socket.AF_INET6, socket.SOCK_STREAM).close()
        return True
    except OSError:
        return False


def read_settings(python):
    result = subprocess.run([python, '-m', 'server.settings.config'], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise InstallError((result.stderr or result.stdout).strip())
    settings = json.loads(result.stdout.strip().splitlines()[-1])
    if not settings['server_name']:
        settings['server_name'] = (socket.getfqdn() or socket.gethostname()).lower()
    if settings['http_port'] == settings['https_port']:
        raise InstallError('install.http_port and install.https_port must differ.')
    if settings['port'] in (settings['http_port'], settings['https_port']):
        raise InstallError('server.port (%d) is the port of the app behind nginx: it must differ from '
                           'install.http_port and install.https_port.' % settings['port'])
    return settings


def build_ui(installer, skip):
    index = os.path.join(DIST, 'index.html')
    if skip or installer.dry_run:
        if not os.path.isfile(index) and not installer.dry_run:
            raise InstallError('client/dist/index.html is missing: build the UI (drop --skip-build).')
        return
    npm = shutil.which('npm')
    if not npm:
        if os.path.isfile(index):
            say('npm not found: using the UI already built in client/dist.')
            return
        raise InstallError('npm not found: install Node.js 22 or later to build the UI '
                           '(or copy a built client/dist and use --skip-build).')
    from serve import check_node
    check_node()
    if not os.path.isdir(os.path.join(CLIENT, 'node_modules')):
        say('installing the client dependencies (npm ci)...')
        installer.run([npm, 'ci', '--no-audit', '--no-fund'], cwd=CLIENT)
    say('building the UI (npm run build)...')
    installer.run([npm, 'run', 'build'], cwd=CLIENT)
    if not os.path.isfile(index):
        raise InstallError('the UI build did not produce client/dist/index.html.')


def publish_ui(installer):
    say('copying the UI to %s...' % WEB_ROOT)
    staging, old = WEB_ROOT + '.new', WEB_ROOT + '.old'
    installer.root(['rm', '-rf', staging, old])
    installer.root(['install', '-d', '-m', '755', os.path.dirname(WEB_ROOT)])
    installer.root(['cp', '-r', DIST, staging])
    installer.root(['chown', '-R', 'root:root', staging])
    installer.root(['chmod', '-R', 'u=rwX,go=rX', staging])
    if installer.root_file_exists(WEB_ROOT):
        installer.root(['mv', WEB_ROOT, old])
    installer.root(['mv', staging, WEB_ROOT])
    installer.root(['rm', '-rf', old])


def self_signed_certificate(installer, names, renew=False):
    """Creates (or renews) the self-signed certificate; returns (certificate, key) paths."""
    certificate, key, names_file = TLS_DIR + '/neverdie.crt', TLS_DIR + '/neverdie.key', TLS_DIR + '/names.json'
    if not renew and not installer.dry_run and certificate_is_current(installer, certificate, names_file, names):
        say('keeping the self-signed certificate of %s (%s).' % (', '.join(names), certificate))
        return certificate, key
    openssl = ensure_program(installer, 'openssl')
    say('creating a self-signed certificate for %s (valid %d days)...' % (', '.join(names), CERT_DAYS))
    with tempfile.TemporaryDirectory() as work:
        os.chmod(work, 0o700)
        crt_tmp, key_tmp = os.path.join(work, 'neverdie.crt'), os.path.join(work, 'neverdie.key')
        create_certificate(installer, openssl, names, crt_tmp, key_tmp)
        names_tmp = os.path.join(work, 'names.json')
        with open(names_tmp, 'w', encoding='utf-8') as file:
            json.dump(names, file)
        installer.root(['install', '-d', '-m', '755', TLS_DIR])
        installer.root(['install', '-m', '644', '-o', 'root', '-g', 'root', crt_tmp, certificate])
        installer.root(['install', '-m', '600', '-o', 'root', '-g', 'root', key_tmp, key])
        installer.root(['install', '-m', '644', '-o', 'root', '-g', 'root', names_tmp, names_file])
    return certificate, key


def create_certificate(installer, openssl, names, certificate, key):
    command = [openssl, 'req', '-x509', '-newkey', 'rsa:3072', '-sha256', '-days', str(CERT_DAYS), '-nodes',
               '-keyout', key, '-out', certificate, '-subj', '/CN=Neverdie',
               '-addext', 'subjectAltName=' + subject_alt_names(names),
               '-addext', 'basicConstraints=critical,CA:FALSE',
               '-addext', 'keyUsage=critical,digitalSignature,keyEncipherment',
               '-addext', 'extendedKeyUsage=serverAuth']
    if installer.dry_run:
        print('  would run: %s' % shlex.join(command))
        return
    installer.run(command, capture=True)


def certificate_is_current(installer, certificate, names_file, names):
    """The certificate exists, has these names and is valid for 30 more days."""
    try:
        with open(names_file, encoding='utf-8') as file:
            if json.load(file) != names:
                return False
    except (OSError, ValueError):
        return False
    openssl = find_program('openssl')
    return bool(openssl) and subprocess.run(
        [openssl, 'x509', '-checkend', str(RENEW_BEFORE_SECONDS), '-noout', '-in', certificate],
        capture_output=True).returncode == 0


def nginx_layout(installer):
    """(site file, enabled link or None): Debian style sites-available, else conf.d."""
    if os.path.isdir(SITES_AVAILABLE) and os.path.isdir(SITES_ENABLED):
        return SITES_AVAILABLE + '/neverdie', SITES_ENABLED + '/neverdie'
    return CONF_D + '/neverdie.conf', None


def disable_stock_default_site(installer, settings):
    """Debian's default site also answers on port 80: turn it off (uninstall turns it back on)."""
    link = SITES_ENABLED + '/default'
    if settings['http_port'] != 80 or not os.path.islink(link):
        return False
    if os.path.realpath(link) != os.path.realpath(SITES_AVAILABLE + '/default'):
        return False
    say('turning off the stock nginx default site (it answers on port 80 too).')
    installer.root(['rm', '-f', link])
    return True


def apply_nginx(installer, nginx):
    installer.root([nginx, '-t'], capture=not installer.dry_run)
    if installer.dry_run or subprocess.run(['systemctl', 'is-active', '--quiet', 'nginx']).returncode == 0:
        installer.root(['systemctl', 'reload', 'nginx'])
    else:
        installer.root(['systemctl', 'enable', '--now', 'nginx'])


def write_site(installer, nginx, settings, certificate, key, site, link, version):
    installer.put(render_nginx(settings, certificate, key, version, ipv6_available()), site)
    if link:
        installer.root(['ln', '-sfn', site, link])
    apply_nginx(installer, nginx)


def letsencrypt_certificate(installer, settings):
    name = settings['server_name']
    live = '%s/%s' % (LETSENCRYPT_LIVE, name)
    certificate, key = live + '/fullchain.pem', live + '/privkey.pem'
    if installer.root_file_exists(certificate):
        say('using the Let\'s Encrypt certificate of %s (certbot renews it).' % name)
        return certificate, key, False
    return certificate, key, True


def request_letsencrypt(installer, settings):
    certbot = ensure_program(installer, 'certbot')
    say('asking Let\'s Encrypt for a certificate of %s (certbot may ask you to accept its terms)...'
        % settings['server_name'])
    command = [certbot, 'certonly', '--webroot', '-w', ACME_ROOT, '-d', settings['server_name'],
               '--deploy-hook', 'systemctl reload nginx']
    command += ['--email', settings['email']] if settings['email'] else ['--register-unsafely-without-email']
    installer.root(command)


def install_service(installer, python):
    user = getpass.getuser()
    env = service_environment(os.environ, os.getcwd())
    installer.put(render_service(user, python, env), SERVICE_FILE)
    installer.root(['systemctl', 'daemon-reload'])
    installer.root(['systemctl', 'enable', SERVICE_NAME])
    installer.root(['systemctl', 'restart', SERVICE_NAME])
    return user


def wait_for(url, expected, timeout, host=None, insecure=False):
    """Status of the first answer of `url` among `expected`, or the last error after `timeout` seconds."""
    context = ssl._create_unverified_context() if insecure else None  # noqa: S323 (own self-signed site)
    request = urllib.request.Request(url, headers={'Host': host} if host else {})  # noqa: S310 (http/https only)
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(request, timeout=5, context=context) as response:  # noqa: S310
                last = response.status
        except urllib.error.HTTPError as error:
            last = error.code
        except (urllib.error.URLError, OSError) as error:
            last = str(error)
        if last in expected:
            return last
        time.sleep(1)
    return last


def check_site(installer, settings, service):
    if installer.dry_run:
        return
    backend = backend_url(settings['host'], settings['port'])
    if service:
        status = wait_for(backend + '/api/auth', (401,), 60)
        if status != 401 or subprocess.run(['systemctl', 'is-active', '--quiet', SERVICE_NAME]).returncode:
            raise InstallError('the app did not start (%s). See: journalctl -u %s -n 50' % (status, SERVICE_NAME))
        say('the app answers on %s.' % backend)
    https = 'https://127.0.0.1:%d' % settings['https_port']
    page = wait_for(https + '/', (200,), 30, host=settings['server_name'], insecure=True)
    api = wait_for(https + '/api/auth', (401,), 30, host=settings['server_name'], insecure=True)
    if page != 200 or (service and api != 401):
        raise InstallError('nginx does not serve the site as expected (page: %s, API: %s). '
                           'See: sudo nginx -t; journalctl -u nginx' % (page, api))
    say('nginx serves the UI and forwards the API over HTTPS.')


def allow_proxy_with_selinux(installer):
    """With SELinux enforcing (Fedora, RHEL...), nginx may only connect to the app once allowed."""
    getenforce = find_program('getenforce')
    if not getenforce or installer.run([getenforce], check=False, capture=True).stdout.strip() != 'Enforcing':
        return
    say('SELinux: allowing nginx to connect to the app (httpd_can_network_connect).')
    installer.root(['setsebool', '-P', 'httpd_can_network_connect', '1'])


def install(args):
    installer = Installer(args.dry_run)
    python = ensure_venv()
    settings = read_settings(python)
    if settings['certificate'] == 'letsencrypt':
        check_letsencrypt(settings)
    if settings['host'] not in ('127.0.0.1', 'localhost', '::1'):
        say('warning: server.host is %s, so the app is also reachable without nginx (and without HTTPS) '
            'on port %d. 127.0.0.1 is recommended behind nginx.' % (settings['host'], settings['port']))
    build_ui(installer, args.skip_build)

    nginx = ensure_program(installer, 'nginx')
    version = None
    if not installer.dry_run:
        version = parse_nginx_version(installer.run([nginx, '-v'], capture=True).stderr)
    site, link = nginx_layout(installer)
    publish_ui(installer)
    installer.root(['install', '-d', '-m', '755', ACME_ROOT])
    disabled_default = disable_stock_default_site(installer, settings)
    allow_proxy_with_selinux(installer)

    names = certificate_names(settings['server_name'])
    if settings['certificate'] == 'letsencrypt':
        certificate, key, missing = letsencrypt_certificate(installer, settings)
        if missing:
            # nginx needs a certificate to start: a self-signed one until Let's Encrypt answers.
            temporary = self_signed_certificate(installer, names)
            write_site(installer, nginx, settings, temporary[0], temporary[1], site, link, version)
            request_letsencrypt(installer, settings)
    else:
        certificate, key = self_signed_certificate(installer, names, renew=args.renew_certificate)

    say('writing the nginx site %s...' % site)
    write_site(installer, nginx, settings, certificate, key, site, link, version)

    user = None
    if not args.no_service:
        say('installing the systemd service %s...' % SERVICE_NAME)
        user = install_service(installer, python)

    state = {
        'site': site,
        'link': link,
        'web_root': WEB_ROOT,
        'service': None if args.no_service else SERVICE_FILE,
        'certificate': settings['certificate'],
        'server_name': settings['server_name'],
        # Keep the record of a default site turned off by an earlier install.
        'disabled_default_site': disabled_default or read_state().get('disabled_default_site', False),
    }
    installer.put(json.dumps(state, indent=2) + '\n', STATE)
    check_site(installer, settings, not args.no_service)

    url = site_url(settings['server_name'], settings['https_port'])
    if installer.dry_run:
        say('dry run: nothing was changed. Files written to %s.' % installer.dry_run)
        return 0
    print()
    print('Neverdie is installed: %s' % url)
    if settings['certificate'] == 'self-signed':
        print('* The certificate is self-signed: browsers warn about it until you trust %s/neverdie.crt '
              'on the computers that open the site.' % TLS_DIR)
    if user:
        print('* The app runs as %s (systemd service %s): journalctl -u %s -f' % (user, SERVICE_NAME, SERVICE_NAME))
    print('* Create a user if needed: python scripts/run.py manage.py create-user <username>')
    print('* After an update (git pull), run make install again.')
    return 0


def read_state():
    try:
        with open(STATE, encoding='utf-8') as file:
            return json.load(file)
    except (OSError, ValueError):
        return {}


def uninstall(args):
    installer = Installer(args.dry_run)
    state = read_state()
    if not state:
        say('nothing to remove: %s not found (Neverdie was not installed with make install).' % STATE)
        return 0
    if state.get('service'):
        say('stopping and removing the systemd service %s...' % SERVICE_NAME)
        installer.root(['systemctl', 'disable', '--now', SERVICE_NAME], check=False)
        installer.root(['rm', '-f', SERVICE_FILE])
        installer.root(['systemctl', 'daemon-reload'])
    say('removing the nginx site...')
    for path in (state.get('link'), state.get('site')):
        if path and path.startswith('/etc/nginx/') and 'neverdie' in path:
            installer.root(['rm', '-f', path])
    if state.get('disabled_default_site') and os.path.exists(SITES_AVAILABLE + '/default'):
        say('turning the stock nginx default site back on.')
        installer.root(['ln', '-sfn', SITES_AVAILABLE + '/default', SITES_ENABLED + '/default'])
    nginx = find_program('nginx')
    if nginx:
        apply_nginx(installer, nginx)
    say('removing %s...' % WEB_ROOT)
    installer.root(['rm', '-rf', WEB_ROOT])
    installer.root(['rm', '-f', STATE])
    say('done. Kept: the certificates (%s, %s), nginx, the database and .venv.' % (TLS_DIR, LETSENCRYPT_LIVE))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Install Neverdie behind nginx with HTTPS (Linux, systemd)')
    parser.add_argument('--dry-run', metavar='DIR', help='write the files to DIR and print the commands, change nothing')
    parser.add_argument('--skip-build', action='store_true', help='use the UI already built in client/dist')
    parser.add_argument('--no-service', action='store_true', help='do not install the systemd service of the app')
    parser.add_argument('--renew-certificate', action='store_true', help='create a new self-signed certificate')
    parser.add_argument('--uninstall', action='store_true', help='remove what make install added')
    args = parser.parse_args(argv)

    if not args.dry_run:
        if not sys.platform.startswith('linux'):
            sys.exit('install: make install sets up nginx and systemd on Linux. '
                     'Use --dry-run DIR to see the files it would write.')
        if os.geteuid() == 0:
            sys.exit('install: run it as the user that will run Neverdie, not as root: it asks for sudo when needed.')
    try:
        return uninstall(args) if args.uninstall else install(args)
    except InstallError as error:
        sys.exit('install: %s' % error)


if __name__ == '__main__':
    sys.exit(main())
