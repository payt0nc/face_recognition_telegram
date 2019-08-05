''' Telegram user module '''

import time
import logging

from telethon import TelegramClient
from pymongo import MongoClient

from utils import pack_model, unpack_model

LOGGER = logging.getLogger(__name__)
DELAY = 1.0

DB_URL = 'mongodb://mongo:27017'
DB_NAME = 'testing_setup'

MAX_TIMEOUT_MS = 1000


def read_user():
    ''' Read user credential '''
    file = open('test/user_token.txt', 'r')
    content = file.readlines()
    file.close()
    api_id = content[0].replace("\n", "")
    api_hash = content[1].replace("\n", "")
    bot_id = content[2].replace("\n", "")
    bot_id = bot_id.lower()
    user_id = content[3].replace("\n", "")
    return api_id, api_hash, bot_id, user_id


try:
    SESSION = 'test/user.session'
    API_ID, API_HASH, BOT_ID, USER_ID = read_user()
except IOError:
    print("Cannot open file for telegram user credential")
    exit(1)


class TelegramUser:
    ''' Telegram User '''

    def __init__(self):
        self.client = TelegramClient(SESSION, API_ID, API_HASH)
        self.last_message_id = None
        self.user_id = USER_ID
        self.mongo_client = MongoClient(
            DB_URL, serverSelectionTimeoutMS=MAX_TIMEOUT_MS)
        self.database = self.mongo_client[DB_NAME]
        self.chat = None
        self.bot_id = BOT_ID

    async def start(self):
        ''' Start client '''
        await self.client.start()

    async def setup_chat(self):
        ''' Setup chat target '''
        chat_collection = self.database.chat
        chat = chat_collection.find_one()
        if chat:
            print("Using entity from database")
            self.chat = unpack_model(chat['entity'])
        else:
            print("Fetching entity")
            chat = await self.client.get_entity(BOT_ID)
            chat_bin = pack_model(chat)
            chat_collection.insert_one({'entity': chat_bin})
            self.chat = chat

    async def stop(self):
        ''' Stop client '''
        await self.client.disconnect()

    async def send_message(self, message):
        ''' Send message to bot '''
        sent_message = await self.client.send_message(self.chat, message)
        self.last_message_id = sent_message.id
        return sent_message

    async def get_message(self, retry=5, last=False):
        ''' Get one message until encountering new message '''
        count = 1
        while True:
            time.sleep(DELAY)
            message = await self._get_message()
            if message is not None and message.id != self.last_message_id:
                break
            if count == retry:
                return None
            if last:  # For modified message
                return message
            count += 1
        return message

    async def _get_message(self):
        ''' Get one message '''
        try:
            return (await self.client.get_messages(self.chat, 1))[0]
        except AttributeError:
            return None

    async def get_messages(self, num=2, retry=5, max_num=10):
        ''' Get multiple messages '''
        messages = None
        for _count in range(retry):
            time.sleep(DELAY)
            messages = await self.client.get_messages(self.chat, max_num)
            messages = [
                msg for msg in messages if msg.id > self.last_message_id]
            messages.sort(key=lambda x: x.id)
            if len(messages) != num:
                continue
            break
        return messages

    async def send_photo(self, photo):
        ''' Send photo '''
        sent_photo = await self.client.send_file(self.chat, file=photo)
        self.last_message_id = sent_photo.id
        return sent_photo
