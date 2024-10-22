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
from src.BotRefactor import start, onetime_start, add_handlers
from src.MessageOptions import *
from . import NetworkMocking

load_dotenv()


# create separate db for testing
TEST_DB = MySQLDatabase(os.getenv("MYSQLT_DB"), user=os.getenv("MYSQLT_USER"), password=os.getenv("MYSQLT_PASSWORD"),
                                host=os.getenv("MYSQLT_HOST"), port=int(os.getenv("MYSQLT_PORT")))
TEST_DB.connect()


TEST_USER_ID = 123456

user_user_obj = tg.User(first_name='Desmond', id=1710495555, is_bot=False, language_code='en', last_name='Harris',
                     username='desmondktharris')
bot_user_obj = tg.User(first_name='Scheduler', id=6446614126, is_bot=True, username='dkhschedule_bot')

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


def message_factory(message_id, text="", **kwargs):
    """
    @param message_id: fixture
    @param text: message text(defaults to blank)
    @param kwargs: other attributes for ptb to handle(entities, etc)
    @return:
    """
    return Message(message_id=message_id.inc(), text=text, chat=tg.Chat(TEST_USER_ID, "PRIVATE"), date=datetime.datetime.today(), **kwargs)


# set up bot that doesn't check for updates
@pytest.fixture(scope='session')
def app():
    application = Application.builder().token(os.getenv("TELEGRAM_API_KEY")).updater(None).request(
        NetworkMocking.NetworkMocking()).build()
    add_handlers(application)
    yield application


class TestBot:
    from_user_chat = tg.Chat(TEST_USER_ID, "PRIVATE")

    @pytest.mark.asyncio
    async def test_start(self, app, update_id, message_id):
        await app.initialize()
        ent = tg.MessageEntity(length=6, offset=0, type=tg.MessageEntity.BOT_COMMAND)
        m = message_factory(message_id, "/start", entities=[ent])
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
    @pytest.mark.parametrize("day, time, name",
                             [
                                 ("monday", "1700", "Test Non Recurring Event 1", ),
                                    ("tuesday", "1700", "Test Non Recurring Event 2"),
                                    ("wednesday", "1700", "Test Non Recurring Event 3"),
                                    ("thursday", "1700", "Test Non Recurring Event 4"),
                                    ("friday", "1700", "Test Non Recurring Event 5"),
                                    ("saturday", "1700", "Test Non Recurring Event 6"),
                                    ("sunday", "1700", "Test Non Recurring Event 7")
                             ])
    @pytest.mark.asyncio
    async def test_ot_event(self, app, update_id, message_id, day, time, name):
        msg_txt = f"/ot {day} {time} {name}"
        ent = tg.MessageEntity(length=3, offset=0, type=tg.MessageEntity.BOT_COMMAND)
        m = message_factory(message_id, msg_txt, entities=[ent])
        ud = tg.Update(update_id.inc(), message=m)
        ud.set_bot(app.bot)
        m.set_bot(app.bot)
        res = await app.process_update(ud)
        assert type(res) == Message, f"Expected start to return Message, got {type(res)}"
        assert res.text == WEEKDAY_INLINE_TEXT, f"Expected {WEEKDAY_INLINE_TEXT}, got {res.text}"
        assert res.reply_markup == WEEKDAY_INLINE_KB, "Improper InlineKeyboard"

        try:
            created_event = NonRecurringEvent.select().where((NonRecurringEvent.user == TEST_USER_ID)
                                                             & (NonRecurringEvent.name == name))[0]
        except peewee.DoesNotExist:
            pytest.fail("NonRecurringEvent not added to database")

        assert created_event.reminder_open == True
        assert created_event.name == name
        assert created_event.time ==  datetime.datetime.strptime(time, "%H%M").time()

        reminders_responses = [("5-minutes", "Set 5 minute reminder."), ("15-minutes", "Set 15 minute reminder."),
                                 ("30-minutes", "Set 30 minute reminder."), ("1-hours", "Set 1 hour reminder."),
                                 ("2-hours", "Set 2 hour reminder."), ("4-hours", "Set 4 hour reminder."),
                               ("close-reminder", "Reminders set.")]
        for callback_data, expected_reply in reminders_responses:
            cbq = tg.CallbackQuery(id=str(message_id.inc()), data=callback_data,
                                   message=m, from_user=user_user_obj, chat_instance="7849395941589147207")
            m = message_factory(message_id, from_user=bot_user_obj, reply_markup=WEEKDAY_INLINE_KB, text="Reminders?")
            ud = tg.Update(update_id.inc(), callback_query=cbq)
            [tg_element.set_bot(app.bot) for tg_element in [m, cbq, ud]]
            res = await app.process_update(ud)

            assert res.text == expected_reply, f"Expected {expected_reply}, got {res}"
            created_event = NonRecurringEvent.get_by_id(created_event.event_id)
            if cbq.data != "close-reminder":
                assert cbq.data in created_event.reminders, f"Expected {cbq.data} in reminders, got {created_event.reminders}"
            else:
                assert created_event.reminder_open == False

    def test_clean_db(self):
        NonRecurringEvent.delete().execute()
        RecurringEvent.delete().execute()
        ToDo.delete().execute()
        Chat.delete().execute()
        assert Chat.select().count() == 0, "Chat table not cleared"
        assert NonRecurringEvent.select().count() == 0, "NonRecurringEvent table not cleared"
        assert RecurringEvent.select().count() == 0, "RecurringEvent table not cleared"
        assert ToDo.select().count() == 0, "ToDo table not cleared"
