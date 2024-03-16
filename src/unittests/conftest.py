import pytest
from unittest.mock import AsyncMock, patch, Mock

from src.PersistentBot import PersistentBot


@pytest.fixture(scope='session')
def mock_send_message():
    with patch("telegram.ext.ExtBot.send_message", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(scope='session')
def mock_db_insert():
    with patch("src.BotSQL.BotSQL.insert", new_callable=Mock) as mock:
        yield mock


@pytest.fixture(scope='session')
def mock_reply_text():
    with patch("telegram.Message.reply_text", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(scope='session')
def mock_set_reminder():
    with patch("src.PersistentBot.PersistentBot.event_set_reminder", new_callable=AsyncMock) as mock:
        yield True


@pytest.fixture(scope='session')
def mock_run_once():
    with patch("telegram.ext._jobqueue.JobQueue.run_once", new_callable=Mock) as mock:
        yield mock
