import os
from functools import wraps
import datetime
from pprint import pprint as prp

import pytest
import peewee
from peewee import MySQLDatabase, Update
from dotenv import load_dotenv

import telegram as tg
from telegram import Update, Message
from telegram.ext import Application, CommandHandler, ContextTypes

from ..BotSQL import Chat, NonRecurringEvent, RecurringEvent, ToDo
from ..BotRefactor import start
from ..MessageOptions import *
from . import NetworkMocking

load_dotenv()


# create separate db for testing
TEST_DB = MySQLDatabase(os.getenv("MYSQLT_DB"), user=os.getenv("MYSQLT_USER"), password=os.getenv("MYSQLT_PASSWORD"),
                                host=os.getenv("MYSQLT_HOST"), port=int(os.getenv("MYSQLT_PORT")))
TEST_DB.connect()


TEST_USER_ID = 2350495555

"""
IMPORTANT
Application.process_update must have a return statement added on line 1335 for tests to function. 


any_blocking = True
return await coroutine

process_update will now return the mock response for assertion.
^^^^^^
"""


# utility for getting telegram object ids
class UpdateIdClass:
    def __init__(self):
        self.count = 0

    def inc(self):
        self.count += 1
        return self.count


@pytest.fixture(scope='session')
def update_id():
    return UpdateIdClass()


class MessageIdClass:
    def __init__(self):
        self.count = 0

    def inc(self):
        self.count += 1
        return self.count


@pytest.fixture(scope='session')
def message_id():
    return MessageIdClass()


# set up bot that doesn't check for updates
@pytest.fixture(scope='session')
def app():
    application = Application.builder().token(os.getenv("TELEGRAM_API_KEY")).updater(None).request(NetworkMocking.NetworkMocking()).build()
    application.add_handler(CommandHandler("start", start))
    yield application



class TestBot:
    @pytest.mark.asyncio
    async def test_start(self, app, update_id, message_id):
        await app.initialize()
        temp_chat = tg.Chat(TEST_USER_ID, "PRIVATE")
        m = Message(message_id=message_id.inc(), text="/start", chat=temp_chat, date=datetime.datetime.today(),
                    entities=[tg.MessageEntity(length=6, offset=0, type=tg.MessageEntity.BOT_COMMAND)])
        m.set_bot(app.bot)

        ud = tg.Update(update_id.inc(), message=m)
        ud.set_bot(app.bot)

        res = await app.process_update(ud)
        prp(res)

        # Proper response from Telegram
        assert type(res) == Message

        # Test user should be brand new
        assert res.text == FIRST_TIME_GREETING

        # User should be in database
        try:
            Chat.get_by_id(TEST_USER_ID)
        except peewee.DoesNotExist:
            pytest.fail("Test user not added to database")


