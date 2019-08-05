''' Database module for wrap up interactions '''
import logging
from bson.errors import BSONError
from pymongo import MongoClient, DESCENDING, errors
import datetime as dt
from dateutil.tz import gettz
from model.config import DB_URL, DB_NAME, MAX_TIMEOUT_MS

LOGGER = logging.getLogger(__name__)


class DatabaseError(Exception):
    ''' Base database error '''


class Database:
    ''' Database object '''

    def __init__(self, testing=False):
        db_name = DB_NAME
        if testing:
            db_name = 'testing'
        self.mongo_client = MongoClient(
            DB_URL, serverSelectionTimeoutMS=MAX_TIMEOUT_MS)
        self.database = self.mongo_client[db_name]
        try:
            LOGGER.debug("MongoDB info: %s", self.mongo_client.server_info())
            LOGGER.info("Connected to MongoDB")
        except errors.ServerSelectionTimeoutError:
            LOGGER.info("Cannot connect to MongoDB, exiting")
            exit(1)

    def add_note(self, label, note):
        ''' Add note for label '''
        LOGGER.debug("Adding note for %s", label)
        try:
            note_collection = self.database.notes
            note_collection.update_one({'label': label},
                                       {'$set':
                                        {'label': label, 'note': note}
                                        },
                                       upsert=True)
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def get_note(self, label):
        ''' Get note for label '''
        LOGGER.debug("Getting note for %s", label)
        try:
            note_collection = self.database.notes
            return note_collection.find_one({'label': label})
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def find_label(self, label):
        ''' Find label if exist '''
        LOGGER.debug("Finding label %s", label)
        try:
            face_collection = self.database.faces
            result = face_collection.find_one({'label': label}, {'label': 1})
            return result is not None
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def add_faces(self, faces):
        ''' Add faces to database '''
        LOGGER.debug("Adding %d faces to database", len(faces))
        try:
            face_collection = self.database.faces
            face_collection.insert_many(faces)
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def update_face(self, face):
        ''' Update face encoding '''
        LOGGER.debug("Update face in database")
        try:
            face_collection = self.database.faces
            face_collection.update_one({'_id': face['_id']},
                                       {'$set': {'face': face['face']}})
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def add_model(self, model):
        ''' Add model to database '''
        LOGGER.debug("Adding model to database")
        try:
            model_collection = self.database.models
            model_collection.insert_one(model)
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def get_face(self, query=None):
        ''' Get face from database '''
        if query is None:
            query = {}
        LOGGER.debug("Getting face with query: %s", query)
        try:
            face_collection = self.database.faces
            return face_collection.find_one(query)
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def get_faces(self, query=None):
        ''' Get faces from database '''
        if query is None:
            query = {}
        LOGGER.debug("Getting faces with query: %s", query)
        try:
            face_collection = self.database.faces
            return list(face_collection.find(query))
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def get_model(self):
        ''' Get latest model from database '''
        LOGGER.debug("Getting latest model")
        try:
            model_collection = self.database.models
            return model_collection.find_one({},
                                             sort=[('createdAt', DESCENDING)])
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def delete_outdated_models(self):
        ''' Delete ALL old models in database '''
        LOGGER.debug("Finding latest model")
        try:
            model_collection = self.database.models
            latest_model = model_collection.find_one(
                {}, sort=[('createdAt', DESCENDING)])
            if latest_model is None:
                return
            latest_model_id = latest_model['_id']
            LOGGER.debug("Deleting old models")
            model_collection.delete_many({'_id': {'$ne': latest_model_id}})
        except (errors.PyMongoError, ValueError, TypeError, BSONError,
                AttributeError) as exp:
            raise DatabaseError(exp)

    def list_user(self, user_type):
        ''' List users '''
        LOGGER.debug("Listing users")
        try:
            user_collection = self.database.users
            return list(user_collection.find({'type': user_type}))
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def add_user(self, username, user_type):
        ''' Add user '''
        LOGGER.debug("Adding user")
        try:
            user_collection = self.database.users
            # Either insert or do nothing
            user_collection.update_one({'username': username},
                                       {'$setOnInsert': {'type': user_type,
                                                         'username': username}},
                                       upsert=True)
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def remove_user(self, username, user_type):
        ''' Remove user '''
        LOGGER.debug("Removing user")
        try:
            user_collection = self.database.users
            user_collection.delete_one(
                {'username': username, 'type': user_type})
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def find_user(self, username):
        ''' Find user '''
        LOGGER.debug("Finding user")
        try:
            user_collection = self.database.users
            return user_collection.find_one({'username': username})
        except (errors.PyMongoError, ValueError) as exp:
            raise DatabaseError(exp)

    def drop_testing_database(self):
        ''' Drop testing database '''
        LOGGER.debug("Dropping testing database")
        self.mongo_client.drop_database('testing')

    def get_datetime(self):
        hktz = gettz("Asia/Hong_Kong")
        return dt.datetime.now(hktz).strftime('%Y-%m-%d')

    def update_command_counter(self, field_type):
        ''' Update command counter '''
        counter_collection = self.database.counters
        counter_collection.update_one({'date': self.get_datetime()},
                                      {'$inc': {field_type: 1}},
                                      upsert=True)
