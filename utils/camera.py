import os
import cv2
from PyQt5.QtCore import  QThread, pyqtSignal
from PyQt5.QtGui import QImage

from biometria.biometria import CASCADE, face_dir_for, face_model, IMG_H, IMG_W

try:
    from picamera2 import Picamera2
except ModuleNotFoundError:
    Picamera2 = None

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

    def _open_camera(self):
        if Picamera2 is not None:
            camera = Picamera2()
            config = camera.create_video_configuration(
                main={"size": (640, 480), "format": "RGB888"}
            )
            camera.configure(config)
            camera.start()
            return camera, "picamera2"

        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return camera, "opencv"

    def _read_frame(self, camera, backend):
        if backend == "picamera2":
            return camera.capture_array()

        ret, frame = camera.read()
        if not ret:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def _close_camera(self, camera, backend):
        if backend == "picamera2":
            camera.stop()
            camera.close()
        else:
            camera.release()

    def run(self):
        camera = None
        backend = None
        fc = cv2.CascadeClassifier(CASCADE)
        cnt = 0
        sdir = face_dir_for(self.face_uid) if self.mode == self.CAPTURE else None
        if sdir:
            os.makedirs(sdir, exist_ok=True)

        try:
            camera, backend = self._open_camera()

            while self._active:
                frame = self._read_frame(camera, backend)
                if frame is None:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
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
                                return
                        except Exception:
                            pass

                self._emit_frame(frame)
        finally:
            if camera is not None and backend is not None:
                self._close_camera(camera, backend)

        if self.mode == self.CAPTURE:
            self.cap_done.emit(cnt >= 20, self.face_uid)
        elif self.mode == self.RECOGNIZE:
            self.rec_done.emit("")

    def _emit_frame(self, frame):
        h, w, ch = frame.shape
        self.frame_sig.emit(QImage(frame.data, w, h, ch * w, QImage.Format_RGB888).copy())

