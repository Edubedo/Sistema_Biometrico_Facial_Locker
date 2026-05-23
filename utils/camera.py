import sys
import os
import cv2
import time
import math
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except Exception:
    mp = None
    MP_AVAILABLE = False

from biometria.biometria import CASCADE, face_dir_for, face_model, IMG_H, IMG_W

# ── Singleton global de Picamera2 ─────────────────────────────────────────────
_picam_instance = None
_picam_lock = __import__("threading").Lock()


def _get_picam():
    global _picam_instance
    with _picam_lock:
        if _picam_instance is not None:
            return _picam_instance
        if Picamera2 is None:
            return None
        try:
            cam = Picamera2()
            config = cam.create_video_configuration(main={"size": (640, 480)})
            cam.configure(config)
            cam.start()
            time.sleep(1.5)
            _picam_instance = cam
            return _picam_instance
        except Exception as e:
            print(f"[Camera] No se pudo inicializar Picamera2: {e}")
            return None


def _release_picam():
    global _picam_instance
    with _picam_lock:
        if _picam_instance is not None:
            try:
                _picam_instance.stop()
                _picam_instance.close()
            except Exception:
                pass
            _picam_instance = None


# ── Helpers de validación ─────────────────────────────────────────────────────

def _is_valid_face(x: int, y: int, fw: int, fh: int, w_img: int, h_img: int) -> bool:
    """
    Valida que una detección sea realmente un rostro y no ropa u otro objeto.

    Criterios:
    - Tamaño mínimo: el rostro debe tener al menos 70×70 px.
    - Relación de aspecto: entre 0.5 y 1.6 (caras no son muy alargadas ni muy anchas).
    - Posición vertical: el borde inferior del bounding box no debe superar el 90 %
      del alto del frame, lo que evita detectar el torso/ropa en la parte baja.
    """
    if fh <= 0 or fw <= 0:
        return False
    if fw < 70 or fh < 70:
        return False
    aspect = fw / fh
    if not (0.50 <= aspect <= 1.60):
        return False
    face_bottom_frac = (y + fh) / h_img
    if face_bottom_frac > 0.90:
        return False
    return True


def _boxes_overlap(a, b, min_iou: float = 0.15) -> bool:
    """
    Comprueba si dos cajas (x, y, w, h) se solapan al menos min_iou (IoU).
    Usado para validación cruzada MediaPipe ↔ cascade.
    """
    ax1, ay1, ax2, ay2 = a[0], a[1], a[0] + a[2], a[1] + a[3]
    bx1, by1, bx2, by2 = b[0], b[1], b[0] + b[2], b[1] + b[3]
    ix = max(0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0, min(ay2, by2) - max(ay1, by1))
    inter = ix * iy
    union = a[2] * a[3] + b[2] * b[3] - inter
    return (inter / union) >= min_iou if union > 0 else False


# ─────────────────────────────────────────────────────────────────────────────

class CamThread(QThread):
    frame_sig = pyqtSignal(QImage)
    cap_done  = pyqtSignal(bool, str)
    rec_done  = pyqtSignal(str)
    progress  = pyqtSignal(int)

    CAPTURE      = "capture"
    RECOGNIZE    = "recognize"
    CAMERA_ERROR = "__CAMERA_ERROR__"
    _disable_picamera2 = False

    # Número de fotos a capturar por sesión.
    CAPTURE_TARGET = 12
    # Reconocimiento: umbral máximo de confianza (LBPH devuelve distancia; menor es mejor)
    RECOGNIZE_CONF_THRESHOLD = 60
    # Número de frames consecutivos con la misma etiqueta requeridos para confirmar
    RECOGNIZE_CONFIRM_FRAMES = 2

    # ── Parámetros de anclaje de posición (solo CAPTURE mode) ────────────────
    # Una vez detectado el primer rostro, solo se aceptan rostros cuyo centro
    # esté dentro de ANCHOR_RADIUS px del ancla.  Evita que una segunda persona
    # que aparezca en cámara "robe" la sesión de captura.
    _ANCHOR_RADIUS   = 180   # px — tolerancia de movimiento de cabeza
    _ANCHOR_MAX_MISS = 20    # frames sin detección antes de resetear el ancla

    def __init__(self, mode, face_uid="", labels=None, detect_roi=None):
        """
        detect_roi: (x_frac, y_frac, w_frac, h_frac) normalizado [0..1].
                    Limita la detección al área del marco verde de la UI.
        """
        super().__init__()
        self.mode       = mode
        self.face_uid   = face_uid
        self.labels     = labels or {}
        # Número de etiquetas en el modelo (cantidad de personas registradas)
        self.labels_count = len(self.labels) if self.labels is not None else 0
        # Umbral dinámico de reconocimiento (LBPH devuelve distancia; menor es mejor)
        if self.labels_count < 2:
            # Desactivar reconocimiento cuando hay menos de 2 personas.
            self._recognize_threshold = None
        elif self.labels_count <= 3:
            self._recognize_threshold = 45
        elif self.labels_count <= 8:
            self._recognize_threshold = 60
        else:
            self._recognize_threshold = 80
        self.detect_roi = detect_roi
        self._active    = True
        self._manual_stop = False
        self.cap = None

        if Picamera2 is not None and not CamThread._disable_picamera2:
            self.use_picamera2 = True
        else:
            self.use_picamera2 = False
            self._open_cv_capture()

    def _open_cv_capture(self):
        self.cap = None
        for idx in (0, 1, 2, 3, 4, 5):
            cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            if not cap.isOpened():
                cap.release()
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            ok, _ = cap.read()
            if ok:
                self.cap = cap
                return
            cap.release()

    def _switch_to_cv_fallback(self):
        self.use_picamera2 = False
        CamThread._disable_picamera2 = True
        self._open_cv_capture()

    def stop(self):
        self._manual_stop = True
        self._active = False
        self.wait(3000)

    def run(self):
        capture_count  = 0
        recognized_uid = ""
        read_failed    = False

        # Estado del anclaje de posición (solo CAPTURE)
        face_anchor    = None   # (cx, cy) del primer rostro capturado
        anchor_misses  = 0      # frames consecutivos sin detección válida

        if self.use_picamera2:
            picam = _get_picam()
            if picam is None:
                self._switch_to_cv_fallback()
        else:
            picam = None

        if not self.use_picamera2 and (not self.cap or not self.cap.isOpened()):
            if self.mode == self.CAPTURE:
                self.cap_done.emit(False, self.CAMERA_ERROR)
            elif self.mode == self.RECOGNIZE:
                self.rec_done.emit(self.CAMERA_ERROR)
            return

        fc    = cv2.CascadeClassifier(CASCADE)
        sdir  = face_dir_for(self.face_uid) if self.mode == self.CAPTURE else None
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

        # FIX ROPA: confianza más alta (0.65 en lugar de 0.4).
        # A 0.4 MediaPipe deja pasar texturas de ropa y fondo.
        mp_face = None
        if MP_AVAILABLE:
            try:
                mp_face = mp.solutions.face_detection.FaceDetection(
                    model_selection=0, min_detection_confidence=0.65
                )
            except Exception:
                mp_face = None

        if sdir:
            os.makedirs(sdir, exist_ok=True)

        while self._active:
            # ── Lectura del frame ──────────────────────────────────────────
            if self.use_picamera2:
                try:
                    frame = picam.capture_array()
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                except Exception as e:
                    print(f"[Camera] Error leyendo Picamera2: {e}")
                    self._switch_to_cv_fallback()
                    if not self.cap or not self.cap.isOpened():
                        read_failed = True
                        break
                    ok, frame = self.cap.read()
                    if not ok:
                        read_failed = True
                        break
            else:
                ok, frame = self.cap.read()
                if not ok:
                    read_failed = True
                    break

            # Espejo corregido
            frame = cv2.flip(frame, 1)

            gray     = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_enh = clahe.apply(gray)   # mejora contraste en oscuridad

            h_img, w_img = frame.shape[:2]

            # ── ROI de detección (limita al marco verde) ───────────────────
            if self.detect_roi:
                xf, yf, wf, hf = self.detect_roi
                rx1 = max(0, int(xf * w_img))
                ry1 = max(0, int(yf * h_img))
                rx2 = min(w_img, int((xf + wf) * w_img))
                ry2 = min(h_img, int((yf + hf) * h_img))
                det_gray  = gray_enh[ry1:ry2, rx1:rx2]
                det_frame = frame[ry1:ry2, rx1:rx2]
                off_x, off_y = rx1, ry1
            else:
                det_gray  = gray_enh
                det_frame = frame
                off_x, off_y = 0, 0

            h_det, w_det = det_gray.shape[:2]

            # ── Detección de rostros ───────────────────────────────────────
            raw_faces = []   # candidatos antes de filtrar

            if mp_face is not None:
                try:
                    rgb     = cv2.cvtColor(det_frame, cv2.COLOR_BGR2RGB)
                    results = mp_face.process(rgb)
                    if results.detections:
                        for det in results.detections:
                            score = det.score[0] if det.score else 0
                            # FIX ROPA: descartamos detecciones de baja confianza
                            if score < 0.65:
                                continue
                            bbox = det.location_data.relative_bounding_box
                            x  = int(bbox.xmin * w_det) + off_x
                            y  = int(bbox.ymin * h_det) + off_y
                            bw = int(bbox.width  * w_det)
                            bh = int(bbox.height * h_det)
                            x  = max(0, x)
                            y  = max(0, y)
                            bw = max(1, min(w_img - x, bw))
                            bh = max(1, min(h_img - y, bh))
                            raw_faces.append((x, y, bw, bh))
                except Exception:
                    # Fallback cascade con parámetros más estrictos
                    casc_raw = fc.detectMultiScale(
                        det_gray, scaleFactor=1.2, minNeighbors=6,
                        minSize=(80, 80), flags=cv2.CASCADE_SCALE_IMAGE
                    )
                    if len(casc_raw):
                        raw_faces = [
                            (int(x) + off_x, int(y) + off_y, int(w), int(h))
                            for x, y, w, h in casc_raw
                        ]
            else:
                # Solo cascade — parámetros más estrictos para evitar falsos +
                casc_raw = fc.detectMultiScale(
                    det_gray, scaleFactor=1.2, minNeighbors=6,
                    minSize=(80, 80), flags=cv2.CASCADE_SCALE_IMAGE
                )
                if len(casc_raw):
                    raw_faces = [
                        (int(x) + off_x, int(y) + off_y, int(w), int(h))
                        for x, y, w, h in casc_raw
                    ]

            # ── FIX ROPA: validación de aspecto, tamaño y posición ────────
            # Filtra cualquier detección que no tenga la geometría de un rostro.
            faces = [
                f for f in raw_faces
                if _is_valid_face(f[0], f[1], f[2], f[3], w_img, h_img)
            ]

            # ── FIX DOS PERSONAS: si hay 2+ rostros → saltar el frame ─────
            # No capturamos ni reconocemos cuando hay más de una persona en
            # cámara.  Se dibuja aviso visual y se espera a que quede 1 solo.
            if len(faces) > 1:
                # Dibujar todos los bounding boxes en naranja
                for (fx, fy, ffw, ffh) in faces:
                    cv2.rectangle(frame, (fx, fy), (fx + ffw, fy + ffh),
                                  (0, 140, 255), 2)
                # Aviso centrado
                txt = "Solo 1 persona a la vez"
                (tw, th), _ = cv2.getTextSize(
                    txt, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
                tx = max(0, (w_img - tw) // 2)
                ty = 34
                cv2.rectangle(frame, (tx - 6, ty - th - 6),
                              (tx + tw + 6, ty + 6), (0, 0, 0), -1)
                cv2.putText(frame, txt, (tx, ty),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 140, 255), 2)
                # Si había ancla, incrementar misses (quizás se pusieron dos personas)
                anchor_misses += 1
                if anchor_misses >= self._ANCHOR_MAX_MISS:
                    face_anchor   = None
                    anchor_misses = 0
                self._emit_frame(frame)
                continue   # no procesar este frame

            # ── Un solo rostro válido ──────────────────────────────────────
            if not faces:
                # Sin detección — acumular misses y posiblemente resetear ancla
                anchor_misses += 1
                if anchor_misses >= self._ANCHOR_MAX_MISS:
                    face_anchor   = None
                    anchor_misses = 0
                self._emit_frame(frame)
                continue

            # Exactamente 1 cara
            (x, y, fw, fh) = faces[0]

            # ── FIX DOS PERSONAS (CAPTURE): ancla de posición ─────────────
            # Al capturar, anclamos en el primer rostro detectado y rechazamos
            # cualquier detección que aparezca lejos de esa posición (otra persona).
            if self.mode == self.CAPTURE:
                cx_now = x + fw // 2
                cy_now = y + fh // 2

                if face_anchor is None:
                    # Primera detección → establecer ancla
                    face_anchor   = (cx_now, cy_now)
                    anchor_misses = 0
                else:
                    dist = math.hypot(cx_now - face_anchor[0],
                                      cy_now - face_anchor[1])
                    if dist > self._ANCHOR_RADIUS:
                        # Cara demasiado lejos del ancla → otra persona, rechazar
                        cv2.rectangle(frame, (x, y), (x + fw, y + fh),
                                      (0, 80, 220), 2)
                        txt2 = "Mantente frente a la camara"
                        cv2.putText(frame, txt2, (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                    (0, 80, 220), 2)
                        anchor_misses += 1
                        self._emit_frame(frame)
                        continue
                    # Cara dentro del área aceptable → suavizar ancla
                    face_anchor = (
                        int(0.85 * face_anchor[0] + 0.15 * cx_now),
                        int(0.85 * face_anchor[1] + 0.15 * cy_now),
                    )
                    anchor_misses = 0

            # ── Clamp final para no salir del frame ───────────────────────
            x  = max(0, min(x,  w_img - 1))
            y  = max(0, min(y,  h_img - 1))
            fw = max(1, min(fw, w_img - x))
            fh = max(1, min(fh, h_img - y))

            # ROI para guardar/reconocer — usa gray_enh (mejor calidad con CLAHE)
            roi = cv2.resize(gray_enh[y:y + fh, x:x + fw], (IMG_W, IMG_H))

            # ── CAPTURE ───────────────────────────────────────────────────
            if self.mode == self.CAPTURE:
                cv2.rectangle(frame, (x, y), (x + fw, y + fh),
                              (185, 234, 137), 2)
                cv2.imwrite(
                    os.path.join(sdir, "{}.png".format(capture_count)), roi
                )
                capture_count += 1
                self.progress.emit(capture_count)
                cv2.putText(
                    frame,
                    f"{capture_count}/{self.CAPTURE_TARGET}",
                    (x, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 180, 255), 2,
                )
                if capture_count >= self.CAPTURE_TARGET:
                    self._active = False

            # ── RECOGNIZE ─────────────────────────────────────────────────
            elif self.mode == self.RECOGNIZE:
                try:
                    # Si no hay suficientes etiquetas, no intentamos reconocer.
                    if getattr(self, '_recognize_threshold', None) is None:
                        continue
                    lbl_idx, conf = face_model.predict(roi)
                    # LBPH: menor distancia -> mejor coincidencia
                    if conf < self._recognize_threshold and lbl_idx in self.labels:
                        # Mantener buffer de confirmación entre frames
                        if 'last_lbl_idx' not in locals():
                            last_lbl_idx = None
                            last_count = 0
                        if last_lbl_idx == lbl_idx:
                            last_count += 1
                        else:
                            last_lbl_idx = lbl_idx
                            last_count = 1
                        if last_count >= self.RECOGNIZE_CONFIRM_FRAMES:
                            recognized_uid = self.labels[lbl_idx]
                            cv2.rectangle(frame, (x, y), (x + fw, y + fh),
                                          (185, 234, 137), 2)
                            cv2.putText(frame, recognized_uid, (x, y - 8),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                        (80, 180, 255), 2)
                            self._active = False
                    else:
                        # reset on weak/unknown predictions
                        if 'last_lbl_idx' in locals():
                            last_lbl_idx = None
                            last_count = 0
                except Exception:
                    pass

            self._emit_frame(frame)

        # ── Liberación de recursos ─────────────────────────────────────────
        # La Picamera2 global NO se cierra aquí — se reutiliza en el siguiente hilo.
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        if 'mp_face' in locals() and mp_face is not None:
            try:
                mp_face.close()
            except Exception:
                pass

        if self.mode == self.CAPTURE:
            if capture_count >= self.CAPTURE_TARGET or not self._manual_stop:
                ref = self.face_uid
                if read_failed and capture_count == 0:
                    ref = self.CAMERA_ERROR
                self.cap_done.emit(capture_count >= self.CAPTURE_TARGET, ref)
        elif self.mode == self.RECOGNIZE:
            if recognized_uid:
                self.rec_done.emit(recognized_uid)
            elif read_failed and not self._manual_stop:
                self.rec_done.emit(self.CAMERA_ERROR)
            elif not self._active and not self._manual_stop:
                self.rec_done.emit("")

    def _emit_frame(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        img_qt = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self.frame_sig.emit(img_qt)