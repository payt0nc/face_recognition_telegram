''' Common functions for test cases '''
import unittest
import asyncio

from test.telegram_user import TelegramUser
from telegram.ext import Dispatcher

from controller.client import Client
from model.telegram_client import TelegramClient
from model.user_model import TelegramUserClient
from model.database import Database


def async_test(func):
    ''' Async test '''
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(func)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
    wrapper.__name__ = func.__name__
    return wrapper


class BaseTestCase(unittest.TestCase):
    ''' Test case '''

    @classmethod
    @async_test
    async def setUpClass(cls):
        telegram_client = TelegramClient()
        # A hack to ensure dispatcher exist
        Dispatcher._set_singleton(               # pylint: disable=W0212
            telegram_client.updater.dispatcher)  # pylint: disable=W0212
        database_handle = Database(testing=True)
        database_handle.drop_testing_database()
        cls.client = Client(database_handle, telegram_client)
        cls.client.start()
        cls.user = TelegramUser()
        await cls.user.start()
        await cls.user.setup_chat()

    @classmethod
    @async_test
    async def tearDownClass(cls):
        cls.client.stop()
        await cls.user.stop()


class UserModelTestCase(BaseTestCase):
    ''' Test Case for user model '''

    @classmethod
    @async_test
    async def setUpClass(cls):
        database_handle = Database(testing=True)
        database_handle.drop_testing_database()
        telegram_client = TelegramUserClient(database_handle)
        # A hack to ensure dispatcher exist
        Dispatcher._set_singleton(               # pylint: disable=W0212
            telegram_client.updater.dispatcher)  # pylint: disable=W0212
        cls.client = Client(database_handle, telegram_client)
        cls.client.start()
        cls.user = TelegramUser()
        await cls.user.start()
        await cls.user.setup_chat()
        cls.database = database_handle
