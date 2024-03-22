import peewee
from config import config

db = peewee.SqliteDatabase(config["database"]["filename"])


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Chat(BaseModel):
    chat_id = peewee.CharField(primary_key=True, unique=True, null=False)
    enabled = peewee.BooleanField(null=False, default=False)


class Reminder(BaseModel):
    chat = peewee.ForeignKeyField(Chat, backref="reminders", null=False)
    message_id = peewee.CharField(null=False)
    info = peewee.BlobField(null=False)


def setup():
    db.connect()
    db.create_tables([Chat, Reminder])
    db.close()
