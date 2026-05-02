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
from db.models.sesiones import db_create_sesion
from utils.camera import CamThread
from utils.gpio_locker import abrir_locker
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
QWidget#guardar_page { background: #E7E7E7; color: #1f2a44; }

QLabel#h2 {
    color: #305BAB; font-size: 16px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#tag {
    color: #305BAB; font-size: 12px; font-weight: 700;
    font-family: 'Courier New'; letter-spacing: 2px;
}
QLabel#body  { color: #2c3e50; font-size: 13px; font-family: 'Segoe UI', sans-serif; }
QLabel#small { color: #3a5f84; font-size: 10px; font-family: 'Courier New'; }
QLabel#err   {
    color: #BD0A0A; font-size: 12px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}

QFrame#sep      { background: #305BAB; min-height: 1px; max-height: 1px; }
QFrame#card     { background: #C6DCFF; border: 2px solid #305BAB; border-radius: 10px; }
QFrame#cam_card { background: #C6DCFF; border: 2px solid #305BAB; border-radius: 10px; }

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
    padding: 16px 20px; font-size: 19px; font-weight: 800;
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
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4a90d9, stop:1 #7ec8f5);
    color: rgba(0,0,0,120);
}
QPushButton#btn_sm {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #96bfe9, stop:1 #b8e1fa);
    color: #1d3767; border: 2px solid #305bab; border-radius: 8px;
    padding: 10px 16px; font-size: 14px; font-family: 'Segoe UI', sans-serif; font-weight: 700;
    min-height: 48px; min-width: 120px;
}
QPushButton#btn_sm:hover   { color: #305bab; border-color: #838383; }
QPushButton#btn_sm:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #95a49f, stop:0.5 #c1cac7, stop:1 #5681cf);
}

QFrame#carousel_inner { background: white; border-radius: 8px; border: none; }
QLabel#carousel_text  {
    color: #1a3a6b; font-size: 12px; font-weight: 600;
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


class GuardarPage(QWidget):
    done    = pyqtSignal(str, str, int)
    failed  = pyqtSignal(str)
    go_back = pyqtSignal()

    _CAM_W = 440
    _CAM_H = 390

    def __init__(self):
        super().__init__()
        self.setObjectName("guardar_page")
        self.setStyleSheet(STYLE)
        self.cam_thread = None
        self._face_uid  = None
        self._id_locker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 6)
        root.setSpacing(4)

        # Header
        hdr = QHBoxLayout(); hdr.setSpacing(8)
        self.back_btn = QPushButton("")
        back = self.back_btn
        back.setObjectName("btn_sm")
        back.setFixedHeight(48)
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

        # Body
        body = QHBoxLayout(); body.setSpacing(8)

        # Panel izquierdo — ancho fijo para dejar espacio a la camara
        left = QFrame(); left.setObjectName("card")
        left.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        left.setFixedWidth(270)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 8, 10, 8)
        ll.setSpacing(6)

        self._carousel = CarouselWidget()
        ll.addWidget(self._carousel, 1)

        self.start_btn = QPushButton("  INICIAR ESCANEO")
        self.start_btn.setObjectName("btn_blue")
        self.start_btn.setIcon(_svg_to_icon(_CAM_ICON_SVG, 24))
        self.start_btn.setIconSize(QSize(24, 24))
        self.start_btn.setFixedHeight(82)
        self.start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.start_btn.setCursor(Qt.PointingHandCursor)
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
        rl.addWidget(self.scan_title_lbl)

        self.cam = CamWidget(self._CAM_W, self._CAM_H)
        self.cam.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.cam.setMaximumHeight(self._CAM_H)   # evita que se extienda fuera del video
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

    def set_language(self, lang: str):
        self.back_btn.setText(tr("guard.back"))
        self.title_lbl.setText(tr("guard.title"))
        self.subtitle_lbl.setText(tr("guard.subtitle"))
        self.scan_title_lbl.setText(tr("guard.scan_title"))
        self.start_btn.setText(tr("guard.start"))
        self._carousel.set_language(lang)

    def showEvent(self, e):
        super().showEvent(e)
        result = db_next_free_locker()
        if result:
            self._id_locker = result[0]
            self.start_btn.setEnabled(True)
            self.err_lbl.setText("")
        else:
            self._id_locker = None
            self.err_lbl.setText(tr("guard.no_lockers_now"))
            self.start_btn.setEnabled(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_overlay)

    def _start_capture(self):
        if not self._id_locker:
            self.err_lbl.setText(tr("guard.no_lockers"))
            return
        tmp_uid = "tmp_{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        self._face_uid = tmp_uid
        self.start_btn.setEnabled(False)
        self.err_lbl.setText("")
        self.scan_frame.setVisible(True)
        self.face_guide.setVisible(True)
        self._update_overlay()
        self.cam_thread = CamThread(CamThread.CAPTURE, face_uid=tmp_uid)
        self.cam_thread.frame_sig.connect(self.cam.update_frame)
        self.cam_thread.progress.connect(self.cam.set_progress)
        self.cam_thread.cap_done.connect(self._on_capture_done)
        self.cam_thread.finished.connect(self._on_capture_thread_finished)
        self.cam_thread.start()

    def _on_capture_thread_finished(self):
        sender = self.sender()
        if sender is self.cam_thread:
            self.cam_thread = None

    def _on_capture_done(self, ok, tmp_uid):
        self.start_btn.setEnabled(True)
        self.scan_frame.setVisible(False)
        self.scan_line.hide()
        self.face_guide.setVisible(False)
        if tmp_uid == CamThread.CAMERA_ERROR:
            self.cam.set_status(tr("guard.cam_open_error"), "#bd0a0a")
            self.cam.idle()
            if self._id_locker:
                db_log_intento(self._id_locker, "registro_biometrico", "fallido",
                               "No se pudo abrir la camara en registro")
            self.err_lbl.setText(tr("guard.cam_open_error"))
            return
        if not ok:
            self.cam.set_status(tr("guard.capture_error"), "#bd0a0a")
            self.cam.idle()
            delete_face_data(tmp_uid)
            if self._id_locker:
                db_log_intento(self._id_locker, "registro_biometrico", "fallido",
                               "Error durante la captura de imagenes")
            self.err_lbl.setText(tr("guard.capture_error"))
            return
        self.cam.set_status(tr("guard.face_ok"), "#B9EA89")
        QTimer.singleShot(850, self.cam.idle)
        locker = db_next_free_locker()
        if not locker:
            delete_face_data(tmp_uid)
            self.failed.emit(tr("guard.no_lockers"))
            return
        id_locker, num_locker = locker
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
        abrir_locker(num_locker)

        db_log_intento(id_locker, "registro_biometrico", "exitoso",
                       "Sesion {} creada. Locker #{} asignado.".format(id_sesion, num_locker),
                       id_sesion=id_sesion)
        train_model()
        self.done.emit(face_uid, num_locker, id_sesion)

    def _cancel(self):
        if self.cam_thread:
            self.cam_thread.stop()
        if self._face_uid:
            delete_face_data(self._face_uid)
        self.go_back.emit()

    def reset(self):
        if self.cam_thread:
            self.cam_thread.stop()
        self._face_uid  = None
        self._id_locker = None
        self.err_lbl.setText("")
        self.cam.idle()
        self.start_btn.setEnabled(True)
        self.scan_frame.setVisible(False)
        self.scan_line.hide()
        self.face_guide.setVisible(False)

    def _update_overlay(self):
        cam_w = self.cam.width()
        cam_h = self.cam.height()
        # Marco: proporcion vertical alta para cubrir cabeza + hombros
        frame_w = int(cam_w * 0.42)
        frame_h = int(cam_h * 0.80)
        frame_x = (cam_w - frame_w) // 2
        frame_y = (cam_h - frame_h) // 2
        self.scan_frame.setGeometry(frame_x, frame_y, frame_w, frame_h)
        # Silueta coincide exactamente con el marco
        self.face_guide.setGeometry(frame_x, frame_y, frame_w, frame_h)
        self.scan_line.update_bounds(frame_x, frame_y, frame_w, frame_h)