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
QWidget#admin_users_panel, QWidget#admin_users_inner { background: #0a1a2f; color: #e0edff; }
QWidget#inner_bg { background: #11223b; }

/* ===== TIPOGRAFÍA MEJORADA ===== */
QLabel#tag { 
    color: #7aa9d9; 
    font-size: 15px; 
    font-weight: 800; 
    font-family: 'Montserrat', 'Segoe UI', sans-serif; 
    letter-spacing: 2px; 
    text-transform: uppercase;
}
QLabel#body { 
    color: #a0c0e0; 
    font-size: 15px; 
    font-family: 'Segoe UI', sans-serif; 
    font-weight: 500;
}
QLabel#small { 
    color: #a0c0e0; 
    font-size: 13px; 
    font-family: 'Segoe UI', sans-serif; 
    letter-spacing: 0.5px; 
    font-weight: 500;
}
QLabel#ok { 
    color: #3de8a0; 
    font-size: 15px; 
    font-weight: 600; 
    font-family: 'Segoe UI', sans-serif; 
}
QLabel#err { 
    color: #f06a8a; 
    font-size: 15px; 
    font-weight: 600; 
    font-family: 'Segoe UI', sans-serif; 
}

/* ===== BADGES MEJORADOS ===== */
QLabel#badge_blue {
    background: #1e3a5a;
    color: #ffffff;
    border: none;
    border-radius: 20px;
    padding: 6px 18px;
    font-size: 13px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 0.5px;
}
QLabel#badge_green {
    background: #1a4a3a;
    color: #ffffff;
    border: none;
    border-radius: 20px;
    padding: 6px 18px;
    font-size: 13px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#badge_red {
    background: #4a2a3a;
    color: #ffffff;
    border: none;
    border-radius: 20px;
    padding: 6px 18px;
    font-size: 13px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

/* ===== SEPARADOR ===== */
QFrame#sep { 
    background: #1e3a5a; 
    min-height: 2px; 
    max-height: 2px; 
    margin: 8px 0 12px 0;
}

/* ===== TARJETAS ===== */
QFrame#card { 
    background: #11223b; 
    border: 1px solid #1e3a5a; 
    border-radius: 20px; 
}
QFrame#card_blue { 
    background: #0f2a44; 
    border: 1px solid #2b5797; 
    border-radius: 20px; 
}

/* ===== INPUTS MÁS GRANDES ===== */
QLineEdit#inp {
    background: #0a1a2f;
    border: 2px solid #1e3a5a;
    border-radius: 14px;
    color: #ffffff;
    padding: 16px 20px;
    font-size: 15px;
    font-family: 'Segoe UI', sans-serif;
    selection-background-color: #2b6eb0;
    min-height: 30px;
}
QLineEdit#inp:focus { 
    border-color: #4a7db0; 
    background: #0f2a44;
}
QLineEdit#inp::placeholder { 
    color: #5f7fa0; 
    font-style: italic;
    font-size: 14px;
}

/* ===== COMBOBOX MÁS GRANDE ===== */
QComboBox#combo {
    background: #0a1a2f;
    border: 2px solid #1e3a5a;
    border-radius: 14px;
    color: #ffffff;
    padding: 14px 20px;
    font-size: 15px;
    font-family: 'Segoe UI', sans-serif;
    min-height: 30px;
}
QComboBox#combo:focus { 
    border-color: #4a7db0; 
    background: #0f2a44;
}
QComboBox#combo::drop-down { 
    border: none; 
    width: 40px;
}
QComboBox#combo::down-arrow { 
    image: none;
    border-left: 8px solid transparent;
    border-right: 8px solid transparent;
    border-top: 10px solid #7aa9d9;
    margin-right: 12px;
}
QComboBox QAbstractItemView { 
    background: #11223b; 
    color: #ffffff; 
    border: 2px solid #1e3a5a;
    border-radius: 12px;
    selection-background-color: #2b4a70;
    selection-color: #ffffff;
    padding: 8px;
    font-size: 14px;
}

/* ===== BOTONES MEJORADOS ===== */
QPushButton#btn_blue {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2b6eb0, stop:1 #1a4a8a);
    color: #ffffff;
    border: none;
    border-radius: 40px;
    padding: 18px 36px;
    font-size: 16px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1.5px;
    min-height: 40px;
    margin-top: 10px;
}
QPushButton#btn_blue:hover { 
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a7fc9, stop:1 #2b5fa0);
}
QPushButton#btn_blue:pressed { 
    background: #1a4a8a; 
}

QPushButton#btn_red {
    background: #4a2a3a;
    color: #ffffff;
    border: none;
    border-radius: 40px;
    padding: 16px 32px;
    font-size: 15px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
    min-height: 40px;
}
QPushButton#btn_red:hover { 
    background: #5a3a4a;
}
QPushButton#btn_red:pressed { 
    background: #3a1a2a; 
}

/* ===== SCROLLBAR ===== */
QScrollArea { 
    border: none; 
    background: transparent; 
}
QScrollBar:vertical { 
    background: #0a1a2f; 
    width: 10px; 
    margin: 0; 
    border-radius: 5px;
}
QScrollBar::handle:vertical { 
    background: #2b4a70; 
    border-radius: 5px; 
    min-height: 40px; 
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
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # Título de la sección (fuera de las tarjetas)
        title = QLabel("ADMINISTRADORES")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: 900;
                font-family: 'Montserrat', 'Segoe UI', sans-serif;
                letter-spacing: 2px;
                padding: 10px 24px 0 24px;
            }
        """)
        main_layout.addWidget(title)

        # Contenedor de dos columnas
        columns_layout = QHBoxLayout()
        columns_layout.setContentsMargins(24, 10, 24, 24)
        columns_layout.setSpacing(24)

        # ── COLUMNA IZQUIERDA: LISTA DE ADMINISTRADORES ──────────────────
        left_card = QFrame()
        left_card.setObjectName("card")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Header de la tarjeta izquierda
        left_header = QFrame()
        left_header.setStyleSheet("background: #1e3a5a; border-radius: 20px 20px 0 0;")
        left_header.setFixedHeight(60)
        left_header_layout = QHBoxLayout(left_header)
        left_header_layout.setContentsMargins(20, 0, 20, 0)
        
        left_title = QLabel("ADMINISTRADORES ACTIVOS")
        left_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: 800;
                font-family: 'Segoe UI', sans-serif;
                letter-spacing: 1px;
            }
        """)
        left_header_layout.addWidget(left_title)
        left_header_layout.addStretch()
        
        left_layout.addWidget(left_header)

        # Scroll area para la lista de admins
        scroll_left = QScrollArea()
        scroll_left.setWidgetResizable(True)
        scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.inner = QWidget()
        self.inner.setObjectName("admin_users_inner")
        self.il = QVBoxLayout(self.inner)
        self.il.setContentsMargins(16, 16, 16, 16)
        self.il.setSpacing(10)
        self.il.setAlignment(Qt.AlignTop)
        
        scroll_left.setWidget(self.inner)
        left_layout.addWidget(scroll_left, 1)

        # Botón desactivar
        btn_del = QPushButton("DESACTIVAR ADMINISTRADOR")
        btn_del.setObjectName("btn_red")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.clicked.connect(self._delete)
        btn_del.setStyleSheet("""
            QPushButton#btn_red {
                margin: 16px;
                padding: 14px;
            }
        """)
        left_layout.addWidget(btn_del)

        # ── COLUMNA DERECHA: FORMULARIO DE REGISTRO CON SCROLL ────────────
        right_card = QFrame()
        right_card.setObjectName("card_blue")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Header de la tarjeta derecha
        right_header = QFrame()
        right_header.setStyleSheet("background: #1e3a5a; border-radius: 20px 20px 0 0;")
        right_header.setFixedHeight(60)
        right_header_layout = QHBoxLayout(right_header)
        right_header_layout.setContentsMargins(20, 0, 20, 0)
        
        right_title = QLabel("REGISTRAR NUEVO ADMINISTRADOR")
        right_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: 800;
                font-family: 'Segoe UI', sans-serif;
                letter-spacing: 1px;
            }
        """)
        right_header_layout.addWidget(right_title)
        right_header_layout.addStretch()
        
        right_layout.addWidget(right_header)

        # SCROLL AREA para el formulario (para que no se desborde)
        scroll_right = QScrollArea()
        scroll_right.setWidgetResizable(True)
        scroll_right.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_right.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Widget contenedor del formulario
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(16)

        # Campos del formulario (todos con label y campo)
        # Nombre
        nombre_label = QLabel("Nombre completo")
        nombre_label.setStyleSheet("color: #a0c0e0; font-size: 14px; font-weight: 600; margin-top: 5px;")
        form_layout.addWidget(nombre_label)
        
        self.f_nombre = QLineEdit()
        self.f_nombre.setObjectName("inp")
        self.f_nombre.setPlaceholderText("Ej: Juan Carlos")
        form_layout.addWidget(self.f_nombre)

        # Apellido paterno
        ap_label = QLabel("Apellido paterno")
        ap_label.setStyleSheet("color: #a0c0e0; font-size: 14px; font-weight: 600; margin-top: 5px;")
        form_layout.addWidget(ap_label)
        
        self.f_ap = QLineEdit()
        self.f_ap.setObjectName("inp")
        self.f_ap.setPlaceholderText("Ej: García")
        form_layout.addWidget(self.f_ap)

        # Apellido materno
        am_label = QLabel("Apellido materno")
        am_label.setStyleSheet("color: #a0c0e0; font-size: 14px; font-weight: 600; margin-top: 5px;")
        form_layout.addWidget(am_label)
        
        self.f_am = QLineEdit()
        self.f_am.setObjectName("inp")
        self.f_am.setPlaceholderText("Ej: López (opcional)")
        form_layout.addWidget(self.f_am)

        # Usuario
        user_label = QLabel("Nombre de usuario")
        user_label.setStyleSheet("color: #a0c0e0; font-size: 14px; font-weight: 600; margin-top: 5px;")
        form_layout.addWidget(user_label)
        
        self.f_user = QLineEdit()
        self.f_user.setObjectName("inp")
        self.f_user.setPlaceholderText("Ej: jgarcia01")
        form_layout.addWidget(self.f_user)

        # Rol
        rol_label = QLabel("Rol")
        rol_label.setStyleSheet("color: #a0c0e0; font-size: 14px; font-weight: 600; margin-top: 5px;")
        form_layout.addWidget(rol_label)
        
        self.f_rol = QComboBox()
        self.f_rol.setObjectName("combo")
        self.f_rol.addItems(["empleado", "supervisor", "administrador"])
        form_layout.addWidget(self.f_rol)

        # Contraseña
        pass_label = QLabel("Contraseña")
        pass_label.setStyleSheet("color: #a0c0e0; font-size: 14px; font-weight: 600; margin-top: 5px;")
        form_layout.addWidget(pass_label)
        
        self.f_pass = QLineEdit()
        self.f_pass.setObjectName("inp")
        self.f_pass.setEchoMode(QLineEdit.Password)
        self.f_pass.setPlaceholderText("Mínimo 4 caracteres")
        form_layout.addWidget(self.f_pass)

        # Confirmar contraseña
        pass2_label = QLabel("Confirmar contraseña")
        pass2_label.setStyleSheet("color: #a0c0e0; font-size: 14px; font-weight: 600; margin-top: 5px;")
        form_layout.addWidget(pass2_label)
        
        self.f_pass2 = QLineEdit()
        self.f_pass2.setObjectName("inp")
        self.f_pass2.setEchoMode(QLineEdit.Password)
        self.f_pass2.setPlaceholderText("Repite la contraseña")
        form_layout.addWidget(self.f_pass2)

        # Separador
        sep = QFrame()
        sep.setObjectName("sep")
        sep.setFixedHeight(2)
        form_layout.addWidget(sep)

        # Mensajes de error/éxito
        self.reg_err = QLabel("")
        self.reg_err.setObjectName("err")
        self.reg_err.setAlignment(Qt.AlignCenter)
        self.reg_err.setWordWrap(True)
        form_layout.addWidget(self.reg_err)

        self.reg_ok = QLabel("")
        self.reg_ok.setObjectName("ok")
        self.reg_ok.setAlignment(Qt.AlignCenter)
        self.reg_ok.setWordWrap(True)
        form_layout.addWidget(self.reg_ok)

        # Botón registrar
        btn_reg = QPushButton("REGISTRAR ADMINISTRADOR")
        btn_reg.setObjectName("btn_blue")
        btn_reg.setCursor(Qt.PointingHandCursor)
        btn_reg.clicked.connect(self._register)
        form_layout.addWidget(btn_reg)

        # Espacio extra al final
        form_layout.addStretch()

        # Asignar el contenedor al scroll
        scroll_right.setWidget(form_container)
        right_layout.addWidget(scroll_right)

        # Agregar ambas columnas al layout principal
        columns_layout.addWidget(left_card, 1)
        columns_layout.addWidget(right_card, 1)
        main_layout.addLayout(columns_layout)

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
            self.reg_err.setText("❌ Nombre, apellido, usuario y contraseña son obligatorios.")
            return
        if len(pw) < 4:
            self.reg_err.setText("❌ La contraseña debe tener al menos 4 caracteres.")
            return
        if pw != pw2:
            self.reg_err.setText("❌ Las contraseñas no coinciden.")
            return
        if db_admin_exists(user):
            self.reg_err.setText("❌ Ya existe un administrador con ese usuario.")
            return

        new_id = db_register_admin(nombre, ap, am, user, pw, rol, id_reg)
        if new_id:
            for f in [self.f_nombre, self.f_ap, self.f_am, self.f_user, self.f_pass, self.f_pass2]:
                f.clear()
            self.reg_ok.setText(f"✓ Administrador '{user}' registrado correctamente.")
            self.refresh()
        else:
            self.reg_err.setText("❌ No se pudo registrar. Intenta de nuevo.")

    def _delete(self):
        u, ok = QInputDialog.getText(None, "Desactivar Administrador", "Usuario a desactivar:")
        if not ok or not u.strip():
            return
        if not db_admin_exists(u.strip()):
            QMessageBox.warning(None, "Error", "Administrador no encontrado.")
            return
        if db_count_active_admins() <= 1:
            QMessageBox.warning(None, "Error", "Debe existir al menos un administrador activo.")
            return
        id_act = self._current_admin.get("ID_admin")
        db_delete_admin(u.strip(), id_act)
        QMessageBox.information(None, "OK", f"Administrador '{u.strip()}' desactivado.")
        self.refresh()

    def refresh(self):
        # Limpiar lista actual
        for i in reversed(range(self.il.count())):
            item = self.il.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        admins = db_get_all_admins()
        if not admins:
            empty_lbl = QLabel("No hay administradores registrados")
            empty_lbl.setStyleSheet("color: #5f7fa0; font-size: 15px; font-style: italic; padding: 50px 0;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.il.addWidget(empty_lbl)
        else:
            for a in admins:
                # Tarjeta de administrador
                card = QFrame()
                card.setObjectName("card")
                card.setStyleSheet("""
                    QFrame#card {
                        background: #11223b;
                        border: 1px solid #1e3a5a;
                        border-radius: 16px;
                        margin: 2px 0;
                    }
                """)
                
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(16, 16, 16, 16)
                card_layout.setSpacing(8)

                # Fila superior: nombre
                name_lbl = QLabel("{} {} {}".format(
                    a.get("t_nombre", ""),
                    a.get("t_apellido_paterno", ""),
                    a.get("t_apellido_materno", "")
                ).strip())
                name_lbl.setStyleSheet("""
                    color: #ffffff;
                    font-size: 15px;
                    font-weight: 700;
                    font-family: 'Segoe UI', sans-serif;
                """)
                card_layout.addWidget(name_lbl)

                # Fila de usuario
                user_lbl = QLabel(f"@{a.get('t_usuario', '')}")
                user_lbl.setStyleSheet("""
                    color: #7aa9d9;
                    font-size: 14px;
                    font-family: 'Segoe UI', sans-serif;
                    font-weight: 500;
                """)
                card_layout.addWidget(user_lbl)

                # Fila de badges
                badges_row = QHBoxLayout()
                badges_row.setSpacing(8)

                # Badge de rol
                rol_text = a.get("t_rol", "").upper()
                if rol_text == "ADMINISTRADOR":
                    rol_text = "ADMIN"
                rol_badge = QLabel(rol_text)
                rol_badge.setStyleSheet("""
                    background: #1e3a5a;
                    color: #ffffff;
                    border-radius: 16px;
                    padding: 4px 14px;
                    font-size: 12px;
                    font-weight: 600;
                """)
                badges_row.addWidget(rol_badge)

                # Badge de estado
                estado = a.get("t_estado", "").upper()
                if estado == "ACTIVO":
                    estado_badge = QLabel("● ACTIVO")
                    estado_badge.setStyleSheet("""
                        background: #1a4a3a;
                        color: #ffffff;
                        border-radius: 16px;
                        padding: 4px 14px;
                        font-size: 12px;
                        font-weight: 600;
                    """)
                else:
                    estado_badge = QLabel("○ INACTIVO")
                    estado_badge.setStyleSheet("""
                        background: #4a2a3a;
                        color: #ffffff;
                        border-radius: 16px;
                        padding: 4px 14px;
                        font-size: 12px;
                        font-weight: 600;
                    """)
                badges_row.addWidget(estado_badge)
                badges_row.addStretch()

                card_layout.addLayout(badges_row)
                self.il.addWidget(card)
        self.il.addStretch()