import peewee
import os, sys
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
if "pytest" in sys.modules:
    print("PYTEST DETENCTED")
    mysql_db = peewee.MySQLDatabase(os.getenv("MYSQLT_DB"), user=os.getenv("MYSQLT_USER"),
                            password=os.getenv("MYSQLT_PASSWORD"),
                            host=os.getenv("MYSQLT_HOST"), port=int(os.getenv("MYSQLT_PORT")))
else:
    mysql_db = peewee.MySQLDatabase(os.getenv("MYSQL_DB"), user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"),
                                    host=os.getenv("MYSQL_HOST"), port=int(os.getenv("MYSQL_PORT")))


class BaseModel(peewee.Model):
    class Meta:
        database = mysql_db


# Define tables
class Chat(BaseModel):
    id = peewee.IntegerField(primary_key=True)
    zip = peewee.IntegerField()


class NonRecurringEvent(BaseModel):
    event_id = peewee.AutoField()
    reminders = peewee.CharField(255)
    reminder_open = peewee.BooleanField()
    user = peewee.ForeignKeyField(Chat, backref='non_recurring_events')
    name = peewee.CharField(255)
    date = peewee.DateField()
    time = peewee.TimeField()





class RecurringEvent(BaseModel):
    event_id = peewee.AutoField()
    user = peewee.ForeignKeyField(Chat, backref='recurring_events')
    name = peewee.CharField(255)
    recurrence = peewee.CharField(255)
    time = peewee.CharField(5)


class ToDo(BaseModel):
    id = peewee.AutoField()
    user = peewee.ForeignKeyField(Chat, backref='to_do_items')
    text = peewee.CharField(255)
    done = peewee.BooleanField()


if "pytest" in sys.modules:
    mysql_db.create_tables([Chat, NonRecurringEvent, RecurringEvent, ToDo])

if __name__ == "__main__":
    mysql_db.connect()
    mysql_db.close()
