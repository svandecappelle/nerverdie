"""Listening address and ports: configuration file, environment, command line."""
import json

import pytest

from server.application import server_settings
from server.settings import config

DEFAULTS = {'host': '127.0.0.1', 'port': 5000, 'threads': 8, 'ui_port': 4200}


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch, tmp_path):
    """No NEVERDIE_* setting from the machine, and no file unless a test writes one."""
    for variable in ('NEVERDIE_HOST', 'NEVERDIE_PORT', 'NEVERDIE_THREADS', 'NEVERDIE_UI_PORT', 'NEVERDIE_CONFIG'):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(config, 'DEFAULT_FILE', str(tmp_path / 'missing.yml'))


def write(tmp_path, text, monkeypatch=None):
    path = tmp_path / 'neverdie.yml'
    path.write_text(text, encoding='utf-8')
    if monkeypatch:
        monkeypatch.setenv('NEVERDIE_CONFIG', str(path))
    return path


def test_defaults_without_file_or_environment():
    assert config.load() == DEFAULTS


def test_the_shipped_example_file_keeps_the_defaults(monkeypatch):
    # etc/neverdie.yml only holds comments.
    monkeypatch.setenv('NEVERDIE_CONFIG', str(config.ROOT + '/etc/neverdie.yml'))
    assert config.load() == DEFAULTS


def test_reads_the_configuration_file(tmp_path, monkeypatch):
    write(tmp_path, 'server:\n  host: 0.0.0.0\n  port: 8080\ndev:\n  ui_port: 4300\n', monkeypatch)
    assert config.load() == {'host': '0.0.0.0', 'port': 8080, 'threads': 8, 'ui_port': 4300}


def test_default_file_location(tmp_path, monkeypatch):
    path = write(tmp_path, 'server:\n  threads: 4\n')
    monkeypatch.setattr(config, 'DEFAULT_FILE', str(path))
    assert config.load()['threads'] == 4


def test_environment_beats_the_file_and_command_line_beats_both(tmp_path, monkeypatch):
    write(tmp_path, 'server:\n  port: 8080\n  threads: 4\n', monkeypatch)
    monkeypatch.setenv('NEVERDIE_PORT', '9090')
    monkeypatch.setenv('NEVERDIE_HOST', '  ')  # blank: ignored
    assert config.load() == {'host': '127.0.0.1', 'port': 9090, 'threads': 4, 'ui_port': 4200}
    assert config.load({'port': '7070', 'host': None})['port'] == 7070


@pytest.mark.parametrize('text, message', [
    ('server: [1, 2', 'not valid YAML'),
    ('- port: 8080', 'expected sections'),
    ('web:\n  port: 8080', 'unknown section "web"'),
    ('server:\n  prot: 8080', 'unknown setting "server.prot"'),
    ('server: 8080', 'must hold "key: value" lines'),
    ('server:\n  port: 70000', 'port must be a whole number from 1 to 65535'),
    ('server:\n  port: true', 'port must be a whole number'),
    ('server:\n  threads: 0', 'threads must be a whole number from 1 to 256'),
    ('server:\n  host: ""', 'the host must be an address'),
])
def test_refuses_a_bad_file(tmp_path, monkeypatch, text, message):
    path = write(tmp_path, text, monkeypatch)
    with pytest.raises(config.ConfigError, match=message) as error:
        config.load()
    assert str(path) in str(error.value)


def test_empty_sections_and_file_are_fine(tmp_path, monkeypatch):
    write(tmp_path, 'server:\ndev:\n', monkeypatch)
    assert config.load() == DEFAULTS
    write(tmp_path, '# nothing\n', monkeypatch)
    assert config.load() == DEFAULTS


def test_a_missing_file_named_by_neverdie_config_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setenv('NEVERDIE_CONFIG', str(tmp_path / 'nope.yml'))
    with pytest.raises(config.ConfigError, match='configuration file not found'):
        config.load()


def test_refuses_a_bad_environment_value(monkeypatch):
    monkeypatch.setenv('NEVERDIE_PORT', 'http')
    with pytest.raises(config.ConfigError, match='NEVERDIE_PORT: port must be a whole number'):
        config.load()


def test_command_line_options(tmp_path, monkeypatch):
    write(tmp_path, 'server:\n  port: 8080\n', monkeypatch)
    assert server_settings([]) == {'host': '127.0.0.1', 'port': 8080, 'threads': 8, 'ui_port': 4200}
    assert server_settings(['-H', '0.0.0.0', '-P', '6000', '-t', '2'])['port'] == 6000


def test_command_line_reports_a_bad_value(capsys):
    with pytest.raises(SystemExit):
        server_settings(['-P', 'abc'])
    assert 'command line: port must be a whole number' in capsys.readouterr().err


@pytest.mark.parametrize('host, url', [
    ('127.0.0.1', 'http://127.0.0.1:5000'),
    ('0.0.0.0', 'http://127.0.0.1:5000'),
    ('::', 'http://[::1]:5000'),
    ('fe80::1', 'http://[fe80::1]:5000'),
    ('monitor.local', 'http://monitor.local:5000'),
])
def test_local_url(host, url):
    assert config.local_url(host, 5000) == url


def test_prints_the_settings_as_json(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv('NEVERDIE_UI_PORT', '4300')
    assert config.main() == 0
    assert json.loads(capsys.readouterr().out)['ui_port'] == 4300
    monkeypatch.setenv('NEVERDIE_UI_PORT', '0')
    with pytest.raises(SystemExit, match='ui_port must be'):
        config.main()
