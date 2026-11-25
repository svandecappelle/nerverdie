# -*- coding: utf-8 -*-
"""Smoke tests of the monitoring API on the current Python / dependency versions."""

import pytest

from server.application import APP

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
    '/api/history/cpu',
    '/api/history/memory',
    '/api/history/network',
]


def test_all_api_routes_are_registered():
    adapter = APP.url_map.bind('localhost')
    for route in API_ROUTES:
        adapter.match(route)  # raises NotFound when no rule matches


@pytest.mark.parametrize('route', API_ROUTES)
def test_api_route_returns_json(logged_client, route):
    response = logged_client.get(route)
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.is_json


def test_system_info_has_distribution(logged_client):
    platform_info = logged_client.get('/api/system_info').get_json()['platform']
    assert len(platform_info['distribution']) == 3


@pytest.mark.parametrize('path', ['../../../../start.py', '..%2F..%2F..%2Fstart.py', 'missing.js'])
def test_static_route_does_not_leak_files_outside_dist(client, path):
    response = client.get('/' + path)
    # Unknown or out-of-tree paths fall back to the SPA index (or 404 when the
    # client has not been built), never to the requested file.
    assert response.status_code in (200, 404)
    assert b'Starter' not in response.data


def test_cpu_load_is_shared_by_threads_and_close_calls(monkeypatch):
    import collections
    import threading

    from server.console import metric

    Times = collections.namedtuple('Times', 'user system idle')
    samples = iter([
        [Times(0, 0, 0), Times(0, 0, 0)],
        [Times(30, 10, 60), Times(5, 5, 90)],      # 40 % and 10 % busy
        [Times(130, 10, 60), Times(5, 5, 190)],    # then 100 % and 0 %
    ])
    monkeypatch.setattr(metric.psutil, 'cpu_times', lambda percpu: next(samples))
    monkeypatch.setattr(metric.time, 'sleep', lambda seconds: None)
    monkeypatch.setattr(metric, '_cpu_measure', {'time': None, 'times': None, 'usage': None})

    # First call, from a worker thread like in waitress: a real measure, not 0 %.
    results = []
    worker = threading.Thread(target=lambda: results.append(metric.cpu_percent_per_core()))
    worker.start()
    worker.join()
    assert results == [[40.0, 10.0]]
    # A close call (tile and chart together) gets the same measure.
    assert metric.cpu_percent_per_core() == [40.0, 10.0]

    # Later, a new measure since the previous one.
    metric._cpu_measure['time'] -= 2
    assert metric.cpu_percent_per_core() == [100.0, 0.0]
