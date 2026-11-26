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


# The Angular client only loads its own files. Inline styles are required
# by Angular Material component styles and Highcharts.
CONTENT_SECURITY_POLICY = '; '.join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

SECURITY_HEADERS = {
    'Content-Security-Policy': CONTENT_SECURITY_POLICY,
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'no-referrer',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    'Cross-Origin-Opener-Policy': 'same-origin',
}


def https_enabled():
    """True when the app is served over HTTPS (behind a TLS reverse proxy)."""
    return _env_flag('NEVERDIE_COOKIE_SECURE', False)


def trusted_proxy_count():
    """Number of reverse proxies in front of the app (NEVERDIE_TRUSTED_PROXIES)."""
    try:
        return max(0, int(os.environ.get('NEVERDIE_TRUSTED_PROXIES', '0')))
    except ValueError:
        LOGGER.error("NEVERDIE_TRUSTED_PROXIES must be an integer, ignoring it")
        return 0


def configure_app(app):
    """Apply secret key, session cookie, header and proxy settings to a Flask app."""
    app.config.update(
        SECRET_KEY=load_secret_key(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        # Enable once the app is served over HTTPS (recommended).
        SESSION_COOKIE_SECURE=https_enabled(),
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=SESSION_DURATION_SECONDS),
        # The API only receives small JSON bodies.
        MAX_CONTENT_LENGTH=64 * 1024,
    )

    proxies = trusted_proxy_count()
    if proxies:
        # Trust X-Forwarded-For/Proto from that many proxies only, so that
        # request.remote_addr (used by the login throttle) is the real client.
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxies, x_proto=proxies, x_host=proxies)

    @app.after_request
    def add_security_headers(response):
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if https_enabled():
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        if response.mimetype == 'application/json':
            # API responses contain system information: never cache them.
            response.headers.setdefault('Cache-Control', 'no-store')
        return response


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

    def clear(self):
        """Forget every address."""
        with self._lock:
            self._failures.clear()
