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

    def __init__(self, mode, face_uid="", labels=None):
        super().__init__()
        self.mode     = mode
        self.face_uid = face_uid
        self.labels   = labels or {}
        self._active  = True
        self.use_picamera2 = Picamera2 is not None
        self.picam = None
        self.cap = None

        if self.use_picamera2:
            self.picam = Picamera2()
            config = self.picam.create_video_configuration(
                main={"size": (640, 480)}
            )
            self.picam.configure(config)
        else:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def stop(self):
        self._active = False
        self.wait(3000)

    def run(self):
        if self.use_picamera2:
            self.picam.start()
            time.sleep(1.5)
        elif not self.cap or not self.cap.isOpened():
            self.cap_done.emit(False, "No se pudo abrir la cámara con Picamera2 ni con OpenCV.")
            return
        
        fc = cv2.CascadeClassifier(CASCADE)
        cnt = 0
        sdir = face_dir_for(self.face_uid) if self.mode == self.CAPTURE else None
        
        if sdir:
            os.makedirs(sdir, exist_ok=True)

        while self._active:
            if self.use_picamera2:
                frame = self.picam.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                ok, frame = self.cap.read()
                if not ok:
                    break

            # Para detección seguimos usando escala de grises
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = fc.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                roi = cv2.resize(gray[y:y+h, x:x+w], (IMG_W, IMG_H))

                if self.mode == self.CAPTURE:
                    cv2.imwrite(os.path.join(sdir, "{}.png".format(cnt)), roi)
                    cnt += 1
                    self.progress.emit(cnt)
                    # Dibujamos sobre el frame corregido
                    cv2.putText(frame, f"{cnt}/20", (x, y - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 180, 255), 2)
                    if cnt >= 20:
                        self._active = False
                        break

                elif self.mode == self.RECOGNIZE:
                    try:
                        lbl_idx, conf = face_model.predict(roi)
                        if conf < 100 and lbl_idx in self.labels:
                            uid = self.labels[lbl_idx]
                            cv2.putText(frame, uid, (x, y - 8),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 180, 255), 2)
                            self._emit_frame(frame)
                            self.rec_done.emit(uid)
                            return
                    except: pass

            self._emit_frame(frame)

        if self.picam is not None:
            self.picam.stop()
        if self.cap is not None:
            self.cap.release()

    def _emit_frame(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        
        # Al haber invertido a BGR arriba, aquí le decimos a Qt que lea BGR
        # Esto debería corregir los colores pálidos/azules de las fotos anteriores.
        img_qt = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self.frame_sig.emit(img_qt)