import os
import platform
import subprocess
import shutil
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QFrame, QSizePolicy, QLabel, QApplication
)
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QPen,
    QLinearGradient, QRadialGradient, QPixmap, QPainterPath
)

from db.models.intentos_acceso import db_log_intento
from db.models.usuarios import db_admin_exists, db_admin_valid, db_get_admin_by_username
from utils.i18n import tr, get_language


def _dp(v):
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    scale = min(dpi / 96, 1.25)
    return max(1, round(v * scale))


# ── Paleta ────────────────────────────────────────────────────────────────────
BG_TOP      = QColor(10,  20,  45)
BG_BOT      = QColor(16,  32,  68)
ACCENT_BLUE = QColor(41, 128, 255)
CARD_BG     = QColor(20,  38,  78)
CARD_BORDER = QColor(40,  70, 140)


STYLE = """
QWidget#admin_login_page { background: transparent; }
QFrame#card              { background: transparent; border: none; }

QLineEdit#inp {
    background-color: rgba(255,255,255,0.06);
    border: 2px solid rgba(41,128,255,0.28);
    border-radius: 12px;
    color: #ddeeff;
    font-family: 'Segoe UI', sans-serif;
    selection-background-color: rgba(41,128,255,0.50);
}
QLineEdit#inp:hover {
    border-color: rgba(41,128,255,0.55);
    background-color: rgba(41,128,255,0.08);
}
QLineEdit#inp:focus {
    border: 2px solid rgba(41,128,255,1.0);
    background-color: rgba(41,128,255,0.13);
}

QPushButton#btn_primary {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #3d90ff, stop:1 #1a60e0);
    color: #ffffff;
    border: 1px solid rgba(100,180,255,0.40);
    border-radius: 12px;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
}
QPushButton#btn_primary:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #55aaff, stop:1 #2575f5);
    border-color: rgba(130,200,255,0.60);
}
QPushButton#btn_primary:pressed {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #1050c0, stop:1 #0a3a99);
}

QPushButton#btn_ghost {
    background: rgba(255,255,255,0.06);
    color: rgba(160,200,255,0.85);
    border: 1.5px solid rgba(41,128,255,0.30);
    border-radius: 12px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#btn_ghost:hover {
    background: rgba(41,128,255,0.14);
    border-color: rgba(41,128,255,0.65);
    color: #ffffff;
}
QPushButton#btn_ghost:pressed { background: rgba(41,128,255,0.07); }

QLabel#err {
    color: #ff7777;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Teclado nativo — con onboard en modo docked para que NO robe el foco
# ─────────────────────────────────────────────────────────────────────────────
_kbd_process  = None
_main_window  = None   # referencia a la ventana principal para restaurar foco


def _configure_onboard_docked():
    """
    Configura onboard para que se ancle en la parte inferior como panel.
    En modo docked NO roba el foco de la aplicación.
    """
    settings = [
        # Anclar en la parte inferior
        ("org.onboard.window",         "docking-enabled",        "true"),
        ("org.onboard.window.docking", "side",                   "'bottom'"),
        # Que no tome el foco al aparecer
        ("org.onboard",                "show-tooltips",          "false"),
        # Layout compacto para pantalla pequeña
        ("org.onboard",                "layout",
         "/usr/share/onboard/layouts/Phone.onboard"),
        ("org.onboard",                "theme",
         "/usr/share/onboard/themes/Nightshade.theme"),
    ]
    for schema, key, value in settings:
        try:
            subprocess.run(
                ["gsettings", "set", schema, key, value],
                capture_output=True, timeout=2
            )
        except Exception:
            pass


def _open_native_keyboard(restore_widget: QWidget = None):
    """
    Abre el teclado nativo.  En Linux configura onboard como panel docked
    antes de lanzarlo para que no robe el foco.
    `restore_widget` : widget al que se restaura el foco tras abrir el teclado.
    """
    global _kbd_process

    # Si ya está abierto no volver a lanzar
    if _kbd_process is not None and _kbd_process.poll() is None:
        return

    try:
        os_name = platform.system()

        if os_name == "Windows":
            subprocess.Popen(
                r"C:\Program Files\Common Files\Microsoft Shared\ink\TabTip.exe",
                shell=True
            )

        elif os_name == "Linux":
            if shutil.which("onboard"):
                _configure_onboard_docked()
                # --keep-aspect evita que redimensione la ventana principal
                _kbd_process = subprocess.Popen(["onboard", "--keep-aspect"])
            else:
                # Fallback a otros teclados disponibles
                for kbd in ["matchbox-keyboard", "florence",
                            "squeekboard", "wvkbd-mobintl"]:
                    if shutil.which(kbd):
                        _kbd_process = subprocess.Popen([kbd])
                        break

        # Restaurar foco al campo después de que el teclado haya abierto su
        # ventana (onboard tarda ~300 ms en dibujarse).
        if restore_widget is not None:
            def _restore():
                try:
                    top = restore_widget.window()
                    top.activateWindow()
                    top.raise_()
                    restore_widget.setFocus()
                except Exception:
                    pass

            QTimer.singleShot(350, _restore)

    except Exception:
        pass


def _close_native_keyboard():
    global _kbd_process
    try:
        os_name = platform.system()
        if os_name == "Windows":
            subprocess.run(
                ["taskkill", "/IM", "TabTip.exe", "/F"],
                capture_output=True
            )
        elif os_name == "Linux":
            if _kbd_process and _kbd_process.poll() is None:
                _kbd_process.terminate()
                _kbd_process = None
            # Matar cualquier instancia huérfana de onboard
            try:
                subprocess.run(["pkill", "-x", "onboard"],
                               capture_output=True)
            except Exception:
                pass
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  InputField — abre el teclado en mousePressEvent, NO en focusInEvent
#  Esto evita el ciclo foco → teclado → roba foco → pierde foco
# ─────────────────────────────────────────────────────────────────────────────
class InputField(QWidget):
    def __init__(self, icon: str, placeholder: str,
                 password=False, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(_dp(10))

        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setFixedWidth(_dp(40))
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet(
            f"font-size: {_dp(22)}px; background: transparent;"
        )

        self.line = QLineEdit()
        self.line.setObjectName("inp")
        if password:
            self.line.setEchoMode(QLineEdit.Password)
        self.line.setPlaceholderText(placeholder)
        self.line.setFixedHeight(_dp(60))
        self.line.setStyleSheet(
            f"font-size: {_dp(15)}px; padding: 0 {_dp(16)}px;"
        )

        # ── Clave: abrir teclado en mousePressEvent, no en focusInEvent ───────
        # focusInEvent puede dispararse por Tab, programáticamente, etc.
        # mousePressEvent solo se dispara cuando el usuario toca el campo.
        orig_mouse_press = self.line.mousePressEvent

        def _on_mouse_press(e):
            orig_mouse_press(e)                          # procesar click normal
            # Abrir teclado y restaurar foco a este campo
            _open_native_keyboard(restore_widget=self.line)

        self.line.mousePressEvent = _on_mouse_press

        row.addWidget(self.icon_lbl)
        row.addWidget(self.line, 1)
        lay.addLayout(row)

    # ── API pública ───────────────────────────────────────────────────────────
    def text(self):                  return self.line.text()
    def clear(self):                 self.line.clear()
    def setFocus(self):              self.line.setFocus()
    def returnPressed(self):         return self.line.returnPressed
    def installEventFilter(self, f): self.line.installEventFilter(f)


# ─────────────────────────────────────────────────────────────────────────────
#  Panel izquierdo decorativo
# ─────────────────────────────────────────────────────────────────────────────
class LeftPanel(QWidget):
    def __init__(self, logo_path, parent=None):
        super().__init__(parent)
        self.setFixedWidth(_dp(300))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(_dp(20), _dp(28), _dp(20), _dp(28))
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignVCenter)

        logo_lbl = QLabel()
        logo_lbl.setFixedSize(_dp(256), _dp(140))
        logo_lbl.setAlignment(Qt.AlignCenter)
        px = QPixmap(logo_path)
        if not px.isNull():
            logo_lbl.setPixmap(
                px.scaled(_dp(248), _dp(132),
                           Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        lay.addWidget(logo_lbl, 0, Qt.AlignCenter)
        lay.addSpacing(_dp(22))

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color: rgba(41,128,255,0.28);")
        lay.addWidget(div)
        lay.addSpacing(_dp(22))

        desc = QLabel("PANEL\nADMINISTRATIVO")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet(
            f"color: rgba(100,155,255,0.65); font-size: {_dp(11)}px;"
            f"font-family: 'Segoe UI'; font-weight: 800; letter-spacing: 4px;"
        )
        lay.addWidget(desc)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, W, H), _dp(20), _dp(20))
        p.setClipPath(path)

        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0.0, QColor(10, 22, 54))
        bg.setColorAt(1.0, QColor(7,  16, 42))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(bg))
        p.drawPath(path)

        rg = QRadialGradient(W, 0, _dp(200))
        rg.setColorAt(0.0, QColor(41, 128, 255, 25))
        rg.setColorAt(1.0, QColor(0,  0,   0,   0))
        p.setBrush(QBrush(rg))
        p.drawRect(0, 0, W, H)

        p.setClipping(False)
        p.setPen(QPen(QColor(40, 80, 160, 100), _dp(1)))
        p.drawLine(W - 1, _dp(16), W - 1, H - _dp(16))
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  AdminLoginPage
# ─────────────────────────────────────────────────────────────────────────────
class AdminLoginPage(QWidget):
    go_back  = pyqtSignal()
    login_ok = pyqtSignal(dict)

    _CARD_W = 880
    _CARD_H = 420

    def __init__(self):
        super().__init__()
        self.setObjectName("admin_login_page")
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        # ── Tarjeta central ───────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("card")
        card.setFixedSize(_dp(self._CARD_W), _dp(self._CARD_H))
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        card_row = QHBoxLayout(card)
        card_row.setContentsMargins(0, 0, 0, 0)
        card_row.setSpacing(0)

        # Panel izquierdo
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        logo_path = os.path.join(project_root, "logo_LockZtar_Negro.png")
        self._left = LeftPanel(logo_path)
        card_row.addWidget(self._left)

        # ── Columna derecha ───────────────────────────────────────────────────
        right_w = QWidget()
        right_w.setStyleSheet("background: transparent;")
        right = QVBoxLayout(right_w)
        right.setContentsMargins(_dp(30), _dp(30), _dp(30), _dp(30))
        right.setSpacing(0)
        right.setAlignment(Qt.AlignVCenter)

        self.title_lbl = QLabel("LOCKZTAR")
        self.title_lbl.setStyleSheet(
            f"color: #ddeeff; font-size: {_dp(22)}px; font-weight: 900;"
            f"font-family: 'Segoe UI'; letter-spacing: 2px;"
        )
        right.addWidget(self.title_lbl)
        right.addSpacing(_dp(4))

        self.sub_lbl = QLabel("PANEL ADMINISTRATIVO")
        self.sub_lbl.setStyleSheet(
            f"color: rgba(100,155,255,0.75); font-size: {_dp(9)}px;"
            f"font-family: 'Segoe UI'; letter-spacing: 3px; font-weight: 700;"
        )
        right.addWidget(self.sub_lbl)
        right.addSpacing(_dp(24))

        self._user_field = InputField("👤", "", password=False)
        self._user_field.installEventFilter(self)
        right.addWidget(self._user_field)
        right.addSpacing(_dp(14))

        self._pass_field = InputField("🔒", "", password=True)
        self._pass_field.installEventFilter(self)
        self._pass_field.returnPressed().connect(self._check)
        right.addWidget(self._pass_field)
        right.addSpacing(_dp(10))

        self.err_lbl = QLabel("")
        self.err_lbl.setObjectName("err")
        self.err_lbl.setStyleSheet(f"font-size: {_dp(10)}px;")
        self.err_lbl.setMinimumHeight(_dp(18))
        self.err_lbl.setWordWrap(True)
        right.addWidget(self.err_lbl)
        right.addSpacing(_dp(14))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(_dp(12))

        self.back_btn = QPushButton("‹  Volver")
        self.back_btn.setObjectName("btn_ghost")
        self.back_btn.setFixedHeight(_dp(58))
        self.back_btn.setStyleSheet(
            f"font-size: {_dp(13)}px; padding: 0 {_dp(16)}px;"
        )
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setFocusPolicy(Qt.NoFocus)
        self.back_btn.clicked.connect(self._on_back)
        btn_row.addWidget(self.back_btn, 1)

        self.btn_in = QPushButton("INGRESAR  ›")
        self.btn_in.setObjectName("btn_primary")
        self.btn_in.setFixedHeight(_dp(58))
        self.btn_in.setStyleSheet(
            f"font-size: {_dp(15)}px; padding: 0 {_dp(20)}px; font-weight: 900;"
        )
        self.btn_in.setCursor(Qt.PointingHandCursor)
        self.btn_in.clicked.connect(self._check)
        btn_row.addWidget(self.btn_in, 2)

        right.addLayout(btn_row)
        card_row.addWidget(right_w, 1)
        root.addWidget(card)

        self._user_field.setFocus()
        self.set_language(get_language())

    # ── Fondo ─────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0.0, BG_TOP)
        bg.setColorAt(1.0, BG_BOT)
        p.fillRect(0, 0, W, H, QBrush(bg))

        p.setPen(QPen(QColor(40, 70, 140, 22), _dp(1)))
        step = _dp(48)
        for x in range(0, W + step, step):
            p.drawLine(x, 0, x, H)
        for y in range(0, H + step, step):
            p.drawLine(0, y, W, y)

        for rx, ry, col in [
            (W, 0, QColor(41, 128, 255, 16)),
            (0, H, QColor(20,  80, 200, 12)),
        ]:
            rg = QRadialGradient(rx, ry, _dp(320))
            rg.setColorAt(0.0, col)
            rg.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(rg))
            p.drawRect(0, 0, W, H)

        cw = _dp(self._CARD_W)
        ch = _dp(self._CARD_H)
        cx = (W - cw) // 2
        cy = (H - ch) // 2

        for off in range(5, 0, -1):
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(0, 0, 0, int(65 * off / 5))))
            p.drawRoundedRect(cx + off, cy + off * 2,
                              cw, ch, _dp(20), _dp(20))

        card_path = QPainterPath()
        card_path.addRoundedRect(QRectF(cx, cy, cw, ch), _dp(20), _dp(20))
        cbg = QLinearGradient(cx, cy, cx, cy + ch)
        cbg.setColorAt(0.0, QColor(22, 42, 88))
        cbg.setColorAt(1.0, QColor(15, 30, 65))
        p.setBrush(QBrush(cbg))
        p.drawPath(card_path)

        shim = QLinearGradient(cx, cy, cx + cw, cy)
        shim.setColorAt(0.0,  QColor(255, 255, 255, 0))
        shim.setColorAt(0.45, QColor(255, 255, 255, 12))
        shim.setColorAt(1.0,  QColor(255, 255, 255, 0))
        p.setBrush(QBrush(shim))
        p.drawRect(QRectF(cx, cy, cw, _dp(2)))

        p.setPen(QPen(QColor(40, 80, 160, 130), _dp(1.5)))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(
            QRectF(cx + .5, cy + .5, cw - 1, ch - 1),
            _dp(20), _dp(20)
        )
        p.end()

    # ── Idioma ────────────────────────────────────────────────────────────────
    def set_language(self, lang: str):
        self.back_btn.setText("‹  " + tr("login.back"))
        self._user_field.line.setPlaceholderText(tr("login.user_ph"))
        self._pass_field.line.setPlaceholderText(tr("login.pass_ph"))
        self.btn_in.setText(tr("login.enter").upper() + "  ›")

    # ── Compatibilidad ────────────────────────────────────────────────────────
    @property
    def user_inp(self): return self._user_field
    @property
    def pass_inp(self): return self._pass_field

    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)

    # ── Volver ────────────────────────────────────────────────────────────────
    def _on_back(self):
        _close_native_keyboard()
        self.go_back.emit()

    # ── Login ─────────────────────────────────────────────────────────────────
    def _check(self):
        u  = self._user_field.text().strip()
        pw = self._pass_field.text()

        if not u or not pw:
            self.err_lbl.setText("⚠  " + tr("login.fill_fields"))
            return
        if not db_admin_exists(u):
            self.err_lbl.setText("✖  " + tr("login.bad_access"))
            try:
                db_log_intento(0, "acceso_admin", "fallido",
                               f"Intento con usuario: {u}")
            except Exception:
                pass
            return
        if not db_admin_valid(u, pw):
            self.err_lbl.setText("✖  " + tr("login.bad_access"))
            self._pass_field.clear()
            try:
                db_log_intento(0, "acceso_admin", "fallido",
                               f"Contraseña incorrecta para: {u}")
            except Exception:
                pass
            return

        admin = db_get_admin_by_username(u)
        try:
            db_log_intento(0, "acceso_admin", "exitoso",
                           f"Admin {u} ingresó al panel.",
                           id_usuario=admin["ID_admin"])
        except Exception:
            pass

        self.err_lbl.setText("")
        self._user_field.clear()
        self._pass_field.clear()
        _close_native_keyboard()
        self.login_ok.emit(admin)

    def reset(self):
        self._user_field.clear()
        self._pass_field.clear()
        self.err_lbl.setText("")
        self._user_field.setFocus()