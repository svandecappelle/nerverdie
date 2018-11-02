from peewee import *
import datetime

from server.models.base import BaseModel

class User(BaseModel):
    username = CharField(unique=True)
