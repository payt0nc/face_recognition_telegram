''' Telegram client module '''

import io
import os
import sys
from collections import defaultdict
from functools import wraps
import logging

from telegram import ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)

from controller.client import ClientError, ExtractFaceError, NoModelError
from controller.client import LabelNoteFoundError
from model.database import DatabaseError
from model.recognition_model import FaceRecognitionError, NoFaceError, TooManyFacesError


LOGGER = logging.getLogger(__name__)
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

try:
    DIR_NAME = os.path.dirname(__file__) + '/../active_token.txt'
    TOKEN = open(DIR_NAME).read().replace("\n", "")
    LOGGER.debug("Loaded Telegram Token")
except IOError:
    LOGGER.info("Telegram Token file cannot be opened, quitting")
    exit(1)


def send_typing_action(func):
    ''' Sends typing action while processing func command. '''
    @wraps(func)
    @run_async
    def command_func(_, update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id,
                                     action=ChatAction.TYPING)
        return func(_, update, context, *args, **kwargs)
    return command_func


def send_upload_photo_action(func):
    ''' Sends upload photo action while processing func command. '''
    @wraps(func)
    @run_async
    def command_func(_, update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id,
                                     action=ChatAction.UPLOAD_PHOTO)
        return func(_, update, context, *args, **kwargs)
    return command_func


class TelegramClient:
    ''' Telegram client '''

    def __init__(self, num_workers=16):
        try:
            self.updater = Updater(
                TOKEN, workers=num_workers, use_context=True,
                request_kwargs={'read_timeout': 10, 'connect_timeout': 10})
        except ValueError:
            LOGGER.info("Cannot connect to telegram, quitting")
            exit(1)
        LOGGER.info("Connected to telegram")
        # Setup handlers
        dispatcher = self.updater.dispatcher
        dispatcher.add_handler(
            CommandHandler('start', self.start_command_handler))
        dispatcher.add_handler(
            CommandHandler('help', self.start_command_handler))
        dispatcher.add_handler(
            CommandHandler('train', self.train_command_handler))
        dispatcher.add_handler(
            CommandHandler('done', self.done_command_handler))
        dispatcher.add_handler(
            MessageHandler(Filters.photo, self.photo_handler))
        dispatcher.add_handler(
            CommandHandler('note', self.note_command_handler))
        dispatcher.add_handler(
            CommandHandler('retrain', self.retrain_command_handler))
        dispatcher.add_error_handler(self.error_handler)
        # Initialize properties
        self.train_callback = None
        self.predict_callback = None
        self.mention_callback = None
        self.retrain_callback = None
        self.username = None
        self.state = defaultdict(str)
        self.label = defaultdict(str)

    def set_train_handler(self, handler):
        ''' Set training handler '''
        self.train_callback = handler

    def set_predict_handler(self, handler):
        ''' Set predict handler '''
        self.predict_callback = handler

    def set_mention_handler(self, handler):
        ''' Set mention handler '''
        self.mention_callback = handler

    def set_retrain_handler(self, handler):
        ''' Set retrain handler '''
        self.retrain_callback = handler

    def start(self):
        ''' Start telegram bot '''
        try:
            bot_user = self.updater.bot.get_me()
            self.username = bot_user.username
            LOGGER.info("Telegram token is valid")
        except TelegramError:
            LOGGER.info("Telegram token is INVALID, quitting")
            exit(1)
        if not self.train_callback or not self.predict_callback or \
           not self.mention_callback:
            LOGGER.info("Telegram handlers not set!")
            exit(1)
        dispatcher = self.updater.dispatcher
        dispatcher.add_handler(
            MessageHandler(
                Filters.regex(r'\@{}'.format(self.username)),
                self.mention_handler))
        self.updater.start_polling()
        LOGGER.info("Polling started")

    def idle(self):
        ''' Set bot to idle '''
        LOGGER.info("Setting bot to idle")
        self.updater.idle()

    def stop(self):
        ''' Stop telegram bot '''
        LOGGER.info("Stopping bot")
        self.updater.stop()

    @send_typing_action
    @run_async
    def retrain_command_handler(self, update, context):
        ''' Handle /retrain command '''
        self.retrain_callback()
        update.message.reply_text('Model extracted and retrained')

    @send_typing_action
    @run_async
    def note_command_handler(self, update, _context):
        ''' Handle /note command '''
        from_user = str(update.message.from_user)
        args = TelegramClient.extract_args('note', update.message.text)
        if args:
            try:
                self.mention_callback(args)
            except LabelNoteFoundError:
                update.message.reply_text(
                    'Label does not exist.\n' +
                    'Use this to train a label first: /train label1')
                return
            self.state[from_user] = 'Note'
            self.label[from_user] = args
            update.message.reply_text(
                'Note is turned on with tag **{}**, please send the description\n'
                .format(self.label[from_user]) +
                'it must contain @{}'.format(self.username))
        else:
            update.message.reply_text('Example: /note label1')

    @send_typing_action
    @run_async
    def mention_handler(self, update, _context):
        ''' Handle mention '''
        from_user = str(update.message.from_user)
        if self.state[from_user] == 'Note':
            label = self.label[from_user]
            note = update.message.text
            note = note.replace('@{}'.format(self.username), '')
            self.clean_state(from_user)
            try:
                self.mention_callback(label, note=note)
            except LabelNoteFoundError:
                update.message.reply_text(
                    'Label does not exist.\n' +
                    'Use this to train a label first: /train label1')
            except DatabaseError:
                LOGGER.exception("mention handler error")
                update.message.reply_text(
                    'DatabaseError')
            update.message.reply_text('Note updated for **{}**'.format(label))
        else:
            update.message.reply_text(
                'Not in note state.\n' +
                'Use this first: /note label1')

    @send_typing_action
    @run_async
    def start_command_handler(self, update, _):
        ''' Handle /start command '''
        from_user = str(update.message.from_user)
        self.clean_state(from_user)
        update.message.reply_text(
            'To predict a face, send the photo\n\n' +
            'To add a face, /train ExampleName\n' +
            'and then send me all the photos\n\n' +
            'To stop adding face, /done')

    def clean_state(self, from_user):
        ''' Clear user state '''
        if self.state[from_user]:
            del self.state[from_user]
        if self.label[from_user]:
            del self.label[from_user]

    @send_typing_action
    @run_async
    def error_handler(self, update, context):
        ''' Handle errors '''
        try:
            chat_id = str(update.message.chat_id)
            from_user = str(update.message.from_user)
            raise context.error
        except Unauthorized:
            self.clean_state(from_user)
            LOGGER.info("Unauthorized error with from_user %s", from_user)
        except BadRequest:
            self.clean_state(from_user)
            LOGGER.info("Bad request with from_user %s", from_user)
            try:
                context.bot.send_message(
                    chat_id, "Please resend command, your request was malformed")
            except TelegramError:
                LOGGER.info("Failed to resend message with chat_id %s",
                            chat_id)
        except TimedOut:
            LOGGER.info("Timeout with chat_id %s", chat_id)
        except NetworkError:
            LOGGER.info("Network error with chat_id %s", chat_id)
        except ChatMigrated as exp:
            self.clean_state(chat_id)
            # the chat_id of a group has changed, use e.new_chat_id instead
            LOGGER.info("chat_id changed: %s to %s", chat_id, exp.new_chat_id)
            try:
                context.bot.send_message(
                    exp.new_chat_id,
                    "Please resend command, your chat_id has changed")
            except TelegramError:
                LOGGER.info("Failed to send message with new chat_id %s",
                            exp.new_chat_id)
        except TelegramError as telegram_error:
            # handle all other telegram related errors
            LOGGER.info("TelegramError: %s", telegram_error)

    @staticmethod
    def extract_args(command, text):
        ''' Extract command argument '''
        parts = text.split('/{} '.format(command))
        if len(parts) < 2:
            return None
        if not parts[1]:
            return None
        return parts[1]

    @send_typing_action
    @run_async
    def train_command_handler(self, update, _):
        ''' Handle /train command '''
        from_user = str(update.message.from_user)
        args = TelegramClient.extract_args('train', update.message.text)
        if args:
            self.state[from_user] = 'Train'
            self.label[from_user] = args
            update.message.reply_text(
                'Train is turned on with tag **{}**, please send the photo'
                .format(self.label[from_user]))
        else:
            update.message.reply_text('Example: /train test1')

    @send_typing_action
    @run_async
    def done_command_handler(self, update, _):
        ''' Handle /done command '''
        from_user = str(update.message.from_user)
        self.state[from_user] = 'Done'
        label = self.label[from_user]
        if self.label[from_user]:
            del self.label[from_user]
            update.message.reply_text('Done with tag **{}**'.format(label))
        else:
            update.message.reply_text('No current tag')

    @send_typing_action
    @run_async
    def photo_handler(self, update, context):
        ''' Handle photo receiving '''
        from_user = str(update.message.from_user)
        if self.state[from_user] == 'Train':
            self.train_handler(update, context)
        else:
            self.predict_handler(update, context)

    @send_typing_action
    @run_async
    def train_handler(self, update, context):
        ''' Handle train request '''
        from_user = str(update.message.from_user)
        if self.label[from_user] is None:
            update.message.reply_text('No label found, use /train')
            return
        if not self.label[from_user]:
            update.message.reply_text('Label must be at least length of one')
            return
        # Download latest photo
        try:
            photo = update.message.photo[-1]
            file_id = photo.file_id
            file = context.bot.get_file(file_id)
            fopen = io.BytesIO()
            file.download(out=fopen)
        except (IndexError, AttributeError, IOError):
            LOGGER.exception("train handler error")
            update.message.reply_text('Cannot download image')
            return
        # Check file size
        try:
            size = sys.getsizeof(fopen)
            if size > MAX_FILE_SIZE:
                update.message.reply_text('Image file size too large')
                return
        except TypeError:
            LOGGER.exception("predict handler file size check error")
            update.message.reply_text("Cannot check image file size")
            return
        # Train and check result
        try:
            self.train_callback(fopen, self.label[from_user])
            update.message.reply_text(
                'Model trained for **{}**, use /done or send more'.format(
                    self.label[from_user]))
            return
        except NoFaceError:
            update.message.reply_text("No face found")
        except TooManyFacesError:
            update.message.reply_text("More than one face found")
        except FaceRecognitionError:
            LOGGER.exception("train handler error")
            update.message.reply_text("Model error")
        except DatabaseError:
            LOGGER.exception("train handler error")
            update.message.reply_text("Database error")
        except ClientError:
            LOGGER.exception("train handler error")
            update.message.reply_text("ClientError error")

    @send_upload_photo_action
    @run_async
    def predict_handler(self, update, context):
        ''' Handle prediction request '''
        # Download latest photo
        try:
            photo = update.message.photo[-1]
            file_id = photo.file_id
            file = context.bot.get_file(file_id)
            fopen = io.BytesIO()
            file.download(out=fopen)
        except (IndexError, AttributeError, IOError):
            LOGGER.exception("predict handler error")
            update.message.reply_text('Cannot download image')
            return
        # Check file size
        try:
            size = sys.getsizeof(fopen)
            if size > MAX_FILE_SIZE:
                update.message.reply_text('Image file size too large')
                return
        except TypeError:
            LOGGER.exception("predict handler file size check error")
            update.message.reply_text("Cannot check image file size")
            return
        # Predict
        try:
            result = self.predict_callback(fopen)
            context.bot.send_photo(update.message.chat_id, result['image'],
                                   caption=result['caption'])
            note_reply = ''
            for note in result['notes']:
                note_reply += '{}: {}\n'.format(note['label'], note['note'])
            update.message.reply_text(note_reply)
            for ref in result['references']:
                cap = 'references: {}'.format(ref['label'])
                context.bot.send_photo(update.message.chat_id, ref['image'],
                                       caption=cap)
        except ExtractFaceError:
            update.message.reply_text("No face found")
        except NoModelError:
            update.message.reply_text("No model trained for prediction")
        except FaceRecognitionError:
            LOGGER.exception("predict handler error")
            update.message.reply_text("Model error")
        except DatabaseError:
            LOGGER.exception("predict handler error")
            update.message.reply_text("Database error")
        except ClientError:
            LOGGER.exception("predict handler error")
            update.message.reply_text("ClientError error")
