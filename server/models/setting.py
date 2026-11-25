from peewee import CharField, TextField

from server.models.base import BaseModel


class Setting(BaseModel):
    """Application setting stored in the database (key / text value)."""
    key = CharField(unique=True)
    value = TextField(null=True)

    @classmethod
    def read(cls, key, default=None):
        setting = cls.get_or_none(cls.key == key)
        return default if setting is None else setting.value

    @classmethod
    def write(cls, key, value):
        cls.insert(key=key, value=value).on_conflict(
            conflict_target=[cls.key], update={cls.value: value}
        ).execute()
