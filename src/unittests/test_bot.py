import pytest
from unittest.mock import AsyncMock, patch

from telegram import Update, User, Message, Chat, MessageEntity
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


