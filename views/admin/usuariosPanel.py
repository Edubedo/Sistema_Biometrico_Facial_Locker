from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFrame,
    QSizePolicy,
    QApplication,
    QDialog,
    QGridLayout,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient

from db.models.usuarios import (
    db_admin_exists,
    db_count_active_admins,
    db_delete_admin,
    db_get_all_admins,
    db_register_admin,
    db_set_admin_estado,
    db_update_admin,
)
from views.style.adminDialogs import DlgError, DlgInfo, DlgConfirm
from utils.i18n import tr, get_language


def _dp(v):
    s = QApplication.primaryScreen()
    return max(1, round(v * (s.logicalDotsPerInch() if s else 96) / 96))


_C = {
    "activo":   ("#e8f5e9", "#2e7d32", "#c8e6c9", "#1b5e20", "#a5d6a7"),
    "inactivo": ("#fafafa", "#78909c", "#eceff1", "#000000", "#b0bec5"),
}

STYLE = """
QWidget#panel,QWidget#inner{
    background:transparent;
}
QLabel#ttl{
    color:#1565c0;
    font-weight:900;
    font-family:'Segoe UI';
    letter-spacing:3px;
    font-size:18px;
}
QLabel#sub{
    color:#000000;
    font-family:'Segoe UI';
    letter-spacing:2px;
    font-size:15px;
}
QFrame#h_div{
    background:#cfd8e3;
    border:none;
    min-height:1px;
    max-height:1px;
}
QFrame#cnt{
    background:#fff;
    border:none;
    border-left:4px solid #1565c0;
    border-radius:8px;
}
QLabel#cn_b{
    color:#1565c0;
    font-weight:800;
    font-family:'Segoe UI';
}
QLabel#cn_o{
    color:#2e7d32;
    font-weight:800;
    font-family:'Segoe UI';
}
QLabel#cn_g{
    color:#000000;
    font-weight:800;
    font-family:'Segoe UI';
}
QLabel#ck  {
    color:#000000;
    font-family:'Segoe UI';
    letter-spacing:2px;
}
QFrame#card_activo   {
    background:#fff;
    border:none;
    border-left:4px solid #2e7d32;
    border-radius:8px;
}
QFrame#card_inactivo {
    background:#fafafa;
    border:none;
    border-left:4px solid #78909c;
    border-radius:8px;
}
QLabel#meta{
    color:#000000;
    font-family:'Segoe UI';
    letter-spacing:1px;
}
QPushButton#btn_add{
    background:#1976d2;
    color:#fff;border:none;
    border-radius:7px;
    font-family:'Segoe UI';
    font-weight:700;
    letter-spacing:2px;
}
QPushButton#btn_add:hover{
    background:#1565c0;
}
QPushButton#btn_ref{
    background:transparent;
    color:#000000;
    border:1px solid #cfd8e3;
    border-radius:6px;
    font-family:'Segoe UI';
    letter-spacing:2px;
}
QPushButton#btn_ref:hover{
    color:#1565c0;
    border-color:#1976d2;
    background:#e3f0ff;
}
QPushButton#btn_cfg{
    background:transparent;
    color:#000000;
    border:1px solid #e0e8f4;
    border-radius:5px;
    font-family:'Segoe UI';
}
QPushButton#btn_cfg:hover{
    color:#1565c0;
    border-color:#1976d2;
    background:#e3f0ff;
}
QPushButton#btn_del{
    background:transparent;
    color:#c62828;
    border:1px solid #ef9a9a;
    border-radius:5px;
    font-family:'Segoe UI';
    font-weight:700;
    }
QPushButton#btn_del:hover{
    background:#ffebee;
    border-color:#c62828;
}
QScrollArea{
    border:none;
    background:transparent;
}
QScrollBar:vertical{
    background:#e8f0fb;
    width:4px;margin:0;
}
QScrollBar::handle:vertical{
    background:#90c4f0;
    border-radius:2px;
    min-height:20px;
}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{
    height:0;
}
QDialog{
    background:#f0f6ff;
}
QLineEdit,QComboBox{
    background:#fff;
    border:1px solid #cfd8e3;
    border-radius:5px;
    padding:5px 8px;color:#1565c0;
    font-family:'Segoe UI';
}
QLineEdit:focus,QComboBox:focus{
    border-color:#1976d2;
}
QLabel#flbl{
    color:#000000;
    font-family:'Segoe UI';
    font-weight:700;
    letter-spacing:1px;
}
QPushButton#dok{
    background:#1976d2;
    color:#fff;border:none;
    border-radius:6px;
    padding:7px 20px;
    font-family:'Segoe UI';
    font-weight:700;
}
QPushButton#dok:hover{
    background:#1565c0;
}
QPushButton#dno{
    background:transparent;
    color:#000000;
    border:1px solid #cfd8e3;
    border-radius:6px;
    padding:7px 16px;
    font-family:'Segoe UI';
}
QLabel#empty{
    color:#000000;font-family:'Segoe UI';
    letter-spacing:3px;
}

/* ── Real table ───────────────────────────────────────────────────────── */
QTableWidget#admin_users_tbl {
    background: #ffffff;
    border: 1px solid #cfd8e3;
    border-radius: 10px;
    gridline-color: #e3f0ff;
}
QHeaderView::section {
    background: #e3f0ff;
    color: #1565c0;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
    padding: 8px 10px;
    border: none;
}
QTableWidget::item {
    padding: 8px 10px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 15px;
    color: #000000;
}
QTableWidget::item:selected { background: #bbdefb; }
QPushButton#btn_toggle_on{
    background:#e8f5e9;
    color:#1b5e20;
    border:1px solid #a5d6a7;
    border-radius:5px;
    font-family:'Segoe UI';
    font-weight:700;
}
QPushButton#btn_toggle_on:hover{ background:#d6f0d8; }
QPushButton#btn_toggle_off{
    background:#ffebee;
    color:#c62828;
    border:1px solid #ef9a9a;
    border-radius:5px;
    font-family:'Segoe UI';
    font-weight:700;
}
QPushButton#btn_toggle_off:hover{ background:#ffe1e6; }
"""


class AdminRegisterDialog(QDialog):
    ROLES = ["empleado", "supervisor", "administrador"]

    def __init__(self, admin_id=None, parent=None):
        super().__init__(parent)
        self.admin_id = admin_id
        self.data = None
        self.setWindowTitle(tr("admin.users.register_title"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(_dp(380))
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(_dp(20), _dp(16), _dp(20), _dp(16))
        root.setSpacing(_dp(12))

        ttl = QLabel(tr("admin.users.register_head"))
        ttl.setStyleSheet(
            f"color:#1565c0;font-size:{_dp(11)}px;font-weight:900;"
            "font-family:'Segoe UI';letter-spacing:2px;"
        )
        root.addWidget(ttl)
        d = QFrame()
        d.setObjectName("h_div")
        root.addWidget(d)

        grid = QGridLayout()
        grid.setSpacing(_dp(8))
        grid.setColumnStretch(1, 1)
        fs = f"font-size:{_dp(9)}px;"

        def add_row(lbl_text, widget, r):
            lb = QLabel(lbl_text)
            lb.setObjectName("flbl")
            lb.setStyleSheet(fs)
            grid.addWidget(lb, r, 0, Qt.AlignRight | Qt.AlignVCenter)
            widget.setStyleSheet(fs)
            grid.addWidget(widget, r, 1)

        # Campos del formulario
        self.e_nombre = QLineEdit()
        self.e_nombre.setPlaceholderText(tr("admin.users.placeholder.first"))
        self.e_ap = QLineEdit()
        self.e_ap.setPlaceholderText(tr("admin.users.placeholder.last"))
        self.e_am = QLineEdit()
        self.e_am.setPlaceholderText(tr("admin.users.placeholder.mother"))
        self.e_usuario = QLineEdit()
        self.e_usuario.setPlaceholderText(tr("admin.users.placeholder.user"))
        self.e_pass = QLineEdit()
        self.e_pass.setEchoMode(QLineEdit.Password)
        self.e_pass.setPlaceholderText(tr("admin.users.placeholder.pass"))
        self.e_pass2 = QLineEdit()
        self.e_pass2.setEchoMode(QLineEdit.Password)
        self.e_pass2.setPlaceholderText(tr("admin.users.placeholder.pass"))
        self.c_rol = QComboBox()
        self.c_rol.addItems(self.ROLES)

        add_row(tr("admin.users.field.name"), self.e_nombre, 0)
        add_row(tr("admin.users.field.ap"), self.e_ap, 1)
        add_row(tr("admin.users.field.am"), self.e_am, 2)
        add_row(tr("admin.users.field.user"), self.e_usuario, 3)
        add_row(tr("admin.users.field.role"), self.c_rol, 4)
        add_row(tr("admin.users.field.pass"), self.e_pass, 5)
        add_row(tr("admin.users.field.confirm"), self.e_pass2, 6)

        root.addLayout(grid)

        # Mensajes de error
        self.msg_error = QLabel("")
        self.msg_error.setObjectName("err")
        self.msg_error.setStyleSheet(f"color:#c62828;font-size:{_dp(10)}px;")
        self.msg_error.setAlignment(Qt.AlignCenter)
        root.addWidget(self.msg_error)

        br = QHBoxLayout()
        br.addStretch()
        bn = QPushButton(tr("common.cancel"))
        bn.setObjectName("dno")
        bn.setStyleSheet(fs)
        bn.setCursor(Qt.PointingHandCursor)
        bn.clicked.connect(self.reject)
        bo = QPushButton(tr("common.confirm"))
        bo.setObjectName("dok")
        bo.setStyleSheet(fs)
        bo.setCursor(Qt.PointingHandCursor)
        bo.clicked.connect(self._save)
        br.addWidget(bn)
        br.addWidget(bo)
        root.addLayout(br)

    def _save(self):
        nombre = self.e_nombre.text().strip()
        ap = self.e_ap.text().strip()
        am = self.e_am.text().strip()
        usuario = self.e_usuario.text().strip()
        rol = self.c_rol.currentText()
        pw = self.e_pass.text()
        pw2 = self.e_pass2.text()

        self.msg_error.setText("")

        if not all([nombre, ap, usuario, pw]):
            self.msg_error.setText(tr("admin.users.err.required"))
            return
        if len(pw) < 4:
            self.msg_error.setText(tr("admin.users.err.pass_min"))
            return
        if pw != pw2:
            self.msg_error.setText(tr("admin.users.err.pass_mismatch"))
            return
        if db_admin_exists(usuario):
            self.msg_error.setText(tr("admin.users.err.exists"))
            return

        self.data = {
            "nombre": nombre,
            "apellido_paterno": ap,
            "apellido_materno": am or None,
            "usuario": usuario,
            "rol": rol,
            "contrasena": pw,
        }
        self.accept()


class AdminEditDialog(QDialog):
    ROLES = ["empleado", "supervisor", "administrador"]

    def __init__(self, admin: dict, parent=None):
        super().__init__(parent)
        self.admin = admin
        self.data = None
        self.setWindowTitle(tr("admin.users.edit_title"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(_dp(400))
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(_dp(20), _dp(16), _dp(20), _dp(16))
        root.setSpacing(_dp(12))

        ttl = QLabel(tr("admin.users.edit_head"))
        ttl.setStyleSheet(
            f"color:#1565c0;font-size:{_dp(11)}px;font-weight:900;"
            "font-family:'Segoe UI';letter-spacing:2px;"
        )
        root.addWidget(ttl)
        d = QFrame()
        d.setObjectName("h_div")
        root.addWidget(d)

        grid = QGridLayout()
        grid.setSpacing(_dp(8))
        grid.setColumnStretch(1, 1)
        fs = f"font-size:{_dp(9)}px;"

        def add_row(lbl_text, widget, r):
            lb = QLabel(lbl_text)
            lb.setObjectName("flbl")
            lb.setStyleSheet(fs)
            grid.addWidget(lb, r, 0, Qt.AlignRight | Qt.AlignVCenter)
            widget.setStyleSheet(fs)
            grid.addWidget(widget, r, 1)

        self.e_nombre = QLineEdit(admin.get("t_nombre", ""))
        self.e_ap = QLineEdit(admin.get("t_apellido_paterno", ""))
        self.e_am = QLineEdit(admin.get("t_apellido_materno", "") or "")
        self.e_usuario = QLineEdit(admin.get("t_usuario", ""))
        self.c_rol = QComboBox()
        self.c_rol.addItems(self.ROLES)
        self.c_rol.setCurrentText((admin.get("t_rol", "empleado") or "empleado").lower())
        self.e_pass = QLineEdit()
        self.e_pass.setEchoMode(QLineEdit.Password)
        self.e_pass.setPlaceholderText(tr("admin.users.placeholder.new_pass"))
        self.e_pass2 = QLineEdit()
        self.e_pass2.setEchoMode(QLineEdit.Password)
        self.e_pass2.setPlaceholderText(tr("admin.users.placeholder.confirm_pass"))

        add_row(tr("admin.users.field.name"), self.e_nombre, 0)
        add_row(tr("admin.users.field.ap"), self.e_ap, 1)
        add_row(tr("admin.users.field.am"), self.e_am, 2)
        add_row(tr("admin.users.field.user"), self.e_usuario, 3)
        add_row(tr("admin.users.field.role"), self.c_rol, 4)
        add_row(tr("admin.users.field.new_pass"), self.e_pass, 5)
        add_row(tr("admin.users.field.confirm"), self.e_pass2, 6)
        root.addLayout(grid)

        self.msg_error = QLabel("")
        self.msg_error.setObjectName("err")
        self.msg_error.setStyleSheet(f"color:#c62828;font-size:{_dp(10)}px;")
        self.msg_error.setAlignment(Qt.AlignCenter)
        root.addWidget(self.msg_error)

        br = QHBoxLayout()
        br.addStretch()
        bn = QPushButton(tr("common.cancel"))
        bn.setObjectName("dno")
        bn.setStyleSheet(fs)
        bn.setCursor(Qt.PointingHandCursor)
        bn.clicked.connect(self.reject)
        bo = QPushButton(tr("common.update"))
        bo.setObjectName("dok")
        bo.setStyleSheet(fs)
        bo.setCursor(Qt.PointingHandCursor)
        bo.clicked.connect(self._save)
        br.addWidget(bn)
        br.addWidget(bo)
        root.addLayout(br)

    def _save(self):
        nombre = self.e_nombre.text().strip()
        ap = self.e_ap.text().strip()
        am = self.e_am.text().strip()
        usuario = self.e_usuario.text().strip()
        rol = self.c_rol.currentText().strip().lower()
        pw = self.e_pass.text()
        pw2 = self.e_pass2.text()

        self.msg_error.setText("")
        if not all([nombre, ap, usuario, rol]):
            self.msg_error.setText(tr("admin.users.err.required_role"))
            return
        if pw or pw2:
            if len(pw) < 4:
                self.msg_error.setText(tr("admin.users.err.pass_min"))
                return
            if pw != pw2:
                self.msg_error.setText(tr("admin.users.err.pass_mismatch"))
                return

        self.data = {
            "id_admin": self.admin.get("ID_admin"),
            "nombre": nombre,
            "apellido_paterno": ap,
            "apellido_materno": am or None,
            "usuario": usuario,
            "rol": rol,
            "contrasena": pw or None,
        }
        self.accept()


class AdminCard(QFrame):
    def __init__(self, admin, index, admin_id=None, on_refresh=None, parent=None):
        super().__init__(parent)
        self.admin = admin
        self.admin_id = admin_id
        self.on_refresh = on_refresh

        estado = admin.get("t_estado", "activo").lower()
        if estado not in _C:
            estado = "activo"
        _, _, badge_bg, badge_fg, badge_border = _C[estado]

        self.setObjectName(f"card_{estado}")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(_dp(12), _dp(8), _dp(12), _dp(8))
        lay.setSpacing(_dp(10))

        idx = QLabel(f"{index:02d}")
        idx.setStyleSheet(
            f"color:#bbdefb;font-size:{_dp(13)}px;font-weight:900;"
            f"font-family:'Segoe UI';min-width:{_dp(22)}px;"
        )
        idx.setAlignment(Qt.AlignCenter)
        lay.addWidget(idx)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(
            f"background:#e3f0ff;border:none;"
            f"min-width:{_dp(1)}px;max-width:{_dp(1)}px;"
        )
        lay.addWidget(sep)

        col = QVBoxLayout()
        col.setSpacing(_dp(2))

        # Nombre completo
        nombre_completo = "{} {} {}".format(
            admin.get("t_nombre", ""),
            admin.get("t_apellido_paterno", ""),
            admin.get("t_apellido_materno", "")
        ).strip()
        name_lbl = QLabel(nombre_completo)
        name_lbl.setStyleSheet(
            f"color:#000000;font-size:{_dp(13)}px;font-weight:900;font-family:'Segoe UI';"
        )
        col.addWidget(name_lbl)

        # Usuario y rol
        meta = QLabel(f"@{admin.get('t_usuario', '')}   ·   {admin.get('t_rol', '').upper()}")
        meta.setObjectName("meta")
        meta.setStyleSheet(f"font-size:{_dp(10)}px;")
        col.addWidget(meta)
        lay.addLayout(col)
        lay.addStretch()

        # Badge de estado
        badge_txt = tr("admin.users.active") if estado == "activo" else tr("admin.users.inactive")
        badge = QLabel(badge_txt)
        badge.setStyleSheet(
            f"background:{badge_bg};color:{badge_fg};border:1px solid {badge_border};"
            f"border-radius:8px;font-size:{_dp(7)}px;font-weight:700;"
            f"font-family:'Segoe UI';letter-spacing:2px;padding:{_dp(2)}px {_dp(8)}px;"
        )
        lay.addWidget(badge)

        # Botón eliminar (solo para admins activos y no el último)
        if estado == "activo" and db_count_active_admins() > 1:
            bd = QPushButton("✕")
            bd.setObjectName("btn_del")
            bd.setToolTip(tr("admin.users.confirm.deactivate_btn"))
            bd.setFixedSize(_dp(26), _dp(26))
            bd.setCursor(Qt.PointingHandCursor)
            bd.clicked.connect(self._eliminar)
            lay.addWidget(bd)

    def _eliminar(self):
        usuario = self.admin["t_usuario"]
        nombre = self.admin["t_nombre"]

        if db_count_active_admins() <= 1:
            DlgError.show(tr("admin.users.err.need_one"), title=tr("common.error"), parent=self)
            return

        if not DlgConfirm.ask(
            tr("admin.users.confirm.deactivate", name=nombre, user=usuario),
            title=tr("admin.users.confirm.deactivate_title"),
            confirm_label=tr("admin.users.confirm.deactivate_btn"),
            danger=True,
            parent=self,
        ):
            return

        try:
            db_delete_admin(usuario, self.admin_id)
            DlgInfo.show(tr("admin.users.msg.deleted", user=usuario), parent=self)
            if self.on_refresh:
                self.on_refresh()
        except Exception as ex:
            DlgError.show(str(ex), parent=self)


class _AdminUsersPanel(QWidget):
    def __init__(self, admin_id=None):
        super().__init__()
        self.admin_id = admin_id
        self.role = "administrador"
        self._current_admin = {}  # Inicializar _current_admin
        self.setObjectName("panel")
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        m = _dp(14)
        root.setContentsMargins(m, _dp(10), m, _dp(10))
        root.setSpacing(_dp(8))

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(_dp(6))
        tc = QVBoxLayout()
        tc.setSpacing(_dp(2))
        self.title_lbl = QLabel(tr("admin.users.title"))
        self.title_lbl.setObjectName("ttl")
        self.title_lbl.setStyleSheet(f"font-size:{_dp(12)}px;")
        self.subtitle_lbl = QLabel(tr("admin.users.subtitle"))
        self.subtitle_lbl.setObjectName("sub")
        self.subtitle_lbl.setStyleSheet(f"font-size:{_dp(11)}px;")
        tc.addWidget(self.title_lbl)
        tc.addWidget(self.subtitle_lbl)
        hdr.addLayout(tc)
        hdr.addStretch()

        # Botones
        self.btn_add = QPushButton(tr("admin.users.add"))
        self.btn_add.setObjectName("btn_add")
        self.btn_add.setStyleSheet(f"font-size:{_dp(11)}px;padding:{_dp(7)}px {_dp(16)}px;")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self._agregar)
        hdr.addWidget(self.btn_add)

        self.btn_ref = QPushButton(tr("admin.users.refresh"))
        self.btn_ref.setObjectName("btn_ref")
        self.btn_ref.setStyleSheet(f"font-size:{_dp(11)}px;padding:{_dp(7)}px {_dp(16)}px;")
        self.btn_ref.setCursor(Qt.PointingHandCursor)
        self.btn_ref.clicked.connect(self.refresh)
        hdr.addWidget(self.btn_ref)

        root.addLayout(hdr)
        root.addWidget(self._div())

        # Tabla (estilo "real" con campos)
        self.table = QTableWidget()
        self.table.setObjectName("admin_users_tbl")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["🔢", tr("admin.users.name"), tr("admin.users.user"), tr("admin.users.role"), tr("admin.users.state"), tr("admin.users.actions")])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setMinimumSectionSize(_dp(110))
        self.table.verticalHeader().setDefaultSectionSize(_dp(44))
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        root.addWidget(self.table, 1)

        self.set_language(get_language())
        self.refresh()

    def set_language(self, _lang: str):
        self.title_lbl.setText(tr("admin.users.title"))
        self.subtitle_lbl.setText(tr("admin.users.subtitle"))
        self.btn_add.setText(tr("admin.users.add"))
        self.btn_ref.setText(tr("admin.users.refresh"))
        self.table.setHorizontalHeaderLabels([
            "🔢",
            tr("admin.users.name"),
            tr("admin.users.user"),
            tr("admin.users.role"),
            tr("admin.users.state"),
            tr("admin.users.actions"),
        ])
        self.refresh()

    def set_current_admin(self, admin_data):
        """Método requerido para establecer el administrador actual"""
        self._current_admin = admin_data
        self.admin_id = admin_data.get("ID_admin") if admin_data else None
        self.role = (admin_data.get("t_rol", "empleado") if admin_data else "empleado").lower()
        can_manage_admins = self.role == "administrador"
        self.btn_add.setEnabled(can_manage_admins)
        self.btn_add.setToolTip(
            tr("admin.users.role_hint")
            if not can_manage_admins else tr("admin.users.role_register")
        )
        self.refresh()

    def _div(self):
        d = QFrame()
        d.setObjectName("h_div")
        return d

    def _delete_admin(self, admin: dict):
        if self.role != "administrador":
            DlgError.show(tr("admin.users.err.no_perm_mod"), parent=self)
            return
        usuario = admin.get("t_usuario", "")
        nombre = "{} {} {}".format(
            admin.get("t_nombre", ""),
            admin.get("t_apellido_paterno", ""),
            admin.get("t_apellido_materno", ""),
        ).strip()

        if admin.get("ID_admin") == self.admin_id:
            DlgError.show(
                "Esta cuenta ya está activa y no se puede eliminar.",
                title="Operación no permitida",
                parent=self,
            )
            return

        if db_count_active_admins() <= 1:
            DlgError.show(
                "Debe existir al menos un administrador activo.",
                title="No se puede desactivar",
                parent=self,
            )
            return

        if not DlgConfirm.ask(
            f"¿Desactivar permanentemente al administrador <b>{nombre}</b> (@{usuario})?\n"
            "Esta acción no se puede deshacer.",
            title="Desactivar Admin",
            confirm_label="DESACTIVAR",
            danger=True,
            parent=self,
        ):
            return

        try:
            db_delete_admin(usuario, self.admin_id)
            DlgInfo.show(f"Admin '{usuario}' desactivado correctamente.", parent=self)
        except Exception as ex:
            DlgError.show(str(ex), parent=self)
        finally:
            self.refresh()

    def _set_admin_status(self, admin: dict, target_status: str):
        if self.role != "administrador":
            DlgError.show("No tienes permisos para modificar administradores.", parent=self)
            return
        usuario = admin.get("t_usuario", "")
        nombre = "{} {} {}".format(
            admin.get("t_nombre", ""),
            admin.get("t_apellido_paterno", ""),
            admin.get("t_apellido_materno", ""),
        ).strip()

        if target_status == "inactivo":
            if admin.get("ID_admin") == self.admin_id:
                DlgError.show(tr("admin.users.err.self_delete"), title=tr("common.error"), parent=self)
                return
            if db_count_active_admins() <= 1:
                DlgError.show(tr("admin.users.err.need_one"), title=tr("common.error"), parent=self)
                return

        accion = tr("admin.users.confirm.activate_btn") if target_status == "activo" else tr("admin.users.confirm.deactivate_btn")
        if not DlgConfirm.ask(
            tr("admin.users.confirm.deactivate", name=nombre, user=usuario),
            title=tr("admin.users.confirm.activate_title") if target_status == "activo" else tr("admin.users.confirm.deactivate_title"),
            confirm_label=accion,
            danger=(target_status == "inactivo"),
            parent=self,
        ):
            return

        try:
            db_set_admin_estado(usuario, target_status, self.admin_id)
            DlgInfo.show(tr("admin.users.msg.activated", user=usuario) if target_status == "activo" else tr("admin.users.msg.deactivated", user=usuario), parent=self)
        except Exception as ex:
            DlgError.show(str(ex), parent=self)
        finally:
            self.refresh()

    def paintEvent(self, e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, QColor(232, 240, 251))
        g.setColorAt(1.0, QColor(214, 230, 248))
        p.fillRect(0, 0, self.width(), self.height(), QBrush(g))
        p.end()

    def _agregar(self):
        if self.role != "administrador":
            DlgError.show(tr("admin.users.err.no_perm"), parent=self)
            return
        dlg = AdminRegisterDialog(self.admin_id, parent=self)
        if dlg.exec_() != QDialog.Accepted or not dlg.data:
            return

        d = dlg.data
        try:
            new_id = db_register_admin(
                d["nombre"],
                d["apellido_paterno"],
                d["apellido_materno"],
                d["usuario"],
                d["contrasena"],
                d["rol"],
                self.admin_id,
            )
            if new_id:
                DlgInfo.show(tr("admin.users.msg.registered", user=d['usuario']), parent=self)
                self.refresh()
            else:
                DlgError.show(tr("admin.users.msg.fail_register"), parent=self)
        except Exception as ex:
            DlgError.show(str(ex), parent=self)

    def _editar(self, admin: dict):
        if self.role != "administrador":
            DlgError.show(tr("admin.users.err.no_perm_edit"), parent=self)
            return

        dlg = AdminEditDialog(admin, parent=self)
        if dlg.exec_() != QDialog.Accepted or not dlg.data:
            return

        d = dlg.data
        try:
            db_update_admin(
                id_admin=d["id_admin"],
                nombre=d["nombre"],
                ap_paterno=d["apellido_paterno"],
                ap_materno=d["apellido_materno"],
                username=d["usuario"],
                rol=d["rol"],
                password=d["contrasena"],
                id_admin_actual=self.admin_id,
            )
            DlgInfo.show(tr("admin.users.msg.updated", user=d['usuario']), parent=self)
        except Exception as ex:
            DlgError.show(str(ex), parent=self)
        finally:
            self.refresh()

    def refresh(self):
        admins = db_get_all_admins()

        self.table.setRowCount(0)

        if not admins:
            self.table.setRowCount(1)
            itm = QTableWidgetItem(tr("admin.users.no_admins"))
            itm.setTextAlignment(Qt.AlignCenter)
            itm.setFlags(itm.flags() & ~Qt.ItemIsSelectable)
            self.table.setItem(0, 0, itm)
            self.table.setSpan(0, 0, 1, 6)
            return

        # Orden: activos primero, luego inactivos
        _ord = {"activo": 0, "inactivo": 1}
        ordered = sorted(admins, key=lambda a: _ord.get(a.get("t_estado", ""), 9))

        active_count = db_count_active_admins()
        self.table.setRowCount(len(ordered))
        self.table.setColumnWidth(0, _dp(52))
        self.table.setColumnWidth(1, _dp(300))
        self.table.setColumnWidth(2, _dp(170))
        self.table.setColumnWidth(3, _dp(150))
        self.table.setColumnWidth(4, _dp(130))
        self.table.setColumnWidth(5, _dp(240))

        for r, admin in enumerate(ordered):
            full_name = "{} {} {}".format(
                admin.get("t_nombre", ""),
                admin.get("t_apellido_paterno", ""),
                admin.get("t_apellido_materno", ""),
            ).strip()
            usuario = admin.get("t_usuario", "") or ""
            rol = (admin.get("t_rol", "") or "").upper()
            estado = (admin.get("t_estado", "activo") or "").lower()
            estado_lbl = estado.upper()

            idx_item = QTableWidgetItem(str(r + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 0, idx_item)

            name_item = QTableWidgetItem(full_name)
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(r, 1, name_item)

            user_item = QTableWidgetItem(f"@{usuario}" if usuario else "")
            user_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, user_item)

            rol_item = QTableWidgetItem(rol)
            rol_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 3, rol_item)

            estado_item = QTableWidgetItem(estado_lbl)
            estado_item.setTextAlignment(Qt.AlignCenter)
            if estado == "activo":
                estado_item.setBackground(QColor("#e8f5e9"))
                estado_item.setForeground(QColor("#1b5e20"))
            else:
                estado_item.setBackground(QColor("#fafafa"))
                estado_item.setForeground(QColor("#000000"))
            estado_item.setFlags(estado_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, 4, estado_item)

            if self.role == "administrador":
                acts = QWidget()
                acts_l = QHBoxLayout(acts)
                acts_l.setContentsMargins(4, 2, 4, 2)
                acts_l.setSpacing(6)

                btn_edit = QPushButton(tr("common.edit"))
                btn_edit.setObjectName("btn_cfg")
                btn_edit.setFixedHeight(_dp(28))
                btn_edit.setCursor(Qt.PointingHandCursor)
                btn_edit.clicked.connect(lambda _, a=admin: self._editar(a))
                acts_l.addWidget(btn_edit)

                btn = QPushButton(tr("admin.users.confirm.activate_btn") if estado == "inactivo" else tr("admin.users.confirm.deactivate_btn"))
                btn.setObjectName("btn_toggle_on" if estado == "inactivo" else "btn_toggle_off")
                btn.setFixedHeight(_dp(28))
                btn.setCursor(Qt.PointingHandCursor)
                btn.setEnabled(
                    not (estado == "activo" and active_count <= 1)
                    and admin.get("ID_admin") != self.admin_id
                )
                target = "activo" if estado == "inactivo" else "inactivo"
                btn.clicked.connect(lambda _, a=admin, t=target: self._set_admin_status(a, t))
                acts_l.addWidget(btn)

                self.table.setCellWidget(r, 5, acts)
            else:
                ro_item = QTableWidgetItem(tr("admin.users.readonly"))
                ro_item.setTextAlignment(Qt.AlignCenter)
                ro_item.setForeground(QColor("#000000"))
                ro_item.setFlags(ro_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, 5, ro_item)