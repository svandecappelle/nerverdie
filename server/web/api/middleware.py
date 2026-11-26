# -*- coding: utf-8 -*-
import logging

from server.application import APP as app
from server.application import login_required
from server.models.user import User
from server.settings.security import LoginThrottle, SESSION_DURATION_SECONDS
from server.storage import logins
import werkzeug.exceptions as ex

from flask import jsonify, request, session

LOGGER = logging.getLogger(__name__)

LOGIN_THROTTLE = LoginThrottle(max_failures=5, window_seconds=300)


class AuthenticationError(ex.HTTPException):
    code = 401
    description = 'Invalid credentials'


@app.errorhandler(AuthenticationError)
def invalid_credentials(e):
    return jsonify({'error': e.description}), e.code


def _session_payload():
    return {
        'duration': SESSION_DURATION_SECONDS,
        'user': {'uid': session.get('user_id'), 'username': session.get('username')},
        'connected': True,
    }


@app.route('/api/auth', methods=['GET'])
@login_required
def get_user_logged():
    return jsonify(_session_payload())


def _account_locked(until):
    """423 Locked: the account is locked after too many failed logins."""
    return jsonify({
        'error': 'account locked after too many failed logins',
        'locked_until': logins.describe_lock(until),
    }), 423


@app.route('/api/auth/login', methods=['POST'])
def autentication():
    client = request.remote_addr or 'unknown'
    payload = request.get_json(silent=True)
    payload = payload if isinstance(payload, dict) else {}
    username = logins.clean_username(payload.get('username'))

    if LOGIN_THROTTLE.is_blocked(client):
        LOGGER.warning("Login throttled for %s", client)
        logins.record(username, client, 'throttled')
        return jsonify({'error': 'too many failed attempts, retry later'}), 429

    # A locked account is refused even with the right password.
    until = logins.locked_until(username)
    if until is not None:
        LOGGER.warning("Login refused for locked account %r from %s", username, client)
        logins.record(username, client, 'locked')
        return _account_locked(until)

    user = User.authenticate(payload.get('username'), payload.get('password'))
    if user is None:
        LOGIN_THROTTLE.record_failure(client)
        LOGGER.warning("Failed login for %r from %s", username, client)
        logins.record(username, client, 'failure')
        until = logins.register_failure(username)
        if until is not None:
            return _account_locked(until)
        raise AuthenticationError()

    LOGIN_THROTTLE.reset(client)
    logins.register_success(user)
    logins.record(user.username, client, 'success')
    # Start from a clean session to avoid session fixation.
    session.clear()
    session.permanent = True
    session['logged_in'] = True
    session['user_id'] = user.id
    session['username'] = user.username
    LOGGER.info("User %s logged in from %s", user.username, client)
    return jsonify(_session_payload())


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'ok'})
