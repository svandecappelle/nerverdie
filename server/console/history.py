# -*- coding: utf-8 -*-
"""Stored metrics history, read by time range for the dashboard charts."""

import math
from datetime import datetime, timedelta, timezone

from server.models.base import db
from server.models.metrics import Cpu, CpuCore, Measure

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_SPAN = timedelta(hours=1)
# The collector stores a sample every 3 seconds.
COLLECT_PERIOD = 3
# One hour of samples without averaging.
DEFAULT_POINTS = 1200
MIN_POINTS = 10
MAX_POINTS = 2000
MAX_SPAN = timedelta(days=400)

# Series of each metric: stored name -> name in the history entries.
MEASURES = {
    'memory': {'memory.used': 'used', 'memory.swap': 'swap'},
    'network': {'network.incoming': 'incoming', 'network.outgoing': 'outgoing'},
}
METRICS = ('cpu',) + tuple(MEASURES)


def _format(moment):
    return moment.strftime(DATE_FORMAT)


def _from_epoch(seconds):
    """Inverse of SQLite strftime('%s'), which reads a stored local time as UTC."""
    return datetime.fromtimestamp(seconds, timezone.utc).replace(tzinfo=None)


class History:
    def get(self, metric='cpu', start=None, end=None, points=DEFAULT_POINTS):
        """Values of `metric` between `start` and `end` (local datetimes).

        At most about `points` entries are returned: over long ranges the
        samples are averaged by time buckets of `step` seconds. Returns
        {'step': seconds, 'from': date, 'to': date, 'samples': [
            {'date': 'YYYY-MM-DD HH:MM:SS', '<serie>': value, ...}, ...]}
        oldest first, where the series are cpu0, cpu1... for 'cpu',
        used / swap for 'memory' and incoming / outgoing (bytes/s) for
        'network'.
        """
        if metric not in METRICS:
            raise ValueError('unknown metric %r' % metric)
        end = end or datetime.now()
        start = start or end - DEFAULT_SPAN
        if start >= end:
            raise ValueError('the start of the range must be before its end')
        if end - start > MAX_SPAN:
            raise ValueError('the range cannot exceed %d days' % MAX_SPAN.days)
        points = min(max(int(points), MIN_POINTS), MAX_POINTS)

        step = max(COLLECT_PERIOD, math.ceil((end - start).total_seconds() / points))
        # Short ranges: one entry per sample (they are 3 s apart, never in the same second).
        bucket = step if step > COLLECT_PERIOD else 1

        sample = Cpu._meta.table_name
        if metric == 'cpu':
            table, link, value, names = CpuCore._meta.table_name, 'cpu_id', 'load', None
        else:
            table, link, value, names = Measure._meta.table_name, 'sample_id', 'value', MEASURES[metric]
        # Only internal constants are formatted in; the range and names are parameters.
        query = (  # noqa: S608
            'SELECT (CAST(strftime(\'%%s\', s."time") AS INTEGER) / %(bucket)d) * %(bucket)d AS bucket, '
            'v."name", AVG(v."%(value)s") '
            'FROM "%(table)s" AS v JOIN "%(sample)s" AS s ON v."%(link)s" = s."id" '
            'WHERE s."time" >= ? AND s."time" <= ? %(names)s'
            'GROUP BY bucket, v."name" ORDER BY bucket'
        ) % {
            'bucket': bucket, 'value': value, 'table': table, 'sample': sample, 'link': link,
            'names': 'AND v."name" IN (%s) ' % ', '.join('?' * len(names)) if names else '',
        }
        params = [_format(start), _format(end)] + (list(names) if names else [])

        samples = []
        entries = {}
        for moment, name, average in db.execute_sql(query, params):
            entry = entries.get(moment)
            if entry is None:
                entry = entries[moment] = {'date': _format(_from_epoch(moment))}
                samples.append(entry)
            entry[names[name] if names else name] = round(average, 2)
        return {'step': step, 'from': _format(start), 'to': _format(end), 'samples': samples}
