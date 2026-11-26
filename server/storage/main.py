#!/usr/bin/env python
# -*- coding: utf-8 -*-

from playhouse.migrate import SqliteMigrator, migrate

from server.models.base import db
from server.models.metrics import Cpu, CpuCore, Measure
from server.models.security import LoginEvent
from server.models.setting import Setting
from server.models.user import User


def _add_missing_user_columns():
    """Add columns introduced after the user table was first created."""
    columns = {column.name for column in db.get_columns(User._meta.table_name)}
    migrator = SqliteMigrator(db)
    missing = [
        migrator.add_column(User._meta.table_name, field.column_name, field)
        for field in (User.password_hash, User.failed_logins, User.locked_until)
        if field.column_name not in columns
    ]
    if missing:
        migrate(*missing)


class Datastore():

    def __init__(self, args=None):
        db.connect(reuse_if_open=True)
        db.create_tables([Cpu, CpuCore, Measure, User, Setting, LoginEvent])
        _add_missing_user_columns()
        # Databases created before the time index existed.
        db.execute_sql('CREATE INDEX IF NOT EXISTS "cpu_time" ON "cpu" ("time")')

    def close(self):
        db.close()
