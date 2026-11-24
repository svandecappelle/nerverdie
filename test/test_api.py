# -*- coding: utf-8 -*-
"""Smoke tests of the monitoring API on the current Python / dependency versions."""

import datetime

import pytest

from server.application import APP
from server.models.metrics import Cpu, CpuCore

API_ROUTES = [
    '/api/metrics',
    '/api/cpu',
    '/api/cpu/load',
    '/api/memory',
    '/api/memory/load',
    '/api/partitions',
    '/api/system_info',
    '/api/uptime',
    '/api/sensors',
    '/api/network',
    '/api/history/cpu/load',
]


def test_all_api_routes_are_registered():
    registered = {rule.rule for rule in APP.url_map.iter_rules()}
    assert set(API_ROUTES) <= registered


@pytest.mark.parametrize('route', API_ROUTES)
def test_api_route_returns_json(logged_client, route):
    response = logged_client.get(route)
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.is_json


def test_system_info_has_distribution(logged_client):
    platform_info = logged_client.get('/api/system_info').get_json()['platform']
    assert len(platform_info['distribution']) == 3


def test_history_on_empty_database(logged_client):
    history = logged_client.get('/api/history/cpu/load').get_json()
    assert isinstance(history, list)


def test_history_with_stored_metrics(logged_client):
    now = datetime.datetime.now().replace(microsecond=0)
    for offset in (6, 3, 0):
        cpu = Cpu.create(time=now - datetime.timedelta(seconds=offset))
        CpuCore.create(cpu=cpu, name='cpu0', load=12.5)
        CpuCore.create(cpu=cpu, name='cpu1', load=50)
    history = logged_client.get('/api/history/cpu/load').get_json()
    assert any(entry.get('cpu0') == 12.5 for entry in history)


@pytest.mark.parametrize('path', ['../../../../start.py', '..%2F..%2F..%2Fstart.py', 'missing.js'])
def test_static_route_does_not_leak_files_outside_dist(client, path):
    response = client.get('/' + path)
    # Unknown or out-of-tree paths fall back to the SPA index (or 404 when the
    # client has not been built), never to the requested file.
    assert response.status_code in (200, 404)
    assert b'Starter' not in response.data
