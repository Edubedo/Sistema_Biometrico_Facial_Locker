from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QFrame, QSizePolicy

from db.models.intentos_acceso import db_log_intento
from db.models.usuarios import db_admin_exists, db_admin_valid, db_get_admin_by_username
from views.style.widgets.widgets import lbl, sep_line

STYLE = """
/* Fondo principal con azul cielo */
QWidget#admin_login_page {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #b3e0ff, stop:1 #87CEEB);
}

/* Tarjeta blanca - CON MARGEN DE 10px */
QFrame#card_blue {
    background-color: white;
    border: 1px solid #c0dcf0;
    border-radius: 25px;
    margin: 10px;  /* ← MARGEN DE 10px EN TODOS LOS BORDES */
}

/* Título grande (Acceso al Panel) */
QLabel#h2 {
    color: #145388;
    font-size: 28px;
    font-weight: 700;
}

/* Etiqueta ADMINISTRACIÓN */
QLabel#tag {
    color: #3a7ca5;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 4px;
}

/* Etiquetas normales (Usuario, Contraseña) */
QLabel {
    color: #1e4b6e;
    font-size: 16px;
}

/* Línea separadora */
QFrame#sep {
    background: #7bb3d9;
    min-height: 3px;
    max-height: 3px;
}

/* Campos de texto */
QLineEdit#inp {
    background-color: #f0f8ff;
    border: 2px solid #b8d6f0;
    border-radius: 15px;
    color: #0a2a44;
    padding: 16px 20px;
    font-size: 16px;
}

QLineEdit#inp:focus {
    border-color: #3d8cff;
    background-color: white;
}

/* Placeholder */
QLineEdit#inp::placeholder {
    color: #8fb4d9;
    font-size: 16px;
}

/* Botón INGRESAR */
QPushButton#btn_blue {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5da5ff, stop:1 #3a7cd9);
    color: white;
    border: none;
    border-radius: 15px;
    padding: 18px 36px;
    font-size: 18px;
    font-weight: 700;
    min-height: 30px;
}

QPushButton#btn_blue:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4a95ff, stop:1 #2c6ac9);
}

/* Botón Volver */
QPushButton#btn_sm {
    background-color: transparent;
    color: #2c6289;
    border: 2px solid #aac9e5;
    border-radius: 12px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 500;
}

QPushButton#btn_sm:hover {
    background-color: #e2f0ff;
    border-color: #5d9fd3;
}

/* Mensajes de error */
QLabel#err {
    color: #c74545;
    font-size: 16px;
    font-weight: 600;
    padding: 10px;
}
"""

class AdminLoginPage(QWidget):
    go_back  = pyqtSignal()
    login_ok = pyqtSignal(dict)   # dict con datos del admin autenticado

    def __init__(self):
        super().__init__()
        self.setObjectName("admin_login_page")
        self.setStyleSheet(STYLE)
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setAlignment(Qt.AlignCenter)

        card = QFrame(); card.setObjectName("card_blue")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(80, 60, 80, 60)  # Antes 56,48,56,48
        cl.setSpacing(25)  # Antes 18
        # card.setFixedWidth(460) #Eliminado para quitar el ancho fijo

        # Fila superior con botón Volver
        hdr_row = QHBoxLayout()
        bk = QPushButton("< Volver"); bk.setObjectName("btn_sm")
        bk.setCursor(Qt.PointingHandCursor); bk.clicked.connect(self.go_back.emit)
        hdr_row.addWidget(bk); hdr_row.addStretch()
        cl.addLayout(hdr_row)

        # Títulos y separador (usando las funciones existentes)
        cl.addWidget(lbl("ADMINISTRACION", "tag", Qt.AlignCenter))
        cl.addWidget(lbl("Acceso al Panel", "h2", Qt.AlignCenter))
        cl.addWidget(sep_line())

        # Campo Usuario
        cl.addWidget(lbl("Usuario"))
        self.user_inp = QLineEdit(); self.user_inp.setObjectName("inp")
        self.user_inp.setPlaceholderText("nombre de usuario")
        cl.addWidget(self.user_inp)

        # Campo Contraseña
        cl.addWidget(lbl("Contrasena"))
        self.pass_inp = QLineEdit(); self.pass_inp.setObjectName("inp")
        self.pass_inp.setEchoMode(QLineEdit.Password)
        self.pass_inp.setPlaceholderText("••••••••")
        self.pass_inp.returnPressed.connect(self._check)
        cl.addWidget(self.pass_inp)

        # Label de error
        self.err_lbl = lbl("", "err", Qt.AlignCenter)
        cl.addWidget(self.err_lbl)

        # Botón INGRESAR
        btn_in = QPushButton("INGRESAR"); btn_in.setObjectName("btn_blue")
        btn_in.setCursor(Qt.PointingHandCursor)
        btn_in.clicked.connect(self._check)
        cl.addWidget(btn_in)

        vl.addWidget(card)

    def _check(self):
        u = self.user_inp.text().strip()
        p = self.pass_inp.text()
        if not u or not p:
            self.err_lbl.setText("Completa los campos.")
            return
        if not db_admin_exists(u):
            self.err_lbl.setText("Usuario no encontrado.")
            # Loguear intento fallido (sin locker especifico, usamos 0)
            try:
                db_log_intento(0, "acceso_admin", "fallido",
                               "Intento con usuario: {}".format(u))
            except Exception:
                pass
            return
        if not db_admin_valid(u, p):
            self.err_lbl.setText("Contrasena incorrecta.")
            self.pass_inp.clear()
            try:
                db_log_intento(0, "acceso_admin", "fallido",
                               "Contrasena incorrecta para: {}".format(u))
            except Exception:
                pass
            return
        admin = db_get_admin_by_username(u)
        # Loguear acceso exitoso
        try:
            db_log_intento(0, "acceso_admin", "exitoso",
                           "Admin {} ingreso al panel.".format(u),
                           id_usuario=admin["ID_admin"])
        except Exception:
            pass
        self.err_lbl.setText("")
        self.user_inp.clear(); self.pass_inp.clear()
        self.login_ok.emit(admin)
        

    def reset(self):
        self.user_inp.clear(); self.pass_inp.clear(); self.err_lbl.setText("")
