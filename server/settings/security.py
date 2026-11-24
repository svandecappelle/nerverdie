# -*- coding: utf-8 -*-
"""Security related settings: secret key, session cookies, login throttling."""

import logging
import os
import secrets
import threading
import time
from datetime import timedelta

LOGGER = logging.getLogger(__name__)

INSTANCE_DIR = os.environ.get(
    'NEVERDIE_INSTANCE_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'instance')
)

SESSION_DURATION_SECONDS = 600


def _env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def load_secret_key():
    """Return the Flask secret key.

    Order: NEVERDIE_SECRET_KEY env var, then instance/secret_key file.
    If neither exists, a random key is generated and stored in that file
    (instance/ is git-ignored) so that sessions survive a restart.
    """
    key = os.environ.get('NEVERDIE_SECRET_KEY')
    if key:
        return key

    key_path = os.path.join(INSTANCE_DIR, 'secret_key')
    if os.path.isfile(key_path):
        with open(key_path, 'r') as key_file:
            key = key_file.read().strip()
        if key:
            return key

    os.makedirs(INSTANCE_DIR, exist_ok=True)
    key = secrets.token_hex(32)
    # Create the file readable by the owner only.
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as key_file:
        key_file.write(key)
    LOGGER.warning("Generated a new secret key in %s", key_path)
    return key


def configure_app(app):
    """Apply secret key and hardened session cookie settings to a Flask app."""
    app.config.update(
        SECRET_KEY=load_secret_key(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        # Enable once the app is served over HTTPS (recommended).
        SESSION_COOKIE_SECURE=_env_flag('NEVERDIE_COOKIE_SECURE', False),
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=SESSION_DURATION_SECONDS),
    )


class LoginThrottle(object):
    """In-memory limiter of failed login attempts per client address."""

    def __init__(self, max_failures=5, window_seconds=300):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures = {}
        self._lock = threading.Lock()

    def _recent(self, key, now):
        attempts = [t for t in self._failures.get(key, []) if now - t < self.window_seconds]
        if attempts:
            self._failures[key] = attempts
        else:
            self._failures.pop(key, None)
        return attempts

    def is_blocked(self, key):
        with self._lock:
            return len(self._recent(key, time.monotonic())) >= self.max_failures

    def record_failure(self, key):
        with self._lock:
            now = time.monotonic()
            self._recent(key, now)
            self._failures.setdefault(key, []).append(now)

    def reset(self, key):
        with self._lock:
            self._failures.pop(key, None)
