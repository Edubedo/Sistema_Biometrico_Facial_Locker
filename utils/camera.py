import sys
import os
import platform
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
except Exception:
    mp = None

# MediaPipe causa segfault en Python 3.14 / Windows — siempre deshabilitado.
# El sistema usa Haar cascade que es estable en todas las plataformas.
MP_AVAILABLE = False

from biometria.biometria import CASCADE, face_dir_for, face_model, IMG_H, IMG_W

# Eye cascade — confirma que el ROI facial contiene ojos (protección contra objetos).
# Se usa el cascade tolerante a anteojos para reducir falsos negativos en personas con lentes.
_EYE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
)

# ── Singleton global de Picamera2 ─────────────────────────────────────────────
_picam_instance = None
_picam_lock     = __import__("threading").Lock()


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
            time.sleep(2.0)
            try:
                cam.set_controls({"AeEnable": True, "AwbEnable": True})
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


# ── Singleton global de OpenCV VideoCapture ───────────────────────────────────
_cv_cap_instance = None
_cv_cap_lock     = __import__("threading").Lock()
_cv_read_lock    = __import__("threading").Lock()


def _get_cv_cap():
    """
    Crea (o reutiliza) el singleton de cv2.VideoCapture.
    Windows → DirectShow (DSHOW).  Linux/RPi → V4L2 → genérico.
    Descarta frames de calentamiento para estabilizar el stream.
    """
    global _cv_cap_instance
    with _cv_cap_lock:
        if _cv_cap_instance is not None:
            if _cv_cap_instance.isOpened():
                return _cv_cap_instance
            # La instancia existente ya no sirve — limpiar y recrear
            try:
                _cv_cap_instance.release()
            except Exception:
                pass
            _cv_cap_instance = None

        is_windows = platform.system() == "Windows"
        backends   = [cv2.CAP_DSHOW, cv2.CAP_ANY] if is_windows \
                     else [cv2.CAP_V4L2, cv2.CAP_ANY]

        for idx in (0, 1, 2):
            for backend in backends:
                try:
                    cap = cv2.VideoCapture(idx, backend)
                    if not cap.isOpened():
                        cap.release()
                        continue
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

                    # Calentamiento: esperar hasta 10 frames válidos
                    warmed = False
                    for _ in range(15):
                        ok, _ = cap.read()
                        if ok:
                            warmed = True
                            break
                        time.sleep(0.05)

                    if warmed:
                        bname = "DSHOW" if backend == cv2.CAP_DSHOW \
                                else ("V4L2" if backend == cv2.CAP_V4L2 else backend)
                        print(f"[Camera] OpenCV lista: índice={idx} backend={bname}")
                        _cv_cap_instance = cap
                        return _cv_cap_instance
                    cap.release()
                except Exception as e:
                    print(f"[Camera] Error abriendo idx={idx} backend={backend}: {e}")

        print("[Camera] No se encontró ninguna cámara disponible")
        return None


def _flush_cv_cap(cap, n: int = 4):
    """Descarta N frames del buffer para entregar solo frames actuales."""
    if cap is None:
        return
    for _ in range(n):
        cap.grab()


def _safe_read(cap, retries: int = 3) -> tuple:
    """
    Intenta leer un frame con reintentos. Devuelve (ok, frame).
    Evita romper el loop de captura por un frame ocasionalmente perdido.
    """
    with _cv_read_lock:
        for i in range(retries):
            ok, frame = cap.read()
            if ok:
                return True, frame
            if i < retries - 1:
                time.sleep(0.02)
    return False, None


# ── Tablas de Gamma precalculadas ─────────────────────────────────────────────
_GAMMA_CACHE: dict = {}


def _gamma_lut(gamma: float) -> np.ndarray:
    key = round(gamma, 2)
    if key not in _GAMMA_CACHE:
        _GAMMA_CACHE[key] = np.array(
            [min(255, int(((i / 255.0) ** (1.0 / gamma)) * 255))
             for i in range(256)], dtype=np.uint8
        )
    return _GAMMA_CACHE[key]


# ── Validación de rostros ─────────────────────────────────────────────────────

def _is_valid_face(x: int, y: int, fw: int, fh: int,
                   w_img: int, h_img: int,
                   gray: np.ndarray | None = None,
                   frame_bgr: np.ndarray | None = None) -> bool:
    """
    Descarta detecciones que claramente no sean rostros humanos.
    Criterios ordenados de más rápido a más costoso.
    """
    if fh <= 0 or fw <= 0:
        return False
    # Tamaño mínimo: 80 px (funciona con webcams a distancia normal)
    if fw < 80 or fh < 80:
        return False
    # Aspecto: rostros humanos son casi cuadrados
    aspect = fw / fh
    if not (0.60 <= aspect <= 1.45):
        return False
    # No capturar el torso como cara
    if (y + fh) / h_img > 0.92:
        return False

    x1 = max(0, x);  y1 = max(0, y)
    x2 = min(w_img, x + fw); y2 = min(h_img, y + fh)

    # Textura: umbral adaptativo al brillo del ROI.
    # En baja luz (centro comercial) las imágenes son inherentemente más borrosas,
    # así que exigir menos varianza para no rechazar caras reales.
    if gray is not None:
        roi_g = gray[y1:y2, x1:x2]
        if roi_g.size > 0:
            roi_brightness = float(np.mean(roi_g))
            lap_thresh = 10.0 if roi_brightness < 55 else 22.0
            if cv2.Laplacian(roi_g, cv2.CV_64F).var() < lap_thresh:
                return False

    # Color piel: solo se aplica con luz suficiente (>= 55 de brillo medio).
    # En baja luz los colores son poco fiables y el chequeo rechazaría caras reales.
    # Con buena luz exigimos al menos 13 % de tono piel para filtrar objetos.
    if frame_bgr is not None and fw >= 80 and fh >= 80:
        roi_bgr = frame_bgr[y1:y2, x1:x2]
        if roi_bgr.size > 0:
            roi_mean_v = float(np.mean(cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)))
            if roi_mean_v >= 55:
                roi_hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
                lower1  = np.array([0,  15,  50], dtype=np.uint8)
                upper1  = np.array([25, 175, 255], dtype=np.uint8)
                lower2  = np.array([160, 15, 50], dtype=np.uint8)
                upper2  = np.array([180, 175, 255], dtype=np.uint8)
                skin    = cv2.bitwise_or(cv2.inRange(roi_hsv, lower1, upper1),
                                         cv2.inRange(roi_hsv, lower2, upper2))
                if np.count_nonzero(skin) / skin.size < 0.13:
                    return False

    return True


# ── Anti-spoofing: detección de suplantación con teléfono/foto ───────────────
_SPOOF_BRIGHT_MEAN  = 210    # Pantalla: brillo medio máximo para "screen glow"
_SPOOF_BRIGHT_STD   = 20     # Pantalla: std mínima cuando brillo supera umbral
_SPOOF_MOD_FRAC_MIN = 0.048  # Textura: fracción mínima de gradiente moderado


def _has_eyes(roi_gray: np.ndarray) -> bool:
    """
    Devuelve True si se detecta al menos un ojo en el ROI facial.
    minNeighbors=2 y minSize pequeño para ser tolerante con lentes y ángulos.
    """
    if _EYE_CASCADE.empty():
        return True
    eyes = _EYE_CASCADE.detectMultiScale(
        roi_gray, scaleFactor=1.1, minNeighbors=2, minSize=(12, 12)
    )
    return len(eyes) >= 1


def _is_spoof_roi(roi_gray: np.ndarray) -> bool:
    """
    Devuelve True si el ROI facial es claramente una suplantación estática.
    Dos comprobaciones rápidas (fallback al liveness check como defensa principal):
      1. Screen glow: pantalla a muy alto brillo + muy uniforme.
      2. Textura plana: casi sin gradiente moderado (foto muy comprimida o foto impresa).
    """
    mean_b = float(np.mean(roi_gray))
    std_b  = float(np.std(roi_gray))

    # Pantalla con mucho brillo y poca varianza → screen glow típico
    if mean_b > _SPOOF_BRIGHT_MEAN and std_b < _SPOOF_BRIGHT_STD:
        return True

    # Imagen demasiado plana: fracción de gradiente moderado muy baja
    lap_abs  = np.abs(cv2.Laplacian(roi_gray.astype(np.float32), cv2.CV_32F))
    mod_frac = float(np.sum((lap_abs > 5) & (lap_abs <= 50))) / float(lap_abs.size)
    if mod_frac < _SPOOF_MOD_FRAC_MIN:
        return True

    return False


# ── Blur de región ocular (tolerancia a lentes) ───────────────────────────────

def _apply_eye_blur(img: np.ndarray) -> np.ndarray:
    """
    Difumina la banda ocular antes de LBPH para que el reconocimiento
    sea tolerante a cambios por lentes. Se aplica en entrenamiento y predicción.
    """
    h, w = img.shape
    y1 = int(h * 0.25)
    y2 = int(h * 0.58)
    result = img.copy()
    result[y1:y2, :] = cv2.GaussianBlur(img[y1:y2, :], (15, 15), 7)
    return result


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

    CAPTURE_TARGET = 12   # LBPH no mejora significativamente con más de 12 imágenes similares

    _ANCHOR_RADIUS   = 200
    _ANCHOR_MAX_MISS = 20

    # Liveness anti-spoofing — dos criterios independientes:
    #   event: un solo frame con diff alto (parpadeo, respiración, micro-movimiento)
    #   mean:  movimiento moderado sostenido
    # Foto quieta: diffs ~0.5-2  → no pasa ningún criterio
    # Persona real en baja luz: spikes 3-8 → pasa por event o mean
    _LIVENESS_BUF_SIZE        = 6    # era 8 — buffer más chico = detección más rápida
    _LIVENESS_EVENT_THRESHOLD = 4.0  # era 5.5 — más sensible a micro-movimientos
    _LIVENESS_MIN_MOTION      = 2.0  # era 3.5 — umbral más bajo para baja luz

    def __init__(self, mode, face_uid="", labels=None,
                 detect_roi=None, recog_threshold=None):
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

        # Umbral LBPH fijo (distancia: menor = más parecido).
        # dist ~35-65 → misma persona en condición normal
        # dist ~65-80 → misma persona con variación de luz o ángulo
        # dist > 85   → persona diferente
        # 76 es el punto medio: acepta variaciones naturales, rechaza impostores.
        self._recog_threshold      = 76
        self._recog_min_frames     = 2
        self._recog_fast_threshold = 55   # match casi idéntico → 1 frame

        if isinstance(recog_threshold, (int, float)):
            self._recog_threshold = float(recog_threshold)

    def _open_cv_capture(self):
        self.cap = _get_cv_cap()

    def _switch_to_cv_fallback(self):
        self.use_picamera2 = False
        CamThread._disable_picamera2 = True
        self.cap = _get_cv_cap()

    def stop(self):
        self._manual_stop = True
        self._active = False
        self.wait(3000)

    def run(self):
        capture_count       = 0
        recognized_uid      = ""
        read_failed         = False
        consecutive_fails   = 0
        capture_consecutive = 0   # frames consecutivos con cara válida (CAPTURE)

        face_anchor         = None
        anchor_misses       = 0
        recog_last_label    = None
        recog_confirm_count = 0
        liveness_buf: list  = []
        no_eye_streak       = 0   # frames consecutivos sin ojos detectados (CAPTURE)

        # ── Inicializar cámara ────────────────────────────────────────────
        if self.use_picamera2:
            picam = _get_picam()
            if picam is None:
                self._switch_to_cv_fallback()
        else:
            picam = None

        if not self.use_picamera2:
            self.cap = _get_cv_cap()
            _flush_cv_cap(self.cap)

        if not self.use_picamera2 and (not self.cap or not self.cap.isOpened()):
            print("[Camera] No se pudo obtener instancia de cámara")
            if self.mode == self.CAPTURE:
                self.cap_done.emit(False, self.CAMERA_ERROR)
            else:
                self.rec_done.emit(self.CAMERA_ERROR)
            return

        fc         = cv2.CascadeClassifier(CASCADE)
        sdir       = face_dir_for(self.face_uid) if self.mode == self.CAPTURE else None
        clahe_norm = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
        clahe_dark = cv2.createCLAHE(clipLimit=5.5, tileGridSize=(8, 8))

        if sdir:
            os.makedirs(sdir, exist_ok=True)

        while self._active:
            # ── Lectura del frame ─────────────────────────────────────────
            if self.use_picamera2:
                try:
                    frame = picam.capture_array()
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    consecutive_fails = 0
                except Exception as e:
                    print(f"[Camera] Error leyendo Picamera2: {e}")
                    self._switch_to_cv_fallback()
                    if not self.cap or not self.cap.isOpened():
                        read_failed = True; break
                    ok, frame = _safe_read(self.cap)
                    if not ok:
                        consecutive_fails += 1
                        if consecutive_fails >= 10:
                            read_failed = True; break
                        continue
                    consecutive_fails = 0
            else:
                ok, frame = _safe_read(self.cap)
                if not ok:
                    consecutive_fails += 1
                    if consecutive_fails >= 10:
                        # 10 fallos consecutivos → cámara desconectada
                        read_failed = True; break
                    time.sleep(0.03)
                    continue
                consecutive_fails = 0

            frame = cv2.flip(frame, 1)
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # ── Gamma adaptativo ──────────────────────────────────────────
            mean_brightness = float(np.mean(gray))
            if mean_brightness < 35:
                gray_enh = cv2.LUT(clahe_dark.apply(gray), _gamma_lut(0.40))
            elif mean_brightness < 60:
                gray_enh = cv2.LUT(clahe_dark.apply(gray), _gamma_lut(0.50))
            elif mean_brightness < 95:
                gray_enh = cv2.LUT(clahe_norm.apply(gray), _gamma_lut(0.68))
            elif mean_brightness < 130:
                gray_enh = cv2.LUT(clahe_norm.apply(gray), _gamma_lut(0.82))
            else:
                gray_enh = clahe_norm.apply(gray)

            h_img, w_img = frame.shape[:2]

            # ── ROI de detección ──────────────────────────────────────────
            if self.detect_roi:
                xf, yf, wf, hf = self.detect_roi
                rx1 = max(0, int(xf * w_img));  ry1 = max(0, int(yf * h_img))
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

            # ── Detección de rostros (Haar cascade) ───────────────────────
            if self.mode == self.CAPTURE:
                _min_neighbors = 5
                _min_size      = (80, 80)
            else:
                _min_neighbors = 4 if mean_brightness < 55 else 5
                _min_size      = (70, 70) if mean_brightness < 55 else (80, 80)
            casc_raw = fc.detectMultiScale(
                det_gray, scaleFactor=1.1, minNeighbors=_min_neighbors,
                minSize=_min_size, flags=cv2.CASCADE_SCALE_IMAGE
            )
            raw_faces = []
            if len(casc_raw):
                raw_faces = [(int(x)+off_x, int(y)+off_y, int(w), int(h))
                             for x, y, w, h in casc_raw]

            # ── Validación geométrica + textura + color ───────────────────
            faces = [
                f for f in raw_faces
                if _is_valid_face(f[0], f[1], f[2], f[3],
                                  w_img, h_img, gray_enh, frame)
            ]

            # Ordenar por área: la más grande = más cercana a la cámara
            faces.sort(key=lambda f: f[2] * f[3], reverse=True)

            # ── Múltiples rostros ─────────────────────────────────────────
            if len(faces) > 1:
                primary = faces[0]
                for f in faces[1:]:
                    cv2.rectangle(frame, (f[0], f[1]),
                                  (f[0]+f[2], f[1]+f[3]), (0, 140, 255), 2)

                if self.mode == self.CAPTURE:
                    cx_p = primary[0] + primary[2] // 2
                    cy_p = primary[1] + primary[3] // 2
                    if face_anchor is None:
                        face_anchor = (cx_p, cy_p)
                    dist = math.hypot(cx_p - face_anchor[0], cy_p - face_anchor[1])
                    color = (0, 220, 0) if dist <= self._ANCHOR_RADIUS else (0, 140, 255)
                    cv2.rectangle(frame, (primary[0], primary[1]),
                                  (primary[0]+primary[2], primary[1]+primary[3]),
                                  color, 3)
                    if color == (0, 220, 0):
                        cv2.putText(frame, "TU REGISTRO",
                                    (primary[0], primary[1] - 8),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
                    txt = "Pide a los demas que se aparten"
                    (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.60, 2)
                    tx = max(0, (w_img - tw) // 2); ty = 34
                    cv2.rectangle(frame, (tx-6, ty-th-6), (tx+tw+6, ty+6), (0,0,0), -1)
                    cv2.putText(frame, txt, (tx, ty),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 200, 0), 2)
                    anchor_misses += 1
                    if anchor_misses >= self._ANCHOR_MAX_MISS:
                        face_anchor = None; anchor_misses = 0
                    recog_last_label    = None
                    recog_confirm_count = 0
                    capture_consecutive = 0
                    liveness_buf.clear()
                    self._emit_frame(frame)
                    continue
                else:
                    # RECOGNIZE: usar la cara más cercana, marcarla en verde
                    cv2.rectangle(frame, (primary[0], primary[1]),
                                  (primary[0]+primary[2], primary[1]+primary[3]),
                                  (0, 220, 0), 3)
                    cv2.putText(frame, "ESCANEANDO",
                                (primary[0], primary[1] - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2)
                    faces = [primary]

            # ── Sin rostros ───────────────────────────────────────────────
            if not faces:
                anchor_misses += 1
                if anchor_misses >= self._ANCHOR_MAX_MISS:
                    face_anchor = None; anchor_misses = 0
                recog_last_label    = None
                recog_confirm_count = 0
                capture_consecutive = 0
                liveness_buf.clear()
                self._emit_frame(frame)
                continue

            # ── Una cara válida ───────────────────────────────────────────
            (x, y, fw, fh) = faces[0]

            # Ancla de posición (solo CAPTURE)
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
                        capture_consecutive = 0
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

            roi_raw = cv2.resize(gray_enh[y:y+fh, x:x+fw], (IMG_W, IMG_H))
            roi     = _apply_eye_blur(roi_raw)

            # ── Anti-spoofing liveness (solo RECOGNIZE) ───────────────────
            if self.mode == self.RECOGNIZE:
                roi_f = roi.astype(np.float32)
                liveness_buf.append(roi_f)
                if len(liveness_buf) > self._LIVENESS_BUF_SIZE:
                    liveness_buf.pop(0)
                if len(liveness_buf) >= self._LIVENESS_BUF_SIZE:
                    diffs = [
                        float(np.mean(np.abs(liveness_buf[i] - liveness_buf[i-1])))
                        for i in range(1, len(liveness_buf))
                    ]
                    # Criterio 1: evento de movimiento real en un solo frame
                    # (respiración, parpadeo, pequeño giro de cabeza → spike > 5.5)
                    has_event = any(d >= self._LIVENESS_EVENT_THRESHOLD for d in diffs)
                    # Criterio 2: movimiento moderado sostenido durante la ventana
                    mean_ok   = float(np.mean(diffs)) >= self._LIVENESS_MIN_MOTION
                    if not (has_event or mean_ok):
                        self._emit_frame(frame)
                        continue
            else:
                liveness_buf.clear()

            # ── CAPTURE ───────────────────────────────────────────────────
            if self.mode == self.CAPTURE:
                # Imagen plana / pantalla → rechazar de inmediato
                if _is_spoof_roi(roi_raw):
                    capture_consecutive = 0
                    no_eye_streak = 0
                    cv2.rectangle(frame, (x, y), (x+fw, y+fh), (0, 80, 220), 2)
                    self._emit_frame(frame)
                    continue

                # Chequeo de ojos con racha: solo bloqueamos si 4 frames
                # consecutivos no tienen ojos. Frames aislados sin detección
                # (ángulo, lentes, parpadeo) no interrumpen el registro.
                face_crop_gray = gray_enh[y:y+fh, x:x+fw]
                if _has_eyes(face_crop_gray):
                    no_eye_streak = 0
                else:
                    no_eye_streak += 1
                    if no_eye_streak >= 4:
                        capture_consecutive = 0
                        cv2.rectangle(frame, (x, y), (x+fw, y+fh), (0, 80, 220), 2)
                        self._emit_frame(frame)
                        continue

                capture_consecutive += 1
                cv2.rectangle(frame, (x, y), (x+fw, y+fh), (0, 220, 0), 2)
                # 3 frames consecutivos requeridos antes de guardar cada foto
                if capture_consecutive >= 3:
                    cv2.imwrite(os.path.join(sdir, f"{capture_count}.png"), roi)
                    capture_count += 1
                    self.progress.emit(capture_count)
                    if capture_count >= self.CAPTURE_TARGET:
                        self._active = False
                cv2.putText(frame, f"{capture_count}/{self.CAPTURE_TARGET}",
                            (x, y-8), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (80, 180, 255), 2)

            # ── RECOGNIZE ─────────────────────────────────────────────────
            elif self.mode == self.RECOGNIZE:
                # Anti-spoofing: rechazar pantallas de teléfono y fotos planas
                if _is_spoof_roi(roi_raw):
                    recog_last_label    = None
                    recog_confirm_count = 0
                    liveness_buf.clear()
                    self._emit_frame(frame)
                    continue
                try:
                    lbl_idx, conf = face_model.predict(roi)
                    uid_str = self.labels.get(lbl_idx, f"label_{lbl_idx}")
                    print(
                        f"[RECONOCIMIENTO] dist={conf:.1f}  umbral={self._recog_threshold}"
                        f"  fast={self._recog_fast_threshold}"
                        f"  uid={uid_str}"
                        f"  {'✓ PASA' if conf < self._recog_threshold else '✗ RECHAZA'}"
                    )
                    if conf < self._recog_fast_threshold and lbl_idx in self.labels:
                        needed = 1
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

                    pct = int(recog_confirm_count / needed * 100)
                    cv2.rectangle(frame, (x, y), (x+fw, y+fh), (0, 220, 0), 2)
                    cv2.putText(frame, f"Verificando {min(pct,100)}%",
                                (x, y-8), cv2.FONT_HERSHEY_SIMPLEX,
                                0.6, (80, 180, 255), 2)
                    if recog_confirm_count >= needed:
                        print(
                            f"[RECONOCIMIENTO] *** CONFIRMADO uid={uid_str}"
                            f"  dist_final={conf:.1f}  frames={recog_confirm_count} ***"
                        )
                        recognized_uid = self.labels[lbl_idx]
                        self._active   = False

                except Exception:
                    recog_last_label    = None
                    recog_confirm_count = 0

            self._emit_frame(frame)

        # ── Fin del loop — liberar solo la referencia, NO el singleton ────
        self.cap = None

        if 'mp_face' in dir() and mp_face is not None:
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
        img_qt = QImage(frame.data, w, h, ch * w, QImage.Format_BGR888)
        self.frame_sig.emit(img_qt)