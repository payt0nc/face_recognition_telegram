# -*- coding: utf-8 -*-
''' Test model script '''

import os
import logging
import sys
import face_recognition
from sklearn.model_selection import train_test_split

from controller.client import Client
from model.recognition_model import FaceRecognition, TooManyFacesError, NoFaceError

logging.basicConfig(level=logging.INFO)


def get_full_set(path, num=1000):
    ''' Get full set '''
    set_x = []
    set_y = []
    cnt = 0
    for class_dir in os.listdir(path):
        if class_dir == '.DS_Store':
            continue
        class_cnt = 0
        for file in os.listdir(path + '/' + class_dir):
            if file == '.DS_Store':
                continue
            # print(file)
            file_path = os.path.join(path + '/' + class_dir + '/' + file)
            image = face_recognition.load_image_file(file_path)
            try:
                face_encoding = FaceRecognition.get_face_encoding(image)
            except (NoFaceError, TooManyFacesError):
                continue
            set_x.append(face_encoding)
            set_y.append(class_dir)
            class_cnt += 1
        # All class must have at least two samples
        if class_cnt == 1:
            set_x.pop()
            set_y.pop()
        else:
            cnt += 1
            print("Num: {}".format(cnt))
            if cnt == num:
                break
    return set_x, set_y


def main():
    ''' Main function '''

    if len(sys.argv) < 2:
        print("python3 test_model.py folder_name")
        exit(1)

    client_main = Client()

    set_x, set_y = get_full_set(sys.argv[1], 1000)
    train_x, test_x, train_y, test_y = train_test_split(set_x, set_y,
                                                        test_size=0.3,
                                                        stratify=set_y)
    model = client_main.add_images_mock(train_x, train_y)

    results = client_main.predict_image_mock(test_x, model)
    for result, y_val in zip(results, test_y):
        if result['label'] != y_val:
            print("predicted: {} {}, solution: {}".format(
                result['label'], result['dist'], y_val))

    score = [0 if a['label'] != b else 1 for a, b in zip(results, test_y)]
    print("Score {}".format(round(sum(score) * 1.0 / len(score), 2)))


main()
