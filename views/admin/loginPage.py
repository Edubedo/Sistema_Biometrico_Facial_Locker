from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QFrame, QSizePolicy, QLabel, QApplication
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QFont

from db.models.intentos_acceso import db_log_intento
from db.models.usuarios import db_admin_exists, db_admin_valid, db_get_admin_by_username
from views.style.widgets.widgets import sep_line


def _dp(v):
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    return max(1, round(v * dpi / 96))


def lbl(text, obj="", align=Qt.AlignLeft):
    l = QLabel(text)
    if obj:
        l.setObjectName(obj)
    l.setAlignment(align)
    return l


# ─── PALETTE ────────────────────────────────────────────────────────────────
#   BG      #F7F8FA  (off-white, not glaring)
#   CARD    #FFFFFF  (pure white card)
#   INK     #111318  (near-black text)
#   MUTED   #8B909A  (secondary text)
#   BORDER  #E4E6EA  (very subtle border)
#   ACCENT  #2563EB  (single vivid blue)
#   DANGER  #DC2626  (error red)
# ────────────────────────────────────────────────────────────────────────────

STYLE = """
QWidget#admin_login_page {
    background-color: #F7F8FA;
}

/* ── Card ── */
QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E4E6EA;
    border-radius: 4px;
}

/* ── Labels ── */
QLabel#eyebrow {
    color: #2563EB;
    font-family: 'DM Mono', 'Courier New', monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 4px;
}
QLabel#headline {
    color: #111318;
    font-family: 'Georgia', 'Times New Roman', serif;
    font-size: 32px;
    font-weight: 400;
}
QLabel#field_lbl {
    color: #8B909A;
    font-family: 'DM Mono', 'Courier New', monospace;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 3px;
}

/* ── Inputs ── */
QLineEdit#inp {
    background-color: #F7F8FA;
    border: 1px solid #E4E6EA;
    border-radius: 2px;
    color: #111318;
    padding: 14px 16px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 15px;
    selection-background-color: #DBEAFE;
}
QLineEdit#inp:focus {
    border: 1.5px solid #2563EB;
    background-color: #FFFFFF;
    outline: none;
}
QLineEdit#inp::placeholder {
    color: #C4C7CE;
}

/* ── Primary button ── */
QPushButton#btn_primary {
    background-color: #111318;
    color: #FFFFFF;
    border: none;
    border-radius: 2px;
    padding: 16px 0px;
    font-family: 'DM Mono', 'Courier New', monospace;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 4px;
    min-height: 52px;
}
QPushButton#btn_primary:hover {
    background-color: #2563EB;
}
QPushButton#btn_primary:pressed {
    background-color: #1D4ED8;
}

/* ── Ghost button ── */
QPushButton#btn_ghost {
    background-color: transparent;
    color: #8B909A;
    border: none;
    padding: 6px 0px;
    font-family: 'DM Mono', 'Courier New', monospace;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 2px;
}
QPushButton#btn_ghost:hover {
    color: #111318;
}

/* ── Error ── */
QLabel#err {
    color: #DC2626;
    font-family: 'DM Mono', 'Courier New', monospace;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 1px;
    padding: 0px;
}

/* ── Divider ── */
QFrame#div {
    background-color: #E4E6EA;
    border: none;
    min-height: 1px;
    max-height: 1px;
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
        root.setAlignment(Qt.AlignCenter)

        # ── Card ──────────────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(_dp(440))
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(_dp(56), _dp(52), _dp(56), _dp(52))
        cl.setSpacing(0)

        # ── Back button ───────────────────────────────────────────────────────
        back_row = QHBoxLayout()
        bk = QPushButton("← VOLVER")
        bk.setObjectName("btn_ghost")
        bk.setCursor(Qt.PointingHandCursor)
        bk.clicked.connect(self.go_back.emit)
        back_row.addWidget(bk)
        back_row.addStretch()
        cl.addLayout(back_row)
        cl.addSpacing(_dp(36))

        # ── Eyebrow + Headline ────────────────────────────────────────────────
        cl.addWidget(lbl("ADMINISTRACIÓN", "eyebrow"))
        cl.addSpacing(_dp(10))
        cl.addWidget(lbl("Acceso\nal panel.", "headline"))
        cl.addSpacing(_dp(32))

        # ── Divider ───────────────────────────────────────────────────────────
        div = QFrame(); div.setObjectName("div")
        cl.addWidget(div)
        cl.addSpacing(_dp(32))

        # ── Usuario ───────────────────────────────────────────────────────────
        cl.addWidget(lbl("USUARIO", "field_lbl"))
        cl.addSpacing(_dp(8))
        self.user_inp = QLineEdit()
        self.user_inp.setObjectName("inp")
        self.user_inp.setPlaceholderText("nombre de usuario")
        cl.addWidget(self.user_inp)
        cl.addSpacing(_dp(20))

        # ── Contraseña ────────────────────────────────────────────────────────
        cl.addWidget(lbl("CONTRASEÑA", "field_lbl"))
        cl.addSpacing(_dp(8))
        self.pass_inp = QLineEdit()
        self.pass_inp.setObjectName("inp")
        self.pass_inp.setEchoMode(QLineEdit.Password)
        self.pass_inp.setPlaceholderText("••••••••")
        self.pass_inp.returnPressed.connect(self._check)
        cl.addWidget(self.pass_inp)
        cl.addSpacing(_dp(8))

        # ── Error label ───────────────────────────────────────────────────────
        self.err_lbl = lbl("", "err")
        self.err_lbl.setMinimumHeight(_dp(20))
        cl.addWidget(self.err_lbl)
        cl.addSpacing(_dp(24))

        # ── Submit button ─────────────────────────────────────────────────────
        btn_in = QPushButton("INGRESAR")
        btn_in.setObjectName("btn_primary")
        btn_in.setCursor(Qt.PointingHandCursor)
        btn_in.clicked.connect(self._check)
        cl.addWidget(btn_in)

        root.addWidget(card)

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QBrush(QColor("#F7F8FA")))
        p.end()

    def _check(self):
        u = self.user_inp.text().strip()
        p = self.pass_inp.text()
        if not u or not p:
            self.err_lbl.setText("· Completa todos los campos.")
            return
        if not db_admin_exists(u):
            self.err_lbl.setText("· Usuario no encontrado.")
            try:
                db_log_intento(0, "acceso_admin", "fallido",
                               "Intento con usuario: {}".format(u))
            except Exception:
                pass
            return
        if not db_admin_valid(u, p):
            self.err_lbl.setText("· Contraseña incorrecta.")
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