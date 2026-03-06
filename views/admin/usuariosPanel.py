from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFrame,
    QScrollArea,
    QMessageBox,
    QInputDialog,
    QComboBox,
)

from db.models.usuarios import (
    db_admin_exists,
    db_count_active_admins,
    db_delete_admin,
    db_get_all_admins,
    db_register_admin,
)
from views.style.widgets.widgets import lbl, sep_line

STYLE = """
QWidget#admin_users_panel, QWidget#admin_users_inner { background: #060d1a; color: #c8dff5; }
QWidget#inner_bg { background: #0a1628; }
QLabel#tag { color: #4d8ec4; font-size: 11px; font-weight: 600; font-family: 'Courier New'; letter-spacing: 4px; }
QLabel#body { color: #7ca8d0; font-size: 14px; font-family: 'Segoe UI',sans-serif; }
QLabel#small { color: #3a5f84; font-size: 11px; font-family: 'Courier New'; letter-spacing: 1px; }
QLabel#ok { color: #3de8a0; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#err { color: #f03d5a; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#badge_blue {
    background: #071833; color: #4d8ec4; border: 1px solid #1a4a8a; border-radius: 14px;
    padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px;
}
QLabel#badge_green {
    background: #041a12; color: #3de8a0; border: 1px solid #1a7a50; border-radius: 14px;
    padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px;
}
QLabel#badge_red {
    background: #1a0409; color: #f03d5a; border: 1px solid #7a1a2a; border-radius: 14px;
    padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px;
}
QFrame#sep { background: #0f2035; min-height: 1px; max-height: 1px; }
QFrame#card { background: #0a1628; border: 1px solid #0f2035; border-radius: 16px; }
QFrame#card_blue { background: #071833; border: 1px solid #1a4a8a; border-radius: 16px; }
QLineEdit#inp {
    background: #060d1a; border: 1.5px solid #0f2035; border-radius: 10px;
    color: #e2f0ff; padding: 12px 14px; font-size: 13px; font-family: 'Segoe UI',sans-serif;
}
QLineEdit#inp:focus { border-color: #1a6ef5; }
QComboBox#combo {
    background: #060d1a; border: 1.5px solid #0f2035; border-radius: 10px;
    color: #e2f0ff; padding: 10px 14px; font-size: 13px; font-family: 'Segoe UI',sans-serif;
}
QComboBox#combo:focus { border-color: #1a6ef5; }
QComboBox#combo::drop-down { border: none; }
QComboBox QAbstractItemView { background: #0a1628; color: #c8dff5; border: 1px solid #1a3a5c; }
QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a6ef5, stop:1 #0f4fd4);
    color: #fff; border: none; border-radius: 12px; padding: 14px 30px;
    font-size: 14px; font-weight: 800; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_blue:hover { background: #2b7cff; }
QPushButton#btn_red {
    background: #c0122a; color: #fff; border: none; border-radius: 12px;
    padding: 14px 30px; font-size: 14px; font-weight: 800; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_red:hover { background: #e01535; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #060d1a; width: 6px; margin: 0; }
QScrollBar::handle:vertical { background: #0f2035; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

class _AdminUsersPanel(QWidget):
    """
    Permite registrar nuevos administradores con nombre completo,
    usuario y contrasena. Campos mapeados a la tabla Usuarios.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("admin_users_panel")
        self.setStyleSheet(STYLE)
        self._current_admin = {}
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(16)

        body = QHBoxLayout(); body.setSpacing(28)

        # ── Lista de admins ───────────────────────────────────────────────────
        left = QFrame(); left.setObjectName("card")
        ll   = QVBoxLayout(left); ll.setContentsMargins(24, 24, 24, 24); ll.setSpacing(12)
        ll.addWidget(lbl("ADMINISTRADORES ACTIVOS", "tag"))

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.inner = QWidget(); self.inner.setObjectName("admin_users_inner")
        self.il    = QVBoxLayout(self.inner)
        self.il.setContentsMargins(0, 0, 0, 0); self.il.setSpacing(8)
        scroll.setWidget(self.inner)
        ll.addWidget(scroll, 1)

        btn_del = QPushButton("DESACTIVAR ADMIN"); btn_del.setObjectName("btn_red")
        btn_del.setCursor(Qt.PointingHandCursor); btn_del.clicked.connect(self._delete)
        ll.addWidget(btn_del)

        # ── Formulario de registro ────────────────────────────────────────────
        right = QFrame(); right.setObjectName("card_blue")
        rl    = QVBoxLayout(right); rl.setContentsMargins(28, 28, 28, 28); rl.setSpacing(12)
        rl.addWidget(lbl("REGISTRAR NUEVO ADMIN", "tag"))
        rl.addWidget(sep_line())

        # Campos mapeados a Usuarios
        rl.addWidget(lbl("Nombre"))
        self.f_nombre = QLineEdit(); self.f_nombre.setObjectName("inp")
        self.f_nombre.setPlaceholderText("Juan")
        rl.addWidget(self.f_nombre)

        rl.addWidget(lbl("Apellido paterno"))
        self.f_ap = QLineEdit(); self.f_ap.setObjectName("inp")
        self.f_ap.setPlaceholderText("Garcia")
        rl.addWidget(self.f_ap)

        rl.addWidget(lbl("Apellido materno"))
        self.f_am = QLineEdit(); self.f_am.setObjectName("inp")
        self.f_am.setPlaceholderText("Lopez")
        rl.addWidget(self.f_am)

        rl.addWidget(lbl("Usuario"))
        self.f_user = QLineEdit(); self.f_user.setObjectName("inp")
        self.f_user.setPlaceholderText("jgarcia01")
        rl.addWidget(self.f_user)

        rl.addWidget(lbl("Rol"))
        self.f_rol = QComboBox(); self.f_rol.setObjectName("combo")
        self.f_rol.addItems(["empleado", "supervisor", "administrador"])
        rl.addWidget(self.f_rol)

        rl.addWidget(lbl("Contrasena"))
        self.f_pass = QLineEdit(); self.f_pass.setObjectName("inp")
        self.f_pass.setEchoMode(QLineEdit.Password)
        self.f_pass.setPlaceholderText("••••••••")
        rl.addWidget(self.f_pass)

        rl.addWidget(lbl("Confirmar contrasena"))
        self.f_pass2 = QLineEdit(); self.f_pass2.setObjectName("inp")
        self.f_pass2.setEchoMode(QLineEdit.Password)
        self.f_pass2.setPlaceholderText("••••••••")
        rl.addWidget(self.f_pass2)

        self.reg_err = lbl("", "err", Qt.AlignCenter)
        self.reg_ok  = lbl("", "ok",  Qt.AlignCenter)
        rl.addWidget(self.reg_err)
        rl.addWidget(self.reg_ok)

        btn_reg = QPushButton("REGISTRAR ADMINISTRADOR"); btn_reg.setObjectName("btn_blue")
        btn_reg.setCursor(Qt.PointingHandCursor); btn_reg.clicked.connect(self._register)
        rl.addWidget(btn_reg)
        rl.addStretch()

        body.addWidget(left, 1)
        body.addWidget(right, 1)
        vl.addLayout(body, 1)
        self.refresh()

    def set_current_admin(self, admin_data):
        self._current_admin = admin_data

    def _register(self):
        nombre = self.f_nombre.text().strip()
        ap     = self.f_ap.text().strip()
        am     = self.f_am.text().strip()
        user   = self.f_user.text().strip()
        rol    = self.f_rol.currentText()
        pw     = self.f_pass.text()
        pw2    = self.f_pass2.text()
        id_reg = self._current_admin.get("ID_admin")

        self.reg_err.setText(""); self.reg_ok.setText("")

        if not all([nombre, ap, user, pw]):
            self.reg_err.setText("Nombre, apellido, usuario y contrasena son obligatorios.")
            return
        if len(pw) < 4:
            self.reg_err.setText("La contrasena debe tener al menos 4 caracteres.")
            return
        if pw != pw2:
            self.reg_err.setText("Las contrasenas no coinciden.")
            return
        if db_admin_exists(user):
            self.reg_err.setText("Ya existe un admin con ese usuario.")
            return

        new_id = db_register_admin(nombre, ap, am, user, pw, rol, id_reg)
        if new_id:
            for f in [self.f_nombre, self.f_ap, self.f_am, self.f_user, self.f_pass, self.f_pass2]:
                f.clear()
            self.reg_ok.setText("Admin '{}' registrado correctamente.".format(user))
            self.refresh()
        else:
            self.reg_err.setText("No se pudo registrar. Intenta de nuevo.")

    def _delete(self):
        u, ok = QInputDialog.getText(None, "Desactivar Admin", "Usuario a desactivar:")
        if not ok or not u.strip():
            return
        if not db_admin_exists(u.strip()):
            QMessageBox.warning(None, "Error", "Admin no encontrado.")
            return
        if db_count_active_admins() <= 1:
            QMessageBox.warning(None, "Error", "Debe existir al menos un administrador activo.")
            return
        id_act = self._current_admin.get("ID_admin")
        db_delete_admin(u.strip(), id_act)
        QMessageBox.information(None, "OK", "Admin '{}' desactivado.".format(u.strip()))
        self.refresh()

    def refresh(self):
        for i in reversed(range(self.il.count())):
            item = self.il.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        admins = db_get_all_admins()
        if not admins:
            self.il.addWidget(lbl("Sin administradores.", "small"))
        else:
            for a in admins:
                row = QFrame(); row.setObjectName("card")
                rl  = QHBoxLayout(row); rl.setContentsMargins(16, 12, 16, 12); rl.setSpacing(12)

                nombre = "{} {} {}".format(
                    a.get("t_nombre", ""),
                    a.get("t_apellido_paterno", ""),
                    a.get("t_apellido_materno", "")
                ).strip()
                n_lbl = QLabel(nombre)
                n_lbl.setStyleSheet(
                    "color:#c8dff5; font-size:13px; font-weight:700; font-family:'Segoe UI';"
                )
                u_lbl  = lbl("@{}".format(a.get("t_usuario", "")), "small")
                r_lbl  = lbl(a.get("t_rol", ""), "badge_blue")
                st_obj = "badge_green" if a.get("t_estado") == "activo" else "badge_red"
                s_lbl  = lbl(a.get("t_estado", "").upper(), st_obj)

                rl.addWidget(n_lbl); rl.addWidget(u_lbl)
                rl.addStretch(); rl.addWidget(r_lbl); rl.addWidget(s_lbl)
                self.il.addWidget(row)
        self.il.addStretch()
