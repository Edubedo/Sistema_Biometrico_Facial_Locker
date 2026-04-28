import os
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QFrame, QSizePolicy, QLabel, QApplication, QGridLayout
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QPixmap

from db.models.intentos_acceso import db_log_intento
from db.models.usuarios import db_admin_exists, db_admin_valid, db_get_admin_by_username
from views.style.widgets.widgets import sep_line
from utils.i18n import tr, get_language


def _dp(v):
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    scale = min(dpi / 96, 1.25)
    return max(1, round(v * scale))


def lbl(text, obj="", align=Qt.AlignLeft):
    l = QLabel(text)
    if obj:
        l.setObjectName(obj)
    l.setAlignment(align)
    return l


STYLE = """
QWidget#admin_login_page {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #b3e0ff, stop:1 #87CEEB);
}

QFrame#card {
    background-color: white;
    border: 1px solid #c0dcf0;
    border-radius: 20px;
}

QLabel#brand_icon {
    color: #145388;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#brand_name {
    color: #145388;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
}
QLabel#headline {
    color: #145388;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#eyebrow {
    color: #000000;
    font-weight: 600;
    letter-spacing: 4px;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#field_lbl {
    color: #1e4b6e;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 500;
}
QFrame#div {
    background: #7bb3d9;
    min-height: 2px;
    max-height: 2px;
    border: none;
}

QLineEdit#inp {
    background-color: #f0f8ff;
    border: 2px solid #b8d6f0;
    border-radius: 10px;
    color: #0a2a44;
    font-family: 'Segoe UI', sans-serif;
}
QLineEdit#inp:focus {
    border-color: #3d8cff;
    background-color: white;
}
QLineEdit#inp::placeholder {
    color: #8fb4d9;
    font-family: 'Segoe UI', sans-serif;
}

QPushButton#btn_primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5da5ff, stop:1 #3a7cd9);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#btn_primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4a95ff, stop:1 #2c6ac9);
}
QPushButton#btn_primary:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3a7cd9, stop:1 #2c6ac9);
}

QPushButton#btn_ghost {
    background-color: transparent;
    color: #000000;
    border: 2px solid #aac9e5;
    border-radius: 8px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#btn_ghost:hover   { background-color: #e2f0ff; border-color: #5d9fd3; }
QPushButton#btn_ghost:pressed { background-color: #c5e0ff; }

/* ── Teclado ──────────────────────────────────────────────────────────── */
QFrame#kbd_frame {
    background: #eff7ff;
    border: 1px solid #c5ddf1;
    border-radius: 10px;
}

/* Teclas normales */
QPushButton#kbd_btn {
    background: #ffffff;
    color: #184b74;
    border: 1px solid #9ec4e7;
    border-radius: 6px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#kbd_btn:hover   { background: #e4f1ff; border-color: #5da5e8; }
QPushButton#kbd_btn:pressed { background: #cce4ff; border-color: #3d8cff; }

/* Tecla numérica — fondo ligeramente distinto */
QPushButton#kbd_num {
    background: #f0f8ff;
    color: #0d3558;
    border: 1px solid #9ec4e7;
    border-radius: 6px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 800;
    font-size: 14px;
}
QPushButton#kbd_num:hover   { background: #d9eeff; border-color: #5da5e8; }
QPushButton#kbd_num:pressed { background: #bcd9f7; }

/* Tecla especial (espacio, limpiar) */
QPushButton#kbd_special {
    background: #ddeeff;
    color: #184b74;
    border: 1px solid #8bbfe8;
    border-radius: 6px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 700;
    font-size: 12px;
}
QPushButton#kbd_special:hover   { background: #cce6ff; border-color: #4d9de0; }
QPushButton#kbd_special:pressed { background: #b8d9f7; }

/* Borrar — rojo suave */
QPushButton#kbd_back {
    background: #fff0f0;
    color: #a33030;
    border: 1px solid #f0b8b8;
    border-radius: 6px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 800;
    font-size: 16px;
}
QPushButton#kbd_back:hover   { background: #ffe0e0; border-color: #e08080; }
QPushButton#kbd_back:pressed { background: #ffc8c8; }

/* Mayúsculas inactivo */
QPushButton#kbd_caps {
    background: #f5f5f5;
    color: #555;
    border: 1px solid #bbb;
    border-radius: 6px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 700;
    font-size: 11px;
}
QPushButton#kbd_caps:hover   { background: #ebebeb; }
QPushButton#kbd_caps:pressed { background: #e0e0e0; }

/* Mayúsculas activo */
QPushButton#kbd_caps_on {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5da5ff, stop:1 #3a7cd9);
    color: white;
    border: 1px solid #2c6ac9;
    border-radius: 6px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 700;
    font-size: 11px;
}
QPushButton#kbd_caps_on:hover   { background: #2c6ac9; }
QPushButton#kbd_caps_on:pressed { background: #1e559e; }

QLabel#err {
    color: #c74545;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}
"""


class AdminLoginPage(QWidget):
    go_back  = pyqtSignal()
    login_ok = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setObjectName("admin_login_page")
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("card")
        card.setFixedSize(_dp(760), _dp(525))
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(_dp(28), _dp(24), _dp(28), _dp(24))
        card_layout.setSpacing(_dp(24))

        # ── Columna izquierda: branding ───────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(_dp(8))
        left.setAlignment(Qt.AlignVCenter)

        ew = lbl("ADMINISTRACIÓN", "eyebrow", Qt.AlignCenter)
        ew.setStyleSheet(f"font-size: {_dp(9)}px;")
        left.addWidget(ew)

        left.addSpacing(_dp(4))

        hw = lbl("Acceso al panel.", "headline", Qt.AlignCenter)
        hw.setStyleSheet(f"font-size: {_dp(16)}px;")
        left.addWidget(hw)

        left.addSpacing(_dp(10))

        # Logo PNG debajo del título
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        logo_path = os.path.join(project_root, "logo_LockZtar_Negro.png")
        bicon = QLabel()
        bicon.setAlignment(Qt.AlignCenter)
        bicon.setFixedSize(_dp(140), _dp(72))
        logo_px = QPixmap(logo_path)
        if not logo_px.isNull():
            bicon.setPixmap(logo_px.scaled(_dp(132), _dp(68), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # Fallback a emoji si el logo no existe
            bicon.setText("🔒")
            bicon.setStyleSheet(f"font-size: {_dp(28)}px;")
        left.addWidget(bicon, 0, Qt.AlignCenter)

        left.addSpacing(_dp(10))

        div = QFrame(); div.setObjectName("div")
        left.addWidget(div)

        left.addStretch()

        self.back_btn = QPushButton("")
        bk = self.back_btn
        bk.setObjectName("btn_ghost")
        bk.setFixedHeight(_dp(44))
        bk.setStyleSheet(
            bk.styleSheet() +
            f"font-size: {_dp(12)}px; padding: 0px {_dp(16)}px;"
        )
        bk.setCursor(Qt.PointingHandCursor)
        bk.clicked.connect(self.go_back.emit)
        left.addWidget(bk)

        card_layout.addLayout(left, 1)

        vsep = QFrame()
        vsep.setFrameShape(QFrame.VLine)
        vsep.setStyleSheet("color: #c0dcf0;")
        card_layout.addWidget(vsep)

        # ── Columna derecha: formulario ───────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(_dp(5))
        right.setAlignment(Qt.AlignVCenter)

        # Usuario
        self.user_lbl = lbl("", "field_lbl")
        u_lbl = self.user_lbl
        u_lbl.setStyleSheet(f"font-size: {_dp(9)}px;")
        right.addWidget(u_lbl)
        right.addSpacing(_dp(3))

        row_u = QHBoxLayout()
        row_u.setSpacing(_dp(6))
        uicon = QLabel("👤")
        uicon.setStyleSheet(f"color:#145388; font-size:{_dp(14)}px;")
        self.user_inp = QLineEdit()
        self.user_inp.setObjectName("inp")
        self.user_inp.setPlaceholderText("")
        self.user_inp.setFixedHeight(_dp(40))
        self.user_inp.setStyleSheet(
            self.user_inp.styleSheet() +
            f"font-size: {_dp(12)}px; padding: 0px {_dp(12)}px;"
        )
        self.user_inp.installEventFilter(self)
        row_u.addWidget(uicon)
        row_u.addWidget(self.user_inp, 1)
        right.addLayout(row_u)

        right.addSpacing(_dp(8))

        # Contraseña
        self.pass_lbl = lbl("", "field_lbl")
        p_lbl = self.pass_lbl
        p_lbl.setStyleSheet(f"font-size: {_dp(9)}px;")
        right.addWidget(p_lbl)
        right.addSpacing(_dp(3))

        row_p = QHBoxLayout()
        row_p.setSpacing(_dp(6))
        picon = QLabel("🔑")
        picon.setStyleSheet(f"color:#145388; font-size:{_dp(14)}px;")
        self.pass_inp = QLineEdit()
        self.pass_inp.setObjectName("inp")
        self.pass_inp.setEchoMode(QLineEdit.Password)
        self.pass_inp.setPlaceholderText("")
        self.pass_inp.setFixedHeight(_dp(40))
        self.pass_inp.setStyleSheet(
            self.pass_inp.styleSheet() +
            f"font-size: {_dp(12)}px; padding: 0px {_dp(12)}px;"
        )
        self.pass_inp.installEventFilter(self)
        self.pass_inp.returnPressed.connect(self._check)
        row_p.addWidget(picon)
        row_p.addWidget(self.pass_inp, 1)
        right.addLayout(row_p)

        right.addSpacing(_dp(6))

        # Error
        self.err_lbl = lbl("", "err")
        self.err_lbl.setStyleSheet(f"font-size: {_dp(10)}px;")
        self.err_lbl.setMinimumHeight(_dp(18))
        self.err_lbl.setWordWrap(True)
        right.addWidget(self.err_lbl)

        right.addSpacing(_dp(4))

        # Botón ingresar
        self.btn_in = QPushButton("")
        self.btn_in.setObjectName("btn_primary")
        self.btn_in.setFixedHeight(_dp(52))
        self.btn_in.setStyleSheet(
            self.btn_in.styleSheet() +
            f"font-size: {_dp(14)}px; padding: 0px {_dp(22)}px;"
        )
        self.btn_in.setCursor(Qt.PointingHandCursor)
        self.btn_in.clicked.connect(self._check)
        right.addWidget(self.btn_in)

        right.addSpacing(_dp(4))
        right.addStretch()

        self.user_inp.setFocus()
        self.set_language(get_language())

        card_layout.addLayout(right, 1)

        root.addWidget(card)



    def set_language(self, _lang: str):
        self.back_btn.setText(tr("login.back"))
        self.user_lbl.setText(tr("login.user"))
        self.pass_lbl.setText(tr("login.pass"))
        self.user_inp.setPlaceholderText(tr("login.user_ph"))
        self.pass_inp.setPlaceholderText(tr("login.pass_ph"))
        self.btn_in.setText("🔐  " + tr("login.enter"))

    # ── Resto sin cambios ─────────────────────────────────────────────────────
    def paintEvent(self, e):
        p = QPainter(self)
        W, H = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0.0, QColor("#b3e0ff"))
        g.setColorAt(1.0, QColor("#87CEEB"))
        p.fillRect(0, 0, W, H, QBrush(g))
        p.end()

    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)

    def _check(self):
        u = self.user_inp.text().strip()
        p = self.pass_inp.text()
        if not u or not p:
            self.err_lbl.setText("⚠ " + tr("login.fill_fields"))
            return
        if not db_admin_exists(u):
            self.err_lbl.setText("✖ " + tr("login.bad_access"))
            try:
                db_log_intento(0, "acceso_admin", "fallido",
                               "Intento con usuario: {}".format(u))
            except Exception:
                pass
            return
        if not db_admin_valid(u, p):
            self.err_lbl.setText("✖ " + tr("login.bad_access"))
            self.pass_inp.clear()
            try:
                db_log_intento(0, "acceso_admin", "fallido",
                               "Contraseña incorrecta para: {}".format(u))
            except Exception:
                pass
            return
        admin = db_get_admin_by_username(u)
        try:
            db_log_intento(0, "acceso_admin", "exitoso",
                           "Admin {} ingresó al panel.".format(u),
                           id_usuario=admin["ID_admin"])
        except Exception:
            pass
        self.err_lbl.setText("")
        self.user_inp.clear()
        self.pass_inp.clear()
        self.login_ok.emit(admin)

    def reset(self):
        self.user_inp.clear()
        self.pass_inp.clear()
        self.err_lbl.setText("")
        self.user_inp.setFocus()