import os 
import cv2  
import importlib.util
import pathlib
import site
import numpy as np
import shutil

# ──────────────────────────────────────────────────────────────────────────────
# [SECCION: BIOMETRIA]
# Modelo LBPH + funciones de carpeta facial.
# La clave de identificacion es face_uid = "sesion_<ID_sesion>"
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
FACES_DIR = os.path.join(BASE_DIR, 'locker_faces')
IMG_W, IMG_H = 112, 92

os.makedirs(FACES_DIR, exist_ok=True)

face_model  = cv2.face.LBPHFaceRecognizer_create()
face_labels = {}   # {int_label: face_uid}


def _find_cascade():
    """Localiza haarcascade compatible con cualquier instalacion de OpenCV."""
    fn = "./biometria/haarcascade/haarcascade_frontalface_default.xml"
    try:
        p = cv2.data.haarcascades + fn
        if os.path.exists(p):
            return p
    except AttributeError:
        pass
    try:
        spec = importlib.util.find_spec("cv2")
        if spec and spec.submodule_search_locations:
            for loc in spec.submodule_search_locations:
                for c in pathlib.Path(loc).rglob(fn):
                    return str(c)
    except Exception:
        pass
    try:
        for sp in site.getsitepackages():
            p = os.path.join(sp, "cv2", "data", fn)
            if os.path.exists(p):
                return p
    except Exception:
        pass
    return fn


CASCADE = _find_cascade()


def train_model():
    """
    Entrena el reconocedor LBPH con todas las imagenes en FACES_DIR.
    Cada subcarpeta es un face_uid = 'sesion_<ID>'.
    """
    global face_labels
    images, labels, names, idx = [], [], {}, 0
    for uid in os.listdir(FACES_DIR):
        sub = os.path.join(FACES_DIR, uid)
        if not os.path.isdir(sub):
            continue
        names[idx] = uid
        for fn in os.listdir(sub):
            img = cv2.imread(os.path.join(sub, fn), 0)
            if img is not None:
                images.append(cv2.resize(img, (IMG_W, IMG_H)))
                labels.append(idx)
        idx += 1
    if len(images) > 1:
        face_model.train(np.array(images), np.array(labels))
    face_labels = names
    return names


def face_dir_for(face_uid):
    return os.path.join(FACES_DIR, face_uid)


def delete_face_data(face_uid):
    d = face_dir_for(face_uid)
    if os.path.exists(d):
        shutil.rmtree(d)

