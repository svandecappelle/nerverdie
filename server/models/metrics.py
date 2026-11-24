from peewee import (
    AutoField,
    DateTimeField,
    ForeignKeyField,
    CharField,
    DecimalField
)
import datetime
from server.models.base import BaseModel


class Metric(BaseModel):
    time = DateTimeField(default=datetime.datetime.now)


class Cpu(Metric):
    id = AutoField()


class CpuCore(BaseModel):
    cpu = ForeignKeyField(Cpu)
    name = CharField()
    load = DecimalField()
