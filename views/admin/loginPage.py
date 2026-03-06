from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QFrame

from db.models.intentos_acceso import db_log_intento
from db.models.usuarios import db_admin_exists, db_admin_valid, db_get_admin_by_username
from views.style.widgets.widgets import lbl, sep_line

STYLE = """
QWidget#admin_login_page { background: #060d1a; color: #c8dff5; }
QLabel#h2 { color: #e2f0ff; font-size: 22px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#tag { color: #4d8ec4; font-size: 11px; font-weight: 600; font-family: 'Courier New'; letter-spacing: 4px; }
QLabel#body { color: #7ca8d0; font-size: 14px; font-family: 'Segoe UI',sans-serif; }
QLabel#err { color: #f03d5a; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QFrame#sep { background: #0f2035; min-height: 1px; max-height: 1px; }
QFrame#card_blue { background: #071833; border: 1px solid #1a4a8a; border-radius: 16px; }
QLineEdit#inp {
    background: #060d1a; border: 1.5px solid #0f2035; border-radius: 10px;
    color: #e2f0ff; padding: 14px 18px; font-size: 14px; font-family: 'Segoe UI',sans-serif;
}
QLineEdit#inp:focus { border-color: #1a6ef5; }
QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a6ef5, stop:1 #0f4fd4);
    color: #fff; border: none; border-radius: 12px; padding: 16px 36px;
    font-size: 15px; font-weight: 800; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_blue:hover { background: #2b7cff; }
QPushButton#btn_sm {
    background: #0a1628; color: #4d8ec4; border: 1px solid #1a3a5c; border-radius: 8px;
    padding: 8px 18px; font-size: 12px; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_sm:hover { color: #c8dff5; border-color: #4d8ec4; }
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
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(56, 48, 56, 48); cl.setSpacing(18)
        card.setFixedWidth(460)

        hdr_row = QHBoxLayout()
        bk = QPushButton("< Volver"); bk.setObjectName("btn_sm")
        bk.setCursor(Qt.PointingHandCursor); bk.clicked.connect(self.go_back.emit)
        hdr_row.addWidget(bk); hdr_row.addStretch()
        cl.addLayout(hdr_row)

        cl.addWidget(lbl("ADMINISTRACION", "tag", Qt.AlignCenter))
        cl.addWidget(lbl("Acceso al Panel", "h2", Qt.AlignCenter))
        cl.addWidget(sep_line())

        cl.addWidget(lbl("Usuario"))
        self.user_inp = QLineEdit(); self.user_inp.setObjectName("inp")
        self.user_inp.setPlaceholderText("nombre de usuario")
        cl.addWidget(self.user_inp)

        cl.addWidget(lbl("Contrasena"))
        self.pass_inp = QLineEdit(); self.pass_inp.setObjectName("inp")
        self.pass_inp.setEchoMode(QLineEdit.Password)
        self.pass_inp.setPlaceholderText("••••••••")
        self.pass_inp.returnPressed.connect(self._check)
        cl.addWidget(self.pass_inp)

        self.err_lbl = lbl("", "err", Qt.AlignCenter)
        cl.addWidget(self.err_lbl)

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
