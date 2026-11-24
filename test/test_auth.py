# -*- coding: utf-8 -*-
"""Authentication tests: run with `python -m pytest test/test_auth.py`."""

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix='neverdie-test-')
os.environ['NEVERDIE_DB'] = os.path.join(_TMP, 'test.sqlite')
os.environ['NEVERDIE_INSTANCE_DIR'] = os.path.join(_TMP, 'instance')
os.environ.pop('NEVERDIE_SECRET_KEY', None)

import pytest  # noqa: E402

from server.application import APP  # noqa: E402
from server.models.user import User  # noqa: E402
from server.storage.main import Datastore  # noqa: E402
import server.web.api.middleware as middleware  # noqa: E402
import server.web.api.monitor  # noqa: E402,F401  (registers protected routes)

PASSWORD = 'correct horse battery staple'


@pytest.fixture
def client():
    Datastore()
    User.delete().execute()
    user = User(username='alice')
    user.set_password(PASSWORD)
    user.save()
    middleware.LOGIN_THROTTLE.reset('127.0.0.1')
    with APP.test_client() as test_client:
        yield test_client


def login(client, username='alice', password=PASSWORD):
    return client.post('/api/auth/login', json={'username': username, 'password': password})


def test_secret_key_is_generated_not_hardcoded():
    assert APP.config['SECRET_KEY'] != 'the quick brown fox jumps over the lazy dog'
    assert len(APP.config['SECRET_KEY']) >= 32
    assert os.path.isfile(os.path.join(os.environ['NEVERDIE_INSTANCE_DIR'], 'secret_key'))


def test_cookie_flags():
    assert APP.config['SESSION_COOKIE_HTTPONLY'] is True
    assert APP.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


def test_protected_route_requires_login(client):
    assert client.get('/api/metrics').status_code == 401
    assert client.get('/api/auth').status_code == 401


def test_password_is_hashed(client):
    stored = User.get(User.username == 'alice').password_hash
    assert PASSWORD not in stored


def test_valid_login_then_logout(client):
    response = login(client)
    assert response.status_code == 200
    assert response.get_json()['user']['username'] == 'alice'
    assert client.get('/api/metrics').status_code == 200
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/metrics').status_code == 401


@pytest.mark.parametrize('payload', [
    {'username': 'admin', 'password': 'password'},
    {'username': 'alice', 'password': 'wrong'},
    {'username': 'nobody', 'password': PASSWORD},
    {'token': 'fl?8dnh432fmfokf1!sfz54fxgk84x:wx'},
    {},
    {'username': ['alice'], 'password': {'x': 1}},
])
def test_rejected_credentials(client, payload):
    response = client.post('/api/auth/login', json=payload)
    assert response.status_code == 401
    assert client.get('/api/metrics').status_code == 401


def test_login_get_is_not_allowed(client):
    assert client.get('/api/auth/login').status_code == 405
    assert client.get('/api/auth/logout').status_code == 405


def test_login_is_throttled_after_failures(client):
    for _ in range(5):
        assert login(client, password='wrong').status_code == 401
    assert login(client).status_code == 429


def test_resource_backdoor_route_removed(client):
    assert '/api/resource' not in {rule.rule for rule in APP.url_map.iter_rules()}
