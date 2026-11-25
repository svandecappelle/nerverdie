# -*- coding: utf-8 -*-
"""Stored metrics history, used to seed the dashboard charts."""

from datetime import datetime, timedelta

from server.models.metrics import Cpu, CpuCore

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_SPAN = timedelta(hours=1)


def _format_date(value):
    """Stored dates are datetimes or 'YYYY-MM-DD HH:MM:SS[.ffffff]' strings."""
    if isinstance(value, datetime):
        return value.strftime(DATE_FORMAT)
    return str(value)[:19]


class History:
    def get(self, metric='cpu', span=DEFAULT_SPAN):
        """CPU load samples of the last `span`, oldest first.

        One entry per sample: {'date': 'YYYY-MM-DD HH:MM:SS', 'cpu0': load, ...}.
        An empty list when nothing was stored in that period.
        """
        start = datetime.now() - span
        cores = (CpuCore
                 .select(CpuCore, Cpu)
                 .join(Cpu)
                 .where(Cpu.time > start.strftime(DATE_FORMAT))
                 .order_by(Cpu.time.asc(), Cpu.id.asc(), CpuCore.id.asc()))
        history = []
        entries = {}
        for core in cores:
            entry = entries.get(core.cpu.id)
            if entry is None:
                entry = entries[core.cpu.id] = {'date': _format_date(core.cpu.time)}
                history.append(entry)
            entry[core.name] = float(core.load)
        return history
