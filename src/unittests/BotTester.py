import asyncio
from telethon import TelegramClient
from src.Keys import Key
import time
api_id = Key.TEST_API_KEY
api_hash = Key.TEST_API_HASH
bot_token = Key.TELEGRAM_API_KEY
USER = "dkhschedule_bot"

class Tester:
    def __init__(self):
        self.cli = TelegramClient('botTest', api_id, api_hash)

    async def send_msg(self, msg: str = ""):
        await self.cli.start()
        await self.cli.send_message(USER, msg)

    async def fetch_responses(self, n: int = -1):
        time.sleep(3)
        resp = await self.cli.get_messages(USER)
        resp = [r for r in resp if r.from_id != 1710495555]
        if n == -1:
            n = len(resp) + 1
        return resp[:n]


def create_update():
    pass
    """
    Update Object:
        - most params here have to do with api functionality we don't need for a unit test
            - not sure if a callback function can be called on directly
        message: Message object containing web app data
        
    """