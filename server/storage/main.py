#!/usr/bin/env python
# -*- coding: utf-8 -*-

from playhouse.migrate import SqliteMigrator, migrate

from server.models.base import db
from server.models.metrics import Cpu, CpuCore
from server.models.user import User


def _add_missing_user_columns():
    """Add columns introduced after the user table was first created."""
    columns = {column.name for column in db.get_columns(User._meta.table_name)}
    if 'password_hash' not in columns:
        migrator = SqliteMigrator(db)
        migrate(migrator.add_column(User._meta.table_name, 'password_hash', User.password_hash))


class Datastore():

    def __init__(self, args=None):
        db.connect(reuse_if_open=True)
        db.create_tables([Cpu, CpuCore, User])
        _add_missing_user_columns()

    def close(self):
        db.close()
