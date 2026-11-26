# -*- coding: utf-8 -*-
"""Database size limit: measure the SQLite database and slide the metrics.

When the data stored in the database goes over the configured limit, the
oldest metric samples are deleted until it is back under PURGE_TARGET of
the limit, so that new samples can be stored. Users and settings are never
deleted.

Deleting rows does not shrink the SQLite file: freed pages are reused by
new rows. The limit therefore applies to the pages in use, and `compact()`
(VACUUM) gives the free pages back to the file system.
"""

import logging
import os

from server.console.history import json_date
from server.models.base import db
from server.models.metrics import Cpu, CpuCore, Measure
from server.models.setting import Setting

LOGGER = logging.getLogger(__name__)

MB = 1024 * 1024
LIMIT_SETTING = 'db_max_size_mb'
MIN_LIMIT_MB = 1
MAX_LIMIT_MB = 1024 * 1024  # 1 TB
# Purge down to 90% of the limit, so that purges do not run on every insert.
PURGE_TARGET = 0.9
MIN_BATCH = 50
MAX_PURGE_ROUNDS = 1000


def get_limit_mb():
    """Configured limit in MB, or None when the database size is unlimited."""
    value = Setting.read(LIMIT_SETTING)
    return int(value) if value else None


def set_limit_mb(limit_mb):
    """Set the limit in MB (None: unlimited). Raises ValueError when out of range."""
    if limit_mb is not None:
        limit_mb = int(limit_mb)
        if not MIN_LIMIT_MB <= limit_mb <= MAX_LIMIT_MB:
            raise ValueError('limit must be between %d and %d MB' % (MIN_LIMIT_MB, MAX_LIMIT_MB))
    Setting.write(LIMIT_SETTING, None if limit_mb is None else str(limit_mb))


def _pragma(name):
    return db.execute_sql('PRAGMA %s' % name).fetchone()[0]


def used_bytes():
    """Bytes of the database pages holding data (free pages excluded)."""
    return (_pragma('page_count') - _pragma('freelist_count')) * _pragma('page_size')


def file_bytes():
    """Size on disk of the database file and its write-ahead log."""
    total = 0
    for suffix in ('', '-wal'):
        path = db.database + suffix
        if os.path.isfile(path):
            total += os.path.getsize(path)
    return total


def _delete_oldest(count):
    oldest = Cpu.select(Cpu.id).order_by(Cpu.time.asc(), Cpu.id.asc()).limit(count)
    with db.atomic():
        CpuCore.delete().where(CpuCore.cpu.in_(oldest)).execute()
        Measure.delete().where(Measure.sample.in_(oldest)).execute()
        return Cpu.delete().where(Cpu.id.in_(oldest)).execute()


def enforce_limit():
    """Delete the oldest samples while the data is over the limit.

    Returns the number of deleted samples (one sample = one collector run:
    per-core loads, memory and network).
    """
    limit_mb = get_limit_mb()
    if limit_mb is None:
        return 0
    limit = limit_mb * MB
    used = used_bytes()
    if used <= limit:
        return 0

    target = limit * PURGE_TARGET
    deleted = 0
    for _ in range(MAX_PURGE_ROUNDS):
        samples = Cpu.select().count()
        if not samples:
            break
        # Delete the share of samples matching the excess, at least MIN_BATCH.
        batch = max(MIN_BATCH, int(samples * (used - target) / used) + 1)
        deleted += _delete_oldest(batch)
        used = used_bytes()
        if used <= target:
            break
    LOGGER.info("Database over its %d MB limit: deleted the %d oldest samples (%d bytes used)",
                limit_mb, deleted, used)
    return deleted


def compact():
    """Give the free pages back to the file system (VACUUM)."""
    db.execute_sql('VACUUM')
    db.execute_sql('PRAGMA wal_checkpoint(TRUNCATE)')


def storage_status():
    """Sizes, limit and stored samples, for the admin screen."""
    oldest = Cpu.select(Cpu.time).order_by(Cpu.time.asc()).first()
    newest = Cpu.select(Cpu.time).order_by(Cpu.time.desc()).first()
    limit_mb = get_limit_mb()
    used = used_bytes()
    return {
        'limit_mb': limit_mb,
        'limit_bytes': None if limit_mb is None else limit_mb * MB,
        'used_bytes': used,
        'file_bytes': file_bytes(),
        'free_bytes': _pragma('freelist_count') * _pragma('page_size'),
        'samples': Cpu.select().count(),
        'oldest': json_date(oldest.time) if oldest else None,
        'newest': json_date(newest.time) if newest else None,
        'min_limit_mb': MIN_LIMIT_MB,
        'max_limit_mb': MAX_LIMIT_MB,
    }
