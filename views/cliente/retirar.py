import os

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient, QBrush, QPen, QFont, QPainterPath, QRadialGradient
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QFrame, QSizePolicy, QLabel, QApplication)

from biometria.biometria import train_model
from db.models.intentos_acceso import db_log_intento
from db.models.lockers import db_set_locker_estado
from db.models.sesiones import db_close_sesion, db_get_active_sesion_by_face
from utils.camera import CamThread
from utils.gpio_locker import abrir_locker
from utils.helpers import db_get_locker_num_by_id
from views.style.widgets.widgets import lbl, sep_line, CamWidget
from utils.i18n import tr, get_language
from utils.ui_touch import touch_height


def _dp(value: float) -> int:
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    scale = min(dpi / 96, 1.25)
    return max(1, round(value * scale))


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
QWidget#retirar_page { background: transparent; }

QLabel#h2 {
    color: #dceaff; font-size: 16px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#h3 {
    color: #dceaff; font-size: 14px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#tag {
    color: rgba(110,140,190,0.90); font-size: 12px; font-weight: 700;
    font-family: 'Courier New'; letter-spacing: 2px;
}
QLabel#body  { color: #b0c8f0; font-size: 13px; font-family: 'Segoe UI', sans-serif; }
QLabel#small { color: #6e8cbe; font-size: 10px; font-family: 'Courier New'; }
QLabel#ok    {
    color: #B9EA89; font-size: 12px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#err   {
    color: #ff6b6b; font-size: 12px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}

QFrame#sep      { background: rgba(41,128,255,0.25); min-height: 1px; max-height: 1px; }
QFrame#card     { background: rgba(20,38,78,0.92); border: 1.5px solid rgba(40,70,140,0.80); border-radius: 16px; }
QFrame#cam_card { background: rgba(20,38,78,0.92); border: 1.5px solid rgba(40,70,140,0.80); border-radius: 16px; }
QFrame#detect_card {
    background: rgba(16, 44, 28, 0.90); border: 1.5px solid rgba(185, 234, 137, 0.42); border-radius: 16px;
}
QFrame#inline_result_card {
    background: rgba(245, 249, 255, 0.98); border: 1px solid rgba(135, 178, 235, 0.80);
    border-top: 4px solid #2f80ed; border-radius: 16px;
}
QLabel#inline_result_badge {
    background: rgba(210, 229, 252, 1.0); color: #1f5fb8; border: 1px solid rgba(135, 178, 235, 0.85);
    border-radius: 10px; font-size: 8px; font-weight: 800; font-family: 'Segoe UI';
    letter-spacing: 3px; padding: 4px 16px;
}
QLabel#inline_result_title {
    color: #2f80ed; font-size: 26px; font-weight: 900; font-family: 'Segoe UI';
    letter-spacing: -0.5px;
}
QLabel#inline_result_subtitle {
    color: #000000; font-size: 11px; font-family: 'Segoe UI';
}
QLabel#inline_result_detail {
    color: #000000; font-size: 30px; font-weight: 900; font-family: 'Segoe UI';
    letter-spacing: 2px;
}

QLabel#cam {
    background: #050a1a; border: 3px solid rgba(185, 234, 137, 0.6); border-radius: 12px;
    color: #1a3a5c; font-family: 'Courier New'; font-size: 1px;
}
QFrame#prog_bg  { background: rgba(10,20,50,0.80); border-radius: 4px; min-height: 7px; max-height: 7px; }
QFrame#prog_fill {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2980ff, stop:1 #B9EA89);
    border-radius: 4px; min-height: 7px; max-height: 7px;
}

QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(20,50,120,0.95),
        stop:0.5 rgba(41,128,255,0.90),
        stop:1 rgba(80,140,240,0.90));
    color: #ffffff; border: 1.5px solid rgba(41,128,255,0.55); border-radius: 12px;
    padding: 10px 12px; font-size: 14px; font-weight: 800;
    font-family: 'Segoe UI', sans-serif; letter-spacing: 1px;
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

QPushButton#btn_sm {
    background: rgba(20,38,78,0.80);
    color: #b0c8f0; border: 1.5px solid rgba(41,128,255,0.40); border-radius: 10px;
    padding: 10px 16px; margin-bottom: 6px; font-size: 14px; font-family: 'Segoe UI', sans-serif; font-weight: 700;
    min-height: 48px; min-width: 120px;
}
QPushButton#btn_sm:hover   { background: rgba(26,48,96,0.95); border-color: rgba(41,128,255,0.80); color: #dceaff; }
QPushButton#btn_sm:pressed {
    background: rgba(14,26,58,0.95);
}

/* ── Acciones post-deteccion ── */
QFrame#actions_card {
    background: rgba(16, 30, 62, 0.62); border: 1.5px solid rgba(73, 118, 190, 0.42); border-radius: 18px;
}
QPushButton#btn_action_red {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(140, 20, 20, 0.96), stop:1 rgba(217, 11, 11, 0.98));
    color: #ffffff; border: 1.5px solid rgba(255, 107, 107, 0.55); border-radius: 12px;
    padding: 14px 16px; font-size: 16px; font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#btn_action_red:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(120, 18, 18, 0.98), stop:1 rgba(190, 10, 10, 0.98));
}
QPushButton#btn_action_red:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(100, 14, 14, 0.98), stop:1 rgba(170, 10, 10, 0.98));
}
QPushButton#btn_action_green {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(42, 124, 50, 0.96), stop:1 rgba(25, 168, 91, 0.98));
    color: #ffffff; border: 1.5px solid rgba(185, 234, 137, 0.55); border-radius: 12px;
    padding: 14px 16px; font-size: 16px; font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#btn_action_green:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(35, 105, 42, 0.98), stop:1 rgba(21, 143, 77, 0.98));
}
QPushButton#btn_action_green:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(30, 91, 36, 0.98), stop:1 rgba(17, 117, 63, 0.98));
}

/* ── Carousel ── */
QFrame#carousel_inner { background: rgba(12,22,50,0.70); border-radius: 10px; border: 1px solid rgba(40,70,140,0.50); }
QLabel#carousel_text  {
    color: #b0c8f0; font-size: 12px; font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#dot_inactive {
    background: transparent; border: 2px solid rgba(41,128,255,0.35); border-radius: 3px;
    min-width: 7px; max-width: 7px; min-height: 7px; max-height: 7px;
}
QPushButton#dot_inactive:hover { background: rgba(41,128,255,0.25); border-color: rgba(41,128,255,0.80); }
QPushButton#dot_active {
    background: #2980ff; border: 2px solid rgba(41,128,255,0.80); border-radius: 4px;
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
        inner_l.setContentsMargins(15, 15, 15, 15)
        inner_l.setSpacing(10)
        inner_l.setAlignment(Qt.AlignCenter)

        self._svg = QSvgWidget()
        self._svg.setFixedSize(100, 100)
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


class ActionTile(QWidget):
    clicked = pyqtSignal()

    def __init__(self, mode: str, title: str, image_name: str, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.title = title
        self.image_name = image_name
        self._hovered = False
        self._pressed = False
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        if mode == "take":
            self._accent = QColor(217, 11, 11)
            self._accent_soft = QColor(255, 107, 107, 45)
            self._card_bg = QColor(16, 30, 62)
            self._icon_bg = QColor(120, 20, 20)
            self._icon_bg2 = QColor(217, 11, 11)
        else:
            self._accent = QColor(25, 168, 91)
            self._accent_soft = QColor(185, 234, 137, 45)
            self._card_bg = QColor(16, 30, 62)
            self._icon_bg = QColor(42, 124, 50)
            self._icon_bg2 = QColor(25, 168, 91)

    def enterEvent(self, _):
        self._hovered = True
        self.update()

    def leaveEvent(self, _):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = False
            self.update()
            if self.rect().contains(event.pos()):
                self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        pad = _dp(10)

        shadow = QColor(0, 0, 0, 80 if not self._pressed else 40)
        for off in range(4, 0, -1):
            shadow.setAlpha(int(80 * (off / 4)))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(shadow))
            p.drawRoundedRect(pad + off, pad + off * 2, W - pad * 2, H - pad * 2, _dp(18), _dp(18))

        card_rect = QRectF(pad, pad, W - pad * 2, H - pad * 2)
        bg = QColor(14, 28, 58) if self._pressed else (QColor(26, 48, 96) if self._hovered else self._card_bg)
        path = QPainterPath()
        path.addRoundedRect(card_rect, _dp(18), _dp(18))
        p.setClipPath(path)

        cg = QLinearGradient(0, pad, 0, H - pad)
        cg.setColorAt(0.0, bg.lighter(110))
        cg.setColorAt(1.0, bg)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(cg))
        p.drawPath(path)

        if self._hovered:
            glow_r = int(min(W, H) * 0.55)
            rg = QRadialGradient(W // 2, int(H * 0.38), glow_r)
            rg.setColorAt(0.0, self._accent_soft)
            rg.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(rg))
            p.setPen(Qt.NoPen)
            p.drawRect(pad, pad, W - pad * 2, H - pad * 2)

        p.setClipping(False)
        border_pen = QPen(self._accent.lighter(120) if self._hovered else QColor(73, 118, 190, 160), _dp(1.5) if not self._hovered else _dp(2))
        p.setPen(border_pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(card_rect.adjusted(0.5, 0.5, -0.5, -0.5), _dp(18), _dp(18))

        icon_size = int(min(W, H) * 0.34)
        cx = W // 2
        cy = int(H * 0.36)
        icon_rect = QRectF(cx - icon_size // 2, cy - icon_size // 2, icon_size, icon_size)

        ig = QRadialGradient(cx - icon_size * 0.15, cy - icon_size * 0.15, icon_size * 1.25)
        ig.setColorAt(0.0, self._icon_bg2)
        ig.setColorAt(1.0, self._icon_bg)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(ig))
        p.drawRoundedRect(icon_rect, _dp(16), _dp(16))

        shim = QLinearGradient(cx - icon_size, cy - icon_size, cx + icon_size, cy - icon_size)
        shim.setColorAt(0.0, QColor(255, 255, 255, 0))
        shim.setColorAt(0.5, QColor(255, 255, 255, 28))
        shim.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(shim))
        p.drawRoundedRect(icon_rect, _dp(16), _dp(16))

        p.setPen(QPen(self._accent.lighter(140), _dp(1.2)))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(icon_rect.adjusted(0.5, 0.5, -0.5, -0.5), _dp(16), _dp(16))

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        image_path = os.path.join(project_root, "public", self.image_name)
        pix = QPixmap(image_path)
        if not pix.isNull():
            pix = pix.scaled(int(icon_size * 0.78), int(icon_size * 0.78), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            px = int(cx - pix.width() / 2)
            py = int(cy - pix.height() / 2)
            p.drawPixmap(px, py, pix)

        label_top = cy + icon_size // 2 + int(H * 0.06)
        font = QFont("Segoe UI", max(10, int(H * 0.060)), QFont.Bold)
        p.setFont(font)
        p.setPen(QPen(QColor(220, 235, 255)))
        title_rect = QRectF(pad, label_top, W - pad * 2, int(H * 0.24))
        p.drawText(title_rect, Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, self.title)
        p.end()


class InlineResultCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setAlignment(Qt.AlignCenter)

        self._card = QFrame()
        self._card.setObjectName("inline_result_card")
        self._card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._card.setMaximumWidth(480)
        self._card.setMinimumHeight(420)
        cl = QVBoxLayout(self._card)
        cl.setContentsMargins(48, 40, 48, 40)
        cl.setSpacing(18)
        cl.setAlignment(Qt.AlignCenter)

        self._icon = QLabel("✓")
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setFixedSize(100, 100)
        self._icon.setStyleSheet(
            "background: rgba(47, 128, 237, 0.12); color: #2f80ed; border-radius: 50px; "
            "font-size: 40px; font-weight: 900; font-family: 'Segoe UI';"
        )
        cl.addWidget(self._icon, alignment=Qt.AlignCenter)

        self._badge = QLabel("")
        self._badge.setObjectName("inline_result_badge")
        self._badge.setAlignment(Qt.AlignCenter)
        self._badge.setFixedHeight(26)
        cl.addWidget(self._badge, alignment=Qt.AlignCenter)

        self._title = QLabel("")
        self._title.setObjectName("inline_result_title")
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setWordWrap(True)
        cl.addWidget(self._title)

        self._subtitle = QLabel("")
        self._subtitle.setObjectName("inline_result_subtitle")
        self._subtitle.setAlignment(Qt.AlignCenter)
        self._subtitle.setWordWrap(True)
        cl.addWidget(self._subtitle)

        self._divider = QFrame()
        self._divider.setStyleSheet("background: rgba(135, 178, 235, 0.90); border: none; min-height: 1px; max-height: 1px;")
        cl.addWidget(self._divider)

        self._detail = QLabel("")
        self._detail.setObjectName("inline_result_detail")
        self._detail.setAlignment(Qt.AlignCenter)
        self._detail.setWordWrap(True)
        cl.addWidget(self._detail)

        self._footer = QLabel("")
        self._footer.setAlignment(Qt.AlignCenter)
        self._footer.setWordWrap(True)
        self._footer.setStyleSheet(
            "color: #24405f; font-size: 12px; font-family: 'Segoe UI'; line-height: 1.5;"
        )
        cl.addWidget(self._footer)

        root.addWidget(self._card, alignment=Qt.AlignCenter)

    def show_result(self, kind: str, title: str, subtitle: str, detail: str = ""):
        accent = {
            "ok_blue": "#2f80ed",
            "ok": "#2e7d32",
            "warn": "#e66c00",
            "err": "#c62828",
        }.get(kind, "#2f80ed")
        badge = {
            "ok_blue": tr("result.ok"),
            "ok": tr("result.ok"),
            "warn": tr("result.warn"),
            "err": tr("result.err"),
        }.get(kind, tr("result.ok"))

        self._icon.setStyleSheet(
            "background: rgba(47, 128, 237, 0.12); color: %s; border-radius: 50px; "
            "font-size: 40px; font-weight: 900; font-family: 'Segoe UI';" % accent
        )
        self._badge.setText(badge)
        self._badge.setStyleSheet(
            "background: rgba(210, 229, 252, 1.0); color: %s; border: 1px solid rgba(135, 178, 235, 0.85);"
            " border-radius: 10px; font-size: 8px; font-weight: 800; font-family: 'Segoe UI';"
            " letter-spacing: 3px; padding: 4px 16px;" % accent
        )
        self._title.setText(title)
        self._title.setStyleSheet(
            "color: %s; font-size: 26px; font-weight: 900; font-family: 'Segoe UI'; letter-spacing: -0.5px;" % accent
        )
        self._subtitle.setText(subtitle)
        self._detail.setText(detail)
        self._footer.setText(tr("ret.verified") if detail else tr("ret.detect_text"))
        self._detail.setVisible(bool(detail))
        self._divider.setVisible(bool(detail))
        self.setVisible(True)

    def clear(self):
        self._title.clear()
        self._subtitle.clear()
        self._detail.clear()
        self._footer.clear()
        self.setVisible(False)


class RetirarPage(QWidget):

    go_back      = pyqtSignal()
    retirar_done = pyqtSignal(str, str, int)
    seguir_done  = pyqtSignal(str, str, int)

    _CAM_W = 440
    _CAM_H = 390

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
        back.setFixedHeight(touch_height(48))
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
        self.scan_btn.setFixedHeight(touch_height(80))
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

        self.detect_card = QFrame()
        self.detect_card.setObjectName("detect_card")
        self.detect_card.setVisible(False)
        detect_l = QVBoxLayout(self.detect_card)
        detect_l.setContentsMargins(16, 14, 16, 14)
        detect_l.setSpacing(6)
        detect_l.setAlignment(Qt.AlignCenter)

        detect_title_row = QHBoxLayout()
        detect_title_row.setSpacing(8)
        detect_title_row.setAlignment(Qt.AlignCenter)
        self.detect_icon = QLabel("✓")
        self.detect_icon.setAlignment(Qt.AlignCenter)
        self.detect_icon.setFixedSize(28, 28)
        self.detect_icon.setStyleSheet(
            "background: rgba(185, 234, 137, 0.18); color: #B9EA89; border-radius: 14px; "
            "font-size: 16px; font-weight: 900; font-family: 'Segoe UI';"
        )
        self.detect_title_lbl = lbl(tr("ret.detect_title"), "h3", Qt.AlignCenter)
        detect_title_row.addWidget(self.detect_icon)
        detect_title_row.addWidget(self.detect_title_lbl)
        detect_l.addLayout(detect_title_row)

        self.detect_text_lbl = lbl(tr("ret.detect_text"), "body", Qt.AlignCenter)
        self.detect_text_lbl.setWordWrap(True)
        detect_l.addWidget(self.detect_text_lbl)
        rl.addWidget(self.detect_card)

        # ── Widget de camara a pantalla completa dentro del panel ───────────
        self.cam = CamWidget(self._CAM_W, self._CAM_H)
        self.cam.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rl.addWidget(self.cam, 1)

        # ── Card de acciones post-deteccion ───────────────────────────────────
        self.opts = QFrame()
        self.opts.setObjectName("actions_card")
        self.opts.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        ol = QVBoxLayout(self.opts)
        ol.setContentsMargins(18, 18, 18, 18)
        ol.setSpacing(12)
        ol.setAlignment(Qt.AlignCenter)

        btn_row = QHBoxLayout(); btn_row.setSpacing(14)
        btn_row.setAlignment(Qt.AlignCenter)

        self.btn_retirar = ActionTile("take", "RETIRAR COSAS", "abierta.png")
        self.btn_retirar.setMinimumSize(260, 300)
        self.btn_retirar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.btn_retirar.clicked.connect(self._do_retirar)

        self.btn_seguir = ActionTile("keep", "SEGUIR COMPRANDO", "cerrada.png")
        self.btn_seguir.setMinimumSize(260, 300)
        self.btn_seguir.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.btn_seguir.clicked.connect(self._do_seguir)

        btn_row.addWidget(self.btn_retirar, 1)
        btn_row.addWidget(self.btn_seguir, 1)
        ol.addLayout(btn_row, 1)
        self.opts.setVisible(False)
        rl.addWidget(self.opts, 1)

        self.result_card = InlineResultCard()
        rl.addWidget(self.result_card, 1)
        self.result_card.setVisible(False)

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
        self.detect_title_lbl.setText(tr("ret.detect_title"))
        self.detect_text_lbl.setText(tr("ret.detect_text"))
        self.scan_btn.setText(tr("ret.start"))
        self._carousel.set_language(lang)
        self._carousel._render(self._carousel._current)
        self._carousel.set_language(lang)

    def _show_camera_mode(self):
        self.detect_card.setVisible(False)
        self.result_card.clear()
        self.opts.setVisible(False)
        self.cam.setVisible(True)
        self.scan_btn.setVisible(True)
        self.scan_frame.setVisible(False)
        self.face_guide.setVisible(False)
        self.scan_line.hide()
        self.scan_title_lbl.setText(tr("ret.scan_title"))
        self._update_overlay()

    def _show_actions_mode(self):
        self.cam.setVisible(False)
        self.scan_frame.setVisible(False)
        self.face_guide.setVisible(False)
        self.scan_line.hide()
        self.result_card.clear()
        self.detect_card.setVisible(True)
        self.opts.setVisible(True)
        self.scan_title_lbl.setText(tr("ret.verified"))

    def _show_inline_result(self, kind: str, title: str, subtitle: str, detail: str = ""):
        self.cam.setVisible(False)
        self.scan_frame.setVisible(False)
        self.face_guide.setVisible(False)
        self.scan_line.hide()
        self.detect_card.setVisible(False)
        self.opts.setVisible(False)
        self.result_card.show_result(kind, title, subtitle, detail)
        self.scan_title_lbl.setText(tr("ret.scan_title"))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0.0, QColor(10, 20, 45))
        bg.setColorAt(1.0, QColor(16, 32, 68))
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

        self._show_camera_mode()
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

        self.scan_lbl.setText("")
        self.scan_btn.setVisible(False)
        self._show_actions_mode()

    # ── Dialogo de deteccion ──────────────────────────────────────────────────

    def _show_detected_dialog(self):
        self.detect_card.setVisible(True)
        self.detect_title_lbl.setText(tr("ret.detect_title"))
        self.detect_text_lbl.setText(tr("ret.detect_text"))
        self.scan_title_lbl.setText(tr("ret.verified"))

    def _tick_detected_dialog(self):
        return

    def _close_detected_dialog(self):
        self._detected_msg = None
        self.cam.idle()
        self.detect_card.setVisible(False)
        self.opts.setVisible(False)
        self.result_card.clear()
        self.scan_title_lbl.setText(tr("ret.scan_title"))

    def _on_detected_dialog_closed(self, _result):
        self._detected_msg = None
        self.detect_card.setVisible(False)
        self._show_camera_mode()

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
        self.cam.setVisible(True)
        self.scan_btn.setVisible(True)
        self.scan_btn.setEnabled(True)
        self.scan_lbl.setText("")
        self._face_uid = None
        self._id_sesion = None
        self._id_locker = None
        self.detect_card.setVisible(False)
        self.result_card.clear()
        self.cam.idle()

    def _do_retirar(self):
        if not self._id_sesion:
            return
        self._close_detected_dialog()
        self.scan_btn.setVisible(True)
        num_locker = db_get_locker_num_by_id(self._id_locker)
        db_close_sesion(self._id_sesion)
        db_set_locker_estado(self._id_locker, "libre")
        train_model()

        # Abrir cerradura solenoide para que el cliente retire sus cosas
        abrir_locker(num_locker)

        db_log_intento(self._id_locker, "retirar", "exitoso",
                       "Cliente retiro sus cosas. Sesion {} cerrada.".format(self._id_sesion),
                       id_sesion=self._id_sesion)
        self._show_inline_result(
            "ok_blue",
            tr("flow.bye_title"),
            tr("flow.bye_sub", n=num_locker),
            "LOCKER  #{}".format(num_locker),
        )

    def _do_seguir(self):
        if not self._id_sesion:
            return
        self._close_detected_dialog()
        self.scan_btn.setVisible(True)
        num_locker = db_get_locker_num_by_id(self._id_locker)
        db_log_intento(self._id_locker, "seguir_comprando", "exitoso",
                       "Cliente consulto locker y continuo comprando.",
                       id_sesion=self._id_sesion)
        self._show_inline_result(
            "ok_blue",
            tr("flow.keep_title"),
            tr("flow.keep_sub"),
            "LOCKER  #{}".format(num_locker) if num_locker else "",
        )

    def _cancel(self):
        self._close_detected_dialog()
        if self.cam_thread:
            self.cam_thread.stop()
        self.go_back.emit()