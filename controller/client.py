'''
Client module that controls database, telegram client, and face recognition model
'''

import copy
import datetime
import threading
import logging
from pickle import PicklingError, UnpicklingError
from bson.errors import BSONError

from PIL import Image
import numpy as np

from model.recognition_model import FaceRecognition
from utils import file_to_image_array, pack_model, unpack_model, extract_encodings
from utils import add_label_to_image, image_to_file, predict_caption
from utils import predict_reference_note

LOGGER = logging.getLogger(__name__)


class ClientError(Exception):
    ''' Base client error '''


class ImageFileError(ClientError):
    ''' Image file related error '''


class PackModelError(ClientError):
    ''' Pack model error '''


class UnpackModelError(ClientError):
    ''' Unpack model error '''


class NoModelError(ClientError):
    ''' No model error '''


class NoBinDataError(ClientError):
    ''' No bin-data attribute error '''


class CreateCaptionError(ClientError):
    ''' Error when creating caption '''


class ExtractFaceError(ClientError):
    ''' Error when extracting face data '''


class LabelNoteFoundError(ClientError):
    ''' Error when label does not exist '''


class Client:
    ''' Client object '''

    def __init__(self, database=None, telegram=None):
        self.database = database
        self.telegram = telegram
        if telegram:
            self.telegram.set_train_handler(self.train_image)
            self.telegram.set_predict_handler(self.predict_image)
            self.telegram.set_mention_handler(self.mention_label)
            self.telegram.set_retrain_handler(self.retrain)
        self.model = None
        self.model_lock = threading.Lock()
        LOGGER.info("Client is initialized")

    def start(self):
        ''' To start client before interactions '''
        LOGGER.info("Client starting")
        self.telegram.start()

    def idle(self):
        ''' To make client idle '''
        LOGGER.info("Client idle")
        self.telegram.idle()

    def stop(self):
        ''' To stop client '''
        LOGGER.info("Client stopping")
        self.telegram.stop()

    def retrain(self):
        ''' Retrain and re-extract after DNN update '''
        faces = self.database.get_faces()
        if not faces:
            return
        for face in faces:
            image_f = unpack_model(face['image'])
            image = file_to_image_array(image_f)
            face['face'] = FaceRecognition.get_face_encoding(image).tolist()
            self.database.update_face(face)
        # Retrieve training set
        faces = self.database.get_faces()
        x_train = [np.array(x['face']) for x in faces]
        y_train = [x['label'] for x in faces]
        model = FaceRecognition.train(x_train, y_train)
        self.update_model(model, len(faces))
        self.database.update_command_counter('retrain')

    def mention_label(self, label, note=None):
        ''' Update label with note '''
        # Check if label exist
        result = self.database.find_label(label)
        if not result:
            raise LabelNoteFoundError
        if note:
            self.database.add_note(label, note)
        self.database.update_command_counter('label')

    def get_train(self, image_f, label):
        ''' Retrieve traning set with new image '''
        # Read image from file
        try:
            image = file_to_image_array(image_f)
        except IOError:
            LOGGER.error("cannot read image for train")
            raise ImageFileError
        # Extract target face feature
        face_encoding = FaceRecognition.get_face_encoding(image)
        # Retrieve training set
        faces = self.database.get_faces()
        x_train = [np.array(x['face']) for x in faces]
        y_train = [x['label'] for x in faces]
        # Append new face to training set
        x_train.append(face_encoding)
        y_train.append(label)
        return {'x_train': x_train, 'y_train': y_train,
                'face': face_encoding, 'label': label}

    def update_model(self, model, faces_count):
        ''' Update model in memory and database '''
        # Pack model
        try:
            model_bin = pack_model(model)
        except (PicklingError, BSONError) as exp:
            LOGGER.error("cannot pack model, %s", exp)
            raise PackModelError
        # Update model in memory
        self.model_lock.acquire()
        self.model = model
        self.model_lock.release()
        # Update model in database
        self.database.add_model({'bin-data': model_bin,
                                 'face_count': faces_count,
                                 'createdAt': datetime.datetime.utcnow()})
        self.database.delete_outdated_models()
        LOGGER.debug("update and deleted old model")

    def train_image(self, image_f, label):
        '''
        Train the model with the given image
        :param image_f: file descriptor of the image
        :param label: string label for the image
        :return dict
        '''
        LOGGER.debug("train_image called")
        training_set = self.get_train(image_f, label)
        # Train the model
        model = FaceRecognition.train(training_set['x_train'],
                                      training_set['y_train'])
        # Update model
        self.update_model(model, len(training_set['x_train']))
        # Pack image
        try:
            image_bin = pack_model(image_f)
        except (PicklingError, BSONError) as exp:
            LOGGER.error("cannot pack image, %s", exp)
            raise PackModelError
        self.database.add_faces([{'face': training_set['face'].tolist(
        ), 'label': training_set['label'], 'image': image_bin}])
        self.database.update_command_counter('train')

    def get_model(self):
        ''' Get latest model '''
        # Check existing model
        self.model_lock.acquire()
        if self.model:
            model_copy = copy.deepcopy(self.model)
            self.model_lock.release()
            return model_copy
        self.model_lock.release()
        # Retrieve model from database
        LOGGER.debug("Fetching model")
        model_coll = self.database.get_model()
        # Check model properties
        if model_coll is None:
            LOGGER.debug("No model found")
            raise NoModelError
        if 'bin-data' not in model_coll.keys():
            LOGGER.error("No bin-data in model")
            raise NoBinDataError
        model_bin = model_coll['bin-data']
        # Unpack model
        self.model_lock.acquire()
        try:
            self.model = unpack_model(model_bin)
        except UnpicklingError:
            LOGGER.error("Cannot unpack model")
            self.model_lock.release()
            raise UnpackModelError
        # Release model lock
        model_copy = copy.deepcopy(self.model)
        self.model_lock.release()
        return model_copy

    @staticmethod
    def handle_predict_result(image, x_locations, predictions):
        ''' Handle prediction result '''
        # Add label to image
        LOGGER.debug("Adding label to predicted image")
        try:
            image = add_label_to_image(image, x_locations, predictions)
        except (IOError, TypeError, ValueError) as exp:
            LOGGER.error("Cannot add label to image, %s", exp)
            raise ImageFileError
        # Convert image to file
        LOGGER.debug("Converting labelled image to file")
        try:
            file = image_to_file(image)
        except IOError:
            LOGGER.error("Cannot convert image to file")
            raise ImageFileError
        # Create prediction caption
        LOGGER.debug("Creating prediction caption")
        try:
            caption = predict_caption(predictions)
        except (TypeError, ValueError):
            LOGGER.error("Cannot create caption")
            raise CreateCaptionError
        return {'file': file, 'caption': caption}

    @staticmethod
    def extract_encoding_from_image(image_array):
        ''' Extract face encodings and locations '''
        LOGGER.debug("Extracting encodings")
        try:
            faces_encodings, x_locations = extract_encodings(image_array)
            if (not faces_encodings or not x_locations):
                raise ExtractFaceError("No faces found")
            return {'encodings': faces_encodings, 'locations': x_locations}
        except (TypeError, ValueError) as exp:
            raise ExtractFaceError(exp)

    def predict_image(self, image_f):
        '''
        Predict label of the image with model
        :param image_f: file descriptor of the image
        :return dict: image with label, and caption
        '''
        LOGGER.debug("predict_image called")
        # Convert / Open
        try:
            image = Image.open(image_f)
            image_array = file_to_image_array(image_f)
        except IOError:
            LOGGER.error("cannot read image file")
            raise ImageFileError
        # Extract encoding
        result = Client.extract_encoding_from_image(image_array)
        faces_encodings, x_locations = result['encodings'], result['locations']
        # Get model
        model_copy = self.get_model()
        # Predict
        LOGGER.debug("Starting prediction")
        predictions = FaceRecognition.predict(faces_encodings,
                                              model_copy)
        # Process predicted result
        result = Client.handle_predict_result(image, x_locations, predictions)
        references, notes = predict_reference_note(self.database, predictions)
        self.database.update_command_counter('predict')
        return {'image': result['file'], 'caption': result['caption'],
                'notes': notes, 'references': references}

    @staticmethod
    def add_images_mock(images, labels, weights=None):
        '''
        Add image and train model, development mock
        :param images: images to train with
        :param labels: labels to train with
        :param weights: weights of different models
        :return model: the trained model
        '''
        LOGGER.debug("add_images_mock called")
        return FaceRecognition.train(images, labels, weights)

    @staticmethod
    def predict_image_mock(image, model):
        '''
        Predict label of image with model
        :param image: image to predict
        :param model: model for prediction
        :return list: predicted labels, probability, distance
        '''
        LOGGER.debug("predict_image_mock called")
        return FaceRecognition.predict(image, model)
