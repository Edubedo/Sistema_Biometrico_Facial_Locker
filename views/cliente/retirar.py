from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QSizePolicy, QLabel, QMessageBox

from biometria.biometria import delete_face_data, train_model
from db.models.intentos_acceso import db_log_intento
from db.models.lockers import db_set_locker_estado
from db.models.sesiones import db_close_sesion, db_get_active_sesion_by_face
from utils.camera import CamThread
from utils.helpers import db_get_locker_num_by_id
from views.style.widgets.widgets import lbl, sep_line, CamWidget


class ScanLine(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(6)
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
        m = 4
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
QWidget#retirar_page { background: #e7e7e7; color: #1f2a44 }
QLabel#h2 { color: #305bab; font-size: 24px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#h3 { color: #305bab; font-size: 18px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#tag { color: #305bab; font-size: 22px; font-weight: 700; font-family: 'Courier New'; letter-spacing: 4px; }
QLabel#body { color: #2c3e50; font-size: 20px; font-family: 'Segoe UI',sans-serif; }
QLabel#small { color: #3a5f84; font-size: 16px; font-family: 'Courier New'; letter-spacing: 1px; }
QLabel#ok { color: #b9ea89; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#err { color: #BD0A0A; font-size: 17px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QFrame#sep { background: #305bab; min-height: 1px; max-height: 1px; }
QFrame#card { background: #c6dcff; border: 2px solid #305bab; border-radius: 14px; }
QLabel#cam {
    background: #0c1530; border: 4px solid #305bab; border-radius: 10px;
    color: #1a3a5c; font-family: 'Courier New'; font-size: 0px;
}
QFrame#prog_bg { background: #0a1628; border-radius: 6px; min-height: 12px; max-height: 12px; }
QFrame#prog_fill {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #305bab, stop:1 #B9EA89);
    border-radius: 6px; min-height: 12px; max-height: 12px;
}
QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1a3a6b, stop:0.5 #305bab, stop:1 #678dd3);
    color: white; border: none; border-radius: 14px;
    padding: 22px 30px; font-size: 19px; font-weight: 750;
    font-family: 'Segoe UI', sans-serif; letter-spacing: 2px;
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
QPushButton#btn_green {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #b9ea89, stop:1 #0fa860);
    color: #0a1628; border: none; border-radius: 12px; padding: 14px 30px;
    font-size: 16px; font-weight: 800; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_red {
    background: #bd0a0a; color: #fff; border: none; border-radius: 12px;
    padding: 14px 30px; font-size: 16px; font-weight: 800; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_sm {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #96bfe9, stop:1 #b8e1fa);
    color: #1d3767; border: 3px solid #305bab; border-radius: 8px;
    padding: 8px 18px; font-size: 19px; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_sm:hover { color: #305bab; border-color: #838383; }
QPushButton#btn_sm:pressed { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #95a49f, stop:0.5 #c1cac7, stop:1 #5681cf); }
QFrame#carousel_card { background: white; border-radius: 14px; border: none; }
QLabel#carousel_text {
    color: #1a3a6b; font-size: 17px; font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}
QFrame#actions_card {
    background: #d6e6ff;
    border: 2px solid #305bab;
    border-radius: 12px;
}
QPushButton#btn_action_red {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #a40909, stop:1 #d90b0b);
    color: #ffffff;
    border: none;
    border-radius: 12px;
    padding: 14px 16px;
    font-size: 17px;
    font-weight: 800;
    font-family: 'Segoe UI',sans-serif;
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
    color: #ffffff;
    border: none;
    border-radius: 12px;
    padding: 14px 16px;
    font-size: 17px;
    font-weight: 800;
    font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_action_green:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #23692a, stop:1 #158f4d);
}
QPushButton#btn_action_green:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1e5b24, stop:1 #11753f);
}
QPushButton#dot_inactive {
    background: transparent; border: 2px solid #7aaad4; border-radius: 6px;
    min-width: 11px; max-width: 11px; min-height: 11px; max-height: 11px;
}
QPushButton#dot_inactive:hover { background: #c6dcff; border-color: #305bab; }
QPushButton#dot_active {
    background: #305bab; border: 2px solid #1a3a6b; border-radius: 7px;
    min-width: 14px; max-width: 14px; min-height: 14px; max-height: 14px;
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


def _svg_to_icon(svg_bytes: bytes, size: int = 28) -> QIcon:
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
     </svg>""",
     "Mira directo a la cámara"),

    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#EAF3DE"/>
        <rect x="14" y="14" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
        <rect x="44" y="14" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
        <rect x="14" y="44" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
        <rect x="44" y="44" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
     </svg>""",
     "Tu biometría facial es verificada"),

    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#FAEEDA"/>
        <rect x="14" y="22" width="52" height="38" rx="7"
              stroke="#BA7517" stroke-width="3" fill="#fde8b8"/>
        <rect x="28" y="14" width="24" height="12" rx="4"
              stroke="#BA7517" stroke-width="2.5" fill="#fde8b8"/>
        <circle cx="40" cy="42" r="6" fill="#BA7517"/>
        <line x1="40" y1="48" x2="40" y2="54"
              stroke="#BA7517" stroke-width="3" stroke-linecap="round"/>
     </svg>""",
     "Se te muestra el locker asignado"),

    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#EEEDFE"/>
        <path d="M18 30h44l-7 30H25L18 30z"
              stroke="#534AB7" stroke-width="3" fill="#dddcfa" stroke-linejoin="round"/>
        <circle cx="31" cy="64" r="4.5" fill="#534AB7"/>
        <circle cx="53" cy="64" r="4.5" fill="#534AB7"/>
        <path d="M10 18h10l7 12" stroke="#534AB7" stroke-width="3"
              fill="none" stroke-linecap="round" stroke-linejoin="round"/>
     </svg>""",
     "Elige: retirar tus cosas o seguir comprando"),

    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#FAECE7"/>
        <circle cx="40" cy="40" r="24" stroke="#993C1D" stroke-width="3" fill="#fcd5c5"/>
        <path d="M27 40l9 9 17-18"
              stroke="#993C1D" stroke-width="3.5" fill="none"
              stroke-linecap="round" stroke-linejoin="round"/>
     </svg>""",
     "Tus imágenes se borran al terminar"),
]


class CarouselWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._current = 0
        self._dot_btns = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(0)

        layout.addWidget(lbl("COMO FUNCIONA", "tag", Qt.AlignCenter))
        layout.addStretch(1)

        self._card = QFrame()
        self._card.setObjectName("carousel_card")
        card_l = QVBoxLayout(self._card)
        card_l.setContentsMargins(20, 28, 20, 28)
        card_l.setSpacing(16)
        card_l.setAlignment(Qt.AlignCenter)

        self._svg = QSvgWidget()
        self._svg.setFixedSize(100, 100)
        self._svg.setStyleSheet("background: transparent;")
        card_l.addWidget(self._svg, alignment=Qt.AlignCenter)

        self._text_lbl = QLabel()
        self._text_lbl.setObjectName("carousel_text")
        self._text_lbl.setAlignment(Qt.AlignCenter)
        self._text_lbl.setWordWrap(True)
        card_l.addWidget(self._text_lbl)

        layout.addWidget(self._card)

        dots_row = QHBoxLayout()
        dots_row.setSpacing(10)
        dots_row.setAlignment(Qt.AlignCenter)
        for i in range(len(CAROUSEL_STEPS)):
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._go_to(idx))
            dots_row.addWidget(btn)
            self._dot_btns.append(btn)

        layout.addSpacing(14)
        layout.addLayout(dots_row)
        layout.addStretch(1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next)
        self._timer.start(2800)
        self._render(0)

    def _render(self, idx):
        self._current = idx
        svg_data, text = CAROUSEL_STEPS[idx]
        self._svg.load(svg_data)
        self._text_lbl.setText(text)
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

    def __init__(self):
        super().__init__()
        self.setObjectName("retirar_page")
        self.setStyleSheet(STYLE)

        self.cam_thread  = None
        self._face_uid   = None
        self._id_sesion  = None
        self._id_locker  = None

        vl = QVBoxLayout(self)
        vl.setContentsMargins(60, 40, 60, 40)
        vl.setSpacing(16)

        hdr = QHBoxLayout()
        back = QPushButton("< Volver")
        back.setObjectName("btn_sm")
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self._cancel)
        htxt = QVBoxLayout()
        htxt.setSpacing(4)
        htxt.addWidget(lbl("RETIRAR / CONTINUAR", "h2"))
        htxt.addWidget(lbl("VERIFICACION BIOMETRICA", "tag"))
        hdr.addWidget(back)
        hdr.addSpacing(20)
        hdr.addLayout(htxt)
        hdr.addStretch()
        vl.addLayout(hdr)
        vl.addWidget(sep_line())

        body = QHBoxLayout()
        body.setSpacing(32)

        left = QFrame()
        left.setObjectName("card")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(30, 20, 30, 20)
        ll.setSpacing(0)

        self._carousel = CarouselWidget()
        ll.addWidget(self._carousel, 1)
        ll.addSpacing(16)

        self.scan_btn = QPushButton("  INICIAR ESCANEO")
        self.scan_btn.setObjectName("btn_blue")
        self.scan_btn.setIcon(_svg_to_icon(_CAM_ICON_SVG, 26))
        self.scan_btn.setIconSize(QSize(26, 26))
        self.scan_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self._start_scan)
        ll.addWidget(self.scan_btn)

        self.scan_lbl = lbl("", "err")
        self.scan_lbl.setWordWrap(True)
        ll.addWidget(self.scan_lbl)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(12)
        rl.addWidget(lbl("ESCANER BIOMETRICO", "tag", Qt.AlignCenter))

        self.opts = QFrame()
        self.opts.setObjectName("actions_card")
        ol = QVBoxLayout(self.opts)
        ol.setContentsMargins(18, 14, 18, 14)
        ol.setSpacing(10)
        self.id_lbl = lbl("", "ok", Qt.AlignCenter)
        self.locker_lbl = lbl("", "h3", Qt.AlignCenter)
        ol.addWidget(self.id_lbl)
        ol.addWidget(self.locker_lbl)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(12)

        self.btn_retirar = QPushButton("RETIRAR COSAS Y SALIR")
        self.btn_retirar.setObjectName("btn_action_red")
        self.btn_retirar.setIcon(_svg_to_icon(_RETIRAR_ICON_SVG, 24))
        self.btn_retirar.setIconSize(QSize(24, 24))
        self.btn_retirar.setMinimumHeight(58)
        self.btn_retirar.clicked.connect(self._do_retirar)

        self.btn_seguir = QPushButton("SEGUIR COMPRANDO")
        self.btn_seguir.setObjectName("btn_action_green")
        self.btn_seguir.setIcon(_svg_to_icon(_SEGUIR_ICON_SVG, 24))
        self.btn_seguir.setIconSize(QSize(24, 24))
        self.btn_seguir.setMinimumHeight(58)
        self.btn_seguir.clicked.connect(self._do_seguir)

        btn_row.addWidget(self.btn_retirar, 1)
        btn_row.addWidget(self.btn_seguir, 1)
        ol.addLayout(btn_row)
        self.opts.setVisible(False)
        rl.addWidget(self.opts)

        self.cam = CamWidget(500, 760)
        self.cam.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rl.addWidget(self.cam, 1)

        self.face_guide = QSvgWidget(self.cam)
        self.face_guide.load(b"""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120">
            <circle cx="50" cy="28" r="20" fill="#305bab" opacity="0.5"/>
            <path d="M8 108 Q8 65 50 65 Q92 65 92 108 Z" fill="#305bab" opacity="0.5"/>
            </svg>""")
        self.face_guide.setStyleSheet("background: transparent;")
        self.face_guide.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.scan_frame = QFrame(self.cam)
        self.scan_frame.setStyleSheet(
            "border: 4px solid #B9EA89; border-radius: 10px; background: transparent;")
        self.scan_frame.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.scan_line = ScanLine(self.cam)

        body.addWidget(left, 1)
        body.addWidget(right, 2)
        vl.addLayout(body, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_overlay)

    def _update_overlay(self):
        cam_w = self.cam.width()
        cam_h = self.cam.height()
        frame_w = int(cam_w * 0.45)
        frame_h = int(cam_h * 0.55)
        frame_x = (cam_w - frame_w) // 2
        frame_y = (cam_h - frame_h) // 2
        self.scan_frame.setGeometry(frame_x, frame_y, frame_w, frame_h)
        icon_w = int(frame_w * 0.40)
        icon_h = int(frame_h * 0.40)
        icon_x = frame_x + (frame_w - icon_w) // 2
        icon_y = frame_y + (frame_h - icon_h) // 2
        self.face_guide.setGeometry(icon_x, icon_y, icon_w, icon_h)
        self.scan_line.update_bounds(frame_x, frame_y, frame_w, frame_h)

    def _start_scan(self):
        labels = train_model()
        if not labels:
            self.scan_lbl.setText("No hay biometrias registradas.")
            return
        self.scan_btn.setEnabled(False)
        self.opts.setVisible(False)
        self.scan_lbl.setText("")
        self.cam_thread = CamThread(CamThread.RECOGNIZE, labels=labels)
        self.cam_thread.frame_sig.connect(self.cam.update_frame)
        self.cam_thread.rec_done.connect(self._on_recognized)
        self.cam_thread.start()

    def _on_recognized(self, face_uid):
        self.scan_btn.setEnabled(True)
        self.cam.idle()
        if not face_uid:
            db_log_intento(1, "retirar", "fallido",
                           "Rostro no reconocido en escaneo de retirar")
            self.scan_lbl.setText("No se reconocio el rostro. Intenta de nuevo.")
            return
        sesion = db_get_active_sesion_by_face(face_uid)
        if not sesion:
            self.scan_lbl.setText("No tienes una sesion activa.")
            return
        self._face_uid  = face_uid
        self._id_sesion = sesion["ID_sesion"]
        self._id_locker = sesion["ID_locker"]
        num_locker = db_get_locker_num_by_id(self._id_locker)
        self.scan_lbl.setText("")
        self.id_lbl.setText("Identidad verificada")
        self.locker_lbl.setText("Tu locker: #{}".format(num_locker))
        self.opts.setVisible(True)
        self.scan_btn.setVisible(False)
        self._show_detected_dialog()

    def _show_detected_dialog(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Deteccion exitosa")
        dlg.setText("Cara detectada correctamente.")
        dlg.setInformativeText("Ya puedes elegir una accion.")
        dlg.setIcon(QMessageBox.Information)
        dlg.setStandardButtons(QMessageBox.Ok)
        dlg.button(QMessageBox.Ok).setText("Continuar")
        dlg.setStyleSheet("""
            QMessageBox {
                background: #eaf3ff;
                color: #173b6d;
                font-family: 'Segoe UI';
                font-size: 16px;
            }
            QMessageBox QLabel {
                color: #173b6d;
                font-size: 18px;
                font-weight: 700;
            }
            QMessageBox QPushButton {
                background: #2f80ed;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                min-width: 120px;
                min-height: 36px;
                font-size: 15px;
                font-weight: 700;
                padding: 6px 16px;
            }
            QMessageBox QPushButton:hover { background: #1f6ed8; }
            QMessageBox QPushButton:pressed { background: #1658b0; }
        """)
        dlg.exec_()

    def _do_retirar(self):
        if not self._id_sesion:
            return
        self.scan_btn.setVisible(True)
        self.opts.setVisible(False)
        num_locker = db_get_locker_num_by_id(self._id_locker)
        db_close_sesion(self._id_sesion)
        db_set_locker_estado(self._id_locker, "libre")
        delete_face_data(self._face_uid)
        train_model()
        db_log_intento(self._id_locker, "retirar", "exitoso",
                       "Cliente retiro sus cosas. Sesion {} cerrada.".format(self._id_sesion),
                       id_sesion=self._id_sesion)
        self.retirar_done.emit(self._face_uid, num_locker, self._id_sesion)

    def _do_seguir(self):
        if not self._id_sesion:
            return
        self.scan_btn.setVisible(True)
        self.opts.setVisible(False)
        num_locker = db_get_locker_num_by_id(self._id_locker)
        db_log_intento(self._id_locker, "seguir_comprando", "exitoso",
                       "Cliente consulto locker y continuo comprando.",
                       id_sesion=self._id_sesion)
        self.seguir_done.emit(self._face_uid, num_locker, self._id_sesion)

    def _cancel(self):
        if self.cam_thread:
            self.cam_thread.stop()
        self.go_back.emit()

    def reset(self):
        if self.cam_thread:
            self.cam_thread.stop()
        self._face_uid  = None
        self._id_sesion = None
        self._id_locker = None
        self.opts.setVisible(False)
        self.scan_btn.setVisible(True)
        self.scan_btn.setEnabled(True)
        self.scan_lbl.setText("")
        self.cam.idle()