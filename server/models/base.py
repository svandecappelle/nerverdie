from peewee import SqliteDatabase, Model

db = SqliteDatabase('db.sqlite')


class BaseModel(Model):
    class Meta:
        database = db
