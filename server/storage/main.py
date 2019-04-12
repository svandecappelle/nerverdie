#!/usr/bin/env python
# -*- coding: utf-8 -*-

from peewee import SqliteDatabase
from server.models.metrics import Cpu, CpuCore
from server.models.user import User


db = SqliteDatabase('app.db', pragmas={
    'journal_mode': 'wal',
    'cache_size': -32 * 1000})


class Datastore():

    def __init__(self, args={}):
        db.connect()
        db.create_tables([Cpu, CpuCore, User])

    def close(self):
        db.close()
