import asyncio
import json
import sys
import time

from telegram.request import BaseRequest
from telegram import Message, Chat



class NetworkMocking(BaseRequest):
    def __init__(self):
        # ids for objects created directly by unit tests start at 0
        # for network mocking, they start at the integer max

        self.msg_id = sys.maxsize * 2 + 1

    def msg_factory(self, text: str, chat_id: int):
        temp_chat = Chat(chat_id, "PRIVATE")
        msg = Message(message_id=self.msg_id, text=text, chat=temp_chat, date=time.time())
        self.msg_id += 1
        return msg



    async def do_request(self, url, method, request_data=None, read_timeout=None, write_timeout=None,
                              connect_timeout=None, pool_timeout=None):
        resp = {}
        result = {}
        endpoint = url.rsplit('/', 1)[-1]
        params = request_data.parameters
        if endpoint == "getMe":
            result = {"id": 435345, "first_name": "BotS", "is_bot": True}
            result["username"] = "NoneBot"


        if endpoint == "sendMessage":
            mock_sent_msg = self.msg_factory(params["text"], params["chat_id"])
            result["message_id"] = mock_sent_msg.message_id
            result["text"] = mock_sent_msg.text
            result["chat_id"] = mock_sent_msg.chat.id
            result["date"] = mock_sent_msg.date


        resp["result"] = result
        json_str = json.dumps(resp)
        enc_json = json_str.encode('utf-8')
        return 280, enc_json

    async def initialize(self):
        pass

    async def shutdown(self):
        pass


