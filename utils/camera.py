import sys
import os
import cv2
import time
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None

# Importamos tus configuraciones locales
from biometria.biometria import CASCADE, face_dir_for, face_model, IMG_H, IMG_W

# ── Singleton global de Picamera2 ─────────────────────────────────────────────
# La Raspberry Pi solo permite una instancia activa a la vez.
# Reutilizamos la misma instancia entre hilos para evitar el error
# "Camera in Configured state trying acquire() requiring state Available".
_picam_instance = None
_picam_lock = __import__("threading").Lock()


def _get_picam():
    """Devuelve la instancia global de Picamera2, creándola si no existe."""
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
    """Detiene y libera la instancia global de Picamera2."""
    global _picam_instance
    with _picam_lock:
        if _picam_instance is not None:
            try:
                _picam_instance.stop()
                _picam_instance.close()
            except Exception:
                pass
            _picam_instance = None


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

    def __init__(self, mode, face_uid="", labels=None):
        super().__init__()
        self.mode     = mode
        self.face_uid = face_uid
        self.labels   = labels or {}
        self._active  = True
        self._manual_stop = False
        self.cap = None  # Solo usado como fallback a OpenCV

        # Intentar usar el singleton de Picamera2
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
        capture_count = 0
        recognized_uid = ""
        read_failed = False

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

        fc = cv2.CascadeClassifier(CASCADE)
        sdir = face_dir_for(self.face_uid) if self.mode == self.CAPTURE else None

        if sdir:
            os.makedirs(sdir, exist_ok=True)

        while self._active:
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

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = fc.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                roi = cv2.resize(gray[y:y+h, x:x+w], (IMG_W, IMG_H))

                if self.mode == self.CAPTURE:
                    cv2.imwrite(os.path.join(sdir, "{}.png".format(capture_count)), roi)
                    capture_count += 1
                    self.progress.emit(capture_count)
                    cv2.putText(frame, f"{capture_count}/20", (x, y - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 180, 255), 2)
                    if capture_count >= 20:
                        self._active = False
                        break

                elif self.mode == self.RECOGNIZE:
                    try:
                        lbl_idx, conf = face_model.predict(roi)
                        if conf < 100 and lbl_idx in self.labels:
                            recognized_uid = self.labels[lbl_idx]
                            cv2.putText(frame, recognized_uid, (x, y - 8),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 180, 255), 2)
                            self._active = False
                            break
                    except:
                        pass

            self._emit_frame(frame)

        # Al terminar: liberar solo OpenCV si se usó como fallback.
        # La Picamera2 global NO se cierra aquí — se reutiliza en el siguiente hilo.
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        if self.mode == self.CAPTURE:
            if capture_count >= 20 or not self._manual_stop:
                ref = self.face_uid
                if read_failed and capture_count == 0:
                    ref = self.CAMERA_ERROR
                self.cap_done.emit(capture_count >= 20, ref)
        elif self.mode == self.RECOGNIZE:
            if recognized_uid:
                self.rec_done.emit(recognized_uid)
            elif read_failed and not self._manual_stop:
                self.rec_done.emit(self.CAMERA_ERROR)
            elif self._active is False and not self._manual_stop:
                self.rec_done.emit("")

    def _emit_frame(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        img_qt = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self.frame_sig.emit(img_qt)