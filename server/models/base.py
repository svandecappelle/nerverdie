from peewee import *
import datetime

db = SqliteDatabase('db.sqlite')


class BaseModel(Model):
    class Meta:
        database = db