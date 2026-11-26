# -*- coding: utf-8 -*-
"""Administration API: database size limit, login security."""

import logging
from datetime import datetime, timedelta

from flask import abort, jsonify, request, session

from server.application import APP as app
from server.application import login_required
from server.storage import logins, retention
from server.web.api import middleware
from server.web.api.history import _moment

LOGGER = logging.getLogger(__name__)


def _bad_request(message):
    return jsonify(error=message), 400


@app.route('/api/admin/storage', methods=['GET'])
@login_required
def storage_status():
    """Database sizes, size limit and stored samples."""
    return jsonify(retention.storage_status())


@app.route('/api/admin/storage', methods=['PUT'])
@login_required
def storage_update():
    """Set the size limit in MB (`null` or 0: unlimited), then apply it at once."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or 'limit_mb' not in payload:
        return _bad_request('limit_mb is required')
    limit_mb = payload['limit_mb']
    # bool is an int subclass: reject it explicitly.
    if limit_mb is not None and (isinstance(limit_mb, bool) or not isinstance(limit_mb, (int, float))):
        return _bad_request('limit_mb must be a number or null')
    if limit_mb is not None and limit_mb != int(limit_mb):
        return _bad_request('limit_mb must be a whole number of MB')
    try:
        retention.set_limit_mb(int(limit_mb) if limit_mb else None)
    except ValueError as error:
        return _bad_request(str(error))
    deleted = retention.enforce_limit()
    return jsonify(dict(retention.storage_status(), deleted=deleted))


@app.route('/api/admin/storage/compact', methods=['POST'])
@login_required
def storage_compact():
    """Give the free pages of the database back to the file system."""
    retention.compact()
    return jsonify(retention.storage_status())


def _whole_number(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _security_status():
    throttle = middleware.LOGIN_THROTTLE
    return {
        'policy': logins.get_policy(),
        'limits': {
            'min_attempts': logins.MIN_ATTEMPTS,
            'max_attempts': logins.MAX_ATTEMPTS,
            'max_lock_minutes': logins.MAX_LOCK_MINUTES,
        },
        'throttle': {'max_failures': throttle.max_failures, 'window_seconds': throttle.window_seconds},
        'accounts': logins.accounts(),
        'last_day': logins.totals(datetime.now() - timedelta(days=1)),
        'recent': logins.recent(),
    }


@app.route('/api/admin/security', methods=['GET'])
@login_required
def security_status():
    """Account lock policy, accounts, and the last login attempts."""
    return jsonify(_security_status())


@app.route('/api/admin/security', methods=['PUT'])
@login_required
def security_update():
    """Set the lock policy: `max_attempts` (null: never lock) and `lock_minutes` (0: until unlocked)."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or 'max_attempts' not in payload or 'lock_minutes' not in payload:
        return _bad_request('max_attempts and lock_minutes are required')
    max_attempts, lock_minutes = payload['max_attempts'], payload['lock_minutes']
    if max_attempts is not None and not _whole_number(max_attempts):
        return _bad_request('max_attempts must be a whole number or null')
    if not _whole_number(lock_minutes):
        return _bad_request('lock_minutes must be a whole number')
    try:
        logins.set_policy(max_attempts, lock_minutes)
    except ValueError as error:
        return _bad_request(str(error))
    LOGGER.info("Login lock policy set to %s by %s", logins.get_policy(), session.get('username'))
    return jsonify(_security_status())


@app.route('/api/admin/security/unlock', methods=['POST'])
@login_required
def security_unlock():
    """Unlock an account: `{"username": "..."}`."""
    payload = request.get_json(silent=True)
    username = payload.get('username') if isinstance(payload, dict) else None
    if not isinstance(username, str) or not username:
        return _bad_request('username is required')
    if not logins.unlock(username):
        abort(404, description='unknown user')
    return jsonify(_security_status())


@app.route('/api/admin/security/history', methods=['GET'])
@login_required
def security_history():
    """Login attempts by time bucket. Query: `from`, `to` in epoch milliseconds (default: the last day)."""
    try:
        buckets = int(request.args.get('points', logins.DEFAULT_BUCKETS))
        return jsonify(logins.history(_moment('from'), _moment('to'), buckets))
    except ValueError as error:
        abort(400, description=str(error))
