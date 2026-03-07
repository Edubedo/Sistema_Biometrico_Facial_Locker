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
    QSizePolicy,
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
/* Fondo principal con gradiente azul cielo */
QWidget#admin_users_panel, QWidget#admin_users_inner {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #b3e0ff, stop:1 #87CEEB);
}

/* Widgets internos con fondo blanco */
QWidget#inner_bg { background: white; }

/* Títulos */
QLabel#tag {
    color: #3a7ca5;
    font-size: 11px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
}

QLabel#body {
    color: #1e4b6e;
    font-size: 12px;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#small {
    color: #5f7f9e;
    font-size: 10px;
    font-family: 'Segoe UI', sans-serif;
}

/* Mensajes */
QLabel#ok {
    color: #27ae60;
    font-size: 12px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#err {
    color: #c0392b;
    font-size: 12px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

/* Badges */
QLabel#badge_blue {
    background: #e6f0fa;
    color: #2c6289;
    border: 1px solid #b8d6f0;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 9px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#badge_green {
    background: #e3f7ec;
    color: #27ae60;
    border: 1px solid #a9dfbf;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 9px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#badge_red {
    background: #fbe9eb;
    color: #c0392b;
    border: 1px solid #f0b3b3;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 9px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

/* Línea separadora */
QFrame#sep {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #c2e0ff, stop:0.5 #6ab0e6, stop:1 #c2e0ff);
    min-height: 1px;
    max-height: 1px;
}

/* Tarjetas */
QFrame#card {
    background-color: white;
    border: 1px solid #d0e6ff;
    border-radius: 15px;
}

QFrame#card_blue {
    background-color: white;
    border: 1px solid #b0d4ff;
    border-radius: 15px;
}

/* Campos de texto */
QLineEdit#inp {
    background-color: #f5fbff;
    border: 1.5px solid #c5e2ff;
    border-radius: 8px;
    color: #1e3a5f;
    padding: 6px 8px;  /* Padding reducido */
    font-size: 11px;  /* Fuente más pequeña */
    font-family: 'Segoe UI', sans-serif;
    min-height: 22px;  /* Altura mínima reducida */
}

QLineEdit#inp:focus {
    border-color: #4a9eff;
    background-color: white;
}

QLineEdit#inp::placeholder {
    color: #99badd;
    font-style: italic;
    font-size: 10px;  /* Placeholder más pequeño */
}

/* ComboBox */
QComboBox#combo {
    background-color: #f5fbff;
    border: 1.5px solid #c5e2ff;
    border-radius: 8px;
    color: #1e3a5f;
    padding: 5px 8px;
    font-size: 11px;
    font-family: 'Segoe UI', sans-serif;
    min-height: 22px;
}

QComboBox#combo:focus {
    border-color: #4a9eff;
}

QComboBox#combo::drop-down {
    border: none;
    width: 18px;
}

QComboBox QAbstractItemView {
    background-color: white;
    color: #1e3a5f;
    border: 1px solid #b0d4ff;
    border-radius: 5px;
    selection-background-color: #e6f0fa;
    selection-color: #1e3a5f;
}

/* Botón azul (REGISTRAR) */
QPushButton#btn_blue {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6bb5ff, stop:1 #3d8cff);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;  /* Padding reducido */
    font-size: 12px;  /* Fuente más pequeña */
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
    min-height: 30px;  /* Altura mínima reducida */
}

QPushButton#btn_blue:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5aa5ff, stop:1 #2c7aff);
}

/* Botón rojo (DESACTIVAR) */
QPushButton#btn_red {
    background: #f1948a;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
    min-height: 30px;
}

QPushButton#btn_red:hover {
    background: #ec7063;
}

/* Scroll Area */
QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    background: #e6f0fa;
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #99badd;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #7aa9d4;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
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
        vl = QVBoxLayout(self); vl.setContentsMargins(10, 10, 10, 10); vl.setSpacing(16)

        body = QHBoxLayout(); body.setSpacing(15)

        # ── Lista de admins ───────────────────────────────────────────────────
        left = QFrame(); left.setObjectName("card")
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
        right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rl    = QVBoxLayout(right); rl.setContentsMargins(15, 10, 15, 8); rl.setSpacing(6)
        rl.addWidget(lbl("REGISTRAR NUEVO ADMIN", "tag"))
        rl.addWidget(sep_line())
        rl.addSpacing(4)   # Espacio después del separador


        # Campos mapeados a Usuarios
        rl.addWidget(lbl("Nombre"))
        self.f_nombre = QLineEdit(); self.f_nombre.setObjectName("inp")
        self.f_nombre.setPlaceholderText("Juan")
        rl.addWidget(self.f_nombre)
        rl.addSpacing(4)

        rl.addWidget(lbl("Apellido paterno"))
        self.f_ap = QLineEdit(); self.f_ap.setObjectName("inp")
        self.f_ap.setPlaceholderText("Garcia")
        rl.addWidget(self.f_ap)
        rl.addSpacing(4)

        rl.addWidget(lbl("Apellido materno"))
        self.f_am = QLineEdit(); self.f_am.setObjectName("inp")
        self.f_am.setPlaceholderText("Lopez")
        rl.addWidget(self.f_am)
        rl.addSpacing(4)

        rl.addWidget(lbl("Usuario"))
        self.f_user = QLineEdit(); self.f_user.setObjectName("inp")
        self.f_user.setPlaceholderText("jgarcia01")
        rl.addWidget(self.f_user)
        rl.addSpacing(4)

        rl.addWidget(lbl("Rol"))
        self.f_rol = QComboBox(); self.f_rol.setObjectName("combo")
        self.f_rol.addItems(["empleado", "supervisor", "administrador"])
        rl.addWidget(self.f_rol)
        rl.addSpacing(4)

        rl.addWidget(lbl("Contraseña"))
        self.f_pass = QLineEdit(); self.f_pass.setObjectName("inp")
        self.f_pass.setEchoMode(QLineEdit.Password)
        self.f_pass.setPlaceholderText("••••••••")
        rl.addWidget(self.f_pass)
        rl.addSpacing(4)

        rl.addWidget(lbl("Confirmar contraseña"))
        self.f_pass2 = QLineEdit(); self.f_pass2.setObjectName("inp")
        self.f_pass2.setEchoMode(QLineEdit.Password)
        self.f_pass2.setPlaceholderText("••••••••")
        rl.addWidget(self.f_pass2)

        # Espaciador para separar campos de mensajes
        rl.addSpacing(12)

        # Mensajes de error/éxito
        self.reg_err = lbl("", "err", Qt.AlignCenter)
        self.reg_ok  = lbl("", "ok",  Qt.AlignCenter)
        rl.addWidget(self.reg_err)
        rl.addWidget(self.reg_ok)

        # Espacio antes del botón
        rl.addSpacing(4)

        btn_reg = QPushButton("REGISTRAR ADMINISTRADOR"); btn_reg.setObjectName("btn_blue")
        btn_reg.setCursor(Qt.PointingHandCursor); btn_reg.clicked.connect(self._register)
        btn_reg.setMinimumHeight(32)
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
