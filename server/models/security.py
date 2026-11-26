from peewee import CharField, DateTimeField

from server.models.base import BaseModel


class LoginEvent(BaseModel):
    """One login attempt: who, from where, and how it ended."""
    time = DateTimeField(index=True)
    username = CharField(max_length=150)
    address = CharField(max_length=64)
    # success, failure, locked (refused: account locked) or throttled (refused: address throttled)
    outcome = CharField(max_length=16)
