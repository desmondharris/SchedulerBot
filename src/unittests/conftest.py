import pytest
from unittest.mock import AsyncMock, patch, Mock, MagicMock

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
    with patch("telegram.ext.JobQueue.run_once", new_callable=Mock) as mock:
        yield mock


@pytest.fixture(scope='session')
def mock_exec():
    with patch("src.BotSQL.BotSQL.exec", new_callable=Mock) as mock:
        yield True


@pytest.fixture(scope='session')
def mock_fetchone():
    with patch("src.BotSQL.fetchone", new_callable=Mock) as mock:
        yield mock

@pytest.fixture(scope='session')
def mock_fetchall():
    with patch("src.BotSQL.fetchall", new_callable=Mock) as mock:
        yield mock

@pytest.fixture(scope='session')
def mock_insert_zip():
    with patch("src.BotSQL.BotSQL.insert_zip", new_callable=Mock):
        yield True

@patch('src.BotSQL')  # Adjust the path to match where BotSQL is imported
def mock_botsql(mock_bot_sql_class):
    # Create a mock instance of BotSQL
    mock_bot_sql_instance = MagicMock()
    mock_bot_sql_class.return_value = mock_bot_sql_instance
    mock_bot_sql_instance.check_for_user.return_value = [(1, 'user1', None)]  # Example return value


