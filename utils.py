# -*- coding: UTF-8 -*-
''' Utility functions supporting image & model operation '''

import math
import io
import pickle

import face_recognition
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from bson.binary import Binary

ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg']
FONT_DIR_NAME = "/usr/share/fonts/truetype/arphic/ukai.ttc"
BACKGROUND_COLOR = (255, 0, 0, 200)
TEXT_COLOR = (255, 255, 255, 255)


def legal_file(name):
    ''' Check file extension for image'''
    return name[-3:] in ALLOWED_EXTENSIONS


def pack_model(model):
    ''' Pack model as bytes '''
    thebytes = pickle.dumps(model)
    return Binary(thebytes)


def unpack_model(model_bin):
    ''' Unpack model from bytes '''
    return pickle.loads(model_bin)


def file_to_image_array(file):
    ''' Retrieve image array by file name '''
    image = Image.open(file)
    image = image.convert('RGB')
    return np.array(image)


def extract_encodings(image_array):
    ''' Extract face encoding from image array '''
    x_locations = face_recognition.face_locations(image_array)
    # If no faces are found in the image, return an empty result.
    if not x_locations:
        return None, None
    # Find encodings for faces in the test iamge
    faces_encodings = face_recognition.face_encodings(
        image_array, known_face_locations=x_locations)
    return faces_encodings, x_locations


def image_to_file(image, extension='png'):
    ''' Convert image object to file descriptor '''
    fopen = io.BytesIO()
    image.save(fopen, format=extension)
    fopen.seek(0)  # Beginning of file
    return fopen


def predict_caption(results):
    ''' Craft prediction caption '''
    caption = ''
    for result in results:
        prob = result['prob']
        caption += '{}: {}%\n'.format(result['label'],
                                      round(prob * 100, 2))
    return caption


def predict_reference_note(database, predictions):
    ''' Craft prediction reference '''
    notes = []
    references = []
    labels = []
    for pred in predictions:
        if pred['label'] in labels:
            continue
        labels.append(pred['label'])
        note = database.get_note(pred['label'])
        if note is None:
            notes.append({'note': 'No note', 'label': pred['label']})
        else:
            notes.append({'note': note['note'], 'label': pred['label']})
        ref_face = database.get_face(query={'label': pred['label']})
        if ref_face is not None:
            ref_image = unpack_model(ref_face['image'])
            ref_image.seek(0)
            references.append({'label': pred['label'], 'image': ref_image})
    return references, notes


def create_overlay_image(draw, label, loc, prob):
    ''' Create overlay image of original image '''
    # loc: (top, right, bottom, left)
    top = loc[0]
    right = loc[1]
    bottom = loc[2]
    left = loc[3]

    # Draw a box around the face using the Pillow module
    draw.rectangle(((left, top), (right, bottom)), outline=BACKGROUND_COLOR)

    size = math.sqrt(bottom - top) * 1.5
    size = int(size)
    font = ImageFont.truetype(FONT_DIR_NAME, size)

    label = label + ' {}%'.format(round(prob * 100.0, 2))

    # Draw a label with a name below the face
    text_width, text_height = draw.textsize(label, font=font)
    width = right - left
    pad = (width - text_width) / 2
    if text_width > width:
        left = left + pad
        right = right - pad
    draw.rectangle((
        (left, bottom + text_height), (right, bottom)
    ), fill=BACKGROUND_COLOR, outline=BACKGROUND_COLOR)

    draw.text((left, bottom),
              label, fill=TEXT_COLOR, font=font)


def add_label_to_image(image, x_locations, results):
    '''
    Add label to overlay image
    :param image: image to be added
    :param results: list of results in [label, loc, prob]
    '''
    image = image.convert("RGBA")
    old_image = image

    image = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # loc: (top, right, bottom, left)
    for loc, result in zip(x_locations, results):
        create_overlay_image(draw, result['label'], loc, result['prob'])

    # Remove the drawing library from memory as per the Pillow docs
    del draw

    image = Image.alpha_composite(old_image, image)
    # Display the resulting image
    # image.show()
    return image
