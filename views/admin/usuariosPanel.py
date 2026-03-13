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
    QDialog,
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

/* Botón verde (NUEVO ADMIN) */
QPushButton#btn_green {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2ecc71, stop:1 #27ae60);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
    min-height: 30px;
}

QPushButton#btn_green:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #27ae60, stop:1 #229954);
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

/* Diálogo de registro */
QDialog {
    background: #f0f6ff;
}

QLabel#dialog_title {
    color: #1565c0;
    font-size: 14px;
    font-weight: 900;
    font-family: 'Segoe UI';
    letter-spacing: 2px;
}

QLabel#field_label {
    color: #546e7a;
    font-family: 'Segoe UI';
    font-weight: 700;
    letter-spacing: 1px;
    font-size: 10px;
}

QPushButton#dialog_ok {
    background: #1976d2;
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 7px 20px;
    font-family: 'Segoe UI';
    font-weight: 700;
    font-size: 10px;
}

QPushButton#dialog_ok:hover {
    background: #1565c0;
}

QPushButton#dialog_cancel {
    background: transparent;
    color: #90a4ae;
    border: 1px solid #cfd8e3;
    border-radius: 6px;
    padding: 7px 16px;
    font-family: 'Segoe UI';
    font-size: 10px;
}
"""

class AdminRegisterDialog(QDialog):
    """Diálogo para registrar un nuevo administrador."""
    
    def __init__(self, current_admin_id=None, parent=None):
        super().__init__(parent)
        self.current_admin_id = current_admin_id
        self.setWindowTitle("Registrar Nuevo Administrador")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(450)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # Título
        ttl = QLabel("➕  REGISTRAR NUEVO ADMINISTRADOR")
        ttl.setObjectName("dialog_title")
        root.addWidget(ttl)
        
        # Línea separadora
        d = QFrame()
        d.setObjectName("sep")
        d.setFixedHeight(1)
        root.addWidget(d)

        # Formulario
        form = QVBoxLayout()
        form.setSpacing(8)

        # Nombre
        lbl_nombre = QLabel("NOMBRE")
        lbl_nombre.setObjectName("field_label")
        form.addWidget(lbl_nombre)
        self.f_nombre = QLineEdit()
        self.f_nombre.setPlaceholderText("Juan")
        self.f_nombre.setObjectName("inp")
        form.addWidget(self.f_nombre)

        # Apellido paterno
        lbl_ap = QLabel("APELLIDO PATERNO")
        lbl_ap.setObjectName("field_label")
        form.addWidget(lbl_ap)
        self.f_ap = QLineEdit()
        self.f_ap.setPlaceholderText("Garcia")
        self.f_ap.setObjectName("inp")
        form.addWidget(self.f_ap)

        # Apellido materno
        lbl_am = QLabel("APELLIDO MATERNO")
        lbl_am.setObjectName("field_label")
        form.addWidget(lbl_am)
        self.f_am = QLineEdit()
        self.f_am.setPlaceholderText("Lopez")
        self.f_am.setObjectName("inp")
        form.addWidget(self.f_am)

        # Usuario
        lbl_user = QLabel("USUARIO")
        lbl_user.setObjectName("field_label")
        form.addWidget(lbl_user)
        self.f_user = QLineEdit()
        self.f_user.setPlaceholderText("jgarcia01")
        self.f_user.setObjectName("inp")
        form.addWidget(self.f_user)

        # Rol
        lbl_rol = QLabel("ROL")
        lbl_rol.setObjectName("field_label")
        form.addWidget(lbl_rol)
        self.f_rol = QComboBox()
        self.f_rol.setObjectName("combo")
        self.f_rol.addItems(["empleado", "supervisor", "administrador"])
        form.addWidget(self.f_rol)

        # Contraseña
        lbl_pass = QLabel("CONTRASEÑA")
        lbl_pass.setObjectName("field_label")
        form.addWidget(lbl_pass)
        self.f_pass = QLineEdit()
        self.f_pass.setEchoMode(QLineEdit.Password)
        self.f_pass.setPlaceholderText("••••••••")
        self.f_pass.setObjectName("inp")
        form.addWidget(self.f_pass)

        # Confirmar contraseña
        lbl_pass2 = QLabel("CONFIRMAR CONTRASEÑA")
        lbl_pass2.setObjectName("field_label")
        form.addWidget(lbl_pass2)
        self.f_pass2 = QLineEdit()
        self.f_pass2.setEchoMode(QLineEdit.Password)
        self.f_pass2.setPlaceholderText("••••••••")
        self.f_pass2.setObjectName("inp")
        form.addWidget(self.f_pass2)

        # Espaciador
        form.addSpacing(10)

        # Mensajes de error/éxito
        self.reg_err = QLabel("")
        self.reg_err.setObjectName("err")
        self.reg_err.setAlignment(Qt.AlignCenter)
        form.addWidget(self.reg_err)

        self.reg_ok = QLabel("")
        self.reg_ok.setObjectName("ok")
        self.reg_ok.setAlignment(Qt.AlignCenter)
        form.addWidget(self.reg_ok)

        root.addLayout(form)

        # Botones
        br = QHBoxLayout()
        br.addStretch()

        bn = QPushButton("CANCELAR")
        bn.setObjectName("dialog_cancel")
        bn.setCursor(Qt.PointingHandCursor)
        bn.clicked.connect(self.reject)

        bo = QPushButton("REGISTRAR")
        bo.setObjectName("dialog_ok")
        bo.setCursor(Qt.PointingHandCursor)
        bo.clicked.connect(self._register)

        br.addWidget(bn)
        br.addWidget(bo)
        root.addLayout(br)

    def _register(self):
        nombre = self.f_nombre.text().strip()
        ap = self.f_ap.text().strip()
        am = self.f_am.text().strip()
        user = self.f_user.text().strip()
        rol = self.f_rol.currentText()
        pw = self.f_pass.text()
        pw2 = self.f_pass2.text()

        self.reg_err.setText("")
        self.reg_ok.setText("")

        if not all([nombre, ap, user, pw]):
            self.reg_err.setText("Nombre, apellido paterno, usuario y contraseña son obligatorios.")
            return
        if len(pw) < 4:
            self.reg_err.setText("La contraseña debe tener al menos 4 caracteres.")
            return
        if pw != pw2:
            self.reg_err.setText("Las contraseñas no coinciden.")
            return
        if db_admin_exists(user):
            self.reg_err.setText("Ya existe un administrador con ese usuario.")
            return

        new_id = db_register_admin(nombre, ap, am, user, pw, rol, self.current_admin_id)
        if new_id:
            self.reg_ok.setText(f"Administrador '{user}' registrado correctamente.")
            # Limpiar campos
            self.f_nombre.clear()
            self.f_ap.clear()
            self.f_am.clear()
            self.f_user.clear()
            self.f_pass.clear()
            self.f_pass2.clear()
            # Cerrar después de mostrar el mensaje
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1500, self.accept)
        else:
            self.reg_err.setText("No se pudo registrar. Intenta de nuevo.")


class _AdminUsersPanel(QWidget):
    """
    Permite gestionar administradores: ver lista, desactivar y registrar nuevos.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("admin_users_panel")
        self.setStyleSheet(STYLE)
        self._current_admin = {}
        vl = QVBoxLayout(self); vl.setContentsMargins(10, 10, 10, 10); vl.setSpacing(16)

        body = QHBoxLayout(); body.setSpacing(15)

        # Lista de admins
        left = QFrame(); left.setObjectName("card")
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        ll   = QVBoxLayout(left); ll.setContentsMargins(24, 24, 24, 24); ll.setSpacing(12)
        
        # Header con título y botón NUEVO ADMIN
        header = QHBoxLayout()
        header.addWidget(lbl("ADMINISTRADORES ACTIVOS", "tag"))
        header.addStretch()
        
        btn_new = QPushButton("+  NUEVO ADMIN")
        btn_new.setObjectName("btn_green")
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.clicked.connect(self._nuevo_admin)
        header.addWidget(btn_new)
        
        ll.addLayout(header)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.inner = QWidget(); self.inner.setObjectName("admin_users_inner")
        self.il    = QVBoxLayout(self.inner)
        self.il.setContentsMargins(0, 0, 0, 0); self.il.setSpacing(8)
        scroll.setWidget(self.inner)
        ll.addWidget(scroll, 1)

        btn_del = QPushButton("DESACTIVAR ADMIN"); btn_del.setObjectName("btn_red")
        btn_del.setCursor(Qt.PointingHandCursor); btn_del.clicked.connect(self._delete)
        ll.addWidget(btn_del)

        # Ya no hay panel derecho, solo el izquierdo ocupa todo
        body.addWidget(left, 1)
        vl.addLayout(body, 1)
        self.refresh()

    def set_current_admin(self, admin_data):
        self._current_admin = admin_data

    def _nuevo_admin(self):
        """Abre el diálogo para registrar un nuevo administrador."""
        dlg = AdminRegisterDialog(
            current_admin_id=self._current_admin.get("ID_admin"),
            parent=self
        )
        if dlg.exec_() == QDialog.Accepted:
            self.refresh()
            # Opcional: mostrar mensaje de éxito
            # El diálogo ya muestra su propio mensaje

    def _delete(self):
        u, ok = QInputDialog.getText(self, "Desactivar Admin", "Usuario a desactivar:")
        if not ok or not u.strip():
            return
        if not db_admin_exists(u.strip()):
            QMessageBox.warning(self, "Error", "Admin no encontrado.")
            return
        if db_count_active_admins() <= 1:
            QMessageBox.warning(self, "Error", "Debe existir al menos un administrador activo.")
            return
        id_act = self._current_admin.get("ID_admin")
        db_delete_admin(u.strip(), id_act)
        QMessageBox.information(self, "OK", "Admin '{}' desactivado.".format(u.strip()))
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
                    "color:#2c6289; font-size:13px; font-weight:700; font-family:'Segoe UI';"
                )
                u_lbl  = lbl("@{}".format(a.get("t_usuario", "")), "small")
                r_lbl  = lbl(a.get("t_rol", ""), "badge_blue")
                st_obj = "badge_green" if a.get("t_estado") == "activo" else "badge_red"
                s_lbl  = lbl(a.get("t_estado", "").upper(), st_obj)

                rl.addWidget(n_lbl); rl.addWidget(u_lbl)
                rl.addStretch(); rl.addWidget(r_lbl); rl.addWidget(s_lbl)
                self.il.addWidget(row)
        self.il.addStretch()