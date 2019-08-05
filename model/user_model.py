''' User permission module '''

import os
import logging
from functools import wraps

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler

from model.telegram_client import TelegramClient
from model.database import DatabaseError

from model.config import PUBLIC_USER

LOGGER = logging.getLogger(__name__)

try:
    DIR_NAME = os.path.dirname(__file__) + '/../active_root_token.txt'
    ROOT_ADMINS = open(DIR_NAME).readlines()
    ROOT_ADMINS = [root_adm.replace("\n", "") for root_adm in ROOT_ADMINS]
    ROOT_ADMINS = [root_adm for root_adm in ROOT_ADMINS if root_adm]
    ROOT_ADMINS = [root_adm.lower() for root_adm in ROOT_ADMINS]
    LOGGER.debug("Loaded Root Admin Token")
except IOError:
    LOGGER.info("Root Admin Token file cannot be opened, quitting")
    exit(1)


class UserPermissionError(Exception):
    ''' User Permission error '''


def get_user_permission(database, username):
    ''' Get user permission '''
    if username is None:
        if PUBLIC_USER:
            return 'user'
        return None
    username = username.lower()
    if '@' not in username:
        username = '@' + username
    found_user = database.find_user(username)
    if found_user is None:
        if PUBLIC_USER:
            return 'user'
        return None
    return found_user['type']


def handle_permission(src_type, exp_type, update):
    ''' Handle permission '''
    if src_type not in exp_type:
        # Allow user access for public if enabled
        if PUBLIC_USER and src_type is None and 'user' in exp_type:
            return True
        # Silent for non registered user
        if src_type is None:
            return False
        update.message.reply_text('Permission denied.')
        return False
    return True


def permission_level(level):
    ''' Restricted to run for privilege level '''
    if level == 'root_admin':
        perm = ['root_admin']
    elif level == 'admin':
        perm = ['admin', 'root_admin']
    elif level == 'user':
        perm = ['user', 'admin', 'root_admin']

    def outer_wrap(func):
        ''' Function wrapper '''
        @wraps(func)
        def wrap(self, update, context, *args, **kwargs):
            ''' Checking wrapper '''
            try:
                username = update.effective_user.username
            except AttributeError:
                LOGGER.debug("Ignoring request with channel_post")
                return None
            src_type = get_user_permission(self.database, username)
            passing = handle_permission(src_type, perm, update)
            if passing:
                return func(self, update, context, *args, **kwargs)
            return None
        return wrap
    return outer_wrap


class TelegramUserClient(TelegramClient):
    ''' Telegram Client with User Permission '''

    def __init__(self, database, num_workers=None):
        # TelegramClient will use all new handlers with permission check
        if num_workers:
            TelegramClient.__init__(self, num_workers)
        else:
            TelegramClient.__init__(self)
        self.database = database
        self.import_root_user()
        dispatcher = self.updater.dispatcher
        dispatcher.add_handler(
            CallbackQueryHandler(self.callback_query_handler))
        dispatcher.add_handler(
            CommandHandler('admin', self.list_admin))
        dispatcher.add_handler(
            CommandHandler('user', self.list_user))
        dispatcher.add_handler(
            CommandHandler('addadmin', self.add_admin))
        dispatcher.add_handler(
            CommandHandler('adduser', self.add_user))

    def import_root_user(self):
        ''' Import root user '''
        for root_adm in ROOT_ADMINS:
            self.database.add_user(root_adm, 'root_admin')

    def get_list_markup(self, user_type):
        ''' Get list of user/admin markup '''
        users = self.database.list_user(user_type)
        button_list = []
        for usr in users:
            cbd = '/{} {}'.format(usr['type'], usr['username'])
            button_list.append(
                [InlineKeyboardButton(usr['username'], callback_data=cbd)])
        reply_markup = InlineKeyboardMarkup(button_list)
        return reply_markup

    @permission_level('root_admin')
    def list_admin(self, update, context):
        ''' List all admins '''
        reply_markup = self.get_list_markup('admin')
        context.bot.send_message(
            update.message.chat_id,
            text="List of admins:",
            reply_markup=reply_markup)

    @permission_level('root_admin')
    def add_admin(self, update, _):
        ''' Add new admin '''
        arg = self.extract_args('addadmin', update.message.text)
        if arg:
            arg = arg.lower()  # Force lowercase
        if arg:
            if '@' not in arg:
                arg = '@' + arg
            try:
                self.database.add_user(arg, 'admin')
                update.message.reply_text("Added admin {}".format(arg))
            except DatabaseError as exp:
                LOGGER.error("add admin error, %s", exp)
                update.message.reply_text("Database error")
        else:
            update.message.reply_text("Example: /addadmin @test1")

    @permission_level('root_admin')
    def remove_admin(self, update, _, remove_arg):
        ''' Remove admin '''
        try:
            self.database.remove_user(remove_arg, 'admin')
        except DatabaseError as exp:
            LOGGER.error("Remove admin error, %s", exp)
            update.message.reply_text("Database error")

    @permission_level('admin')
    def list_user(self, update, context):
        ''' List all users '''
        reply_markup = self.get_list_markup('user')
        context.bot.send_message(
            update.message.chat_id,
            text="List of users:",
            reply_markup=reply_markup)

    @permission_level('admin')
    def add_user(self, update, _context):
        ''' Add new user '''
        arg = self.extract_args('adduser', update.message.text)
        if arg:
            arg = arg.lower()  # Force lowercase
        if arg:
            if '@' not in arg:
                arg = '@' + arg
            try:
                self.database.add_user(arg, 'user')
                update.message.reply_text("Added user {}".format(arg))
            except DatabaseError as exp:
                LOGGER.error("add user error, %s", exp)
                update.message.reply_text("Database error")
        else:
            update.message.reply_text("Example: /adduser @test1")

    @permission_level('admin')
    def remove_user(self, update, _context, remove_arg):
        ''' Remove user '''
        try:
            self.database.remove_user(remove_arg, 'user')
        except DatabaseError as exp:
            LOGGER.error("Remove user error, %s", exp)
            update.message.reply_text("Database error")

    @permission_level('admin')
    def callback_query_handler(self, update, context):
        ''' Callback query handler '''
        username = update.effective_user.username
        src_type = get_user_permission(self.database, username)
        if src_type == 'admin':
            self.src_type_callback_query_handler(update, context, 'user')
        elif src_type == 'root_admin':
            completed = self.src_type_callback_query_handler(update, context,
                                                             'admin')
            if not completed:
                self.src_type_callback_query_handler(update, context,
                                                     'user')

    def src_type_callback_query_handler(self, update, context, src_type):
        ''' Respond to callback query based on user type operated on '''
        query = update.callback_query
        # Handle click on user
        arg = self.extract_args(src_type, query.data)
        if arg:
            LOGGER.debug("Pressed %s type", src_type)
            cbd = "/r{} {}".format(src_type, arg)
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Remove {}".format(arg),
                                      callback_data=cbd)],
                [InlineKeyboardButton("Cancel",
                                      callback_data='/list{}'.format(src_type))]
            ])
            context.bot.edit_message_reply_markup(query.message.chat_id,
                                                  query.message.message_id,
                                                  reply_markup=reply_markup)
            return True

        # Handle remove user
        remove_arg = self.extract_args('r{}'.format(src_type), query.data)
        if remove_arg:
            LOGGER.debug("Removing %s", src_type)
            if src_type == 'admin':
                self.remove_admin(update, context, remove_arg)
            elif src_type == 'user':
                self.remove_user(update, context, remove_arg)
            # Return to list of user
            reply_markup = self.get_list_markup(src_type)
            context.bot.edit_message_reply_markup(query.message.chat_id,
                                                  query.message.message_id,
                                                  reply_markup=reply_markup)
            return True

        # Handle listing user
        if query.data == '/list{}'.format(src_type):
            LOGGER.debug("Return to list of %ss", src_type)
            reply_markup = self.get_list_markup(src_type)
            context.bot.edit_message_reply_markup(query.message.chat_id,
                                                  query.message.message_id,
                                                  reply_markup=reply_markup)
            return True
        return False

    @permission_level('user')
    def start_command_handler(self, update, _context):
        ''' Start command '''
        username = update.effective_user.username
        src_type = get_user_permission(self.database, username)
        if src_type == 'user':
            update.message.reply_text(
                'Lookup command: /help or /start\n' +
                'Send me any photo with one face for prediction.\n')
        elif src_type == 'admin':
            update.message.reply_text(
                'Lookup command: /help or /start\n' +
                'Train the model: /train <label name>\n' +
                '    then send photos with one face for the label\n' +
                'Stop training the model: /done\n' +
                'Add note to training label: /note <label name>\n' +
                '    then send text containing @{}\n'.format(self.username) +
                'Send me any photo with one face for prediction.\n' +
                'Get list of users: /user\n' +
                '    click on user to remove/cancel\n' +
                'Add a user: /adduser @userid')
        elif src_type == 'root_admin':
            update.message.reply_text(
                'Lookup command: /help or /start\n' +
                'Train the model: /train <label name>\n' +
                '    then send photos with one face for the label\n' +
                'Stop training the model: /done\n' +
                'Send me any photo with one face for prediction.\n' +
                'Add note to training label: /note <label name>\n' +
                '    then send text containing @{}\n'.format(self.username) +
                'Get list of users: /user\n' +
                '    click on name to remove/cancel\n' +
                'Add a user: /adduser @userid\n' +
                'Get list of admins: /admin\n' +
                '    click on name to remove/cancel\n' +
                'Add an admin: /addadmin @adminid\n' +
                'Re-extract and retrain: /retrain\n' +
                '    use after DNN model update')

    @permission_level('user')
    def photo_handler(self, update, context):
        ''' Photo handler '''
        from_user = str(update.message.from_user)
        username = update.effective_user.username
        src_type = get_user_permission(self.database, username)
        # Disable train mode for user
        if src_type == 'user':
            self.state[from_user] = 'Predict'
        TelegramClient.photo_handler(self, update, context)

    @permission_level('user')
    def error_handler(self, update, context):
        ''' Error handler '''
        TelegramClient.error_handler(self, update, context)

    @permission_level('admin')
    def mention_handler(self, update, context):
        ''' Mention handler '''
        TelegramClient.mention_handler(self, update, context)

    @permission_level('admin')
    def train_command_handler(self, update, context):
        ''' Train command '''
        TelegramClient.train_command_handler(self, update, context)

    @permission_level('admin')
    def done_command_handler(self, update, context):
        ''' Done command '''
        TelegramClient.done_command_handler(self, update, context)

    @permission_level('admin')
    def note_command_handler(self, update, context):
        ''' Note command '''
        TelegramClient.note_command_handler(self, update, context)
