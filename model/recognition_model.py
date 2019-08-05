''' Face recognition module '''

import math
import logging

from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.ensemble import VotingClassifier
from sklearn.base import BaseEstimator, ClassifierMixin
import face_recognition

import dlib
from model.config import MODEL_NAME, DIST_THRESHOLD
if MODEL_NAME:
    face_recognition.api.face_encoder = dlib.face_recognition_model_v1(
        MODEL_NAME)

LOGGER = logging.getLogger(__name__)


class FaceRecognitionError(Exception):
    ''' Base error '''


class NoFaceError(FaceRecognitionError):
    ''' No face on image error '''


class TooManyFacesError(FaceRecognitionError):
    ''' Too many faces on image error, expecting one '''


class ExtractFaceError(FaceRecognitionError):
    ''' Error when extracting face data '''


class PredictWithoutFitError(FaceRecognitionError):
    ''' Predict is called before Fit '''


class TrainSizeMismatch(FaceRecognitionError):
    ''' Training X and y size mismatch '''


class TrainError(FaceRecognitionError):
    ''' Error when training '''


class PredictionError(FaceRecognitionError):
    ''' Error when predicting '''


class MixedClassifier(BaseEstimator, ClassifierMixin):
    ''' Mixed Classifier '''

    def __init__(self, weights=None):
        if weights is None:
            weights = {'knn': 1, 'svc': 0}
        self.main_clf = None
        self.weights = weights

    def init_model(self, n_neighbors):
        '''
        Initialize model
        :param n_neighbors: n_neighbors for KNN model
        '''
        knn_clf = KNeighborsClassifier(
            algorithm='ball_tree',
            n_neighbors=n_neighbors,
            weights='distance')
        svc_clf = SGDClassifier(
            max_iter=10000,
            tol=1e-5,
            loss='modified_huber')
        self.main_clf = VotingClassifier(
            estimators=[('knn', knn_clf), ('svc', svc_clf)],
            weights=[self.weights['knn'], self.weights['svc']],
            voting='soft')
        LOGGER.debug("Model initialized")

    def fit(self, x_train, y_train):
        '''
        Fit training set and append if needed
        :param x_train: list of image encodings
        :param y_train: list of image labels
        '''
        n_neighbors = int(round(math.sqrt(len(x_train))))
        if len(list(set(y_train))) < 2:
            x_train.append([0 for x in range(128)])
            y_train.append('NULL_LABEL')
        self.init_model(n_neighbors)
        self.main_clf.fit(x_train, y_train)
        return self

    def predict(self, x_train):
        '''
        Predict test set
        :param x_train: list of image encodings
        :return prediction result
        '''
        if self.main_clf is None:
            raise PredictWithoutFitError
        return self.main_clf.predict(x_train)

    def predict_proba(self, x_train):
        '''
        Predict test set
        :param x_train: list of image encodings
        :return prediction probabilities of each labels
        '''
        if self.main_clf is None:
            raise PredictWithoutFitError
        return self.main_clf.predict_proba(x_train)

    # X, y naming is used by ClassifierMixin
    def score(self, X, y, sample_weight=None):
        '''
        Predict test set
        :param x_train: list of image encodings
        :param y_train: list of image labels
        :return score of prediction
        '''
        if self.main_clf is None:
            raise PredictWithoutFitError
        return self.main_clf.score(X, y, sample_weight)

    def predict_dist(self, x_train):
        '''
        Predict test set
        :param x_train: list of image encodings
        :return distance to nearest existing face encoding
        '''
        if self.main_clf is None:
            raise PredictWithoutFitError

        knn_clf = self.main_clf.named_estimators_['knn']
        distances = []
        for x_val in x_train:
            # Compute KNN distance to closest point
            closest_distances = knn_clf.kneighbors([x_val], n_neighbors=1)[0]
            knn_dist = closest_distances[0][0]
            distances.append(knn_dist)
        return distances


class FaceRecognition:
    ''' Face recognition handling '''

    def __init__(self):
        pass

    @staticmethod
    def get_face_encoding(image, num_jitters=1):
        '''
        Extract face encoding from image
        :param image: image as np.array
        :return dict: face encoding and status
        '''
        try:
            face_bounding_boxes = face_recognition.face_locations(image)
        except (TypeError, ValueError) as exp:
            raise ExtractFaceError(exp)

        if len(face_bounding_boxes) != 1:
            # If there are no people (or too many people)
            # in a training image, skip the image.
            if not face_bounding_boxes:
                LOGGER.info('Did not find a face')
                raise NoFaceError
            LOGGER.info('Found more than one face')
            raise TooManyFacesError
        try:
            encodings = face_recognition.face_encodings(
                image,
                known_face_locations=face_bounding_boxes,
                num_jitters=num_jitters)
            LOGGER.debug("Face encoding extracted")
            return encodings[0]
        except (TypeError, ValueError) as exp:
            raise ExtractFaceError(exp)

    @staticmethod
    def train(faces, labels, n_neighbors=None, weights=None):
        '''
        images: list of face encoding
        labels: list of text to label image
        return: { 'model': KNN model, 'faces': faces_encodings, 'labels': labels }
        '''
        if len(faces) != len(labels):
            LOGGER.warning(
                'Faces and labels size mismatch, skipping train')
            LOGGER.warning('len of faces: %d', len(faces))
            LOGGER.warning('len of labels: %d', len(labels))
            raise TrainSizeMismatch

        # Determine how many neighbors to use for weighting
        # in the KNN classifier
        if n_neighbors is None:
            n_neighbors = int(round(math.sqrt(len(faces))))
            LOGGER.debug(
                'Chose n_neighbors automatically: %d',
                n_neighbors)

        # Create and train the KNN classifier
        try:
            model = MixedClassifier(weights=weights)
            LOGGER.debug("Model fit started")
            model.fit(faces, labels)
            return model
        except (TypeError, ValueError, AttributeError) as exp:
            raise TrainError(exp)

    @staticmethod
    def pack_result(label, prob, dist):
        ''' Pack prediction result into dict '''
        return {'label': label, 'prob': prob, 'dist': dist}

    @staticmethod
    def predict(faces_encodings, model, dist_threshold=DIST_THRESHOLD,
                prob_threshold=0.0):
        '''
        images: list of raw image data
        knn_clf: KNN model
        return: list of (predicted label, bounding box)
        '''
        # Use the KNN model to find the best matches for the test face
        # closest_distances = model.kneighbors(faces_encodings, n_neighbors=1)
        # distances = [
        #     closest_distances[0][i][0]
        #     for i in range(len(X_locations))
        # ]
        try:
            # Predict classes and remove classifications that
            # aren't within the threshold
            LOGGER.debug("Model prediction started")
            predictions = model.predict(faces_encodings)
            predictions_prob = model.predict_proba(faces_encodings)
            distances = model.predict_dist(faces_encodings)
            LOGGER.debug("Model prediction result packing")
            result = []
            # Run for each predictions, probs for list of corresponded labels
            for label, probs, dist in zip(
                    predictions, predictions_prob, distances):
                # Probabilities for each class (unique labels)
                prob = max(probs)
                if prob < prob_threshold:
                    result.append(
                        FaceRecognition.pack_result('unknown', 1.0, dist))
                elif dist <= dist_threshold:
                    result.append(
                        FaceRecognition.pack_result(label, prob, dist))
                else:
                    result.append(
                        FaceRecognition.pack_result('unknown', 1.0, dist))
            return result
        except (TypeError, ValueError, AttributeError, PredictWithoutFitError) as exp:
            raise PredictionError(exp)
