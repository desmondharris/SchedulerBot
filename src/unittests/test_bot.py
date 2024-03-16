import pytest
from unittest.mock import AsyncMock, patch

from telegram import Update, User, Message, Chat, MessageEntity, WebAppData
from telegram.ext import ContextTypes, CallbackContext, ConversationHandler

import datetime

import sys

sys.path.insert(0, '.\\')
from src.PersistentBot import PersistentBot, GETZIP
from src.BotSQL import BotSQL


@pytest.mark.asyncio
async def test_start_command_response(mock_send_message):
    # Create an instance of your bot
    bot_instance = PersistentBot()

    # Simulate an update object msg="/start"
    update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=Chat(id=12345, type='private'),
            text='/start',
            entities=[MessageEntity(type='bot_command', offset=0, length=6)],
            from_user=User(id=12345, is_bot=False, first_name='Test User'),
        )
    )

    context = ContextTypes.DEFAULT_TYPE(bot_instance.app)

    # Mock sending message
    await bot_instance.start(update, context)
    mock_send_message.assert_awaited_with(12345, text="hello")


@pytest.mark.asyncio
async def test_zip_handler(mock_reply_text, mock_send_message):
    bot = PersistentBot()

    update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.datetime.now(),
            chat=Chat(id=12345, type='private'),
            text='/zip',
            entities=[MessageEntity(type='bot_command', offset=0, length=4)],
            from_user=User(id=12345, is_bot=False, first_name='Test User'),
        )
    )
    # Example of an update object from the webapp
    """
    Update(message=Message(channel_chat_created=False, chat=Chat(first_name='Desmond', id=1710495555, last_name='Harris',
     type=<ChatType.PRIVATE>, username='desmondktharris'), date=datetime.datetime(2024, 3, 15, 18, 53, 7, tzinfo=<DstTzInfo 
     'US/Eastern' EDT-1 day, 20:00:00 DST>), delete_chat_photo=False, from_user=User(first_name='Desmond', id=1710495555,
      is_bot=False, language_code='en', last_name='Harris', username='desmondktharris'), group_chat_created=False, 
      message_id=933, supergroup_chat_created=False, web_app_data=WebAppData(button_text='Go to bot portal', 
      data='{"type":"NONRECURRINGEVENT","eventName":"fsdf","eventDate":"2024-03-15","eventTime":"18:53",
      "reminders":["1-HOURS"]}')), update_id=166519222)
    """
    context = ContextTypes.DEFAULT_TYPE(bot.app)
    state = await bot.zip(update, context)
    assert state == GETZIP

    update = Update(
        update_id=2,
        message=Message(
            message_id=2,
            date=datetime.datetime.now(),
            chat=Chat(id=12345, type='private'),
            text='12345',
            from_user=User(id=12345, is_bot=False, first_name='Test User'),
        )
    )
    state = await bot.get_zip(update, context)
    # check if send message was asserted with zip code saved or zip code not saved
    mock_reply_text.assert_awaited()
    assert state == ConversationHandler.END


@pytest.mark.asyncio
async def test_web_app_data(mock_send_message, mock_db_insert, mock_run_once, mock_set_reminder):
    bot = PersistentBot()
    # Create a generic version of this update
    """
    Update(
    message=Message(channel_chat_created=False,
    chat=Chat(first_name='Desmond', id=1710495555, last_name='Harris', type=<ChatType.PRIVATE>, username='desmondktharris'), 
    date=datetime.datetime(2024, 3, 15, 18, 53, 7, tzinfo=<DstTzInfo 'US/Eastern' EDT-1 day, 20:00:00 DST>), 
    delete_chat_photo=False, 
    from_user=User(first_name='Desmond', id=1710495555, is_bot=False, language_code='en', last_name='Harris', username='desmondktharris'), 
    group_chat_created=False, 
    message_id=933,
    supergroup_chat_created=False,
    web_app_data=WebAppData(button_text='Go to bot portal', 
      data='{"type":"NONRECURRINGEVENT","eventName":"fsdf","eventDate":"2024-03-15","eventTime":"18:53",
      "reminders":["1-HOURS"]}')), update_id=166519222)
    """
    # convert this to a dictionary
    type = "NONRECURRINGEVENT"
    event_name = "Unit Test Event"
    event_date = "2024-03-15"
    event_time = "18:53"
    reminders = ["5-MINUTES"]
    data = {
        "type": type,
        "eventName": event_name,
        "eventDate": event_date,
        "eventTime": event_time,
        "reminders": reminders
    }

    update = Update(
        message=Message(
            channel_chat_created=False,
            chat=Chat(first_name='Desmond', id=172345, last_name='Harris', type='private',
                      username='desmondktharris'),
            date=datetime.datetime.now(),
            delete_chat_photo=False,
            from_user=User(first_name='John', id=172345, is_bot=False, language_code='en'),
            group_chat_created=False,
            message_id=933,
            supergroup_chat_created=False,
            web_app_data=WebAppData(button_text='Go to bot portal',
                                    data=f'{{"type":"{type}","eventName":"{event_name}","eventDate":"{event_date}","eventTime":"{event_time}","reminders":["5-MINUTES"]}}')),
        update_id=166519222
    )
    context = ContextTypes.DEFAULT_TYPE(bot.app)
    await bot.web_app_data(update, context)
    mock_send_message.assert_awaited_with(172345, text="Event added!")
    mock_run_once.assert_called_once()



@pytest.mark.asyncio
async def test_recurring_event():
    pass

