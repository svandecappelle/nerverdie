# -*- coding: utf-8 -*-
"""Database size limit: settings, sliding purge and admin API."""

import datetime

import pytest

from server.models.base import db
from server.models.metrics import Cpu, CpuCore
from server.storage import retention

START = datetime.datetime(2026, 1, 1)
CORES = 8


def fill(samples, start=START):
    """Insert `samples` CPU measures (3 s apart) with CORES loads each."""
    with db.atomic():
        for offset in range(0, samples, 500):
            count = min(500, samples - offset)
            first = Cpu.insert_many(
                [{'time': start + datetime.timedelta(seconds=3 * (offset + i))} for i in range(count)]
            ).execute()
            # SQLite returns the id of the last inserted row.
            ids = range(first - count + 1, first + 1)
            CpuCore.insert_many(
                [{'cpu': cpu_id, 'name': 'cpu%d' % core, 'load': 12.5} for cpu_id in ids for core in range(CORES)]
            ).execute()


@pytest.fixture
def storage(client):
    """Empty metrics tables, no limit; the database is compacted afterwards."""
    yield client
    retention.compact()


def test_unlimited_by_default(storage):
    fill(100)
    assert retention.get_limit_mb() is None
    assert retention.enforce_limit() == 0
    assert Cpu.select().count() == 100


def test_set_limit_validates_the_range(storage):
    retention.set_limit_mb(5)
    assert retention.get_limit_mb() == 5
    retention.set_limit_mb(None)
    assert retention.get_limit_mb() is None
    for value in (0, -1, retention.MAX_LIMIT_MB + 1):
        with pytest.raises(ValueError):
            retention.set_limit_mb(value)


def test_enforce_limit_deletes_the_oldest_samples(storage):
    fill(8000)
    assert retention.used_bytes() > 2 * retention.MB
    newest = Cpu.select(Cpu.time).order_by(Cpu.time.desc()).first().time

    retention.set_limit_mb(1)
    deleted = retention.enforce_limit()

    assert deleted > 0
    assert retention.used_bytes() <= retention.MB
    remaining = Cpu.select().count()
    assert remaining == 8000 - deleted
    assert remaining > 0
    # The newest samples are kept, the oldest ones are gone.
    assert Cpu.select(Cpu.time).order_by(Cpu.time.desc()).first().time == newest
    oldest = Cpu.select(Cpu.time).order_by(Cpu.time.asc()).first().time
    assert oldest == START + datetime.timedelta(seconds=3 * deleted)
    # No orphan per-core loads.
    assert CpuCore.select().count() == remaining * CORES
    # Under the limit: nothing more to delete.
    assert retention.enforce_limit() == 0


def test_new_samples_slide_the_data(storage):
    retention.set_limit_mb(1)
    fill(8000)
    retention.enforce_limit()
    later = START + datetime.timedelta(days=1)
    for day in range(3):
        fill(2000, start=later + datetime.timedelta(hours=day))
        retention.enforce_limit()
        assert retention.used_bytes() <= retention.MB
    assert Cpu.select(Cpu.time).order_by(Cpu.time.desc()).first().time > later


def test_compact_shrinks_the_file(storage):
    fill(8000)
    retention.set_limit_mb(1)
    retention.enforce_limit()
    before = retention.file_bytes()
    retention.compact()
    assert retention.file_bytes() < before
    assert retention.storage_status()['free_bytes'] == 0


def test_status_api(logged_client):
    fill(10)
    status = logged_client.get('/api/admin/storage').get_json()
    assert status['limit_mb'] is None
    assert status['limit_bytes'] is None
    assert status['samples'] == 10
    assert status['used_bytes'] > 0
    assert status['file_bytes'] > 0
    assert status['oldest'] == '2026-01-01 00:00:00'
    assert status['newest'] == '2026-01-01 00:00:27'


def test_update_api_applies_the_limit(logged_client):
    fill(8000)
    response = logged_client.put('/api/admin/storage', json={'limit_mb': 1})
    assert response.status_code == 200
    status = response.get_json()
    assert status['limit_mb'] == 1
    assert status['limit_bytes'] == retention.MB
    assert status['deleted'] > 0
    assert status['used_bytes'] <= retention.MB

    for unlimited in (None, 0):
        response = logged_client.put('/api/admin/storage', json={'limit_mb': unlimited})
        assert response.status_code == 200
        assert response.get_json()['limit_mb'] is None
    retention.compact()


@pytest.mark.parametrize('payload', [
    None,
    {},
    {'limit_mb': 'big'},
    {'limit_mb': True},
    {'limit_mb': 1.5},
    {'limit_mb': -3},
    {'limit_mb': retention.MAX_LIMIT_MB + 1},
])
def test_update_api_rejects_invalid_limits(logged_client, payload):
    response = logged_client.put('/api/admin/storage', json=payload)
    assert response.status_code == 400
    assert 'error' in response.get_json()
    assert retention.get_limit_mb() is None


def test_compact_api(logged_client):
    response = logged_client.post('/api/admin/storage/compact')
    assert response.status_code == 200
    assert response.get_json()['free_bytes'] == 0


@pytest.mark.parametrize('method, route', [
    ('get', '/api/admin/storage'),
    ('put', '/api/admin/storage'),
    ('post', '/api/admin/storage/compact'),
])
def test_admin_api_requires_login(client, method, route):
    response = getattr(client, method)(route, json={'limit_mb': 1})
    assert response.status_code == 401
