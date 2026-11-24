import os

from peewee import SqliteDatabase, Model

DB_PATH = os.environ.get('NEVERDIE_DB', 'db.sqlite')

db = SqliteDatabase(DB_PATH, pragmas={
    'journal_mode': 'wal',
    'cache_size': -32 * 1000})


class BaseModel(Model):
    class Meta:
        database = db
