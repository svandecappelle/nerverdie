"""scripts/install.py: production install behind nginx (rendering, checks, dry run)."""
import json
import os
import sys

import pytest

from scripts import install
from server.settings import config
from server.settings.security import CONTENT_SECURITY_POLICY

SETTINGS = {'host': '127.0.0.1', 'port': 5000, 'threads': 8, 'ui_port': 4200, 'server_name': 'monitor.example.com',
            'http_port': 80, 'https_port': 443, 'certificate': 'self-signed', 'email': ''}


def settings(**changes):
    return dict(SETTINGS, **changes)


def test_certificate_names_and_alt_names():
    assert install.certificate_names('monitor.example.com') == ['monitor.example.com', 'localhost', '127.0.0.1', '::1']
    assert install.certificate_names('127.0.0.1') == ['127.0.0.1', 'localhost', '::1']
    assert install.subject_alt_names(['web', '10.0.0.2', '::1']) == 'DNS:web,IP:10.0.0.2,IP:::1'


def test_parse_nginx_version():
    assert install.parse_nginx_version('nginx version: nginx/1.24.0 (Ubuntu)') == (1, 24, 0)
    assert install.parse_nginx_version('nothing') is None


def test_site_and_backend_urls():
    assert install.site_url('monitor.example.com', 443) == 'https://monitor.example.com/'
    assert install.site_url('fe80::1', 8443) == 'https://[fe80::1]:8443/'
    assert install.backend_url('0.0.0.0', 5000) == 'http://127.0.0.1:5000'
    assert install.backend_url('::', 5001) == 'http://[::1]:5001'


def test_nginx_site_redirects_to_https_and_forwards_the_api():
    site = install.render_nginx(settings(port=5050), '/tls/c.crt', '/tls/c.key', (1, 26, 0))
    assert 'server_name monitor.example.com;' in site
    assert 'return 301 https://$host$request_uri;' in site
    assert 'listen 443 ssl;' in site and 'http2 on;' in site and 'listen [::]:443 ssl;' in site
    assert 'ssl_certificate /tls/c.crt;' in site and 'ssl_certificate_key /tls/c.key;' in site
    assert 'location ^~ /api/ {' in site and 'proxy_pass http://127.0.0.1:5050;' in site
    assert 'root %s;' % install.WEB_ROOT in site
    assert 'try_files $uri $uri/ /index.html;' in site
    # Same headers as the app on every location that serves files (add_header is not inherited).
    assert site.count('add_header Content-Security-Policy "%s" always;' % CONTENT_SECURITY_POLICY) == 3
    assert site.count('Strict-Transport-Security') == 3
    assert 'TLSv1.2 TLSv1.3' in site and 'TLSv1 ' not in site


def test_nginx_site_with_other_ports_old_nginx_and_no_ipv6():
    site = install.render_nginx(settings(http_port=8080, https_port=8443), 'c', 'k', (1, 18, 0), ipv6=False)
    assert 'listen 8080;' in site and 'listen 8443 ssl http2;' in site
    assert 'http2 on;' not in site and '[::]' not in site
    assert 'return 301 https://$host:8443$request_uri;' in site


def test_service_runs_the_app_behind_the_proxy(monkeypatch, tmp_path):
    monkeypatch.setenv('NEVERDIE_DB', 'data/db.sqlite')
    monkeypatch.setenv('NEVERDIE_PORT', '5050')
    monkeypatch.setenv('NEVERDIE_SECRET_KEY', 'secret')
    env = install.service_environment(os.environ, str(tmp_path))
    assert env['NEVERDIE_COOKIE_SECURE'] == '1' and env['NEVERDIE_TRUSTED_PROXIES'] == '1'
    assert env['NEVERDIE_DB'] == os.path.join(str(tmp_path), 'data', 'db.sqlite')
    assert env['NEVERDIE_PORT'] == '5050'
    assert 'NEVERDIE_SECRET_KEY' not in env  # the unit file is world readable

    unit = install.render_service('bob', '/srv/neverdie/.venv/bin/python', {'NEVERDIE_DB': '/data/50%"x'})
    assert 'User=bob' in unit
    assert 'WorkingDirectory=%s\n' % install.ROOT.replace('%', '%%') in unit
    assert 'Environment="NEVERDIE_DB=/data/50%%\\"x"' in unit
    assert 'ExecStart="/srv/neverdie/.venv/bin/python" "' in unit
    with pytest.raises(install.InstallError, match='line break'):
        install.render_service('bob', '/usr/bin/python', {'X': 'a\nb'})


@pytest.mark.parametrize('changes, message', [
    ({'server_name': '203.0.113.7'}, 'public domain name'),
    ({'server_name': 'monitor'}, 'public domain name'),
    ({'server_name': 'monitor.local'}, 'public domain name'),
    ({'http_port': 8080}, 'port 80'),
])
def test_letsencrypt_needs_a_public_domain_on_port_80(changes, message):
    with pytest.raises(install.InstallError, match=message):
        install.check_letsencrypt(settings(certificate='letsencrypt', **changes))


def test_letsencrypt_accepts_a_domain():
    install.check_letsencrypt(settings(certificate='letsencrypt'))


@pytest.fixture
def clean_config(monkeypatch, tmp_path):
    for name in (entry[2] for entry in config.SETTINGS.values()):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv('NEVERDIE_CONFIG', raising=False)
    monkeypatch.setattr(config, 'DEFAULT_FILE', str(tmp_path / 'missing.yml'))


def test_install_settings_of_the_configuration(clean_config, monkeypatch, tmp_path):
    path = tmp_path / 'neverdie.yml'
    path.write_text('install:\n  server_name: Monitor.Example.com\n  https_port: 8443\n'
                    '  certificate: letsencrypt\n  email: ops@example.com\n')
    monkeypatch.setenv('NEVERDIE_CONFIG', str(path))
    values = config.load()
    assert (values['server_name'], values['https_port'], values['certificate'], values['email']) == \
        ('monitor.example.com', 8443, 'letsencrypt', 'ops@example.com')
    assert config.load()['http_port'] == 80


@pytest.mark.parametrize('variable, value, message', [
    ('NEVERDIE_SERVER_NAME', 'evil.com; include /etc/passwd', 'server_name must be host names'),
    ('NEVERDIE_SERVER_NAME', 'a"b', 'server_name must be host names'),
    ('NEVERDIE_SERVER_NAME', 'monitor.example.com {', 'server_name must be host names'),
    ('NEVERDIE_CERTIFICATE', 'acme', 'certificate must be one of'),
    ('NEVERDIE_LETSENCRYPT_EMAIL', 'not-an-email', 'email must be an e-mail address'),
    ('NEVERDIE_HTTPS_PORT', '0', 'https_port must be a whole number'),
    ('NEVERDIE_HOST', '127.0.0.1;', 'the host must be an address'),
])
def test_refuses_install_values_that_could_break_nginx(clean_config, monkeypatch, variable, value, message):
    monkeypatch.setenv(variable, value)
    with pytest.raises(config.ConfigError, match=message):
        config.load()


def test_runs_only_on_linux_and_not_as_root(monkeypatch):
    monkeypatch.setattr(install.sys, 'platform', 'win32')
    with pytest.raises(SystemExit, match='on Linux'):
        install.main([])
    monkeypatch.setattr(install.sys, 'platform', 'linux')
    monkeypatch.setattr(install.os, 'geteuid', lambda: 0, raising=False)
    with pytest.raises(SystemExit, match='not as root'):
        install.main([])


@pytest.fixture
def dry_run(clean_config, monkeypatch, tmp_path):
    """A dry run that reads the configuration with this Python and writes to tmp_path/out."""
    monkeypatch.setattr(install, 'ensure_venv', lambda: sys.executable)
    monkeypatch.setattr(install, 'nginx_layout', lambda installer: (install.CONF_D + '/neverdie.conf', None))
    monkeypatch.setattr(install, 'STATE', str(tmp_path / 'install.json'))
    monkeypatch.setenv('NEVERDIE_SERVER_NAME', 'monitor.example.com')
    monkeypatch.setenv('NEVERDIE_HTTPS_PORT', '8443')
    return tmp_path / 'out'


def test_dry_run_writes_the_files_and_changes_nothing(dry_run, capsys):
    assert install.main(['--dry-run', str(dry_run)]) == 0
    output = capsys.readouterr().out

    site = (dry_run / 'neverdie.conf').read_text()
    assert 'server_name monitor.example.com;' in site and 'listen 8443 ssl' in site
    assert 'ExecStart=' in (dry_run / 'neverdie.service').read_text()
    state = json.loads((dry_run / 'install.json').read_text())
    assert state['server_name'] == 'monitor.example.com' and state['certificate'] == 'self-signed'
    assert 'subjectAltName=DNS:monitor.example.com,DNS:localhost,IP:127.0.0.1,IP:::1' in output
    assert 'would run: systemctl restart neverdie' in output
    assert 'nothing was changed' in output


def test_dry_run_refuses_a_bad_configuration(dry_run, monkeypatch):
    monkeypatch.setenv('NEVERDIE_HTTPS_PORT', '5000')
    with pytest.raises(SystemExit, match='server.port'):
        install.main(['--dry-run', str(dry_run)])
    monkeypatch.setenv('NEVERDIE_HTTPS_PORT', '80')
    with pytest.raises(SystemExit, match='must differ'):
        install.main(['--dry-run', str(dry_run)])


def test_dry_run_with_letsencrypt_checks_the_domain_first(dry_run, monkeypatch):
    monkeypatch.setenv('NEVERDIE_CERTIFICATE', 'letsencrypt')
    monkeypatch.setenv('NEVERDIE_SERVER_NAME', 'monitor.local')
    with pytest.raises(SystemExit, match='public domain name'):
        install.main(['--dry-run', str(dry_run)])


def test_uninstall_removes_what_install_recorded(dry_run, tmp_path, capsys):
    (tmp_path / 'install.json').write_text(json.dumps({
        'site': '/etc/nginx/sites-available/neverdie', 'link': '/etc/nginx/sites-enabled/neverdie',
        'service': install.SERVICE_FILE, 'web_root': install.WEB_ROOT, 'disabled_default_site': False}))
    assert install.main(['--uninstall', '--dry-run', str(dry_run)]) == 0
    output = capsys.readouterr().out
    for command in ('systemctl disable --now neverdie', 'rm -f /etc/systemd/system/neverdie.service',
                    'rm -f /etc/nginx/sites-enabled/neverdie', 'rm -f /etc/nginx/sites-available/neverdie',
                    'rm -rf /var/www/neverdie'):
        assert 'would run: ' + command in output


NGINX_DUMP = """\
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# configuration file /etc/nginx/nginx.conf:
user www-data;
events { worker_connections 768; }
http {
    upstream app { server 127.0.0.1:9000; }   # not a site
    include /etc/nginx/sites-enabled/*;
}
stream {
    server { listen 443; proxy_pass app; }
}

# configuration file /etc/nginx/sites-enabled/blog:
server {
    listen 80;
    server_name blog.example.com www.example.com;
}
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name blog.example.com
                Monitor.Example.com;   # a name over two lines
    location / { root /srv/blog; }
}

# configuration file /etc/nginx/sites-enabled/neverdie:
server {
    listen 443 ssl;
    server_name monitor.example.com;
}

# configuration file /etc/nginx/conf.d/legacy.conf:
server {
    server_name legacy.example.com;  # no listen: port 80
}
"""


def test_parse_the_sites_of_nginx_t():
    servers = install.parse_servers(NGINX_DUMP)
    assert [(s['file'].rsplit('/', 1)[1], s['ports'], s['default_ports']) for s in servers] == [
        ('blog', [80], []),
        ('blog', [443], [443]),
        ('neverdie', [443], []),
        ('legacy.conf', [80], []),
    ]
    assert servers[1]['names'] == ['blog.example.com', 'monitor.example.com']


@pytest.mark.parametrize('arguments, port', [
    (['443', 'ssl'], 443), (['0.0.0.0:8443'], 8443), (['[::]:443', 'ssl'], 443), (['*:80'], 80),
    (['127.0.0.1'], 80), (['unix:/run/nginx.sock'], None), ([], 80),
])
def test_listen_port(arguments, port):
    assert install.listen_port(arguments) == port


def test_conflicts_with_other_sites():
    others = [s for s in install.parse_servers(NGINX_DUMP) if not s['file'].endswith('neverdie')]
    clashes, defaults = install.site_conflicts(others, ['monitor.example.com', '10.0.0.5'], (80, 443))
    assert clashes == [('/etc/nginx/sites-enabled/blog', 'monitor.example.com', 443)]
    # The blog is the first site on port 80, and default_server on 443.
    assert defaults == {80: '/etc/nginx/sites-enabled/blog', 443: '/etc/nginx/sites-enabled/blog'}


def test_install_stops_on_a_site_with_the_same_name(monkeypatch):
    installer = install.Installer()
    monkeypatch.setattr(installer, 'root', lambda *a, **k: install.subprocess.CompletedProcess(a, 0, NGINX_DUMP, ''))
    with pytest.raises(install.InstallError, match='(?s)already answer.*blog: monitor.example.com on port 443'):
        install.check_other_sites(installer, 'nginx', settings(), install.SITES_AVAILABLE + '/neverdie',
                                  install.SITES_ENABLED + '/neverdie')
    # Other names: no clash, but the blog stays the default site of both ports.
    install.check_other_sites(installer, 'nginx', settings(server_name='status.example.com'),
                              install.SITES_AVAILABLE + '/neverdie', install.SITES_ENABLED + '/neverdie')
    notes = install.default_site_notes(installer, 'nginx', settings(server_name='status.example.com'),
                                       install.SITES_AVAILABLE + '/neverdie', install.SITES_ENABLED + '/neverdie')
    assert len(notes) == 2 and 'shows /etc/nginx/sites-enabled/blog' in notes[1]


def test_default_names_are_the_machine_names_and_addresses(monkeypatch):
    monkeypatch.setattr(install.socket, 'getfqdn', lambda: 'Server1.Example.lan')
    monkeypatch.setattr(install.socket, 'gethostname', lambda: 'server1')
    assert install.machine_names('192.168.1.20 127.0.0.1 169.254.3.3 fe80::1 2001:db8::5') == \
        ['server1.example.lan', 'server1', '192.168.1.20']
    monkeypatch.setattr(install.socket, 'getfqdn', lambda: 'localhost')
    monkeypatch.setattr(install.socket, 'gethostname', lambda: 'bad_name')
    assert install.machine_names('') == ['localhost']


def test_several_server_names():
    many = settings(server_name='monitor.example.com 192.168.1.20')
    assert install.certificate_names(many['server_name']) == \
        ['monitor.example.com', '192.168.1.20', 'localhost', '127.0.0.1', '::1']
    assert install.site_url(many['server_name'], 443) == 'https://monitor.example.com/'
    assert 'server_name monitor.example.com 192.168.1.20;' in install.render_nginx(many, 'c', 'k')
    with pytest.raises(install.InstallError, match="'192.168.1.20'"):
        install.check_letsencrypt(dict(many, certificate='letsencrypt'))


def test_letsencrypt_asks_for_every_name(capsys, tmp_path):
    installer = install.Installer(dry_run=str(tmp_path))  # prints the commands only
    install.request_letsencrypt(installer, settings(server_name='monitor.example.com status.example.com',
                                                    email='ops@example.com'))
    command = capsys.readouterr().out
    assert '--cert-name monitor.example.com' in command and '--keep-until-expiring --expand' in command
    assert '-d monitor.example.com -d status.example.com --email ops@example.com' in command


@pytest.mark.parametrize('value, expected', [
    ('monitor.example.com 192.168.1.20', 'monitor.example.com 192.168.1.20'),
    ('Monitor.example.com, 192.168.1.20,monitor.example.com', 'monitor.example.com 192.168.1.20'),
])
def test_server_names_of_the_configuration(clean_config, monkeypatch, value, expected):
    monkeypatch.setenv('NEVERDIE_SERVER_NAME', value)
    assert config.load()['server_name'] == expected


def test_server_names_as_a_yaml_list(clean_config, monkeypatch, tmp_path):
    path = tmp_path / 'neverdie.yml'
    path.write_text('install:\n  server_name:\n    - monitor.example.com\n    - 10.0.0.5\n')
    monkeypatch.setenv('NEVERDIE_CONFIG', str(path))
    assert config.load()['server_name'] == 'monitor.example.com 10.0.0.5'
    path.write_text('install:\n  server_name: [monitor.example.com, "bad;name"]\n')
    with pytest.raises(config.ConfigError, match="'bad;name'"):
        config.load()


def test_uninstall_without_install(dry_run, capsys):
    assert install.main(['--uninstall', '--dry-run', str(dry_run)]) == 0
    assert 'nothing to remove' in capsys.readouterr().out


def installed(tmp_path, **changes):
    """The state file of an earlier make install of monitor.example.com on port 8443."""
    state = {'site': '/etc/nginx/sites-available/neverdie', 'link': '/etc/nginx/sites-enabled/neverdie',
             'service': install.SERVICE_FILE, 'web_root': install.WEB_ROOT, 'certificate': 'self-signed',
             'server_name': 'monitor.example.com', 'host': '127.0.0.1', 'port': 5000,
             'http_port': 80, 'https_port': 8443, 'disabled_default_site': False}
    state.update(changes)
    (tmp_path / 'install.json').write_text(json.dumps(state))


def test_install_records_what_update_checks(dry_run):
    install.main(['--dry-run', str(dry_run)])
    state = json.loads((dry_run / 'install.json').read_text())
    assert {key: state[key] for key in ('host', 'port', 'http_port', 'https_port')} == {
        'host': '127.0.0.1', 'port': 5000, 'http_port': 80, 'https_port': 8443}


def test_update_publishes_the_ui_and_restarts_the_service_only(dry_run, tmp_path, capsys):
    installed(tmp_path)
    assert install.main(['--update', '--no-pull', '--dry-run', str(dry_run)]) == 0
    output = capsys.readouterr().out
    assert 'would run: mv /var/www/neverdie.new /var/www/neverdie' in output
    assert 'would run: systemctl restart neverdie' in output
    # The configuration stays as installed: no nginx site, unit, certificate or state written.
    assert not dry_run.exists() or not list(dry_run.iterdir())
    for command in ('would write', 'openssl', 'nginx -t', 'systemctl reload nginx', 'daemon-reload', 'enable'):
        assert command not in output
    assert 'note:' not in output


def test_update_without_service_does_not_restart_it(dry_run, tmp_path, capsys):
    installed(tmp_path, service=None)
    assert install.main(['--update', '--no-pull', '--dry-run', str(dry_run)]) == 0
    assert 'systemctl' not in capsys.readouterr().out


def test_update_needs_an_install(dry_run):
    with pytest.raises(SystemExit, match='run make install first'):
        install.main(['--update', '--dry-run', str(dry_run)])


def test_update_refuses_a_new_app_address(dry_run, tmp_path, monkeypatch):
    installed(tmp_path)
    monkeypatch.setenv('NEVERDIE_PORT', '5001')
    with pytest.raises(SystemExit, match=r'server\.port.*run make install'):
        install.main(['--update', '--no-pull', '--dry-run', str(dry_run)])


def test_update_tells_about_site_settings_it_does_not_apply(dry_run, tmp_path, monkeypatch, capsys):
    installed(tmp_path, server_name='old.example.com')
    assert install.main(['--update', '--no-pull', '--dry-run', str(dry_run)]) == 0
    assert 'install.server_name' in capsys.readouterr().out


def test_update_of_an_older_install_compares_what_it_recorded(dry_run, tmp_path, capsys):
    installed(tmp_path)
    state = json.loads((tmp_path / 'install.json').read_text())
    for key in ('host', 'port', 'http_port', 'https_port'):
        del state[key]
    (tmp_path / 'install.json').write_text(json.dumps(state))
    assert install.main(['--update', '--no-pull', '--dry-run', str(dry_run)]) == 0
    assert 'note:' not in capsys.readouterr().out


def test_update_and_uninstall_together_are_refused():
    with pytest.raises(SystemExit):
        install.main(['--update', '--uninstall', '--dry-run', 'out'])


def test_client_dependencies_are_installed_again_when_the_lock_changes(tmp_path):
    lock = tmp_path / 'package-lock.json'
    lock.write_text('{}')
    assert install.client_dependencies_outdated(str(tmp_path))  # no node_modules
    installed_lock = tmp_path / 'node_modules' / '.package-lock.json'
    installed_lock.parent.mkdir()
    installed_lock.write_text('{}')
    os.utime(lock, (1_000, 1_000))
    os.utime(installed_lock, (2_000, 2_000))
    assert not install.client_dependencies_outdated(str(tmp_path))
    os.utime(lock, (3_000, 3_000))  # git pull brought a new lock
    assert install.client_dependencies_outdated(str(tmp_path))


class Git:
    """Fake git of pull_sources: HEAD moves from `before` to `after` on pull."""

    def __init__(self, before, after, upstream=True, pull_fails=False):
        self.head, self.after, self.upstream, self.pull_fails = before, after, upstream, pull_fails
        self.commands = []

    def __call__(self, command, check=True, capture=False, **kwargs):
        self.commands.append(command[1:])
        code, out = 0, ''
        if command[1:2] == ['pull']:
            code = 1 if self.pull_fails else 0
            if not self.pull_fails:
                self.head = self.after
        elif '@{upstream}' in command:
            code = 0 if self.upstream else 128
        elif command[1:] == ['rev-parse', 'HEAD']:
            out = self.head
        return install.subprocess.CompletedProcess(command, code, out, 'error: local changes')


@pytest.fixture
def git_checkout(monkeypatch, tmp_path):
    (tmp_path / '.git').mkdir()
    monkeypatch.setattr(install, 'ROOT', str(tmp_path))
    monkeypatch.setattr(install.shutil, 'which', lambda name: '/usr/bin/' + name)
    installer = install.Installer()

    def use(git):
        monkeypatch.setattr(installer, 'run', git)
        return installer
    return use


def test_pull_sources(git_checkout):
    assert install.pull_sources(git_checkout(Git('a' * 40, 'b' * 40))) is True
    assert install.pull_sources(git_checkout(Git('a' * 40, 'a' * 40))) is False
    git = Git('a' * 40, 'b' * 40, upstream=False)
    assert install.pull_sources(git_checkout(git)) is False
    assert ['pull', '--ff-only'] not in git.commands
    with pytest.raises(install.InstallError, match='NEVERDIE_CONFIG'):
        install.pull_sources(git_checkout(Git('a' * 40, 'b' * 40, pull_fails=True)))


def test_update_runs_the_new_scripts_after_a_pull(dry_run, tmp_path, monkeypatch):
    installed(tmp_path)
    monkeypatch.setattr(install, 'pull_sources', lambda installer: True)
    calls = []
    monkeypatch.setattr(install.os, 'execv', lambda program, argv: calls.append(argv) or sys.exit(0))
    with pytest.raises(SystemExit):
        install.main(['--update', '--dry-run', str(dry_run)])
    [argv] = calls
    assert argv[1].endswith('install.py') and argv[2:] == ['--update', '--dry-run', str(dry_run), '--no-pull']
