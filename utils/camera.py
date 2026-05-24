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
            # 2 s para que AWB y AE se estabilicen — importante con piel oscura
            time.sleep(2.0)
            # Controles de cámara para mejor exposición facial (piel oscura + oscuridad)
            try:
                cam.set_controls({
                    "AeEnable": True,
                    "AwbEnable": True,
                })
            except Exception:
                pass
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


# ── Tablas de Gamma precalculadas ─────────────────────────────────────────────
# Gamma < 1.0 aclara píxeles oscuros → mejora detección en piel oscura y oscuridad
_GAMMA_CACHE: dict = {}

def _gamma_lut(gamma: float) -> np.ndarray:
    key = round(gamma, 2)
    if key not in _GAMMA_CACHE:
        _GAMMA_CACHE[key] = np.array(
            [min(255, int(((i / 255.0) ** (1.0 / gamma)) * 255))
             for i in range(256)], dtype=np.uint8
        )
    return _GAMMA_CACHE[key]


# ── Validación geométrica de detecciones ──────────────────────────────────────

def _is_valid_face(x, y, fw, fh, w_img, h_img) -> bool:
    """
    Descarta ropa, objetos y detecciones que no son rostros por geometría.
    - Tamaño mínimo 70×70 px
    - Relación de aspecto 0.50–1.60 (caras son aproximadamente cuadradas)
    - Borde inferior < 90% del frame (evita capturar torso/ropa)
    """
    if fh <= 0 or fw <= 0:
        return False
    if fw < 70 or fh < 70:
        return False
    aspect = fw / fh
    if not (0.50 <= aspect <= 1.60):
        return False
    if (y + fh) / h_img > 0.90:
        return False
    return True


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

    CAPTURE_TARGET = 12

    # Anclaje de posición: evita capturar a una segunda persona
    _ANCHOR_RADIUS   = 180  # px de tolerancia de movimiento de cabeza
    _ANCHOR_MAX_MISS = 20   # frames sin detección antes de resetear el ancla

    # Anti-spoofing (anti-foto): buffer de ROIs para detectar movimiento real
    _LIVENESS_BUF_SIZE   = 5    # número de frames en el buffer
    _LIVENESS_MIN_MOTION = 4.5  # diferencia mínima media entre frames consecutivos
                                 # Foto/pantalla estática ≈ 0–3; cara real ≈ 8–40

    def __init__(self, mode, face_uid="", labels=None, detect_roi=None):
        """
        detect_roi: (x_frac, y_frac, w_frac, h_frac) en [0..1].
                    Limita la detección al área del marco verde de la UI.
        """
        super().__init__()
        self.mode         = mode
        self.face_uid     = face_uid
        self.labels       = labels or {}
        self.detect_roi   = detect_roi
        self._active      = True
        self._manual_stop = False
        self.cap          = None

        if Picamera2 is not None and not CamThread._disable_picamera2:
            self.use_picamera2 = True
        else:
            self.use_picamera2 = False
            self._open_cv_capture()

        # ── Umbrales dinámicos de reconocimiento ─────────────────────────
        # LBPH con pocos registros no discrimina bien entre personas.
        # → Con 1 persona usamos un umbral estricto (confidence < umbral).
        # → Con más personas el modelo mejora y podemos ser más permisivos.
        #
        # LBPH confidence: MENOR = mejor coincidencia.
        # Fast-accept: si confidence < _recog_fast_threshold acepta en 2 frames
        # (cara genuina en buenas condiciones → coincidencia muy clara).
        n = len(self.labels)
        if n <= 1:
            self._recog_threshold      = 52
            self._recog_min_frames     = 3
        elif n <= 3:
            self._recog_threshold      = 60
            self._recog_min_frames     = 3
        elif n <= 6:
            self._recog_threshold      = 68
            self._recog_min_frames     = 3
        else:
            self._recog_threshold      = 75
            self._recog_min_frames     = 3

        # Fast-accept: coincidencia muy alta → solo 2 frames necesarios
        self._recog_fast_threshold = 32

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

        # Anclaje de posición (solo CAPTURE)
        face_anchor   = None
        anchor_misses = 0

        # Confirmación multi-frame (solo RECOGNIZE)
        recog_last_label    = None
        recog_confirm_count = 0

        # Anti-spoofing: buffer de ROIs para detección de movimiento
        liveness_buf = []   # lista de np.ndarray float32

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
        clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))

        # MediaPipe: 0.60 en lugar de 0.65 → mejor detección con lentes
        # (el modelo sigue siendo estricto pero tolera más variación de textura)
        mp_face = None
        if MP_AVAILABLE:
            try:
                mp_face = mp.solutions.face_detection.FaceDetection(
                    model_selection=0, min_detection_confidence=0.60
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

            # Modo espejo corregido → imagen natural (no invertida)
            frame = cv2.flip(frame, 1)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # ── Gamma adaptativo para piel oscura y poca luz ─────────────
            # Mide el brillo medio del frame. Si es oscuro, aplica corrección
            # gamma que aclara los píxeles oscuros sin quemar los brillantes.
            mean_brightness = float(np.mean(gray))
            if mean_brightness < 60:
                # Muy oscuro (poca luz o piel muy oscura): boost fuerte
                gray_enh = cv2.LUT(clahe.apply(gray), _gamma_lut(0.50))
            elif mean_brightness < 95:
                # Moderadamente oscuro: boost medio
                gray_enh = cv2.LUT(clahe.apply(gray), _gamma_lut(0.68))
            elif mean_brightness < 130:
                # Algo oscuro: boost leve
                gray_enh = cv2.LUT(clahe.apply(gray), _gamma_lut(0.82))
            else:
                # Normal / bien iluminado: solo CLAHE
                gray_enh = clahe.apply(gray)

            h_img, w_img = frame.shape[:2]

            # ── ROI de detección (área del marco verde de la UI) ──────────
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
            raw_faces = []

            if mp_face is not None:
                try:
                    rgb     = cv2.cvtColor(det_frame, cv2.COLOR_BGR2RGB)
                    results = mp_face.process(rgb)
                    if results.detections:
                        for det in results.detections:
                            score = det.score[0] if det.score else 0
                            if score < 0.60:
                                continue
                            bbox = det.location_data.relative_bounding_box
                            x  = int(bbox.xmin * w_det) + off_x
                            y  = int(bbox.ymin * h_det) + off_y
                            bw = int(bbox.width  * w_det)
                            bh = int(bbox.height * h_det)
                            x  = max(0, x);  y  = max(0, y)
                            bw = max(1, min(w_img - x, bw))
                            bh = max(1, min(h_img - y, bh))
                            raw_faces.append((x, y, bw, bh))
                except Exception:
                    # Fallback cascade si MediaPipe falla
                    casc_raw = fc.detectMultiScale(
                        det_gray, scaleFactor=1.2, minNeighbors=5,
                        minSize=(70, 70), flags=cv2.CASCADE_SCALE_IMAGE
                    )
                    if len(casc_raw):
                        raw_faces = [
                            (int(x)+off_x, int(y)+off_y, int(w), int(h))
                            for x, y, w, h in casc_raw
                        ]
            else:
                casc_raw = fc.detectMultiScale(
                    det_gray, scaleFactor=1.2, minNeighbors=5,
                    minSize=(70, 70), flags=cv2.CASCADE_SCALE_IMAGE
                )
                if len(casc_raw):
                    raw_faces = [
                        (int(x)+off_x, int(y)+off_y, int(w), int(h))
                        for x, y, w, h in casc_raw
                    ]

            # ── Validación de geometría (descarta ropa / objetos) ─────────
            faces = [
                f for f in raw_faces
                if _is_valid_face(f[0], f[1], f[2], f[3], w_img, h_img)
            ]

            # ── 2+ rostros → saltar frame ─────────────────────────────────
            if len(faces) > 1:
                for (fx, fy, ffw, ffh) in faces:
                    cv2.rectangle(frame, (fx, fy), (fx+ffw, fy+ffh), (0, 140, 255), 2)
                txt = "Solo 1 persona a la vez"
                (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
                tx = max(0, (w_img - tw) // 2)
                ty = 34
                cv2.rectangle(frame, (tx-6, ty-th-6), (tx+tw+6, ty+6), (0, 0, 0), -1)
                cv2.putText(frame, txt, (tx, ty),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 140, 255), 2)
                anchor_misses += 1
                if anchor_misses >= self._ANCHOR_MAX_MISS:
                    face_anchor = None; anchor_misses = 0
                recog_last_label = None; recog_confirm_count = 0
                liveness_buf.clear()
                self._emit_frame(frame)
                continue

            # ── Sin rostro → acumular misses ──────────────────────────────
            if not faces:
                anchor_misses += 1
                if anchor_misses >= self._ANCHOR_MAX_MISS:
                    face_anchor = None; anchor_misses = 0
                recog_last_label = None; recog_confirm_count = 0
                liveness_buf.clear()
                self._emit_frame(frame)
                continue

            # ── Exactamente 1 cara válida ─────────────────────────────────
            (x, y, fw, fh) = faces[0]

            # ── Ancla de posición (solo CAPTURE) ──────────────────────────
            if self.mode == self.CAPTURE:
                cx_now = x + fw // 2
                cy_now = y + fh // 2

                if face_anchor is None:
                    face_anchor   = (cx_now, cy_now)
                    anchor_misses = 0
                else:
                    dist = math.hypot(cx_now - face_anchor[0],
                                      cy_now - face_anchor[1])
                    if dist > self._ANCHOR_RADIUS:
                        cv2.rectangle(frame, (x, y), (x+fw, y+fh), (0, 80, 220), 2)
                        cv2.putText(frame, "Mantente frente a la camara",
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.6, (0, 80, 220), 2)
                        anchor_misses += 1
                        self._emit_frame(frame)
                        continue
                    face_anchor = (
                        int(0.85 * face_anchor[0] + 0.15 * cx_now),
                        int(0.85 * face_anchor[1] + 0.15 * cy_now),
                    )
                    anchor_misses = 0

            # Clamp
            x  = max(0, min(x,  w_img - 1))
            y  = max(0, min(y,  h_img - 1))
            fw = max(1, min(fw, w_img - x))
            fh = max(1, min(fh, h_img - y))

            roi = cv2.resize(gray_enh[y:y+fh, x:x+fw], (IMG_W, IMG_H))

            # ── Anti-spoofing: solo rostros reales, no fotos ──────────────
            # Acumula ROIs recientes y mide cuánto cambian entre frames.
            # Cara real: micro-movimientos → variación > umbral.
            # Foto/pantalla: imagen estática → variación ≈ 0.
            # Solo aplicamos en RECOGNIZE (en CAPTURE no tiene sentido bloquear).
            if self.mode == self.RECOGNIZE:
                roi_f = roi.astype(np.float32)
                liveness_buf.append(roi_f)
                if len(liveness_buf) > self._LIVENESS_BUF_SIZE:
                    liveness_buf.pop(0)

                if len(liveness_buf) >= 3:
                    diffs = [
                        float(np.mean(np.abs(liveness_buf[i] - liveness_buf[i-1])))
                        for i in range(1, len(liveness_buf))
                    ]
                    avg_motion = float(np.mean(diffs))
                    if avg_motion < self._LIVENESS_MIN_MOTION:
                        # Sin movimiento → imagen estática (probable foto/pantalla)
                        # No mostramos mensaje (no avisamos al intento de fraude)
                        self._emit_frame(frame)
                        continue
            else:
                # En CAPTURE limpiamos el buffer pero no bloqueamos
                liveness_buf.clear()

            # ── CAPTURE ───────────────────────────────────────────────────
            if self.mode == self.CAPTURE:
                cv2.rectangle(frame, (x, y), (x+fw, y+fh), (185, 234, 137), 2)
                cv2.imwrite(os.path.join(sdir, "{}.png".format(capture_count)), roi)
                capture_count += 1
                self.progress.emit(capture_count)
                cv2.putText(frame, f"{capture_count}/{self.CAPTURE_TARGET}",
                            (x, y-8), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (80, 180, 255), 2)
                if capture_count >= self.CAPTURE_TARGET:
                    self._active = False

            # ── RECOGNIZE ─────────────────────────────────────────────────
            elif self.mode == self.RECOGNIZE:
                try:
                    lbl_idx, conf = face_model.predict(roi)

                    # Fast-accept: si la coincidencia es muy alta (conf muy baja),
                    # solo necesitamos 2 frames consecutivos → detección rápida.
                    # Para coincidencias moderadas exigimos más frames → seguridad.
                    if conf < self._recog_fast_threshold and lbl_idx in self.labels:
                        needed = 2   # coincidencia clara → rápido
                    elif conf < self._recog_threshold and lbl_idx in self.labels:
                        needed = self._recog_min_frames
                    else:
                        recog_last_label    = None
                        recog_confirm_count = 0
                        self._emit_frame(frame)
                        continue

                    if recog_last_label == lbl_idx:
                        recog_confirm_count += 1
                    else:
                        recog_last_label    = lbl_idx
                        recog_confirm_count = 1

                    # Barra de progreso visual
                    pct = int(recog_confirm_count / needed * 100)
                    cv2.rectangle(frame, (x, y), (x+fw, y+fh), (185, 234, 137), 2)
                    cv2.putText(frame, f"Verificando {min(pct,100)}%",
                                (x, y-8), cv2.FONT_HERSHEY_SIMPLEX,
                                0.6, (80, 180, 255), 2)

                    if recog_confirm_count >= needed:
                        recognized_uid = self.labels[lbl_idx]
                        self._active   = False

                except Exception:
                    recog_last_label    = None
                    recog_confirm_count = 0

            self._emit_frame(frame)

        # ── Liberación de recursos ─────────────────────────────────────────
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