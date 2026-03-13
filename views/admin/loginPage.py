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
/* Fondo principal con azul cielo */
QWidget#admin_login_page {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #b3e0ff, stop:1 #87CEEB);
}

/* Tarjeta blanca - CON MARGEN DE 10px (como en el primer código) */
QFrame#card {
    background-color: white;
    border: 1px solid #c0dcf0;
    border-radius: 25px;
    margin: 10px;  /* Margen de 10px en todos los bordes */
}

/* Título grande (Acceso al panel) - usando #h2 del primer código */
QLabel#headline {
    color: #145388;
    font-size: 28px;
    font-weight: 700;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}

/* Etiqueta ADMINISTRACIÓN - usando #tag del primer código */
QLabel#eyebrow {
    color: #3a7ca5;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 4px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}

/* Etiquetas normales (Usuario, Contraseña) */
QLabel#field_lbl {
    color: #1e4b6e;
    font-size: 16px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-weight: 500;
}

/* Línea separadora - usando #sep del primer código */
QFrame#div {
    background: #7bb3d9;
    min-height: 3px;
    max-height: 3px;
    border: none;
}

/* Campos de texto */
QLineEdit#inp {
    background-color: #f0f8ff;
    border: 2px solid #b8d6f0;
    border-radius: 15px;
    color: #0a2a44;
    padding: 16px 20px;
    font-size: 16px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}
QLineEdit#inp:focus {
    border-color: #3d8cff;
    background-color: white;
}
QLineEdit#inp::placeholder {
    color: #8fb4d9;
    font-size: 16px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}

/* Botón INGRESAR - usando #btn_blue del primer código */
QPushButton#btn_primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5da5ff, stop:1 #3a7cd9);
    color: white;
    border: none;
    border-radius: 15px;
    padding: 18px 36px;
    font-size: 18px;
    font-weight: 700;
    min-height: 30px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}
QPushButton#btn_primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4a95ff, stop:1 #2c6ac9);
}
QPushButton#btn_primary:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3a7cd9, stop:1 #2c6ac9);
}

/* Botón Volver - usando #btn_sm del primer código */
QPushButton#btn_ghost {
    background-color: transparent;
    color: #2c6289;
    border: 2px solid #aac9e5;
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 500;
    font-family: 'Segoe UI', 'Inter', sans-serif;
}
QPushButton#btn_ghost:hover {
    background-color: #e2f0ff;
    border-color: #5d9fd3;
}
QPushButton#btn_ghost:pressed {
    background-color: #c5e0ff;
}

/* Mensajes de error */
QLabel#err {
    color: #c74545;
    font-size: 16px;
    font-weight: 600;
    padding: 10px;
    font-family: 'Segoe UI', 'Inter', sans-serif;
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
        cl.addWidget(lbl("Acceso al panel.", "headline"))
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