from peewee import *
import datetime
from server.models.base import BaseModel

class Metric(BaseModel):
	time = DateTimeField(default=datetime.datetime.now)

class Cpu(Metric):
	id = PrimaryKeyField()
	
class CpuCore(BaseModel):
	cpu = ForeignKeyField(Cpu)
	name = CharField()
	load = DecimalField()