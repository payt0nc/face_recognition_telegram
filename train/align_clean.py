import sys
import os
from multiprocessing import Pool

from PIL import Image
import dlib

detector = None
sp = None


def get_all_paths(folder_path):
    all_paths = []
    for class_dir in os.listdir(folder_path):
        if class_dir == '.DS_Store':
            continue
        for file in os.listdir(folder_path + '/' + class_dir):
            if file == '.DS_Store':
                continue
            file_path = os.path.join(
                folder_path + '/' + class_dir + '/' + file)
            all_paths.append(file_path)
            # if len(all_paths) == 2: return all_paths
    return all_paths


def process_image(path):
    global detector, sp
    print(path)
    # Load the image using Dlib
    img = dlib.load_rgb_image(path)

    # Ask the detector to find the bounding boxes of each face. The 1 in the
    # second argument indicates that we should upsample the image 1 time. This
    # will make everything bigger and allow us to detect more faces.
    dets = detector(img, 1)

    num_faces = len(dets)
    if num_faces != 1:
        print("Mismatch face count in '{}'".format(path))
        os.remove(path)
        return

    faces = dlib.full_object_detections()
    faces.append(sp(img, dets[0]))

    # Get a single chip
    image = dlib.get_face_chip(img, faces[0])
    im = Image.fromarray(image)
    im.save(path)


def main():
    if len(sys.argv) != 2:
        print(
            "Call this program like this:\n"
            "   ./face_alignment.py ../examples/faces/\n"
            "You can download a trained facial shape predictor from:\n"
            "    http://dlib.net/files/shape_predictor_5_face_landmarks.dat.bz2\n"
            "The shape predictor must be available at the working directory")
        exit()

    predictor_path = 'shape_predictor_5_face_landmarks.dat'
    face_file_path = sys.argv[1]

    # Load all the models we need: a detector to find the faces, a shape predictor
    # to find face landmarks so we can precisely localize the face
    global detector, sp
    detector = dlib.get_frontal_face_detector()
    sp = dlib.shape_predictor(predictor_path)

    all_paths = get_all_paths(face_file_path)
    pool = Pool(processes=4)
    pool.map(process_image, all_paths)


main()
