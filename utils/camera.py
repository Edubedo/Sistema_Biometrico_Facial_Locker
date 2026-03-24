import sys
import os
import cv2
from PyQt5.QtCore import  QThread, pyqtSignal
from PyQt5.QtGui import QImage

from biometria.biometria import CASCADE, face_dir_for, face_model, IMG_H, IMG_W

class CamThread(QThread):
    frame_sig = pyqtSignal(QImage)
    cap_done  = pyqtSignal(bool, str)   # (exito, face_uid)
    rec_done  = pyqtSignal(str)          # face_uid reconocido o ""
    progress  = pyqtSignal(int)          # 0..20

    CAPTURE   = "capture"
    RECOGNIZE = "recognize"

    def __init__(self, mode, face_uid="", labels=None):
        super().__init__()
        self.mode     = mode
        self.face_uid = face_uid
        self.labels   = labels or {}
        self._active  = True

    def stop(self):
        self._active = False
        self.wait(3000)

    def run(self):
        cap  = cv2.VideoCapture(0)
        fc   = cv2.CascadeClassifier(CASCADE)
        cnt  = 0
        sdir = face_dir_for(self.face_uid) if self.mode == self.CAPTURE else None
        if sdir:
            os.makedirs(sdir, exist_ok=True)

        while self._active:
            ret, frame = cap.read()
            if not ret:
                break

            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = fc.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                roi = cv2.resize(gray[y:y+h, x:x+w], (IMG_W, IMG_H))

                if self.mode == self.CAPTURE:
                    cv2.imwrite(os.path.join(sdir, "{}.png".format(cnt)), roi)
                    cnt += 1
                    self.progress.emit(cnt)
                    cv2.putText(
                        frame, "{}/20".format(cnt), (x, y - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 180, 255), 2
                    )
                    if cnt >= 20:
                        self._active = False
                        break

                elif self.mode == self.RECOGNIZE:
                    try:
                        lbl_idx, conf = face_model.predict(roi)
                        if conf < 100 and lbl_idx in self.labels:
                            uid = self.labels[lbl_idx]
                            cv2.putText(
                                frame, uid, (x, y - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 180, 255), 2
                            )
                            self._emit_frame(frame)
                            self.rec_done.emit(uid)
                            cap.release()
                            return
                    except Exception:
                        pass

            self._emit_frame(frame)

        cap.release()
        if self.mode == self.CAPTURE:
            self.cap_done.emit(cnt >= 20, self.face_uid)
        elif self.mode == self.RECOGNIZE:
            self.rec_done.emit("")

    def _emit_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        self.frame_sig.emit(QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888))

