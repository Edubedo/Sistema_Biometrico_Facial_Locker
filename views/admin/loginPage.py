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

        # ── Layout horizontal: form izquierda | branding derecha ──────────────
        # En 800×480 la card vertical clásica es muy alta.
        # Usamos dos columnas dentro de la card para aprovechar el ancho.
        card = QFrame()
        card.setObjectName("card")
        card.setFixedSize(_dp(720), _dp(360))   # ocupa casi toda la pantalla
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(_dp(28), _dp(24), _dp(28), _dp(24))
        card_layout.setSpacing(_dp(24))

        # ── Columna izquierda: branding ───────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(_dp(8))
        left.setAlignment(Qt.AlignVCenter)

        # Ícono + nombre
        br = QHBoxLayout()
        br.setSpacing(_dp(8))
        br.setAlignment(Qt.AlignCenter)
        bicon = lbl("🔒", "brand_icon", Qt.AlignCenter)
        bicon.setStyleSheet(f"font-size: {_dp(28)}px;")
        bname = lbl("SuperLocker", "brand_name", Qt.AlignCenter)
        bname.setStyleSheet(f"font-size: {_dp(16)}px;")
        br.addWidget(bicon)
        br.addWidget(bname)
        left.addLayout(br)

        left.addSpacing(_dp(12))

        ew = lbl("ADMINISTRACIÓN", "eyebrow", Qt.AlignCenter)
        ew.setStyleSheet(f"font-size: {_dp(9)}px;")
        left.addWidget(ew)

        left.addSpacing(_dp(4))

        hw = lbl("Acceso al panel.", "headline", Qt.AlignCenter)
        hw.setStyleSheet(f"font-size: {_dp(16)}px;")
        left.addWidget(hw)

        left.addSpacing(_dp(12))

        div = QFrame(); div.setObjectName("div")
        left.addWidget(div)

        left.addStretch()

        # Botón volver abajo a la izquierda
        bk = QPushButton("← VOLVER")
        bk.setObjectName("btn_ghost")
        bk.setFixedHeight(_dp(30))
        bk.setStyleSheet(
            bk.styleSheet() +
            f"font-size: {_dp(9)}px; padding: 0px {_dp(14)}px;"
        )
        bk.setCursor(Qt.PointingHandCursor)
        bk.clicked.connect(self.go_back.emit)
        left.addWidget(bk)

        card_layout.addLayout(left, 1)

        # Separador vertical
        vsep = QFrame()
        vsep.setFrameShape(QFrame.VLine)
        vsep.setStyleSheet("color: #c0dcf0;")
        card_layout.addWidget(vsep)

        # ── Columna derecha: formulario ───────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(_dp(6))
        right.setAlignment(Qt.AlignVCenter)

        # Usuario
        u_lbl = lbl("USUARIO", "field_lbl")
        u_lbl.setStyleSheet(f"font-size: {_dp(9)}px;")
        right.addWidget(u_lbl)
        right.addSpacing(_dp(3))

        row_u = QHBoxLayout()
        row_u.setSpacing(_dp(6))
        uicon = QLabel("👤")
        uicon.setStyleSheet(f"color:#145388; font-size:{_dp(14)}px;")
        self.user_inp = QLineEdit()
        self.user_inp.setObjectName("inp")
        self.user_inp.setPlaceholderText("Nombre de usuario")
        self.user_inp.setFixedHeight(_dp(34))
        self.user_inp.setStyleSheet(
            self.user_inp.styleSheet() +
            f"font-size: {_dp(11)}px; padding: 0px {_dp(12)}px;"
        )
        row_u.addWidget(uicon)
        row_u.addWidget(self.user_inp, 1)
        right.addLayout(row_u)

        right.addSpacing(_dp(12))

        # Contraseña
        p_lbl = lbl("CONTRASEÑA", "field_lbl")
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
        self.pass_inp.setPlaceholderText("••••••••")
        self.pass_inp.setFixedHeight(_dp(34))
        self.pass_inp.setStyleSheet(
            self.pass_inp.styleSheet() +
            f"font-size: {_dp(11)}px; padding: 0px {_dp(12)}px;"
        )
        self.pass_inp.returnPressed.connect(self._check)
        row_p.addWidget(picon)
        row_p.addWidget(self.pass_inp, 1)
        right.addLayout(row_p)

        right.addSpacing(_dp(14))

        # Error
        self.err_lbl = lbl("", "err")
        self.err_lbl.setStyleSheet(f"font-size: {_dp(9)}px;")
        self.err_lbl.setMinimumHeight(_dp(18))
        self.err_lbl.setWordWrap(True)
        right.addWidget(self.err_lbl)

        right.addSpacing(_dp(6))

        # Botón ingresar
        btn_in = QPushButton("🔐  INGRESAR")
        btn_in.setObjectName("btn_primary")
        btn_in.setFixedHeight(_dp(38))
        btn_in.setStyleSheet(
            btn_in.styleSheet() +
            f"font-size: {_dp(11)}px; padding: 0px {_dp(20)}px;"
        )
        btn_in.setCursor(Qt.PointingHandCursor)
        btn_in.clicked.connect(self._check)
        right.addWidget(btn_in)

        card_layout.addLayout(right, 1)

        root.addWidget(card)

    def paintEvent(self, e):
        p = QPainter(self)
        W, H = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0.0, QColor("#b3e0ff"))
        g.setColorAt(1.0, QColor("#87CEEB"))
        p.fillRect(0, 0, W, H, QBrush(g))
        p.end()

    def _check(self):
        u = self.user_inp.text().strip()
        p = self.pass_inp.text()
        if not u or not p:
            self.err_lbl.setText("⚠ Llena todos los campos.")
            return
        if not db_admin_exists(u):
            self.err_lbl.setText("✖ Acceso incorrecto.")
            try:
                db_log_intento(0, "acceso_admin", "fallido",
                               "Intento con usuario: {}".format(u))
            except Exception:
                pass
            return
        if not db_admin_valid(u, p):
            self.err_lbl.setText("✖ Acceso incorrecto.")
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