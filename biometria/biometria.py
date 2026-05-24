import os 
import cv2  
import importlib.util
import pathlib
import site
import numpy as np
import shutil

from db.connection import connectionDB

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


def _decode_face_uid(raw_value):
    if isinstance(raw_value, bytes):
        return raw_value.decode("utf-8", errors="ignore").strip()
    if isinstance(raw_value, str):
        return raw_value.strip()
    return ""


def _get_active_face_uids():
    """
    Devuelve los face_uid activos segun la BD.
    Incluye fallback por convencion: "sesion_<ID_sesion>".
    """
    try:
        with connectionDB() as con:
            rows = con.execute(
                "SELECT ID_sesion, b_vector_biometrico_temp FROM Sesiones "
                "WHERE t_estado='activo'"
            ).fetchall()
        active = set()
        for r in rows:
            face_uid = _decode_face_uid(r["b_vector_biometrico_temp"]) if r else ""
            if face_uid:
                active.add(face_uid)
            active.add(f"sesion_{r['ID_sesion']}")
        return active
    except Exception:
        return None


def _apply_eye_blur_train(img: np.ndarray) -> np.ndarray:
    """
    Difumina la región ocular (25-58% de la altura) durante el entrenamiento.
    Esto hace que el modelo LBPH sea más tolerante a cambios por lentes,
    ya que el algoritmo no puede basar el reconocimiento en los detalles del ojo.
    La misma función se aplica en camera.py durante la predicción.
    """
    h, w = img.shape
    y1 = int(h * 0.25)
    y2 = int(h * 0.58)
    result = img.copy()
    result[y1:y2, :] = cv2.GaussianBlur(img[y1:y2, :], (15, 15), 7)
    return result


def train_model():
    """
    Entrena el reconocedor LBPH con imagenes activas en FACES_DIR.
    Cada subcarpeta es un face_uid = 'sesion_<ID>'.
    Aplica blur en region ocular para mayor tolerancia a lentes.
    """
    global face_labels
    images, labels, names, idx = [], [], {}, 0
    active_uids = _get_active_face_uids()

    for uid in os.listdir(FACES_DIR):
        if active_uids is not None and uid not in active_uids:
            continue
        sub = os.path.join(FACES_DIR, uid)
        if not os.path.isdir(sub):
            continue
        names[idx] = uid
        for fn in os.listdir(sub):
            img = cv2.imread(os.path.join(sub, fn), 0)
            if img is not None:
                img_resized = cv2.resize(img, (IMG_W, IMG_H))
                # Aplicar blur ocular para tolerancia a lentes
                img_blurred = _apply_eye_blur_train(img_resized)
                images.append(img_blurred)
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