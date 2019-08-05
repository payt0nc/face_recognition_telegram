# -*- coding: utf-8 -*-
''' Main program to run client '''
import logging
from controller.client import Client
from model.user_model import TelegramUserClient
from model.database import Database

# Initialize loggers
logging.basicConfig(level=logging.INFO)
logging.getLogger('telegram').setLevel(logging.INFO)
logging.getLogger('JobQueue').setLevel(logging.INFO)
# logging.getLogger('model.user_model').setLevel(logging.DEBUG)


def main():
    ''' Main function '''
    database_handle = Database()
    telegram_client = TelegramUserClient(database_handle)
    client = Client(database_handle, telegram_client)
    client.start()
    client.idle()


if __name__ == '__main__':
    main()
