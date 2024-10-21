import os
import datetime

import pytest
import peewee
from peewee import MySQLDatabase
from dotenv import load_dotenv

import telegram as tg
from telegram import Message
from telegram.ext import Application, CommandHandler

from src.BotSQL import Chat, NonRecurringEvent, RecurringEvent, ToDo
from src.BotRefactor import start, onetime_start
from src.MessageOptions import *
from . import NetworkMocking

load_dotenv()


# create separate db for testing
TEST_DB = MySQLDatabase(os.getenv("MYSQLT_DB"), user=os.getenv("MYSQLT_USER"), password=os.getenv("MYSQLT_PASSWORD"),
                                host=os.getenv("MYSQLT_HOST"), port=int(os.getenv("MYSQLT_PORT")))
TEST_DB.connect()


TEST_USER_ID = 123456

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
    application = Application.builder().token(os.getenv("TELEGRAM_API_KEY")).updater(None).request(
        NetworkMocking.NetworkMocking()).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ot", onetime_start))
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

        # Proper response from Telegram
        assert type(res) == Message, f"Expected start to return Message, got {type(res)}"

        # Test user should be brand new
        assert res.text == FIRST_TIME_GREETING, f"Expected {FIRST_TIME_GREETING}, got {res.text}"

        # User should be in database
        try:
            Chat.get_by_id(TEST_USER_ID)
        except peewee.DoesNotExist:
            pytest.fail("Test user not added to database")


    # test conversation handler for messages of form "<weekday> <24hrtimestamp> <event name>
    @pytest.mark.asyncio
    async def test_ot_event(self, app, update_id, message_id):
        temp_chat = tg.Chat(TEST_USER_ID, "PRIVATE")
        weekday_int = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6
        }
        int_weekday = {
            0: "monday",
            1: "tuesday",
            2: "wednesday",
            3: "thursday",
            4: "friday",
            5: "saturday",
            6: "sunday"
        }
        day = datetime.date.today().weekday() + 3
        day = day % 6
        day = int_weekday[day]
        msg_txt = f"/ot {day} 1700 Test Non Reccuring Event"
        m = Message(message_id=message_id.inc(), text=msg_txt, chat=temp_chat, date=datetime.datetime.today(),
                    entities=[tg.MessageEntity(length=3, offset=0, type=tg.MessageEntity.BOT_COMMAND)])
        ud = tg.Update(update_id.inc(), message=m)
        ud.set_bot(app.bot)
        m.set_bot(app.bot)
        res = await app.process_update(ud)
        assert type(res) == Message, f"Expected start to return Message, got {type(res)}"
        assert res.text == WEEKDAY_INLINE_TEXT, f"Expected {WEEKDAY_INLINE_TEXT}, got {res.text}"
        assert res.reply_markup == WEEKDAY_INLINE_KB, "Improper InlineKeyboard"


    def test_clean_db(self):
        Chat.delete().execute()
        NonRecurringEvent.delete().execute()
        RecurringEvent.delete().execute()
        ToDo.delete().execute()
        assert Chat.select().count() == 0, "Chat table not cleared"
        assert NonRecurringEvent.select().count() == 0, "NonRecurringEvent table not cleared"
        assert RecurringEvent.select().count() == 0, "RecurringEvent table not cleared"
        assert ToDo.select().count() == 0, "ToDo table not cleared"


"""
Update(callback_query=CallbackQuery(chat_instance='7849395941589147207', data='1', from_user=User(first_name='Desmond',
 id=1710495555, is_bot=False, language_code='en', last_name='Harris', username='desmondktharris'),
  id='7346522472035322334', 
  message=Message(channel_chat_created=False, chat=Chat(first_name='Desmond', id=1710495555, last_name='Harris', 
  type=<ChatType.PRIVATE>, username='desmondktharris'), 
  date=datetime.datetime(2024, 10, 20, 3, 28, 26, tzinfo=<UTC>), delete_chat_photo=False, 
  from_user=User(first_name='Scheduler', id=6446614126, is_bot=True, username='dkhschedule_bot'), 
  group_chat_created=False, message_id=1694, 
  reply_markup=InlineKeyboardMarkup(inline_keyboard=((InlineKeyboardButton(callback_data='1', text='Option 1'), 
  InlineKeyboardButton(callback_data='2', text='Option 2')), (InlineKeyboardButton(callback_data='3', text='Option 3'),))), 
  supergroup_chat_created=False, text='Please choose:')), update_id=166519697)
"""

