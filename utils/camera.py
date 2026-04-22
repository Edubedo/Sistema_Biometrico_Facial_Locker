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

class CamThread(QThread):
    frame_sig = pyqtSignal(QImage)
    cap_done  = pyqtSignal(bool, str)
    rec_done  = pyqtSignal(str)
    progress  = pyqtSignal(int)

    CAPTURE   = "capture"
    RECOGNIZE = "recognize"
    CAMERA_ERROR = "__CAMERA_ERROR__"
    _disable_picamera2 = False

    def __init__(self, mode, face_uid="", labels=None):
        super().__init__()
        self.mode     = mode
        self.face_uid = face_uid
        self.labels   = labels or {}
        self._active  = True
        self._manual_stop = False
        self.use_picamera2 = (Picamera2 is not None) and (not CamThread._disable_picamera2)
        self.picam = None
        self.cap = None

        if self.use_picamera2:
            try:
                self.picam = Picamera2()
                config = self.picam.create_video_configuration(
                    main={"size": (640, 480)}
                )
                self.picam.configure(config)
            except Exception:
                CamThread._disable_picamera2 = True
                self.use_picamera2 = False
                self.picam = None
                self._open_cv_capture()
        else:
            self._open_cv_capture()

    def _open_cv_capture(self):
        self.cap = None
        # Probamos multiples indices para evitar depender de /dev/video0.
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
        if self.picam is not None:
            try:
                self.picam.stop()
            except Exception:
                pass
        self.picam = None
        if self.cap is None or not self.cap.isOpened():
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
            try:
                self.picam.start()
                time.sleep(1.5)
            except Exception:
                self._switch_to_cv_fallback()
        elif not self.cap or not self.cap.isOpened():
            if self.mode == self.CAPTURE:
                self.cap_done.emit(False, self.face_uid)
            elif self.mode == self.RECOGNIZE:
                self.rec_done.emit(self.CAMERA_ERROR)
            return

        if not self.use_picamera2 and (not self.cap or not self.cap.isOpened()):
            if self.mode == self.CAPTURE:
                self.cap_done.emit(False, self.face_uid)
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
                    frame = self.picam.capture_array()
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                except Exception:
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

            # Para detección seguimos usando escala de grises
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = fc.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                roi = cv2.resize(gray[y:y+h, x:x+w], (IMG_W, IMG_H))

                if self.mode == self.CAPTURE:
                    cv2.imwrite(os.path.join(sdir, "{}.png".format(capture_count)), roi)
                    capture_count += 1
                    self.progress.emit(capture_count)
                    # Dibujamos sobre el frame corregido
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
                    except: pass

            self._emit_frame(frame)

        if self.picam is not None:
            self.picam.stop()
        if self.cap is not None:
            self.cap.release()

        if self.mode == self.CAPTURE:
            if capture_count >= 20 or not self._manual_stop:
                self.cap_done.emit(capture_count >= 20, self.face_uid)
        elif self.mode == self.RECOGNIZE:
            # Emitimos siempre un resultado para que la UI no se quede esperando.
            if recognized_uid:
                self.rec_done.emit(recognized_uid)
            elif read_failed and not self._manual_stop:
                self.rec_done.emit(self.CAMERA_ERROR)
            elif self._active is False and not self._manual_stop:
                self.rec_done.emit("")

    def _emit_frame(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        
        # Al haber invertido a BGR arriba, aquí le decimos a Qt que lea BGR
        # Esto debería corregir los colores pálidos/azules de las fotos anteriores.
        img_qt = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self.frame_sig.emit(img_qt)