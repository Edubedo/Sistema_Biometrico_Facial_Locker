from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QFrame, QSizePolicy, QLabel, QMessageBox)

from biometria.biometria import train_model
from db.models.intentos_acceso import db_log_intento
from db.models.lockers import db_set_locker_estado
from db.models.sesiones import db_close_sesion, db_get_active_sesion_by_face
from utils.camera import CamThread
from utils.gpio_locker import abrir_locker
from utils.helpers import db_get_locker_num_by_id
from views.style.widgets.widgets import lbl, sep_line, CamWidget
from utils.i18n import tr, get_language


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

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0,  QColor(185, 234, 137, 0))
        grad.setColorAt(0.15, QColor(185, 234, 137, 220))
        grad.setColorAt(0.5,  QColor(185, 234, 137, 255))
        grad.setColorAt(0.85, QColor(185, 234, 137, 220))
        grad.setColorAt(1.0,  QColor(185, 234, 137, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(0, 0, w, h, h // 2, h // 2)
        p.end()


STYLE = """
QWidget#retirar_page { background: #e7e7e7; color: #1f2a44; }

QLabel#h2 {
    color: #305bab; font-size: 13px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#h3 {
    color: #305bab; font-size: 11px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#tag {
    color: #305bab; font-size: 10px; font-weight: 700;
    font-family: 'Courier New'; letter-spacing: 2px;
}
QLabel#body  { color: #2c3e50; font-size: 11px; font-family: 'Segoe UI', sans-serif; }
QLabel#small { color: #3a5f84; font-size: 9px; font-family: 'Courier New'; }
QLabel#ok    {
    color: #2a7c32; font-size: 10px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#err   {
    color: #BD0A0A; font-size: 10px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}

QFrame#sep      { background: #305bab; min-height: 1px; max-height: 1px; }
QFrame#card     { background: #c6dcff; border: 2px solid #305bab; border-radius: 10px; }
QFrame#cam_card { background: #c6dcff; border: 2px solid #305bab; border-radius: 10px; }

QLabel#cam {
    background: #0c1530; border: 3px solid #305bab; border-radius: 8px;
    color: #1a3a5c; font-family: 'Courier New'; font-size: 1px;
}
QFrame#prog_bg  { background: #0a1628; border-radius: 4px; min-height: 7px; max-height: 7px; }
QFrame#prog_fill {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #305bab, stop:1 #B9EA89);
    border-radius: 4px; min-height: 7px; max-height: 7px;
}

QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1a3a6b, stop:0.5 #305bab, stop:1 #678dd3);
    color: white; border: none; border-radius: 8px;
    padding: 13px 18px; font-size: 15px; font-weight: 800;
    font-family: 'Segoe UI', sans-serif; letter-spacing: 1px;
}
QPushButton#btn_blue:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #2952a3, stop:0.5 #3d6fd1, stop:1 #7aa3e8);
}
QPushButton#btn_blue:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1a3a6b, stop:0.5 #305bab, stop:1 #5681cf);
}
QPushButton#btn_blue:disabled {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #4a90d9, stop:1 #7ec8f5);
    color: rgba(0,0,0,120);
}

QPushButton#btn_sm {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #96bfe9, stop:1 #b8e1fa);
    color: #1d3767; border: 2px solid #305bab; border-radius: 5px;
    padding: 6px 14px; font-size: 13px; font-family: 'Segoe UI', sans-serif; font-weight: 700;
}
QPushButton#btn_sm:hover   { color: #305bab; border-color: #838383; }
QPushButton#btn_sm:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #95a49f, stop:0.5 #c1cac7, stop:1 #5681cf);
}

/* ── Acciones post-deteccion ── */
QFrame#actions_card {
    background: #d6e6ff; border: 2px solid #305bab; border-radius: 10px;
}
QPushButton#btn_action_red {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #a40909, stop:1 #d90b0b);
    color: #ffffff; border: none; border-radius: 8px;
    padding: 12px 14px; font-size: 14px; font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#btn_action_red:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #8e0909, stop:1 #be0a0a);
}
QPushButton#btn_action_red:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #770707, stop:1 #a40909);
}
QPushButton#btn_action_green {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #2a7c32, stop:1 #19a85b);
    color: #ffffff; border: none; border-radius: 8px;
    padding: 12px 14px; font-size: 14px; font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#btn_action_green:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #23692a, stop:1 #158f4d);
}
QPushButton#btn_action_green:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1e5b24, stop:1 #11753f);
}

/* ── Carousel ── */
QFrame#carousel_inner { background: white; border-radius: 8px; border: none; }
QLabel#carousel_text  {
    color: #000000; font-size: 10px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#dot_inactive {
    background: transparent; border: 2px solid #7aaad4; border-radius: 3px;
    min-width: 7px; max-width: 7px; min-height: 7px; max-height: 7px;
}
QPushButton#dot_inactive:hover { background: #c6dcff; border-color: #305bab; }
QPushButton#dot_active {
    background: #305bab; border: 2px solid #1a3a6b; border-radius: 4px;
    min-width: 9px; max-width: 9px; min-height: 9px; max-height: 9px;
}
"""

_CAM_ICON_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
     fill="none" stroke="white" stroke-width="2"
     stroke-linecap="round" stroke-linejoin="round">
  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8
           a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
  <circle cx="12" cy="13" r="4"/>
</svg>"""

_RETIRAR_ICON_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
     fill="none" stroke="white" stroke-width="2"
     stroke-linecap="round" stroke-linejoin="round">
    <path d="M6 6h12l-1 12H7L6 6z"/>
    <path d="M9 6V4h6v2"/>
    <line x1="10" y1="10" x2="10" y2="15"/>
    <line x1="14" y1="10" x2="14" y2="15"/>
</svg>"""

_SEGUIR_ICON_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
     fill="none" stroke="white" stroke-width="2"
     stroke-linecap="round" stroke-linejoin="round">
    <circle cx="11" cy="11" r="7"/>
    <line x1="16.5" y1="16.5" x2="22" y2="22"/>
    <line x1="11" y1="8" x2="11" y2="14"/>
    <line x1="8" y1="11" x2="14" y2="11"/>
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
     </svg>""", "Tu biometria facial es verificada"),
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#FAEEDA"/>
        <rect x="14" y="22" width="52" height="38" rx="7"
              stroke="#BA7517" stroke-width="3" fill="#fde8b8"/>
        <rect x="28" y="14" width="24" height="12" rx="4"
              stroke="#BA7517" stroke-width="2.5" fill="#fde8b8"/>
        <circle cx="40" cy="42" r="6" fill="#BA7517"/>
        <line x1="40" y1="48" x2="40" y2="54"
              stroke="#BA7517" stroke-width="3" stroke-linecap="round"/>
     </svg>""", "Se te muestra el locker asignado"),
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#EEEDFE"/>
        <path d="M18 30h44l-7 30H25L18 30z"
              stroke="#534AB7" stroke-width="3" fill="#dddcfa" stroke-linejoin="round"/>
        <circle cx="31" cy="64" r="4.5" fill="#534AB7"/>
        <circle cx="53" cy="64" r="4.5" fill="#534AB7"/>
        <path d="M10 18h10l7 12" stroke="#534AB7" stroke-width="3"
              fill="none" stroke-linecap="round" stroke-linejoin="round"/>
     </svg>""", "Elige: retirar tus cosas o seguir comprando"),
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#FAECE7"/>
        <circle cx="40" cy="40" r="24" stroke="#993C1D" stroke-width="3" fill="#fcd5c5"/>
        <path d="M27 40l9 9 17-18"
              stroke="#993C1D" stroke-width="3.5" fill="none"
              stroke-linecap="round" stroke-linejoin="round"/>
     </svg>""", "Tus imagenes se borran al terminar"),
]


class CarouselWidget(QWidget):
    """Carousel plano, sin QFrame propio — vive dentro del card azul del panel izquierdo."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = 0
        self._dot_btns = []
        self._step_keys = [
            "ret.step1", "ret.step2", "ret.step3", "ret.step4", "ret.step5"
        ]

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.how_lbl = lbl("", "tag", Qt.AlignCenter)
        root.addWidget(self.how_lbl)

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

        root.addWidget(self._inner, 1)   # stretch=1: rellena el espacio

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
        self.how_lbl.setText(tr("ret.how"))

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


class RetirarPage(QWidget):

    go_back      = pyqtSignal()
    retirar_done = pyqtSignal(str, str, int)
    seguir_done  = pyqtSignal(str, str, int)

    _CAM_W = 440
    _CAM_H = 340   # mas bajo que GuardarPage porque el panel derecho tambien tiene opts

    def __init__(self):
        super().__init__()
        self.setObjectName("retirar_page")
        self.setStyleSheet(STYLE)

        self.cam_thread  = None
        self._face_uid   = None
        self._id_sesion  = None
        self._id_locker  = None
        self._detected_msg = None
        self._closing_detected_msg = False
        self._detected_left = 0
        self._detected_timer = QTimer(self)
        self._detected_timer.setInterval(1000)
        self._detected_timer.timeout.connect(self._tick_detected_dialog)
        self._detected_force_close = QTimer(self)
        self._detected_force_close.setSingleShot(True)
        self._detected_force_close.timeout.connect(self._close_detected_dialog)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 6)
        root.setSpacing(4)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(8)
        self.back_btn = QPushButton("")
        back = self.back_btn
        back.setObjectName("btn_sm")
        back.setFixedHeight(46)
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self._cancel)
        htxt = QVBoxLayout(); htxt.setSpacing(0)
        self.title_lbl = lbl("", "h2")
        self.subtitle_lbl = lbl("", "tag")
        htxt.addWidget(self.title_lbl)
        htxt.addWidget(self.subtitle_lbl)
        hdr.addWidget(back); hdr.addSpacing(6); hdr.addLayout(htxt); hdr.addStretch()
        root.addLayout(hdr)
        root.addWidget(sep_line())

        # ── Body ──────────────────────────────────────────────────────────────
        body = QHBoxLayout(); body.setSpacing(8)

        # ── Panel izquierdo ───────────────────────────────────────────────────
        left = QFrame(); left.setObjectName("card")
        left.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        left.setFixedWidth(300)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 8, 10, 8)
        ll.setSpacing(6)

        self._carousel = CarouselWidget()
        ll.addWidget(self._carousel, 1)

        self.scan_btn = QPushButton("  INICIAR ESCANEO")
        self.scan_btn.setObjectName("btn_blue")
        self.scan_btn.setIcon(_svg_to_icon(_CAM_ICON_SVG, 24))
        self.scan_btn.setIconSize(QSize(24, 24))
        self.scan_btn.setFixedHeight(80)
        self.scan_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self._start_scan)
        ll.addWidget(self.scan_btn)

        self.scan_lbl = lbl("", "err")
        self.scan_lbl.setWordWrap(True)
        self.scan_lbl.setFixedHeight(28)
        ll.addWidget(self.scan_lbl)

        body.addWidget(left)

        # ── Panel derecho ─────────────────────────────────────────────────────
        right = QFrame(); right.setObjectName("cam_card")
        right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 6, 6, 6); rl.setSpacing(4)
        self.scan_title_lbl = lbl("", "tag", Qt.AlignCenter)
        rl.addWidget(self.scan_title_lbl)

        # ── Card de acciones post-deteccion ───────────────────────────────────
        self.opts = QFrame()
        self.opts.setObjectName("actions_card")
        ol = QVBoxLayout(self.opts)
        ol.setContentsMargins(10, 8, 10, 8)
        ol.setSpacing(6)

        self.id_lbl     = lbl("", "ok",  Qt.AlignCenter)
        self.locker_lbl = lbl("", "h3",  Qt.AlignCenter)
        ol.addWidget(self.id_lbl)
        ol.addWidget(self.locker_lbl)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        self.btn_retirar = QPushButton("RETIRAR Y SALIR")
        self.btn_retirar.setObjectName("btn_action_red")
        self.btn_retirar.setIcon(_svg_to_icon(_RETIRAR_ICON_SVG, 22))
        self.btn_retirar.setIconSize(QSize(22, 22))
        self.btn_retirar.setFixedHeight(62)
        self.btn_retirar.clicked.connect(self._do_retirar)

        self.btn_seguir = QPushButton("SEGUIR COMPRANDO")
        self.btn_seguir.setObjectName("btn_action_green")
        self.btn_seguir.setIcon(_svg_to_icon(_SEGUIR_ICON_SVG, 22))
        self.btn_seguir.setIconSize(QSize(22, 22))
        self.btn_seguir.setFixedHeight(62)
        self.btn_seguir.clicked.connect(self._do_seguir)

        btn_row.addWidget(self.btn_retirar, 1)
        btn_row.addWidget(self.btn_seguir, 1)
        ol.addLayout(btn_row)
        self.opts.setVisible(False)
        rl.addWidget(self.opts)

        # ── Widget de camara con altura maxima controlada ──────────────────
        self.cam = CamWidget(self._CAM_W, self._CAM_H)
        self.cam.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.cam.setMaximumHeight(self._CAM_H)
        rl.addWidget(self.cam, 1)

        body.addWidget(right, 1)
        root.addLayout(body, 1)

        # ── Overlays de camara ─────────────────────────────────────────────
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

    def set_language(self, lang: str):
        self.back_btn.setText(tr("ret.back"))
        self.title_lbl.setText(tr("ret.title"))
        self.subtitle_lbl.setText(tr("ret.subtitle"))
        self.scan_title_lbl.setText(tr("ret.scan_title"))
        self.scan_btn.setText(tr("ret.start"))
        self.btn_retirar.setText(tr("ret.btn_take"))
        self.btn_seguir.setText(tr("ret.btn_continue"))
        self._carousel.set_language(lang)
        self._carousel._render(self._carousel._current)
        self._carousel.set_language(lang)

    # ── Eventos ───────────────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_overlay)

    def _update_overlay(self):
        cam_w = self.cam.width()
        cam_h = self.cam.height()
        frame_w = int(cam_w * 0.42)
        frame_h = int(cam_h * 0.80)
        frame_x = (cam_w - frame_w) // 2
        frame_y = (cam_h - frame_h) // 2
        self.scan_frame.setGeometry(frame_x, frame_y, frame_w, frame_h)
        self.face_guide.setGeometry(frame_x, frame_y, frame_w, frame_h)
        self.scan_line.update_bounds(frame_x, frame_y, frame_w, frame_h)

    # ── Escaneo ───────────────────────────────────────────────────────────────

    def _start_scan(self):
        labels = train_model()
        if not labels:
            self.scan_lbl.setText(tr("ret.no_biometrics"))
            return
        if self.cam_thread:
            self.cam_thread.stop()
            self.cam_thread = None

        self.scan_frame.setVisible(True)
        self.face_guide.setVisible(True)
        self._update_overlay()
        self.scan_btn.setEnabled(False)
        self.opts.setVisible(False)
        self.scan_lbl.setText("")
        self.cam.set_status("Escaneando biometria...", "#000000")
        self.cam_thread = CamThread(CamThread.RECOGNIZE, labels=labels)
        self.cam_thread.frame_sig.connect(self.cam.update_frame)
        self.cam_thread.rec_done.connect(self._on_recognized)
        self.cam_thread.finished.connect(self._on_scan_thread_finished)
        self.cam_thread.start()

    def _on_scan_thread_finished(self):
        sender = self.sender()
        if sender is self.cam_thread:
            self.cam_thread = None

    def _on_recognized(self, face_uid):
        self.scan_btn.setEnabled(True)
        if face_uid == CamThread.CAMERA_ERROR:
            self.cam.idle()
            self.scan_frame.setVisible(False)
            self.scan_line.hide()
            self.face_guide.setVisible(False)
            self.scan_lbl.setText(tr("ret.cam_open_error"))
            db_log_intento(1, "retirar", "fallido",
                           "No se pudo abrir la camara en escaneo de retirar")
            return
        if not face_uid:
            self.cam.idle()
            self.scan_frame.setVisible(False)
            self.scan_line.hide()
            self.face_guide.setVisible(False)
            db_log_intento(1, "retirar", "fallido",
                           "Rostro no reconocido en escaneo de retirar")
            self.scan_lbl.setText(tr("ret.not_recognized"))
            return

        sesion = db_get_active_sesion_by_face(face_uid)
        if not sesion:
            self.cam.idle()
            self.scan_frame.setVisible(False)
            self.scan_line.hide()
            self.face_guide.setVisible(False)
            self.scan_lbl.setText(tr("ret.no_active_session"))
            return

        self._face_uid = face_uid
        if isinstance(sesion, dict):
            self._id_sesion = sesion["ID_sesion"]
            self._id_locker = sesion["ID_locker"]
        else:
            self._id_sesion, self._id_locker = sesion

        num_locker = db_get_locker_num_by_id(self._id_locker)
        self.scan_lbl.setText("")
        self.id_lbl.setText(tr("ret.verified"))
        self.locker_lbl.setText(tr("ret.your_locker", n=num_locker))
        self.scan_frame.setVisible(False)
        self.scan_line.hide()
        self.scan_btn.setVisible(False)
        self.opts.setVisible(False)
        self._show_detected_dialog()

    # ── Dialogo de deteccion ──────────────────────────────────────────────────

    def _show_detected_dialog(self):
        if self._detected_msg and self._detected_msg.isVisible():
            self._detected_msg.close()

        self._detected_left = 3
        dlg = QMessageBox(self)
        dlg.setWindowTitle(tr("ret.detect_title"))
        dlg.setText(tr("ret.detect_text"))
        dlg.setInformativeText(tr("ret.choice_prompt", n=3))
        dlg.setIcon(QMessageBox.Information)
        dlg.setStandardButtons(QMessageBox.NoButton)
        dlg.setWindowModality(Qt.NonModal)
        dlg.finished.connect(self._on_detected_dialog_closed)
        dlg.setStyleSheet("""
            QMessageBox {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #eaf3ff, stop:1 #d8ebff);
                color: #123866; border: 2px solid #2f80ed;
                border-radius: 12px; font-family: 'Segoe UI'; font-size: 11px;
            }
            QMessageBox QLabel          { color: #123866; font-size: 12px; font-weight: 700; }
            QLabel#qt_msgbox_label      { font-size: 13px; font-weight: 800; }
            QLabel#qt_msgbox_informativelabel { color: #2f80ed; font-size: 10px; font-weight: 600; }
        """)
        self._detected_msg = dlg
        dlg.show()
        self._detected_timer.start()
        self._detected_force_close.start(3200)

    def _tick_detected_dialog(self):
        if not self._detected_msg or not self._detected_msg.isVisible():
            self._detected_timer.stop()
            return
        self._detected_left -= 1
        if self._detected_left <= 0:
            self._close_detected_dialog()
            return
        self._detected_msg.setInformativeText(
            tr("ret.choice_prompt", n=self._detected_left)
        )

    def _close_detected_dialog(self):
        self._detected_timer.stop()
        self._detected_force_close.stop()
        dlg = self._detected_msg
        self._detected_msg = None
        if dlg:
            try:
                dlg.finished.disconnect(self._on_detected_dialog_closed)
            except Exception:
                pass
            dlg.hide()
            dlg.deleteLater()
        self._closing_detected_msg = False
        self.cam.idle()
        if self._id_sesion:
            self.opts.setVisible(True)

    def _on_detected_dialog_closed(self, _result):
        self._detected_timer.stop()
        self._detected_force_close.stop()
        self._detected_msg = None
        self._closing_detected_msg = False
        self.cam.idle()
        if self._id_sesion:
            self.opts.setVisible(True)

    # ── Acciones ──────────────────────────────────────────────────────────────

    def reset(self):
        self._close_detected_dialog()
        if self.cam_thread:
            self.cam_thread.stop()
            self.cam_thread = None
        self.face_guide.setVisible(False)
        self.scan_frame.setVisible(False)
        self.scan_line.hide()
        self.opts.setVisible(False)
        self.scan_btn.setVisible(True)
        self.scan_btn.setEnabled(True)
        self.scan_lbl.setText("")
        self._face_uid = None
        self._id_sesion = None
        self._id_locker = None
        self.cam.idle()

    def _do_retirar(self):
        if not self._id_sesion:
            return
        self._close_detected_dialog()
        self.scan_btn.setVisible(True)
        self.opts.setVisible(False)
        num_locker = db_get_locker_num_by_id(self._id_locker)
        db_close_sesion(self._id_sesion)
        db_set_locker_estado(self._id_locker, "libre")
        train_model()

        # Abrir cerradura solenoide para que el cliente retire sus cosas
        abrir_locker(num_locker)

        db_log_intento(self._id_locker, "retirar", "exitoso",
                       "Cliente retiro sus cosas. Sesion {} cerrada.".format(self._id_sesion),
                       id_sesion=self._id_sesion)
        self.retirar_done.emit(self._face_uid, num_locker, self._id_sesion)

    def _do_seguir(self):
        if not self._id_sesion:
            return
        self._close_detected_dialog()
        self.scan_btn.setVisible(True)
        self.opts.setVisible(False)
        num_locker = db_get_locker_num_by_id(self._id_locker)
        db_log_intento(self._id_locker, "seguir_comprando", "exitoso",
                       "Cliente consulto locker y continuo comprando.",
                       id_sesion=self._id_sesion)
        self.seguir_done.emit(self._face_uid, num_locker, self._id_sesion)

    def _cancel(self):
        self._close_detected_dialog()
        if self.cam_thread:
            self.cam_thread.stop()
        self.go_back.emit()