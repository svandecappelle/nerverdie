# -*- coding: utf-8 -*-
"""Shared test setup: isolated database and instance dir, logged-in client."""

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix='neverdie-test-')
os.environ['NEVERDIE_DB'] = os.path.join(_TMP, 'test.sqlite')
os.environ['NEVERDIE_INSTANCE_DIR'] = os.path.join(_TMP, 'instance')
os.environ.pop('NEVERDIE_SECRET_KEY', None)

import pytest  # noqa: E402

import start  # noqa: E402
from server.application import APP  # noqa: E402
from server.models.metrics import Cpu, CpuCore, Measure  # noqa: E402
from server.models.setting import Setting  # noqa: E402
from server.models.user import User  # noqa: E402
from server.storage.main import Datastore  # noqa: E402
import server.web.api.middleware as middleware  # noqa: E402

PASSWORD = 'correct horse battery staple'

# Register every route module exactly like the real entry point does.
start.Starter()


@pytest.fixture
def client():
    Datastore()
    for model in (CpuCore, Measure, Cpu, User, Setting):
        model.delete().execute()
    user = User(username='alice')
    user.set_password(PASSWORD)
    user.save()
    middleware.LOGIN_THROTTLE.reset('127.0.0.1')
    with APP.test_client() as test_client:
        yield test_client


@pytest.fixture
def logged_client(client):
    response = client.post('/api/auth/login', json={'username': 'alice', 'password': PASSWORD})
    assert response.status_code == 200
    return client
