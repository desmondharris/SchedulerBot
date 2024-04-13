import pytest
from unittest.mock import AsyncMock, patch

from telegram import Update, User, Message, Chat, MessageEntity, WebAppData
from telegram.ext import ContextTypes, CallbackContext, ConversationHandler

import datetime

from src.PersistentBot import PersistentBot, GETZIP
from src.BotSQL import *
from src.unittests.BotTester import Tester

CLI = Tester()


@pytest.mark.asyncio
async def test_main():
    async def test_zip_convo():
        await CLI.send_msg("/zip")
        resp = await CLI.fetch_responses(1)
        assert resp[0].message == "Enter your ZIP code:"

        await CLI.send_msg("55555")
        resp = await CLI.fetch_responses(1)
        assert resp[0].message == "Your zip code has been added!"

    await test_zip_convo()

    async def test_add_revent():
        await CLI.send_msg("/new")
        resp = await CLI.fetch_responses(1)
        assert resp[0].message == "Launching portal..."
        # Send mock request

    await test_add_revent()






