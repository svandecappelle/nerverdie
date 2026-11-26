from peewee import (
    AutoField,
    DateTimeField,
    ForeignKeyField,
    CharField,
    DecimalField,
    DoubleField,
)
import datetime
from server.models.base import BaseModel


class Metric(BaseModel):
    # Indexed: the history is read by time range.
    time = DateTimeField(default=datetime.datetime.now, index=True)


class Cpu(Metric):
    """One collector run (every 3 s); its time stamps the values below."""
    id = AutoField()


class CpuCore(BaseModel):
    cpu = ForeignKeyField(Cpu)
    name = CharField()
    load = DecimalField()


class Measure(BaseModel):
    """Other value collected with a CPU sample: memory.used, memory.swap,
    network.incoming / network.outgoing (bytes per second)."""
    sample = ForeignKeyField(Cpu, index=True)
    name = CharField()
    value = DoubleField()
