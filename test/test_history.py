# -*- coding: utf-8 -*-
"""Metrics history by time range, and the values stored by the collector."""

import datetime
import time

import pytest

from server.daemon import Daemon
from server.models.metrics import Cpu, CpuCore, Measure
from server.storage import retention

NOW = datetime.datetime.now().replace(microsecond=0)


def ms(moment):
    return int(moment.timestamp() * 1000)


def iso(moment):
    """A local datetime as the API sends it: with the UTC offset of the server."""
    return moment.astimezone().isoformat(timespec='seconds')


def store(moment, loads=(), measures=None, as_string=False):
    cpu = Cpu.create(time=moment.strftime('%Y-%m-%d %H:%M:%S') if as_string else moment)
    for core, load in enumerate(loads):
        CpuCore.create(cpu=cpu, name='cpu%d' % core, load=load)
    for name, value in (measures or {}).items():
        Measure.create(sample=cpu, name=name, value=value)
    return cpu


def history(client, metric, **params):
    response = client.get('/api/history/' + metric, query_string=params)
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()


def test_empty_history(logged_client):
    result = history(logged_client, 'cpu')
    assert result['samples'] == []
    assert result['step'] == 3


def test_cpu_history_returns_every_sample_of_a_short_range(logged_client):
    times = [NOW - datetime.timedelta(seconds=offset) for offset in (9, 6, 3, 0)]
    for index, moment in enumerate(times):
        # The collector stores the time as a string, older rows as datetimes.
        store(moment, [10 * (index + 1) + core for core in range(3)], as_string=index % 2 == 1)
    store(NOW - datetime.timedelta(hours=2), [99])  # before the range

    result = history(logged_client, 'cpu')

    assert result['samples'] == [
        {'date': iso(moment),
         'cpu0': 10.0 * (index + 1), 'cpu1': 10.0 * (index + 1) + 1, 'cpu2': 10.0 * (index + 1) + 2}
        for index, moment in enumerate(times)
    ]


def test_long_ranges_are_averaged_by_buckets(logged_client):
    start = NOW.replace(minute=0, second=0) - datetime.timedelta(hours=2)
    for index in range(1200):  # one hour, every 3 s
        store(start + datetime.timedelta(seconds=3 * index), [index % 2 * 100])

    result = history(logged_client, 'cpu', points=60, **{'from': ms(start), 'to': ms(start + datetime.timedelta(hours=1))})

    assert result['step'] == 60
    assert len(result['samples']) in (60, 61)
    # 0 and 100 alternate: every bucket averages to 50.
    assert all(sample['cpu0'] == 50 for sample in result['samples'][:-1])
    dates = [sample['date'] for sample in result['samples']]
    assert dates == sorted(dates)
    assert dates[0] == iso(start)


def test_range_bounds_are_applied(logged_client):
    for minutes in (50, 30, 10):
        store(NOW - datetime.timedelta(minutes=minutes), [minutes])
    result = history(logged_client, 'cpu', **{
        'from': ms(NOW - datetime.timedelta(minutes=40)), 'to': ms(NOW - datetime.timedelta(minutes=20))})
    assert [sample['cpu0'] for sample in result['samples']] == [30]


def test_memory_and_network_history(logged_client):
    store(NOW - datetime.timedelta(seconds=3), measures={
        'memory.used': 4e9, 'memory.swap': 1e9, 'network.incoming': 1000, 'network.outgoing': 250})
    store(NOW, measures={'memory.used': 5e9, 'memory.swap': 1e9})

    memory = history(logged_client, 'memory')['samples']
    assert [(s['used'], s['swap']) for s in memory] == [(4e9, 1e9), (5e9, 1e9)]
    network = history(logged_client, 'network')['samples']
    assert network == [{'date': iso(NOW - datetime.timedelta(seconds=3)),
                        'incoming': 1000, 'outgoing': 250}]


def test_dates_carry_the_utc_offset_of_the_server(logged_client):
    # A browser in another time zone must read the moment of the sample, not the same clock time.
    store(NOW - datetime.timedelta(seconds=3), [42])
    result = history(logged_client, 'cpu')
    for date in (result['samples'][0]['date'], result['from'], result['to']):
        assert datetime.datetime.fromisoformat(date).utcoffset() is not None
    moment = datetime.datetime.fromisoformat(result['samples'][0]['date'])
    assert moment.timestamp() == (NOW - datetime.timedelta(seconds=3)).timestamp()


@pytest.mark.skipif(not hasattr(time, 'tzset'), reason='changing the time zone needs time.tzset (POSIX)')
@pytest.mark.parametrize('zone', ['UTC', 'Asia/Kolkata', 'America/New_York'])
def test_dates_are_right_whatever_the_server_time_zone(logged_client, monkeypatch, zone):
    monkeypatch.setenv('TZ', zone)
    time.tzset()
    try:
        now = datetime.datetime.now().replace(microsecond=0)
        store(now - datetime.timedelta(seconds=3), [42], as_string=True)
        result = history(logged_client, 'cpu', **{
            'from': ms(now - datetime.timedelta(minutes=5)), 'to': ms(now)})
        [sample] = result['samples']
        assert datetime.datetime.fromisoformat(sample['date']).timestamp() == ms(now) / 1000 - 3
        assert datetime.datetime.fromisoformat(result['to']).timestamp() == ms(now) / 1000
    finally:
        monkeypatch.undo()  # puts TZ back as it was
        time.tzset()


@pytest.mark.parametrize('params', [
    {'from': 'yesterday'},
    {'from': ms(NOW), 'to': ms(NOW - datetime.timedelta(hours=1))},
    {'from': ms(NOW - datetime.timedelta(days=500)), 'to': ms(NOW)},
    {'points': 'many'},
])
def test_invalid_ranges_are_rejected(logged_client, params):
    response = logged_client.get('/api/history/cpu', query_string=params)
    assert response.status_code == 400
    assert response.is_json


def test_unknown_metric(logged_client):
    assert logged_client.get('/api/history/disk').status_code == 404


def test_history_requires_login(client):
    assert client.get('/api/history/memory').status_code == 401


def test_collector_stores_memory_and_network_throughput(client, monkeypatch):
    from server.console import metric

    totals = iter([(1_000, 500), (4_000, 1_100)])
    monkeypatch.setattr(metric, 'network_totals', lambda: next(totals))
    clock = iter([100.0, 103.0])
    monkeypatch.setattr('server.daemon.time.monotonic', lambda: next(clock))
    monkeypatch.setattr(metric, 'cpu_percent_per_core', lambda: [10.0, 20.0])

    daemon = Daemon()
    daemon.job()
    daemon.job()

    first, second = Cpu.select().order_by(Cpu.id)
    assert {m.name for m in Measure.select().where(Measure.sample == first)} == {'memory.used', 'memory.swap'}
    values = {m.name: m.value for m in Measure.select().where(Measure.sample == second)}
    assert values['network.incoming'] == 1000  # 3000 bytes in 3 s
    assert values['network.outgoing'] == 200
    assert values['memory.used'] > 0
    assert CpuCore.select().where(CpuCore.cpu == second).count() == 2


def test_purge_also_deletes_the_measures(client):
    for index in range(200):
        store(NOW - datetime.timedelta(seconds=3 * (200 - index)), [1] * 8,
              {'memory.used': 1, 'memory.swap': 1, 'network.incoming': 1, 'network.outgoing': 1})
    deleted = retention._delete_oldest(50)
    assert deleted == 50
    assert Measure.select().count() == 150 * 4
    assert Measure.select().join(Cpu, on=(Measure.sample == Cpu.id)).count() == 150 * 4
