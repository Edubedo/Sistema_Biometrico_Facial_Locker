import datetime
import os

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF
from PyQt5.QtGui import (QIcon, QPixmap, QPainter, QColor, QLinearGradient, QFont,
                         QBrush, QRadialGradient, QPen, QPainterPath)
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QFrame, QSizePolicy, QLabel, QApplication)

from biometria.biometria import delete_face_data, train_model, face_dir_for
from db.connection import connectionDB
from db.models.intentos_acceso import db_log_intento
from db.models.lockers import db_set_locker_estado, db_next_free_locker
from db.models.sesiones import db_create_sesion, db_get_active_sesion_by_face, db_close_sesion
from utils.camera import CamThread
from utils.gpio_locker import abrir_locker, beep_start_scan, beep_success, beep_error
from utils.helpers import db_get_locker_num_by_id
from views.style.widgets.widgets import lbl, sep_line, CamWidget
from utils.i18n import tr, get_language
from utils.ui_touch import touch_height


def _dp(v):
    s = QApplication.primaryScreen()
    return max(1, round(v * ((s.logicalDotsPerInch() if s else 96) / 96)))


BG_TOP = QColor(10, 20, 45)
BG_BOT = QColor(16, 32, 68)

# ── Step overlay: 900 ms por paso (era 1400) → ~1.4 s menos de espera ────────
_STEP_DURATION_MS = 900

STYLE = """
QWidget#guardar_page { background: transparent; color: #dceaff; }
QLabel#h2 {
    color: #dceaff; font-size: 16px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#tag {
    color: rgba(110,140,190,0.90); font-size: 12px; font-weight: 700;
    font-family: 'Courier New'; letter-spacing: 2px;
}
QLabel#body  { color: #b0c8f0; font-size: 13px; font-family: 'Segoe UI', sans-serif; }
QLabel#small { color: #6e8cbe; font-size: 10px; font-family: 'Courier New'; }
QLabel#err   { color: #ff6b6b; font-size: 12px; font-weight: 700; font-family: 'Segoe UI', sans-serif; }
QFrame#sep   { background: rgba(41,128,255,0.25); min-height: 1px; max-height: 1px; border: none; }
QFrame#card  { background: rgba(20,38,78,0.92); border: 1.5px solid rgba(40,70,140,0.80); border-radius: 16px; }
QFrame#cam_card { background: rgba(14,26,58,0.95); border: 1.5px solid rgba(41,128,255,0.40); border-radius: 16px; }
QLabel#cam   { background: #050a1a; border: 3px solid rgba(185,234,137,0.6); border-radius: 12px; }
QFrame#prog_bg  { background: rgba(10,20,50,0.80); border-radius: 4px; min-height: 7px; max-height: 7px; }
QFrame#prog_fill { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2980ff,stop:1 #B9EA89);
    border-radius: 4px; min-height: 7px; max-height: 7px; }
QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(20,50,120,0.95), stop:0.5 rgba(41,128,255,0.90), stop:1 rgba(80,140,240,0.90));
    color: #ffffff; border: 1.5px solid rgba(41,128,255,0.55); border-radius: 12px;
    padding: 10px 12px; font-size: 14px; font-weight: 800; font-family: 'Segoe UI', sans-serif;
}
QPushButton#btn_blue:disabled {
    background: rgba(20,38,78,0.60); color: rgba(110,140,190,0.55);
    border-color: rgba(40,70,140,0.30);
}
QPushButton#btn_sm {
    background: rgba(20,38,78,0.80); color: #b0c8f0;
    border: 1.5px solid rgba(41,128,255,0.40); border-radius: 10px;
    padding: 10px 18px; margin-bottom: 6px;
    font-size: 15px; font-family: 'Segoe UI', sans-serif; font-weight: 700;
    min-height: 56px; min-width: 140px;
}
QPushButton#btn_sm:hover   { background: rgba(26,48,96,0.95); border-color: rgba(41,128,255,0.80); color: #dceaff; }
QPushButton#btn_sm:pressed { background: rgba(14,26,58,0.95); }
QFrame#step_card {
    background: rgba(8,16,42,0.91); border: 2px solid rgba(41,128,255,0.50); border-radius: 20px;
}
QLabel#step_counter {
    color: rgba(110,140,190,0.85); font-size: 12px; font-weight: 700;
    font-family: 'Courier New'; letter-spacing: 3px;
}
QLabel#step_main_text { color: #dceaff; font-size: 18px; font-weight: 700; font-family: 'Segoe UI', sans-serif; }
QPushButton#dot_inactive {
    background: rgba(41,128,255,0.25); border: 2px solid rgba(41,128,255,0.35); border-radius: 4px;
    min-width: 8px; max-width: 8px; min-height: 8px; max-height: 8px;
}
QPushButton#dot_active {
    background: #2980ff; border: 2px solid rgba(41,128,255,0.90); border-radius: 5px;
    min-width: 10px; max-width: 10px; min-height: 10px; max-height: 10px;
}
/* ── Botones de acción de sesión existente ── */
QPushButton#btn_ex_red {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(140,20,20,0.96), stop:1 rgba(217,11,11,0.98));
    color: #ffffff; border: 2px solid rgba(255,107,107,0.60); border-radius: 14px;
    font-size: 18px; font-weight: 900; font-family: 'Segoe UI', sans-serif;
    min-height: 80px; padding: 0 20px;
}
QPushButton#btn_ex_red:hover  { background: rgba(200,15,15,0.98); }
QPushButton#btn_ex_red:pressed { background: rgba(150,10,10,0.98); }
QPushButton#btn_ex_green {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(42,124,50,0.96), stop:1 rgba(25,168,91,0.98));
    color: #ffffff; border: 2px solid rgba(185,234,137,0.60); border-radius: 14px;
    font-size: 18px; font-weight: 900; font-family: 'Segoe UI', sans-serif;
    min-height: 80px; padding: 0 20px;
}
QPushButton#btn_ex_green:hover  { background: rgba(22,148,80,0.98); }
QPushButton#btn_ex_green:pressed { background: rgba(18,120,65,0.98); }
"""

CAROUSEL_STEPS = [
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#e6f1fb"/>
        <path d="M12 40 Q40 14 68 40 Q40 66 12 40 Z"
              stroke="#185FA5" stroke-width="3" fill="#dceeff" stroke-linejoin="round"/>
        <circle cx="40" cy="40" r="11" stroke="#185FA5" stroke-width="3" fill="white"/>
        <circle cx="40" cy="40" r="4" fill="#185FA5"/>
     </svg>""", "guard.step1"),
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#EAF3DE"/>
        <rect x="14" y="14" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
        <rect x="44" y="14" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
        <rect x="14" y="44" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
        <rect x="44" y="44" width="22" height="22" rx="5" stroke="#3B6D11" stroke-width="3" fill="#d4edbb"/>
     </svg>""", "guard.step2"),
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#FAEEDA"/>
        <rect x="14" y="22" width="52" height="38" rx="7" stroke="#BA7517" stroke-width="3" fill="#fde8b8"/>
        <rect x="28" y="14" width="24" height="12" rx="4" stroke="#BA7517" stroke-width="2.5" fill="#fde8b8"/>
        <circle cx="40" cy="42" r="6" fill="#BA7517"/>
        <line x1="40" y1="48" x2="40" y2="54" stroke="#BA7517" stroke-width="3" stroke-linecap="round"/>
     </svg>""", "guard.step3"),
    (b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="38" fill="#EEEDFE"/>
        <path d="M18 30h44l-7 30H25L18 30z" stroke="#534AB7" stroke-width="3" fill="#dddcfa" stroke-linejoin="round"/>
        <circle cx="31" cy="64" r="4.5" fill="#534AB7"/>
        <circle cx="53" cy="64" r="4.5" fill="#534AB7"/>
        <path d="M10 18h10l7 12" stroke="#534AB7" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
     </svg>""", "guard.step4"),
]

_STEP_KEYS  = ["guard.step1", "guard.step2", "guard.step3", "guard.step4"]

_FRAME_W_FRAC = 0.62
_FRAME_H_FRAC = 0.90
_FRAME_X_FRAC = (1.0 - _FRAME_W_FRAC) / 2.0
_FRAME_Y_FRAC = (1.0 - _FRAME_H_FRAC) / 2.0
_DETECT_ROI   = (_FRAME_X_FRAC, _FRAME_Y_FRAC, _FRAME_W_FRAC, _FRAME_H_FRAC)


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
        self._y = v; self.move(self._x, v); self.update()
    scan_y = pyqtProperty(int, _get_y, _set_y)

    def update_bounds(self, fx, fy, fw, fh):
        m = 3
        self._x, self._top = fx+m, fy+m
        self._bot = fy+fh-m-self.height()
        self._width = fw-m*2
        self.setGeometry(self._x, self._top, self._width, self.height())
        self.show()
        self._anim_down.stop(); self._anim_up.stop()
        self._go_down()

    def _go_down(self):
        self._anim_down.setStartValue(self._top); self._anim_down.setEndValue(self._bot)
        self._anim_down.setDuration(self._speed_ms); self._anim_down.start()

    def _go_up(self):
        self._anim_up.setStartValue(self._bot); self._anim_up.setEndValue(self._top)
        self._anim_up.setDuration(self._speed_ms); self._anim_up.start()

    def paintEvent(self, _):
        from PyQt5.QtGui import QPainter, QLinearGradient, QBrush
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0.0, QColor(10, 20, 45)); bg.setColorAt(1.0, QColor(16, 32, 68))
        p.fillRect(0, 0, self.width(), self.height(), QBrush(bg)); p.end()


class StepOverlay(QWidget):
    """
    Overlay de pasos sobre la cámara. Avanza automáticamente y emite `finished`
    cuando termina el último paso → arranca el escaneo.
    Cada paso dura _STEP_DURATION_MS ms (900 ms, era 1400 ms).
    """
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._current  = 0
        self._dot_btns = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setAlignment(Qt.AlignCenter)

        self._card = QFrame(); self._card.setObjectName("step_card")
        card_l = QVBoxLayout(self._card)
        card_l.setContentsMargins(34, 26, 34, 26); card_l.setSpacing(16)
        card_l.setAlignment(Qt.AlignCenter)

        self._counter_lbl = QLabel()
        self._counter_lbl.setObjectName("step_counter")
        self._counter_lbl.setAlignment(Qt.AlignCenter)
        card_l.addWidget(self._counter_lbl)

        self._svg = QSvgWidget()
        self._svg.setFixedSize(110, 110)
        self._svg.setStyleSheet("background: transparent;")
        card_l.addWidget(self._svg, alignment=Qt.AlignCenter)

        self._text_lbl = QLabel()
        self._text_lbl.setObjectName("step_main_text")
        self._text_lbl.setAlignment(Qt.AlignCenter)
        self._text_lbl.setWordWrap(True)
        card_l.addWidget(self._text_lbl)

        dots_row = QHBoxLayout(); dots_row.setSpacing(8); dots_row.setAlignment(Qt.AlignCenter)
        for i in range(len(CAROUSEL_STEPS)):
            btn = QPushButton()
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setAttribute(Qt.WA_TransparentForMouseEvents)
            dots_row.addWidget(btn); self._dot_btns.append(btn)
        card_l.addLayout(dots_row)
        root.addWidget(self._card)

        self._timer = QTimer(self); self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._next_step)
        self.set_language(get_language())

    def set_language(self, _lang):
        self._render(self._current)

    def start(self):
        self._current = 0; self._render(0); self._timer.start(_STEP_DURATION_MS)

    def stop(self):
        self._timer.stop()

    def _render(self, idx):
        self._current = idx
        svg_data, _key = CAROUSEL_STEPS[idx]
        self._svg.load(svg_data)
        self._text_lbl.setText(tr(_STEP_KEYS[idx]))
        total = len(CAROUSEL_STEPS)
        self._counter_lbl.setText("PASO {} DE {}".format(idx+1, total))
        for i, btn in enumerate(self._dot_btns):
            btn.setObjectName("dot_active" if i == idx else "dot_inactive")
            btn.setStyle(btn.style())

    def _next_step(self):
        nxt = self._current + 1
        if nxt >= len(CAROUSEL_STEPS):
            self.hide(); self.finished.emit()
        else:
            self._render(nxt); self._timer.start(_STEP_DURATION_MS)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        max_w = min(self.width()-40, 500); max_w = max(max_w, 300)
        self._card.setMaximumWidth(max_w)
        self._card.setMinimumWidth(min(300, self.width()-40))


class _ExistingSessionOverlay(QWidget):
    """
    Se muestra cuando el precheck detecta que la persona YA tiene un locker
    asignado. En lugar de solo avisar con countdown, ofrece las mismas
    opciones que retirar.py:
        • RETIRAR COSAS  → cerrar sesión + liberar locker + borrar biometría
        • SEGUIR COMPRANDO → abrir locker para que guarde más cosas
    """
    retirar_clicked = pyqtSignal()
    seguir_clicked  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setAlignment(Qt.AlignCenter)

        # ── Card blanca central ───────────────────────────────────────────────
        self._card = QFrame()
        self._card.setMaximumWidth(560)
        self._card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cl = QVBoxLayout(self._card)
        cl.setContentsMargins(40, 36, 40, 36); cl.setSpacing(16)
        cl.setAlignment(Qt.AlignCenter)

        # Ícono de advertencia (ámbar)
        icon_lbl = QLabel("●")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFixedSize(90, 90)
        icon_lbl.setStyleSheet(
            "background: rgba(251,191,36,0.15); color: #f59e0b; border-radius: 45px;"
            "font-size: 44px; font-weight: 900; font-family: 'Segoe UI';"
        )
        cl.addWidget(icon_lbl, alignment=Qt.AlignCenter)

        # Badge
        badge = QLabel("SESIÓN ACTIVA")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedHeight(28)
        badge.setStyleSheet(
            "background: rgba(254,243,199,0.95); color: #92400e;"
            "border: 1px solid rgba(251,191,36,0.80); border-radius: 10px;"
            "font-size: 10px; font-weight: 800; font-family: 'Segoe UI';"
            "letter-spacing: 3px; padding: 4px 16px;"
        )
        cl.addWidget(badge, alignment=Qt.AlignCenter)

        # Título
        title = QLabel("Ya tienes un locker asignado")
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet(
            "color: #92400e; font-size: 24px; font-weight: 900;"
            "font-family: 'Segoe UI';"
        )
        cl.addWidget(title)

        # Número de locker
        self._locker_lbl = QLabel("")
        self._locker_lbl.setAlignment(Qt.AlignCenter)
        self._locker_lbl.setStyleSheet(
            "color: #1a1a1a; font-size: 58px; font-weight: 900;"
            "font-family: 'Segoe UI'; letter-spacing: 2px;"
        )
        cl.addWidget(self._locker_lbl)

        # Subtítulo
        sub = QLabel("¿Qué deseas hacer?")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(
            "color: #374151; font-size: 15px; font-family: 'Segoe UI';"
        )
        cl.addWidget(sub)

        # Separador
        div = QFrame()
        div.setStyleSheet("background: rgba(251,191,36,0.55); border:none; min-height:1px; max-height:1px;")
        cl.addWidget(div)

        # Botones de acción
        btn_row = QHBoxLayout(); btn_row.setSpacing(16)
        self._btn_retirar = QPushButton("↩  RETIRAR COSAS")
        self._btn_retirar.setObjectName("btn_ex_red")
        self._btn_retirar.setCursor(Qt.PointingHandCursor)
        self._btn_retirar.setFocusPolicy(Qt.NoFocus)
        self._btn_retirar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._btn_retirar.clicked.connect(self.retirar_clicked)

        self._btn_seguir = QPushButton("→  SEGUIR COMPRANDO")
        self._btn_seguir.setObjectName("btn_ex_green")
        self._btn_seguir.setCursor(Qt.PointingHandCursor)
        self._btn_seguir.setFocusPolicy(Qt.NoFocus)
        self._btn_seguir.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._btn_seguir.clicked.connect(self.seguir_clicked)

        btn_row.addWidget(self._btn_retirar, 1)
        btn_row.addWidget(self._btn_seguir, 1)
        cl.addLayout(btn_row)

        root.addWidget(self._card, alignment=Qt.AlignCenter)

    def show_for(self, locker_num):
        """Muestra el overlay con el número de locker ya asignado."""
        num_str = str(locker_num) if locker_num else "?"
        self._locker_lbl.setText(f"#{num_str}")
        self._btn_retirar.setEnabled(True)
        self._btn_seguir.setEnabled(True)
        self.setGeometry(self.parent().rect() if self.parent() else self.rect())
        self.raise_()
        self.setVisible(True)

    def disable_buttons(self):
        """Deshabilita los botones tras pulsar uno (evita doble acción)."""
        self._btn_retirar.setEnabled(False)
        self._btn_seguir.setEnabled(False)

    def paintEvent(self, _):
        p = QPainter(self)
        # Fondo semitransparente oscuro (mismo tono del diseño)
        p.fillRect(self.rect(), QColor(10, 20, 45, 220))
        # Glow ámbar tenue en el centro
        rg = QRadialGradient(self.width()/2, self.height()/2, self.height()*0.55)
        glow = QColor(251, 191, 36); glow.setAlpha(22)
        rg.setColorAt(0.0, glow); rg.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(rg))
        # Estilo de la card (blanco)
        self._card.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid rgba(251,191,36,0.70);
                border-top: 4px solid #f59e0b;
                border-radius: 18px;
            }
        """)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────

class GuardarPage(QWidget):
    done         = pyqtSignal(str, str, int)   # face_uid, num_locker, id_sesion
    failed       = pyqtSignal(str)
    go_back      = pyqtSignal()
    # Emitidos cuando el usuario elige desde la sesión existente detectada
    retirar_done = pyqtSignal(str, str, int)   # face_uid, num_locker, id_sesion
    seguir_done  = pyqtSignal(str, str, int)   # face_uid, num_locker, id_sesion

    _CAM_W = 440
    _CAM_H = 390
    _PRECHECK_TIMEOUT_MS = 4000   # era 6000 → más rápido si no reconoce a nadie

    def __init__(self):
        super().__init__()
        self.setObjectName("guardar_page")
        self.setStyleSheet(STYLE)
        self.cam_thread       = None
        self._face_uid        = None
        self._id_locker       = None
        self._num_locker      = None
        self._capture_started = False
        self._phase           = None
        self._action_done     = False

        # Estado de la sesión existente detectada en el precheck
        self._existing_face_uid  = None
        self._existing_id_sesion = None
        self._existing_id_locker = None
        self._existing_num_locker = None

        self._pre_check_timer = QTimer(self)
        self._pre_check_timer.setSingleShot(True)
        self._pre_check_timer.timeout.connect(self._on_precheck_timeout)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 6)
        root.setSpacing(4)

        # ── Header ───────────────────────────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(6)
        self.back_btn = QPushButton("")
        back = self.back_btn
        back.setObjectName("btn_sm")
        back.setFixedHeight(touch_height(64))
        back.setMinimumWidth(140)
        back.setCursor(Qt.PointingHandCursor)
        back.setFocusPolicy(Qt.NoFocus)
        back.clicked.connect(self._cancel)
        htxt = QVBoxLayout(); htxt.setSpacing(0)
        self.title_lbl    = lbl("", "h2")
        self.subtitle_lbl = lbl("", "tag")
        htxt.addWidget(self.title_lbl)
        htxt.addWidget(self.subtitle_lbl)

        self.err_lbl = lbl("", "err")
        self.err_lbl.setWordWrap(True)
        self.err_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        hdr.addWidget(back); hdr.addSpacing(6); hdr.addLayout(htxt)
        hdr.addStretch(); hdr.addWidget(self.err_lbl)
        root.addLayout(hdr)
        root.addWidget(sep_line())

        # ── Body: cámara a pantalla completa ─────────────────────────────────
        body = QHBoxLayout(); body.setSpacing(0); body.setContentsMargins(6, 4, 6, 4)
        cam_card = QFrame(); cam_card.setObjectName("cam_card")
        cam_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rl = QVBoxLayout(cam_card); rl.setContentsMargins(6, 6, 6, 6); rl.setSpacing(4)

        self.scan_title_lbl = lbl("", "tag", Qt.AlignCenter)
        rl.addWidget(self.scan_title_lbl, 0)

        self.cam = CamWidget(self._CAM_W, self._CAM_H)
        self.cam.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rl.addWidget(self.cam, 1)

        body.addWidget(cam_card, 1)
        root.addLayout(body, 1)

        # ── Overlays sobre la cámara ──────────────────────────────────────────
        self.face_guide = QSvgWidget(self.cam)
        self.face_guide.load(b"""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120">
              <circle cx="50" cy="38" r="26"
                      fill="none" stroke="#B9EA89" stroke-width="2.5"
                      stroke-dasharray="6 4" opacity="0.85"/>
              <path d="M4 120 Q4 78 50 78 Q96 78 96 120 Z"
                    fill="none" stroke="#B9EA89" stroke-width="2.5"
                    stroke-dasharray="6 4" opacity="0.85"/>
              <line x1="50" y1="32" x2="50" y2="44" stroke="#B9EA89" stroke-width="1.5" opacity="0.6"/>
              <line x1="44" y1="38" x2="56" y2="38" stroke="#B9EA89" stroke-width="1.5" opacity="0.6"/>
            </svg>""")
        self.face_guide.setStyleSheet("background: transparent;")
        self.face_guide.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.face_guide.setVisible(False)

        self.scan_frame = QFrame(self.cam)
        self.scan_frame.setStyleSheet("border: 3px solid #B9EA89; border-radius: 8px; background: transparent;")
        self.scan_frame.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.scan_frame.setVisible(False)

        self.scan_line = ScanLine(self.cam)

        # StepOverlay (hijo de self.cam)
        self._step_overlay = StepOverlay(self.cam)
        self._step_overlay.finished.connect(self._start_capture)
        self._step_overlay.setVisible(False)

        # ExistingSessionOverlay (hijo de self — cubre toda la página)
        # Reemplaza al BlockedOverlay: en vez de solo avisar, ofrece acción
        self._existing_overlay = _ExistingSessionOverlay(self)
        self._existing_overlay.retirar_clicked.connect(self._do_retirar_existing)
        self._existing_overlay.seguir_clicked.connect(self._do_seguir_existing)

        self.set_language(get_language())

    # ── Fondo ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0.0, BG_TOP); bg.setColorAt(1.0, BG_BOT)
        p.fillRect(0, 0, W, H, bg)
        hh = 96
        hg = QLinearGradient(0, 0, 0, hh)
        hg.setColorAt(0.0, QColor(13, 24, 54)); hg.setColorAt(1.0, QColor(10, 20, 45))
        p.setPen(Qt.NoPen); p.setBrush(hg); p.drawRect(0, 0, W, hh)
        p.setPen(QColor(41, 128, 255, 140)); p.drawLine(0, hh-1, W, hh-1)
        p.setPen(QColor(40, 70, 140, 28))
        step = 48
        for x in range(0, W+step, step): p.drawLine(x, hh, x, H)
        for y in range(hh, H+step, step): p.drawLine(0, y, W, y)
        p.end()

    # ── Idioma ────────────────────────────────────────────────────────────────

    def set_language(self, lang: str):
        self.back_btn.setText(tr("guard.back"))
        self.title_lbl.setText(tr("guard.title"))
        self.subtitle_lbl.setText(tr("guard.subtitle"))
        self.scan_title_lbl.setText(tr("guard.scan_title"))
        self._step_overlay.set_language(lang)

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def showEvent(self, e):
        super().showEvent(e)
        self._capture_started = False
        self._action_done     = False
        result = db_next_free_locker()
        if result:
            self._id_locker, self._num_locker = result
            self.err_lbl.setText("")
            QTimer.singleShot(400, self._show_steps)
        else:
            self._id_locker  = None
            self._num_locker = None
            self.err_lbl.setText(tr("guard.no_lockers_now"))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_overlay)
        if self._step_overlay.isVisible():
            self._step_overlay.setGeometry(0, 0, self.cam.width(), self.cam.height())
        if self._existing_overlay.isVisible():
            self._existing_overlay.setGeometry(self.rect())

    # ── Pasos de instrucciones ────────────────────────────────────────────────

    def _show_steps(self):
        self._step_overlay.setGeometry(0, 0, self.cam.width(), self.cam.height())
        self._step_overlay.raise_()
        self._step_overlay.setVisible(True)
        self._step_overlay.start()

    # ── Captura (fase 1: precheck → fase 2: captura real) ────────────────────

    def _start_capture(self):
        if self._capture_started:
            return
        self._capture_started = True
        if not self._id_locker:
            self._capture_started = False
            self.err_lbl.setText(tr("guard.no_lockers"))
            beep_error()
            return
        self._stop_cam_thread()
        tmp_uid = "tmp_{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        self._face_uid = tmp_uid
        self.err_lbl.setText("")
        self.scan_frame.setVisible(True)
        self.face_guide.setVisible(True)
        self._update_overlay()
        beep_start_scan()

        labels = train_model()
        if labels:
            self._phase = "precheck"
            self.scan_title_lbl.setText(tr("guard.verifying"))
            self._pre_check_timer.start(self._PRECHECK_TIMEOUT_MS)
            self.cam_thread = CamThread(CamThread.RECOGNIZE, labels=labels, detect_roi=_DETECT_ROI)
            self.cam_thread.frame_sig.connect(self.cam.update_frame)
            self.cam_thread.rec_done.connect(self._on_precheck_done)
            self.cam_thread.finished.connect(self._on_cam_thread_finished)
            self.cam_thread.start()
        else:
            # No hay biometría registrada → pasar directo a captura
            self._start_phase2_capture()

    def _stop_cam_thread(self):
        if self.cam_thread:
            if self.cam_thread.isRunning():
                self.cam_thread.stop()
                if not self.cam_thread.wait(2000):
                    self.cam_thread.terminate(); self.cam_thread.wait(1000)
            self.cam_thread = None

    def _on_cam_thread_finished(self):
        sender = self.sender()
        if sender is self.cam_thread:
            self.cam_thread = None

    def _on_precheck_timeout(self):
        """Timeout: nadie fue reconocido → proceder a captura normal."""
        self._stop_cam_thread()
        self._start_phase2_capture()

    def _on_precheck_done(self, face_uid: str):
        """
        Resultado del precheck biométrico.
        - Si reconoce a alguien con sesión activa → mostrar opciones RETIRAR/SEGUIR
        - Si no reconoce a nadie (o error) → proceder a captura normal
        """
        self._pre_check_timer.stop()

        if face_uid and face_uid != CamThread.CAMERA_ERROR:
            sesion = db_get_active_sesion_by_face(face_uid)
            if sesion:
                # ── Persona con locker activo detectada ─────────────────────
                if isinstance(sesion, dict):
                    id_locker_e  = sesion.get("ID_locker")
                    id_sesion_e  = sesion.get("ID_sesion")
                else:
                    id_sesion_e  = sesion[0]
                    id_locker_e  = sesion[1] if len(sesion) > 1 else None

                num_e = db_get_locker_num_by_id(id_locker_e) if id_locker_e else "?"
                beep_error()
                self._stop_cam_thread()
                self._capture_started = False
                self.scan_frame.setVisible(False)
                self.scan_line.hide()
                self.face_guide.setVisible(False)
                self.scan_title_lbl.setText(tr("guard.scan_title"))

                db_log_intento(
                    id_locker_e or 0, "registro_biometrico", "sesion_activa",
                    f"Persona ya tiene locker #{num_e} activo. Se ofrecen opciones retirar/seguir."
                )

                # Guardar estado para las acciones posteriores
                self._existing_face_uid   = face_uid
                self._existing_id_sesion  = id_sesion_e
                self._existing_id_locker  = id_locker_e
                self._existing_num_locker = num_e
                self._action_done         = False

                # Mostrar overlay con opciones (en lugar de BlockedOverlay con countdown)
                self._show_existing_session(num_e)
                return

        # No hay sesión activa → proceder a captura nueva
        self._start_phase2_capture()

    def _show_existing_session(self, locker_num):
        """
        Muestra el overlay con las mismas opciones que retirar.py:
        RETIRAR COSAS o SEGUIR COMPRANDO.
        """
        self._existing_overlay.setGeometry(self.rect())
        self._existing_overlay.raise_()
        self._existing_overlay.show_for(locker_num)

    # ── Acciones de sesión existente ──────────────────────────────────────────

    def _do_retirar_existing(self):
        """
        Cliente quiere retirar sus cosas:
        1. Abrir cerradura física
        2. Borrar datos biométricos
        3. Cerrar sesión en BD
        4. Marcar locker como libre
        5. Reentrenar modelo
        """
        if self._action_done:
            return
        self._action_done = True
        self._existing_overlay.disable_buttons()

        num  = self._existing_num_locker
        f_uid = self._existing_face_uid
        id_s  = self._existing_id_sesion
        id_l  = self._existing_id_locker

        # Nota: LED solo dentro de abrir_locker() en gpio_locker.py
        abrir_locker(str(num))
        delete_face_data(f_uid)
        db_close_sesion(id_s)
        db_set_locker_estado(id_l, "libre")

        db_log_intento(id_l, "retirar_desde_guardar", "exitoso",
                       f"Cliente retiró sus cosas. Sesión {id_s} cerrada desde guardar.")

        import threading
        threading.Thread(target=train_model, daemon=True).start()

        self._existing_overlay.setVisible(False)
        self.retirar_done.emit(f_uid, str(num), id_s)

    def _do_seguir_existing(self):
        """
        Cliente quiere seguir comprando (no retira todavía):
        1. Abrir cerradura para que guarde más cosas
        2. La sesión sigue activa (no se cierra)
        """
        if self._action_done:
            return
        self._action_done = True
        self._existing_overlay.disable_buttons()

        num  = self._existing_num_locker
        f_uid = self._existing_face_uid
        id_s  = self._existing_id_sesion
        id_l  = self._existing_id_locker

        # Nota: LED solo dentro de abrir_locker() en gpio_locker.py
        abrir_locker(str(num))

        db_log_intento(id_l, "seguir_comprando_desde_guardar", "exitoso",
                       f"Cliente sigue comprando. Locker #{num} abierto desde guardar.",
                       id_sesion=id_s)

        self._existing_overlay.setVisible(False)
        self.seguir_done.emit(f_uid, str(num), id_s)

    # ── Captura fase 2 ────────────────────────────────────────────────────────

    def _start_phase2_capture(self):
        self._phase = "capture"
        self._stop_cam_thread()
        self.scan_title_lbl.setText(tr("guard.scan_title"))
        self.cam_thread = CamThread(CamThread.CAPTURE, face_uid=self._face_uid, detect_roi=_DETECT_ROI)
        self.cam_thread.frame_sig.connect(self.cam.update_frame)
        self.cam_thread.progress.connect(self.cam.set_progress)
        self.cam_thread.cap_done.connect(self._on_capture_done)
        self.cam_thread.finished.connect(self._on_cam_thread_finished)
        self.cam_thread.start()

    def _on_capture_done(self, ok, tmp_uid):
        self._capture_started = False
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

        # Nota: el LED de apertura SOLO debe encenderse dentro de abrir_locker()
        # en gpio_locker.py. Verificar que beep_start_scan/beep_success no lo activen.
        abrir_locker(str(num_locker))

        db_log_intento(id_locker, "registro_biometrico", "exitoso",
                       "Sesion {} creada. Locker #{} asignado.".format(id_sesion, num_locker),
                       id_sesion=id_sesion)

        import threading
        threading.Thread(target=train_model, daemon=True).start()

        self._id_locker  = None
        self._num_locker = None
        self.done.emit(face_uid, num_locker, id_sesion)

    # ── Cancelar / reset ──────────────────────────────────────────────────────

    def _cancel(self):
        self._pre_check_timer.stop()
        self._step_overlay.stop()
        self._existing_overlay.setVisible(False)
        self._stop_cam_thread()
        if self._face_uid:
            delete_face_data(self._face_uid)
        self.go_back.emit()

    def reset(self):
        self._pre_check_timer.stop()
        self._step_overlay.stop()
        self._existing_overlay.setVisible(False)
        self._stop_cam_thread()
        self._face_uid           = None
        self._id_locker          = None
        self._num_locker         = None
        self._capture_started    = False
        self._phase              = None
        self._action_done        = False
        self._existing_face_uid  = None
        self._existing_id_sesion = None
        self._existing_id_locker = None
        self._existing_num_locker = None
        self.err_lbl.setText("")
        self.cam.idle()
        self.scan_frame.setVisible(False)
        self.scan_line.hide()
        self.face_guide.setVisible(False)
        self._step_overlay.setVisible(False)

    def _update_overlay(self):
        cam_w = self.cam.width(); cam_h = self.cam.height()
        frame_w = int(cam_w * _FRAME_W_FRAC); frame_h = int(cam_h * _FRAME_H_FRAC)
        frame_x = (cam_w - frame_w) // 2;     frame_y = (cam_h - frame_h) // 2
        self.scan_frame.setGeometry(frame_x, frame_y, frame_w, frame_h)
        self.face_guide.setGeometry(frame_x, frame_y, frame_w, frame_h)
        self.scan_line.update_bounds(frame_x, frame_y, frame_w, frame_h)