import pytest
from unittest.mock import AsyncMock, patch

from src.PersistentBot import PersistentBot

@pytest.fixture(scope='session')
def mock_send_message():
    with patch("telegram.ext.ExtBot.send_message", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(scope='session')
def mock_db_insert():
    with patch("BotSQL.insert", new=AsyncMock()):
        yield True


@pytest.fixture(scope='session')
def mock_reply_text():
    with patch("telegram.Message.reply_text", new_callable=AsyncMock) as mock:
        yield mock



