from peewee import CharField

from server.models.base import BaseModel


class User(BaseModel):
    username = CharField(unique=True)
