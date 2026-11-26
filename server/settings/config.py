#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Listening address, port and threads of Neverdie.

Each setting comes from, by priority:
1. the command line (start.py -H / -P / -t);
2. an environment variable (NEVERDIE_HOST, NEVERDIE_PORT, NEVERDIE_THREADS, NEVERDIE_UI_PORT);
3. the configuration file: NEVERDIE_CONFIG, or etc/neverdie.yml by default;
4. the defaults below.

    python -m server.settings.config    # prints the resolved settings (JSON)
"""

import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_FILE = os.path.join(ROOT, 'etc', 'neverdie.yml')

# Setting: (section in the file, key in the section, environment variable, default).
SETTINGS = {
    'host': ('server', 'host', 'NEVERDIE_HOST', '127.0.0.1'),
    'port': ('server', 'port', 'NEVERDIE_PORT', 5000),
    'threads': ('server', 'threads', 'NEVERDIE_THREADS', 8),
    # Port of the Angular dev server started by `make serve`.
    'ui_port': ('dev', 'ui_port', 'NEVERDIE_UI_PORT', 4200),
}
MAX_THREADS = 256


class ConfigError(ValueError):
    """A configuration value or file that cannot be used."""


def config_file():
    """(path, explicit): explicit when NEVERDIE_CONFIG names it."""
    path = os.environ.get('NEVERDIE_CONFIG')
    return (os.path.abspath(path), True) if path else (DEFAULT_FILE, False)


def read_file(path, required=False):
    """Settings of a YAML file as {name: value}; {} for a missing or empty file."""
    try:
        with open(path, encoding='utf-8') as file:
            content = yaml.safe_load(file)
    except FileNotFoundError:
        if required:
            raise ConfigError('configuration file not found: %s' % path) from None
        return {}
    except yaml.YAMLError as error:
        raise ConfigError('%s is not valid YAML: %s' % (path, error)) from None
    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ConfigError('%s: expected sections such as "server:", got %s' % (path, type(content).__name__))

    known = {}
    for name, (section, key, _, _) in SETTINGS.items():
        known.setdefault(section, {})[key] = name
    values = {}
    for section, entries in content.items():
        if section not in known:
            raise ConfigError('%s: unknown section "%s" (known: %s)' % (path, section, ', '.join(known)))
        if entries is None:
            continue
        if not isinstance(entries, dict):
            raise ConfigError('%s: section "%s" must hold "key: value" lines' % (path, section))
        for key, value in entries.items():
            if key not in known[section]:
                raise ConfigError('%s: unknown setting "%s.%s" (known: %s)'
                                  % (path, section, key, ', '.join(known[section])))
            values[known[section][key]] = value
    return values


def check(name, value, origin):
    """Validated value of a setting; `origin` names where it comes from in errors."""
    if name == 'host':
        if not isinstance(value, str) or not value.strip():
            raise ConfigError('%s: the host must be an address such as 127.0.0.1, got %r' % (origin, value))
        return value.strip()
    limits = {'port': (1, 65535), 'ui_port': (1, 65535), 'threads': (1, MAX_THREADS)}[name]
    if isinstance(value, bool):
        number = None
    elif isinstance(value, int):
        number = value
    else:
        text = str(value).strip()
        number = int(text) if text.isdigit() else None
    if number is None or not limits[0] <= number <= limits[1]:
        raise ConfigError('%s: %s must be a whole number from %d to %d, got %r'
                          % (origin, name, limits[0], limits[1], value))
    return number


def load(overrides=None):
    """Resolved settings {host, port, threads, ui_port}; `overrides` holds the command line values."""
    path, explicit = config_file()
    from_file = read_file(path, required=explicit)
    settings = {}
    for name, (section, key, variable, default) in SETTINGS.items():
        override = (overrides or {}).get(name)
        if override is not None:
            settings[name] = check(name, override, 'command line')
        elif os.environ.get(variable, '').strip():
            settings[name] = check(name, os.environ[variable], variable)
        elif name in from_file:
            settings[name] = check(name, from_file[name], '%s (%s.%s)' % (path, section, key))
        else:
            settings[name] = default
    return settings


def local_url(host, port):
    """URL to reach a server listening on host:port from this machine."""
    if host in ('0.0.0.0', '', '*'):  # noqa: S104 (we connect to it, not listen)
        host = '127.0.0.1'
    elif host == '::':
        host = '::1'
    if ':' in host:
        host = '[%s]' % host
    return 'http://%s:%d' % (host, port)


def main():
    try:
        print(json.dumps(load()))
    except ConfigError as error:
        sys.exit('config: %s' % error)
    return 0


if __name__ == '__main__':
    sys.exit(main())
