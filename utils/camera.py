import sys
import os
import cv2
import time
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage
import contextlib

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

# Importamos tus configuraciones locales
from biometria.biometria import CASCADE, face_dir_for, face_model, IMG_H, IMG_W

# Suppress OpenCV logging at startup to reduce console noise
os.environ['OPENCV_LOG_LEVEL'] = 'OFF'

# ── Picamera2: Lazy initialization (only when needed, not at startup) ────────
# Each thread creates and owns its own camera instance during run()
# This prevents "list index out of range" at startup when no camera available

def _get_picam():
    """Create a new Picamera2 instance for this thread (lazy initialization).
    Only called during run() when actually needed, not at startup.
    """
    if Picamera2 is None:
        return None
    try:
        cam = Picamera2()
        config = cam.create_video_configuration(main={"size": (640, 480)})
        cam.configure(config)
        cam.start()
        time.sleep(0.5)
        return cam
    except Exception as e:
        print(f"[Camera] No se pudo inicializar Picamera2: {e}")
        return None


def _release_picam(cam):
    """Stop and release a Picamera2 instance."""
    if cam is not None:
        try:
            cam.stop()
            cam.close()
        except Exception:
            pass


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
        self.cap = None  # OpenCV fallback
        self.picam = None  # Picamera2 instance (initialized in run())

        # Determine which camera backend to try
        if Picamera2 is not None and not CamThread._disable_picamera2:
            self.use_picamera2 = True
        else:
            self.use_picamera2 = False

    def _open_cv_capture(self):
        """Try to open camera on indices 0-5, suppressing OpenCV warnings."""
        self.cap = None
        # Suppress stderr to avoid OpenCV VideoIO warnings about failed device opens
        with contextlib.suppress(OSError):
            for idx in (0, 1, 2, 3, 4, 5):
                # Redirect stderr to /dev/null during VideoCapture attempt
                with open(os.devnull, 'w') as devnull:
                    old_stderr = sys.stderr
                    try:
                        sys.stderr = devnull
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
                    finally:
                        sys.stderr = old_stderr

    def _switch_to_cv_fallback(self):
        self.use_picamera2 = False
        CamThread._disable_picamera2 = True
        self._open_cv_capture()

    def stop(self):
        """Stop the camera thread and release resources immediately."""
        self._manual_stop = True
        self._active = False
        # Release Picamera2 immediately if in use
        if self.picam is not None:
            _release_picam(self.picam)
            self.picam = None
        # Release OpenCV fallback immediately
        if self.cap and self.cap.isOpened():
            try:
                self.cap.release()
                self.cap = None
            except Exception:
                pass
        self.wait(3000)

    def run(self):
        capture_count = 0
        recognized_uid = ""
        read_failed = False
        
        try:
            # Try Picamera2 first if available (lazy initialization here)
            if self.use_picamera2:
                self.picam = _get_picam()
                if self.picam is None:
                    self._switch_to_cv_fallback()
            
            # If not using Picamera2, initialize OpenCV
            if not self.use_picamera2:
                if not self.cap:
                    self._open_cv_capture()
                if not self.cap or not self.cap.isOpened():
                    if self.mode == self.CAPTURE:
                        self.cap_done.emit(False, self.CAMERA_ERROR)
                    elif self.mode == self.RECOGNIZE:
                        self.rec_done.emit(self.CAMERA_ERROR)
                    return

            picam = self.picam

            fc = cv2.CascadeClassifier(CASCADE)
            sdir = face_dir_for(self.face_uid) if self.mode == self.CAPTURE else None

            mp_face = None
            if MP_AVAILABLE:
                try:
                    mp_face = mp.solutions.face_detection.FaceDetection(
                        model_selection=0, min_detection_confidence=0.5
                    )
                except Exception:
                    mp_face = None

            if sdir:
                os.makedirs(sdir, exist_ok=True)

            while self._active:
                if self.use_picamera2 and picam is not None:
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
                elif self.cap is not None:
                    ok, frame = self.cap.read()
                    if not ok:
                        read_failed = True
                        break
                else:
                    read_failed = True
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Prefer MediaPipe detections if available (more robust across poses)
                faces = []
                h, w = frame.shape[:2]
                if mp_face is not None:
                    try:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        results = mp_face.process(rgb)
                        if results.detections:
                            for det in results.detections:
                                bbox = det.location_data.relative_bounding_box
                                x = int(bbox.xmin * w)
                                y = int(bbox.ymin * h)
                                bw = int(bbox.width * w)
                                bh = int(bbox.height * h)
                                x = max(0, x)
                                y = max(0, y)
                                bw = max(1, min(w - x, bw))
                                bh = max(1, min(h - y, bh))
                                faces.append((x, y, bw, bh))
                    except Exception:
                        faces = fc.detectMultiScale(gray, 1.3, 5)
                else:
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

        finally:
            # Always cleanup resources at the end
            if 'mp_face' in locals() and mp_face is not None:
                try:
                    mp_face.close()
                except Exception:
                    pass

            # Clean up OpenCV
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None
            
            # Clean up Picamera2
            if self.picam is not None:
                _release_picam(self.picam)
                self.picam = None

        # Emit results
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
