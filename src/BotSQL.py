import peewee
from src.Keys import Key
from datetime import datetime as dt
from datetime import time, date
import logging

logger = logging.getLogger(__name__)

mysql_db = peewee.MySQLDatabase(Key.MYSQL_DB, user=Key.MYSQL_USER, password=Key.MYSQL_PASSWORD,
                                host=Key.MYSQL_HOST, port=3306)


class BaseModel(peewee.Model):
    class Meta:
        database = mysql_db


# Define tables
class User(BaseModel):
    id = peewee.IntegerField(primary_key=True)
    zip = peewee.IntegerField()


class NonRecurringEvent(BaseModel):
    event_id = peewee.AutoField()
    user = peewee.ForeignKeyField(User, backref='non_recurring_events')
    name = peewee.CharField(255)
    date = peewee.DateField()
    time = peewee.TimeField()


class RecurringEvent(BaseModel):
    event_id = peewee.AutoField()
    user = peewee.ForeignKeyField(User, backref='recurring_events')
    name = peewee.CharField(255)
    recurrence = peewee.CharField(255)
    time = peewee.CharField(5)


class ToDo(BaseModel):
    id = peewee.AutoField()
    user = peewee.ForeignKeyField(User, backref='to_do_items')
    text = peewee.CharField(255)
    done = peewee.BooleanField()


if __name__ == "__main__":
    mysql_db.connect()
    mysql_db.create_tables([ToDo])
