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
    QSizePolicy,
    QApplication,
    QDialog,
    QGridLayout,
    QComboBox,
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient

from db.models.usuarios import (
    db_admin_exists,
    db_count_active_admins,
    db_delete_admin,
    db_get_all_admins,
    db_register_admin,
)
from views.style.adminDialogs import DlgError, DlgInfo, DlgConfirm


def _dp(v):
    s = QApplication.primaryScreen()
    return max(1, round(v * (s.logicalDotsPerInch() if s else 96) / 96))


_C = {
    "activo":   ("#e8f5e9", "#2e7d32", "#c8e6c9", "#1b5e20", "#a5d6a7"),
    "inactivo": ("#fafafa", "#78909c", "#eceff1", "#546e7a", "#b0bec5"),
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
}
QLabel#sub{
    color:#90a4ae;
    font-family:'Segoe UI';
    letter-spacing:2px;
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
    color:#546e7a;
    font-weight:800;
    font-family:'Segoe UI';
}
QLabel#ck  {
    color:#90a4ae;
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
    color:#78909c;
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
    color:#90a4ae;
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
    color:#b0bec5;
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
    color:#546e7a;
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
    color:#90a4ae;
    border:1px solid #cfd8e3;
    border-radius:6px;
    padding:7px 16px;
    font-family:'Segoe UI';
}
QLabel#empty{
    color:#b0bec5;font-family:'Segoe UI';
    letter-spacing:3px;
}
"""


class AdminRegisterDialog(QDialog):
    ROLES = ["empleado", "supervisor", "administrador"]

    def __init__(self, admin_id=None, parent=None):
        super().__init__(parent)
        self.admin_id = admin_id
        self.data = None
        self.setWindowTitle("Registrar Nuevo Administrador")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(_dp(380))
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(_dp(20), _dp(16), _dp(20), _dp(16))
        root.setSpacing(_dp(12))

        ttl = QLabel("👤  REGISTRAR NUEVO ADMIN")
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
        self.e_nombre.setPlaceholderText("Juan")
        self.e_ap = QLineEdit()
        self.e_ap.setPlaceholderText("García")
        self.e_am = QLineEdit()
        self.e_am.setPlaceholderText("López")
        self.e_usuario = QLineEdit()
        self.e_usuario.setPlaceholderText("jgarcia01")
        self.e_pass = QLineEdit()
        self.e_pass.setEchoMode(QLineEdit.Password)
        self.e_pass.setPlaceholderText("••••••••")
        self.e_pass2 = QLineEdit()
        self.e_pass2.setEchoMode(QLineEdit.Password)
        self.e_pass2.setPlaceholderText("••••••••")
        self.c_rol = QComboBox()
        self.c_rol.addItems(self.ROLES)

        add_row("NOMBRE", self.e_nombre, 0)
        add_row("APELLIDO PATERNO", self.e_ap, 1)
        add_row("APELLIDO MATERNO", self.e_am, 2)
        add_row("USUARIO", self.e_usuario, 3)
        add_row("ROL", self.c_rol, 4)
        add_row("CONTRASEÑA", self.e_pass, 5)
        add_row("CONFIRMAR", self.e_pass2, 6)

        root.addLayout(grid)

        # Mensajes de error
        self.msg_error = QLabel("")
        self.msg_error.setObjectName("err")
        self.msg_error.setStyleSheet(f"color:#c62828;font-size:{_dp(8)}px;")
        self.msg_error.setAlignment(Qt.AlignCenter)
        root.addWidget(self.msg_error)

        br = QHBoxLayout()
        br.addStretch()
        bn = QPushButton("CANCELAR")
        bn.setObjectName("dno")
        bn.setStyleSheet(fs)
        bn.setCursor(Qt.PointingHandCursor)
        bn.clicked.connect(self.reject)
        bo = QPushButton("REGISTRAR")
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
            self.msg_error.setText("Nombre, apellido, usuario y contraseña son obligatorios.")
            return
        if len(pw) < 4:
            self.msg_error.setText("La contraseña debe tener al menos 4 caracteres.")
            return
        if pw != pw2:
            self.msg_error.setText("Las contraseñas no coinciden.")
            return
        if db_admin_exists(usuario):
            self.msg_error.setText("Ya existe un admin con ese usuario.")
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
            f"color:{badge_fg};font-size:{_dp(11)}px;font-weight:900;font-family:'Segoe UI';"
        )
        col.addWidget(name_lbl)

        # Usuario y rol
        meta = QLabel(f"@{admin.get('t_usuario', '')}   ·   {admin.get('t_rol', '').upper()}")
        meta.setObjectName("meta")
        meta.setStyleSheet(f"font-size:{_dp(7)}px;")
        col.addWidget(meta)
        lay.addLayout(col)
        lay.addStretch()

        # Badge de estado
        badge_txt = "ACTIVO" if estado == "activo" else "INACTIVO"
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
            bd.setToolTip("Desactivar administrador")
            bd.setFixedSize(_dp(26), _dp(26))
            bd.setCursor(Qt.PointingHandCursor)
            bd.clicked.connect(self._eliminar)
            lay.addWidget(bd)

    def _eliminar(self):
        usuario = self.admin["t_usuario"]
        nombre = self.admin["t_nombre"]

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
            title=f"Desactivar Admin",
            confirm_label="DESACTIVAR",
            danger=True,
            parent=self,
        ):
            return

        try:
            db_delete_admin(usuario, self.admin_id)
            DlgInfo.show(f"Admin '{usuario}' desactivado correctamente.", parent=self)
            if self.on_refresh:
                self.on_refresh()
        except Exception as ex:
            DlgError.show(str(ex), parent=self)


class _AdminUsersPanel(QWidget):
    def __init__(self, admin_id=None):
        super().__init__()
        self.admin_id = admin_id
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
        t = QLabel("GESTIÓN DE ADMINISTRADORES")
        t.setObjectName("ttl")
        t.setStyleSheet(f"font-size:{_dp(12)}px;")
        s = QLabel("PANEL ADMIN · USUARIOS DEL SISTEMA")
        s.setObjectName("sub")
        s.setStyleSheet(f"font-size:{_dp(8)}px;")
        tc.addWidget(t)
        tc.addWidget(s)
        hdr.addLayout(tc)
        hdr.addStretch()

        # Botones
        btn_add = QPushButton("＋  NUEVO ADMIN")
        btn_add.setObjectName("btn_add")
        btn_add.setStyleSheet(f"font-size:{_dp(8)}px;padding:{_dp(5)}px {_dp(14)}px;")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._agregar)
        hdr.addWidget(btn_add)

        btn_ref = QPushButton("↺  ACTUALIZAR")
        btn_ref.setObjectName("btn_ref")
        btn_ref.setStyleSheet(f"font-size:{_dp(8)}px;padding:{_dp(5)}px {_dp(14)}px;")
        btn_ref.setCursor(Qt.PointingHandCursor)
        btn_ref.clicked.connect(self.refresh)
        hdr.addWidget(btn_ref)

        root.addLayout(hdr)
        root.addWidget(self._div())

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.inner = QWidget()
        self.inner.setObjectName("inner")
        self.il = QVBoxLayout(self.inner)
        self.il.setContentsMargins(0, _dp(4), _dp(4), 0)
        self.il.setSpacing(_dp(5))
        self.il.setAlignment(Qt.AlignTop)

        scroll.setWidget(self.inner)
        root.addWidget(scroll, 1)

        self.refresh()

    def set_current_admin(self, admin_data):
        """Método requerido para establecer el administrador actual"""
        self._current_admin = admin_data
        self.admin_id = admin_data.get("ID_admin") if admin_data else None

    def _div(self):
        d = QFrame()
        d.setObjectName("h_div")
        return d

    def paintEvent(self, e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, QColor(232, 240, 251))
        g.setColorAt(1.0, QColor(214, 230, 248))
        p.fillRect(0, 0, self.width(), self.height(), QBrush(g))
        p.end()

    def _agregar(self):
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
                DlgInfo.show(f"Administrador '{d['usuario']}' registrado correctamente.", parent=self)
                self.refresh()
            else:
                DlgError.show("No se pudo registrar. Intenta de nuevo.", parent=self)
        except Exception as ex:
            DlgError.show(str(ex), parent=self)

    def refresh(self):
        # Limpiar layout
        for i in reversed(range(self.il.count())):
            w = self.il.itemAt(i)
            if w and w.widget():
                w.widget().deleteLater()

        admins = db_get_all_admins()

        if not admins:
            e = QLabel("·  SIN ADMINISTRADORES REGISTRADOS  ·")
            e.setObjectName("empty")
            e.setAlignment(Qt.AlignCenter)
            e.setStyleSheet(f"font-size:{_dp(9)}px;")
            e.setContentsMargins(0, _dp(20), 0, _dp(20))
            self.il.addWidget(e)
            return

        # Orden: activos primero, luego inactivos
        _ord = {"activo": 0, "inactivo": 1}
        for i, admin in enumerate(
            sorted(admins, key=lambda a: _ord.get(a.get("t_estado", ""), 9)), 1
        ):
            self.il.addWidget(AdminCard(admin, i, self.admin_id, on_refresh=self.refresh))