import datetime
import os

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QFrame, QSizePolicy, QLabel)

from biometria.biometria import delete_face_data, train_model, face_dir_for
from db.connection import connectionDB
from db.models.intentos_acceso import db_log_intento
from db.models.lockers import db_set_locker_estado, db_next_free_locker
from db.models.sesiones import db_create_sesion, db_get_active_sesion_by_face
from utils.camera import CamThread
from utils.gpio_locker import abrir_locker, beep_start_scan, beep_success, beep_error
from utils.helpers import db_get_locker_num_by_id
from views.style.widgets.widgets import lbl, sep_line, CamWidget
from utils.i18n import tr, get_language
from utils.ui_touch import touch_height


class ScanLine(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(4)
        self.hide()
        self._y = 0
        self._anim_down = QPropertyAnimation(self, b"scan_y", self)
        self._anim_down.setEasingCurve(QEasingCurve.Linear)
        self._anim_down.finished.connect(self._go_up)
        self._anim_up = QPropertyAnimation(self, b"scan_y", self)
        self._anim_up.setEasingCurve(QEasingCurve.Linear)
        self._anim_up.finished.connect(self._go_down)
        self._top = self._bot = self._width = self._x = 0
        self._speed_ms = 1800

    def _get_y(self): return self._y
    def _set_y(self, v):
        self._y = v
        self.move(self._x, v)
        self.update()
    scan_y = pyqtProperty(int, _get_y, _set_y)

    def update_bounds(self, fx, fy, fw, fh):
        m = 3
        self._x, self._top = fx + m, fy + m
        self._bot = fy + fh - m - self.height()
        self._width = fw - m * 2
        self.setGeometry(self._x, self._top, self._width, self.height())
        self.show()
        self._anim_down.stop(); self._anim_up.stop()
        self._go_down()

    def _go_down(self):
        self._anim_down.setStartValue(self._top)
        self._anim_down.setEndValue(self._bot)
        self._anim_down.setDuration(self._speed_ms)
        self._anim_down.start()

    def _go_up(self):
        self._anim_up.setStartValue(self._bot)
        self._anim_up.setEndValue(self._top)
        self._anim_up.setDuration(self._speed_ms)
        self._anim_up.start()

    def paintEvent(self, _):
        from PyQt5.QtGui import QPainter, QLinearGradient, QBrush
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0.0, QColor(10, 20, 45))
        bg.setColorAt(1.0, QColor(16, 32, 68))
        p.fillRect(0, 0, self.width(), self.height(), QBrush(bg))
        p.end()


# ─── Paleta (mismos tokens que home.py) ─────────────────────────────────────
BG_TOP       = QColor(10,  20,  45)
BG_BOT       = QColor(16,  32,  68)
ACCENT_BLUE  = QColor(41, 128, 255)
ACCENT_GREEN = QColor(185, 234, 137)   # verde del scan — funcional, se conserva
CARD_BG      = QColor(20,  38,  78)
CARD_BORDER  = QColor(40,  70, 140)
TEXT_PRIMARY = QColor(220, 235, 255)
TEXT_MUTED   = QColor(110, 140, 190)

STYLE = """
/* ── Base ────────────────────────────────────────────────────────────── */
QWidget#guardar_page { background: transparent; color: #dceaff; }

/* ── Tipografía ───────────────────────────────────────────────────────── */
QLabel#h2 {
    color: #dceaff;
    font-size: 16px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#tag {
    color: rgba(110,140,190,0.90);
    font-size: 12px; font-weight: 700;
    font-family: 'Courier New'; letter-spacing: 2px;
}
QLabel#body  { color: #b0c8f0; font-size: 13px; font-family: 'Segoe UI', sans-serif; }
QLabel#small { color: #6e8cbe; font-size: 10px; font-family: 'Courier New'; }
QLabel#err   {
    color: #ff6b6b;
    font-size: 12px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}

/* ── Separadores ──────────────────────────────────────────────────────── */
QFrame#sep {
    background: rgba(41,128,255,0.25);
    min-height: 1px; max-height: 1px; border: none;
}

/* ── Cards ────────────────────────────────────────────────────────────── */
QFrame#card {
    background: rgba(20,38,78,0.92);
    border: 1.5px solid rgba(40,70,140,0.80);
    border-radius: 16px;
}
QFrame#cam_card {
    background: rgba(14,26,58,0.95);
    border: 1.5px solid rgba(41,128,255,0.40);
    border-radius: 16px;
}

/* ── Cámara ───────────────────────────────────────────────────────────── */
QLabel#cam {
    background: #050a1a;
    border: 3px solid rgba(185, 234, 137, 0.6);
    border-radius: 12px;
}

/* ── Barra de progreso ───────────────────────────────────────────────── */
QFrame#prog_bg {
    background: rgba(10,20,50,0.80);
    border-radius: 4px; min-height: 7px; max-height: 7px;
}
QFrame#prog_fill {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #2980ff, stop:1 #B9EA89);
    border-radius: 4px; min-height: 7px; max-height: 7px;
}

/* ── Botones principales ─────────────────────────────────────────────── */
QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(20,50,120,0.95),
        stop:0.5 rgba(41,128,255,0.90),
        stop:1 rgba(80,140,240,0.90));
    color: #ffffff;
    border: 1.5px solid rgba(41,128,255,0.55);
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 14px; font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 0px;
}
QPushButton#btn_blue:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(30,70,160,0.98),
        stop:0.5 rgba(60,148,255,0.98),
        stop:1 rgba(100,160,255,0.98));
    border-color: rgba(41,128,255,0.95);
}
QPushButton#btn_blue:pressed {
    background: rgba(20,38,78,0.95);
}
QPushButton#btn_blue:disabled {
    background: rgba(20,38,78,0.60);
    color: rgba(110,140,190,0.55);
    border-color: rgba(40,70,140,0.30);
}

/* ── Botones secundarios ─────────────────────────────────────────────── */
QPushButton#btn_sm {
    background: rgba(20,38,78,0.80);
    color: #b0c8f0;
    border: 1.5px solid rgba(41,128,255,0.40);
    border-radius: 10px;
    padding: 10px 16px; margin-bottom: 6px;
    font-size: 14px; font-family: 'Segoe UI', sans-serif; font-weight: 700;
    min-height: 48px; min-width: 120px;
}
QPushButton#btn_sm:hover {
    background: rgba(26,48,96,0.95);
    border-color: rgba(41,128,255,0.80);
    color: #dceaff;
}
QPushButton#btn_sm:pressed {
    background: rgba(14,26,58,0.95);
}

/* ── Carousel ────────────────────────────────────────────────────────── */
QFrame#carousel_inner {
    background: rgba(12,22,50,0.70);
    border: 1px solid rgba(40,70,140,0.50);
    border-radius: 10px;
}
QLabel#carousel_text {
    color: #b0c8f0;
    font-size: 12px; font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#dot_inactive {
    background: transparent;
    border: 2px solid rgba(41,128,255,0.35);
    border-radius: 3px;
    min-width: 7px; max-width: 7px;
    min-height: 7px; max-height: 7px;
}
QPushButton#dot_inactive:hover {
    background: rgba(41,128,255,0.25);
    border-color: rgba(41,128,255,0.80);
}
QPushButton#dot_active {
    background: #2980ff;
    border: 2px solid rgba(41,128,255,0.80);
    border-radius: 4px;
    min-width: 9px; max-width: 9px;
    min-height: 9px; max-height: 9px;
}
"""

_CAM_ICON_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
     fill="none" stroke="white" stroke-width="2"
     stroke-linecap="round" stroke-linejoin="round">
  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8
           a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
  <circle cx="12" cy="13" r="4"/>
</svg>"""


def _svg_to_icon(svg_bytes: bytes, size: int = 15) -> QIcon:
    renderer = QSvgRenderer(svg_bytes)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


CAROUSEL_STEPS = [
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#e6f1fb"/>
        <path d="M12 40 Q40 14 68 40 Q40 66 12 40 Z"
              stroke="#185FA5" stroke-width="3" fill="#dceeff" stroke-linejoin="round"/>
        <circle cx="40" cy="40" r="11" stroke="#185FA5" stroke-width="3" fill="white"/>
        <circle cx="40" cy="40" r="4" fill="#185FA5"/>
     </svg>""", "Mira directo a la camara"),
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#EAF3DE"/>
        <rect x="14" y="14" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
        <rect x="44" y="14" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
        <rect x="14" y="44" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
        <rect x="44" y="44" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
     </svg>""", "Tu biometria facial es capturada"),
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#FAEEDA"/>
        <rect x="14" y="22" width="52" height="38" rx="7"
              stroke="#BA7517" stroke-width="3" fill="#fde8b8"/>
        <rect x="28" y="14" width="24" height="12" rx="4"
              stroke="#BA7517" stroke-width="2.5" fill="#fde8b8"/>
        <circle cx="40" cy="42" r="6" fill="#BA7517"/>
        <line x1="40" y1="48" x2="40" y2="54"
              stroke="#BA7517" stroke-width="3" stroke-linecap="round"/>
     </svg>""", "Se te asigna el siguiente locker libre"),
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#EEEDFE"/>
        <path d="M18 30h44l-7 30H25L18 30z"
              stroke="#534AB7" stroke-width="3" fill="#dddcfa" stroke-linejoin="round"/>
        <circle cx="31" cy="64" r="4.5" fill="#534AB7"/>
        <circle cx="53" cy="64" r="4.5" fill="#534AB7"/>
        <path d="M10 18h10l7 12" stroke="#534AB7" stroke-width="3"
              fill="none" stroke-linecap="round" stroke-linejoin="round"/>
     </svg>""", "Guarda tus cosas y disfruta comprando"),
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#FAECE7"/>
        <circle cx="40" cy="40" r="24" stroke="#993C1D" stroke-width="3" fill="#fcd5c5"/>
        <path d="M27 40l9 9 17-18"
              stroke="#993C1D" stroke-width="3.5" fill="none"
              stroke-linecap="round" stroke-linejoin="round"/>
     </svg>""", "Tus imagenes se borran al terminar"),
]


class CarouselWidget(QWidget):
    """Carousel sin QFrame propio — vive dentro del card azul del panel izquierdo."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 0
        self._dot_btns = []
        self._step_keys = [
            "guard.step1", "guard.step2", "guard.step3", "guard.step4", "guard.step5"
        ]

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.how_lbl = lbl("", "tag", Qt.AlignCenter)
        root.addWidget(self.how_lbl)

        # Card blanco interior — stretch=1 para llenar espacio disponible
        self._inner = QFrame()
        self._inner.setObjectName("carousel_inner")
        inner_l = QVBoxLayout(self._inner)
        inner_l.setContentsMargins(10, 10, 10, 10)
        inner_l.setSpacing(8)
        inner_l.setAlignment(Qt.AlignCenter)

        self._svg = QSvgWidget()
        self._svg.setFixedSize(56, 56)
        self._svg.setStyleSheet("background: transparent;")
        inner_l.addWidget(self._svg, alignment=Qt.AlignCenter)

        self._text_lbl = QLabel()
        self._text_lbl.setObjectName("carousel_text")
        self._text_lbl.setAlignment(Qt.AlignCenter)
        self._text_lbl.setWordWrap(True)
        inner_l.addWidget(self._text_lbl)

        root.addWidget(self._inner, 1)   # rellena el espacio

        dots_row = QHBoxLayout()
        dots_row.setSpacing(6)
        dots_row.setAlignment(Qt.AlignCenter)
        for i in range(len(CAROUSEL_STEPS)):
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._go_to(idx))
            dots_row.addWidget(btn)
            self._dot_btns.append(btn)
        root.addLayout(dots_row)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next)
        self._timer.start(2800)
        self._render(0)
        self.set_language(get_language())

    def set_language(self, _lang: str):
        self.how_lbl.setText(tr("guard.how"))
        self._render(self._current)

    def _render(self, idx):
        self._current = idx
        svg_data, _ = CAROUSEL_STEPS[idx]
        self._svg.load(svg_data)
        self._text_lbl.setText(tr(self._step_keys[idx]))
        for i, btn in enumerate(self._dot_btns):
            btn.setObjectName("dot_active" if i == idx else "dot_inactive")
            btn.setStyle(btn.style())

    def _next(self):
        self._render((self._current + 1) % len(CAROUSEL_STEPS))

    def _go_to(self, idx):
        self._timer.stop()
        self._render(idx)
        self._timer.start(2800)


# ── Proporciones del marco de escaneo ────────────────────────────────────────
# FIX #2: marco más grande (0.62 ancho, 0.90 alto) → el usuario cabe mejor
#          y la detección se acota a exactamente esta zona.
_FRAME_W_FRAC = 0.62
_FRAME_H_FRAC = 0.90
_FRAME_X_FRAC = (1.0 - _FRAME_W_FRAC) / 2.0   # ≈ 0.19 — margen izquierdo
_FRAME_Y_FRAC = (1.0 - _FRAME_H_FRAC) / 2.0   # ≈ 0.05 — margen superior

# detect_roi que se pasa a CamThread: coincide con el marco visual
_DETECT_ROI = (_FRAME_X_FRAC, _FRAME_Y_FRAC, _FRAME_W_FRAC, _FRAME_H_FRAC)
# ─────────────────────────────────────────────────────────────────────────────


class GuardarPage(QWidget):
    done    = pyqtSignal(str, str, int)
    failed  = pyqtSignal(str)
    go_back = pyqtSignal()

    _CAM_W = 440
    _CAM_H = 390
    # Tiempo máximo (ms) para la fase de pre-verificación (reconocimiento previo).
    # Si en este tiempo no se detecta ninguna cara conocida, se pasa a captura.
    _PRECHECK_TIMEOUT_MS = 6000

    def __init__(self):
        super().__init__()
        self.setObjectName("guardar_page")
        self.setStyleSheet(STYLE)
        self.cam_thread = None
        self._face_uid        = None
        self._id_locker       = None
        self._num_locker      = None   # FIX #5: guardamos num para no re-consultar
        self._capture_started = False  # FIX #6: evita doble disparo del auto-inicio
        self._phase           = None   # 'precheck' | 'capture'

        # Timer de seguridad para la fase de pre-verificación.
        # Si la cámara no detecta ninguna cara conocida en _PRECHECK_TIMEOUT_MS,
        # se pasa automáticamente a la fase de captura.
        self._pre_check_timer = QTimer(self)
        self._pre_check_timer.setSingleShot(True)
        self._pre_check_timer.timeout.connect(self._on_precheck_timeout)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 6)
        root.setSpacing(4)

        # Header
        hdr = QHBoxLayout(); hdr.setSpacing(6)
        self.back_btn = QPushButton("")
        back = self.back_btn
        back.setObjectName("btn_sm")
        back.setFixedHeight(touch_height(48))
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self._cancel)
        htxt = QVBoxLayout(); htxt.setSpacing(0)
        self.title_lbl    = lbl("", "h2")
        self.subtitle_lbl = lbl("", "tag")
        htxt.addWidget(self.title_lbl)
        htxt.addWidget(self.subtitle_lbl)
        hdr.addWidget(back); hdr.addSpacing(6); hdr.addLayout(htxt); hdr.addStretch()
        root.addLayout(hdr)
        root.addWidget(sep_line())

        # Body
        body = QHBoxLayout(); body.setSpacing(8)
        body.setContentsMargins(6, 4, 6, 4)

        # Panel izquierdo — ancho fijo para dejar espacio a la camara
        left = QFrame(); left.setObjectName("card")
        left.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        left.setFixedWidth(300)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 10, 12, 10)
        ll.setSpacing(10)

        self._carousel = CarouselWidget()
        ll.addWidget(self._carousel, 1)

        # FIX #6: el botón queda como "REINTENTAR" después del primer auto-inicio.
        #         setFocusPolicy(NoFocus) elimina el doble-tap en pantallas táctiles.
        self.start_btn = QPushButton("INICIAR ESCANEO")
        self.start_btn.setObjectName("btn_blue")
        self.start_btn.setIcon(_svg_to_icon(_CAM_ICON_SVG, 20))
        self.start_btn.setIconSize(QSize(20, 20))
        self.start_btn.setFixedHeight(touch_height(72))
        self.start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setFocusPolicy(Qt.NoFocus)   # evita doble-tap en touch
        self.start_btn.clicked.connect(self._start_capture)
        ll.addWidget(self.start_btn)

        self.err_lbl = lbl("", "err")
        self.err_lbl.setWordWrap(True)
        self.err_lbl.setFixedHeight(28)
        ll.addWidget(self.err_lbl)

        body.addWidget(left)

        # Panel derecho — camara
        right = QFrame(); right.setObjectName("cam_card")
        right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 6, 6, 6); rl.setSpacing(4)
        self.scan_title_lbl = lbl("", "tag", Qt.AlignCenter)
        rl.addWidget(self.scan_title_lbl, 0)

        self.cam = CamWidget(self._CAM_W, self._CAM_H)
        self.cam.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rl.addWidget(self.cam, 1)

        body.addWidget(right, 1)
        root.addLayout(body, 1)

        # Overlays (hijos de self.cam — coordenadas relativas al widget de video)
        self.face_guide = QSvgWidget(self.cam)
        self.face_guide.load(b"""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120">
              <circle cx="50" cy="38" r="26"
                      fill="none" stroke="#B9EA89" stroke-width="2.5"
                      stroke-dasharray="6 4" opacity="0.85"/>
              <path d="M4 120 Q4 78 50 78 Q96 78 96 120 Z"
                    fill="none" stroke="#B9EA89" stroke-width="2.5"
                    stroke-dasharray="6 4" opacity="0.85"/>
              <line x1="50" y1="32" x2="50" y2="44"
                    stroke="#B9EA89" stroke-width="1.5" opacity="0.6"/>
              <line x1="44" y1="38" x2="56" y2="38"
                    stroke="#B9EA89" stroke-width="1.5" opacity="0.6"/>
            </svg>""")
        self.face_guide.setStyleSheet("background: transparent;")
        self.face_guide.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.face_guide.setVisible(False)

        self.scan_frame = QFrame(self.cam)
        self.scan_frame.setStyleSheet(
            "border: 3px solid #B9EA89; border-radius: 8px; background: transparent;")
        self.scan_frame.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.scan_frame.setVisible(False)

        self.scan_line = ScanLine(self.cam)
        self.set_language(get_language())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0.0, BG_TOP)
        bg.setColorAt(1.0, BG_BOT)
        p.fillRect(0, 0, W, H, bg)

        hh = 96
        hg = QLinearGradient(0, 0, 0, hh)
        hg.setColorAt(0.0, QColor(13, 24, 54))
        hg.setColorAt(1.0, QColor(10, 20, 45))
        p.setPen(Qt.NoPen)
        p.setBrush(hg)
        p.drawRect(0, 0, W, hh)

        p.setPen(QColor(41, 128, 255, 140))
        p.drawLine(0, hh - 1, W, hh - 1)

        p.setPen(QColor(40, 70, 140, 28))
        step = 48
        for x in range(0, W + step, step):
            p.drawLine(x, hh, x, H)
        for y in range(hh, H + step, step):
            p.drawLine(0, y, W, y)

        p.end()

    def set_language(self, lang: str):
        self.back_btn.setText(tr("guard.back"))
        self.title_lbl.setText(tr("guard.title"))
        self.subtitle_lbl.setText(tr("guard.subtitle"))
        self.scan_title_lbl.setText(tr("guard.scan_title"))
        self.start_btn.setText(tr("guard.start"))
        self._carousel.set_language(lang)

    def showEvent(self, e):
        super().showEvent(e)
        self._capture_started = False   # reset al mostrar la página

        result = db_next_free_locker()
        if result:
            # FIX #5: guardar id Y num en un solo lugar → _on_capture_done
            #          no necesita volver a consultar la BD (evita doble asignación)
            self._id_locker, self._num_locker = result
            self.start_btn.setEnabled(True)
            self.err_lbl.setText("")

            # FIX #6: auto-arranque con 1 solo toque en la pantalla anterior.
            #          400 ms de margen para que la página termine de pintarse.
            QTimer.singleShot(400, self._auto_start)
        else:
            self._id_locker  = None
            self._num_locker = None
            self.err_lbl.setText(tr("guard.no_lockers_now"))
            self.start_btn.setEnabled(False)

    def _auto_start(self):
        """Dispara el escaneo automáticamente al entrar a la página."""
        if not self._capture_started and self._id_locker:
            self._start_capture()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_overlay)

    def _start_capture(self):
        # Guard contra doble disparo (auto + click manual simultáneo)
        if self._capture_started:
            return
        self._capture_started = True

        if not self._id_locker:
            self._capture_started = False
            self.err_lbl.setText(tr("guard.no_lockers"))
            beep_error()
            return

        self._stop_cam_thread()

        # Generar uid temporal para las fotos de esta sesión
        tmp_uid = "tmp_{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        self._face_uid = tmp_uid
        self.start_btn.setEnabled(False)
        self.err_lbl.setText("")
        self.scan_frame.setVisible(True)
        self.face_guide.setVisible(True)
        self._update_overlay()
        beep_start_scan()

        # ── FASE 1: Pre-verificación ──────────────────────────────────────
        # Antes de capturar fotos nuevas, intentar RECONOCER a la persona
        # contra el modelo actual.  Si se la encuentra con sesión activa →
        # ya tiene un locker asignado → bloquear y mostrar el número.
        # Si no se la reconoce (o no hay modelo) → pasar a Fase 2 (captura).
        labels = train_model()
        if labels:
            self._phase = "precheck"
            self.scan_title_lbl.setText(tr("guard.verifying"))  # "VERIFICANDO..."
            self._pre_check_timer.start(self._PRECHECK_TIMEOUT_MS)

            self.cam_thread = CamThread(
                CamThread.RECOGNIZE,
                labels=labels,
                detect_roi=_DETECT_ROI,
            )
            self.cam_thread.frame_sig.connect(self.cam.update_frame)
            self.cam_thread.rec_done.connect(self._on_precheck_done)
            self.cam_thread.finished.connect(self._on_cam_thread_finished)
            self.cam_thread.start()
        else:
            # No hay caras registradas → ir directo a captura
            self._start_phase2_capture()

    # ── Helpers de hilo ───────────────────────────────────────────────────────

    def _stop_cam_thread(self):
        """Detiene el hilo de cámara activo y espera a que termine."""
        if self.cam_thread:
            if self.cam_thread.isRunning():
                self.cam_thread.stop()
                if not self.cam_thread.wait(2000):
                    self.cam_thread.terminate()
                    self.cam_thread.wait(1000)
            self.cam_thread = None

    def _on_cam_thread_finished(self):
        sender = self.sender()
        if sender is self.cam_thread:
            self.cam_thread = None

    # ── Fase 1: Pre-verificación ──────────────────────────────────────────────

    def _on_precheck_timeout(self):
        """
        El timeout de pre-verificación se agotó sin detectar ninguna cara
        conocida → la persona es nueva → pasar a Fase 2 (captura).
        """
        self._stop_cam_thread()
        self._start_phase2_capture()

    def _on_precheck_done(self, face_uid: str):
        """
        Callback de la Fase 1 (RECOGNIZE).  Tres posibles resultados:
          - face_uid válido + sesión activa  → persona ya tiene locker → bloquear
          - face_uid válido + sin sesión     → persona registrada pero sin locker → capturar
          - face_uid vacío / CAMERA_ERROR   → no reconocido / error → capturar
        """
        self._pre_check_timer.stop()

        if face_uid and face_uid != CamThread.CAMERA_ERROR:
            sesion = db_get_active_sesion_by_face(face_uid)
            if sesion:
                # ── BLOQUEADO: ya tiene locker activo ────────────────────
                if isinstance(sesion, dict):
                    id_locker_e = sesion.get("ID_locker")
                else:
                    id_locker_e = sesion[1] if len(sesion) > 1 else None

                num_e = db_get_locker_num_by_id(id_locker_e) if id_locker_e else "?"

                beep_error()
                self._stop_cam_thread()
                self._capture_started = False
                self.scan_frame.setVisible(False)
                self.scan_line.hide()
                self.face_guide.setVisible(False)
                self.scan_title_lbl.setText(tr("guard.scan_title"))

                msg = tr("guard.already_has_locker").format(num=num_e)

                db_log_intento(
                    id_locker_e or 0, "registro_biometrico", "bloqueado",
                    "Persona ya tiene locker #{} activo. Se negó nuevo registro.".format(num_e)
                )

                self.failed.emit(msg)
                return

        # No reconocido o sin sesión activa → proceder a captura
        self._start_phase2_capture()

    # ── Fase 2: Captura de rostro ─────────────────────────────────────────────

    def _start_phase2_capture(self):
        """
        Inicia el hilo de captura (CAPTURE mode).
        Se llama cuando la Fase 1 confirma que la persona NO tiene locker activo.
        """
        self._phase = "capture"
        self._stop_cam_thread()   # asegurar que el hilo de precheck terminó
        self.scan_title_lbl.setText(tr("guard.scan_title"))

        self.cam_thread = CamThread(
            CamThread.CAPTURE,
            face_uid=self._face_uid,
            detect_roi=_DETECT_ROI,
        )
        self.cam_thread.frame_sig.connect(self.cam.update_frame)
        self.cam_thread.progress.connect(self.cam.set_progress)
        self.cam_thread.cap_done.connect(self._on_capture_done)
        self.cam_thread.finished.connect(self._on_cam_thread_finished)
        self.cam_thread.start()

    def _on_capture_thread_finished(self):
        # Mantenido por compatibilidad; la lógica real está en _on_cam_thread_finished
        self._on_cam_thread_finished()

    def _on_capture_done(self, ok, tmp_uid):
        self._capture_started = False   # permite reintentar si hay error
        self.start_btn.setEnabled(True)
        self.scan_frame.setVisible(False)
        self.scan_line.hide()
        self.face_guide.setVisible(False)

        if tmp_uid == CamThread.CAMERA_ERROR:
            beep_error()
            self.cam.set_status(tr("guard.cam_open_error"), "#bd0a0a")
            self.cam.idle()
            if self._id_locker:
                db_log_intento(self._id_locker, "registro_biometrico", "fallido",
                               "No se pudo abrir la camara en registro")
            self.err_lbl.setText(tr("guard.cam_open_error"))
            return

        if not ok:
            beep_error()
            self.cam.set_status(tr("guard.capture_error"), "#bd0a0a")
            self.cam.idle()
            delete_face_data(tmp_uid)
            if self._id_locker:
                db_log_intento(self._id_locker, "registro_biometrico", "fallido",
                               "Error durante la captura de imagenes")
            self.err_lbl.setText(tr("guard.capture_error"))
            return

        beep_success()
        self.cam.set_status(tr("guard.face_ok"), "#B9EA89")
        QTimer.singleShot(850, self.cam.idle)

        # FIX #5: usar el locker ya asignado en showEvent (self._id_locker /
        #          self._num_locker) en lugar de volver a llamar db_next_free_locker().
        #          Esto evita que se asignen dos lockers distintos a la misma persona.
        if not self._id_locker or self._num_locker is None:
            delete_face_data(tmp_uid)
            self.failed.emit(tr("guard.no_lockers"))
            return

        id_locker  = self._id_locker
        num_locker = self._num_locker

        id_sesion = db_create_sesion(id_locker, tmp_uid)
        face_uid  = "sesion_{}".format(id_sesion)
        old_dir   = face_dir_for(tmp_uid)
        new_dir   = face_dir_for(face_uid)
        if os.path.exists(old_dir):
            os.rename(old_dir, new_dir)
        with connectionDB() as con:
            con.execute(
                "UPDATE Sesiones SET b_vector_biometrico_temp=? WHERE ID_sesion=?",
                (face_uid.encode("utf-8"), id_sesion)
            )
        db_set_locker_estado(id_locker, "ocupado")

        # Abrir cerradura solenoide del locker asignado
        abrir_locker(str(num_locker))

        db_log_intento(id_locker, "registro_biometrico", "exitoso",
                       "Sesion {} creada. Locker #{} asignado.".format(id_sesion, num_locker),
                       id_sesion=id_sesion)

        # train_model en background para no bloquear la apertura de la cerradura
        import threading
        threading.Thread(target=train_model, daemon=True).start()

        # Limpiar referencia al locker para que no pueda reasignarse
        self._id_locker  = None
        self._num_locker = None

        self.done.emit(face_uid, num_locker, id_sesion)

    def _cancel(self):
        self._pre_check_timer.stop()
        self._stop_cam_thread()
        if self._face_uid:
            delete_face_data(self._face_uid)
        self.go_back.emit()

    def reset(self):
        self._pre_check_timer.stop()
        self._stop_cam_thread()
        self._face_uid        = None
        self._id_locker       = None
        self._num_locker      = None
        self._capture_started = False
        self._phase           = None
        self.err_lbl.setText("")
        self.cam.idle()
        self.start_btn.setEnabled(True)
        self.scan_frame.setVisible(False)
        self.scan_line.hide()
        self.face_guide.setVisible(False)

    def _update_overlay(self):
        cam_w = self.cam.width()
        cam_h = self.cam.height()

        # FIX #2: proporciones ampliadas — ahora usan las constantes globales
        #          (_FRAME_W_FRAC=0.62, _FRAME_H_FRAC=0.90) en lugar de 0.42/0.80.
        #          Estas mismas fracciones se pasan como detect_roi a CamThread,
        #          de modo que el área verde y la zona de detección siempre coinciden.
        frame_w = int(cam_w * _FRAME_W_FRAC)
        frame_h = int(cam_h * _FRAME_H_FRAC)
        frame_x = (cam_w - frame_w) // 2
        frame_y = (cam_h - frame_h) // 2

        self.scan_frame.setGeometry(frame_x, frame_y, frame_w, frame_h)
        self.face_guide.setGeometry(frame_x, frame_y, frame_w, frame_h)
        self.scan_line.update_bounds(frame_x, frame_y, frame_w, frame_h)