from peewee import *
from src.Keys import Key
from datetime import datetime as dt
from datetime import time, date
import logging

logger = logging.getLogger(__name__)

mysql_db = MySQLDatabase(Key.MYSQL_DB, user=Key.MYSQL_USER, password=Key.MYSQL_PASSWORD,
                         host=Key.MYSQL_HOST, port=3306)


class BaseModel(Model):
    class Meta:
        database = mysql_db


# Define tables
class User(BaseModel):
    id = IntegerField(primary_key=True)
    zip = IntegerField()


class NonRecurringEvent(BaseModel):
    event_id = AutoField()
    user = ForeignKeyField(User, backref='non_recurring_events')
    name = CharField(255)
    date = DateField()
    time = TimeField()


class RecurringEvent(BaseModel):
    event_id = AutoField()
    user = ForeignKeyField(User, backref='recurring_events')
    name = CharField(255)
    recurrence = CharField(255)
    time = CharField(5)


if __name__ == "__main__":
    mysql_db.connect()
    # mysql_db.create_tables([User, NonRecurringEvent, RecurringEvent])
    # User.create(id=453234234)
    NonRecurringEvent.create(user=453234234, date=date(2023, month=12, day=20), time=time(hour=15, minute=0), name="pwtest")
    mysql_db.commit()

