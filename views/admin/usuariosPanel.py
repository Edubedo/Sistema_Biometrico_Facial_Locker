from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFrame, QSizePolicy, QApplication,
    QGraphicsDropShadowEffect, QDialog, QComboBox,
    QTableView, QAbstractItemView, QHeaderView, QScroller,
    QScrollArea,
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QFont

from db.models.usuarios import (
    db_admin_exists, db_count_active_admins, db_delete_admin,
    db_get_all_admins, db_register_admin, db_set_admin_estado, db_update_admin,
)
from views.style.adminDialogs import DlgError, DlgInfo, DlgConfirm
from utils.i18n import tr, get_language


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _dp(v: float) -> int:
    s = QApplication.primaryScreen()
    if s:
        scale = s.logicalDotsPerInch() / 96
    else:
        scale = 1.77   # fallback 7" ~170 DPI
    return max(1, round(v * scale))

_TOUCH_H = 56   # FIX: aumentado de 52 → 56 para mejor touch en 7"

def _shadow(w, blur=12, alpha=18, dy=2):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur); s.setColor(QColor(21, 101, 192, alpha)); s.setOffset(0, dy)
    w.setGraphicsEffect(s)

def _divider():
    d = QFrame(); d.setObjectName("h_div"); return d


# ─────────────────────────────────────────────────────────────────────────────
#  Modelo de tabla
# ─────────────────────────────────────────────────────────────────────────────
_COL_HDR_KEYS = [
    "admin.users.col.num",
    "admin.users.col.name",
    "admin.users.col.user",
    "admin.users.col.role",
    "admin.users.col.state",
    "admin.users.col.actions",
]

class AdminTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[dict] = []

    def load(self, rows: list[dict]):
        self.beginResetModel(); self._data = rows; self.endResetModel()

    def row_data(self, row: int) -> dict:
        return self._data[row] if 0 <= row < len(self._data) else {}

    def rowCount(self,    p=QModelIndex()): return len(self._data)
    def columnCount(self, p=QModelIndex()): return len(_COL_HDR_KEYS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return tr(_COL_HDR_KEYS[section])
        return QVariant()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return QVariant()
        row = self._data[index.row()]
        col = index.column()
        estado = (row.get("t_estado", "activo") or "activo").lower()

        if role == Qt.DisplayRole:
            if col == 0: return str(index.row() + 1)
            if col == 1:
                return "{} {} {}".format(
                    row.get("t_nombre", ""),
                    row.get("t_apellido_paterno", ""),
                    row.get("t_apellido_materno", "") or "",
                ).strip()
            if col == 2: return f"@{row.get('t_usuario', '')}"
            if col == 3: return (row.get("t_rol", "") or "").upper()
            if col == 4: return estado.upper()
            if col == 5: return ""

        if role == Qt.ForegroundRole:
            if col == 4:
                return QBrush(QColor("#1b5e20" if estado == "activo" else "#78909c"))

        if role == Qt.BackgroundRole:
            if col == 4:
                return QBrush(QColor("#e8f5e9" if estado == "activo" else "#f5f5f5"))
            if index.row() % 2 == 1:
                return QBrush(QColor("#f4f8ff"))

        if role == Qt.TextAlignmentRole:
            if col in (0, 2, 3, 4): return Qt.AlignCenter
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        if role == Qt.FontRole:
            # FIX: fuente más grande en toda la tabla
            f = QFont("Segoe UI", _dp(13))
            if col == 4: f.setBold(True)
            return f

        return QVariant()


# ─────────────────────────────────────────────────────────────────────────────
#  ToggleBtn
# ─────────────────────────────────────────────────────────────────────────────
class ToggleBtn(QPushButton):
    _ON  = "QPushButton{{background:{bg};color:{fg};border:2px solid {bg};border-radius:{r}px;font-family:'Segoe UI';font-weight:800;font-size:{fs}px;letter-spacing:1px;padding:0 {p}px;}}"
    _OFF = "QPushButton{{background:#f4f8ff;color:{bd};border:2px solid {bd};border-radius:{r}px;font-family:'Segoe UI';font-weight:700;font-size:{fs}px;letter-spacing:1px;padding:0 {p}px;}}QPushButton:pressed{{background:#e3f0ff;}}"

    def __init__(self, text, bg="#1565c0", fg="#ffffff", border="#1565c0", parent=None):
        super().__init__(text, parent)
        self._bg=bg; self._fg=fg; self._bd=border; self._active=False
        self.setFixedHeight(_dp(_TOUCH_H)); self.setMinimumWidth(_dp(80))
        self.setCursor(Qt.PointingHandCursor); self.setFocusPolicy(Qt.NoFocus)
        self._apply()

    def set_active(self, v: bool): self._active = v; self._apply()

    def _apply(self):
        kw = dict(r=_dp(10), fs=_dp(12), p=_dp(18))
        if self._active:
            self.setStyleSheet(self._ON.format(bg=self._bg, fg=self._fg, **kw))
        else:
            self.setStyleSheet(self._OFF.format(bd=self._bd, **kw))


# ─────────────────────────────────────────────────────────────────────────────
#  Estilos globales
# ─────────────────────────────────────────────────────────────────────────────
def _build_style():
    TH    = _dp(_TOUCH_H)
    r10   = _dp(10)
    INP_H = _dp(56)

    return f"""
QWidget#admin_users_panel {{ background: transparent; }}

QLabel#section_title {{
    color: #1565c0; font-weight: 900;
    font-family: 'Segoe UI'; letter-spacing: 3px; font-size: {_dp(14)}px;
}}
QLabel#section_sub {{
    color: #37474f; font-family: 'Segoe UI';
    letter-spacing: 1px; font-size: {_dp(12)}px;
}}
QFrame#h_div {{
    background: #cfd8e3; border: none; min-height: 1px; max-height: 1px;
}}

/* ── Botones principales ── */
QPushButton#btn_add {{
    background: #1565c0; color: #ffffff; border: none;
    border-radius: {r10}px; font-family: 'Segoe UI';
    font-weight: 800; letter-spacing: 2px; font-size: {_dp(12)}px;
    min-height: {TH}px; min-width: {_dp(150)}px; padding: 0 {_dp(20)}px;
}}
QPushButton#btn_add:hover   {{ background: #1976d2; }}
QPushButton#btn_add:pressed {{ background: #0d47a1; }}
QPushButton#btn_add:disabled{{ background: #90a4ae; }}

QPushButton#btn_refresh {{
    background: #ffffff; color: #1565c0;
    border: 2px solid #90c4f0; border-radius: {r10}px;
    font-family: 'Segoe UI'; font-weight: 800;
    letter-spacing: 2px; font-size: {_dp(12)}px;
    min-height: {TH}px; min-width: {_dp(150)}px; padding: 0 {_dp(20)}px;
}}
QPushButton#btn_refresh:hover   {{ background: #e3f0ff; border-color: #1565c0; }}
QPushButton#btn_refresh:pressed {{ background: #bbdefb; }}

/* ── Tabla ── */
QTableView#admin_users_tbl {{
    background: #ffffff; alternate-background-color: #f4f8ff;
    border: 1px solid #cfd8e3; border-radius: {r10}px;
    gridline-color: #e8f0fb; selection-background-color: #bbdefb;
    font-family: 'Segoe UI'; font-size: {_dp(13)}px; color: #000000;
}}
QTableView#admin_users_tbl::item {{
    padding: {_dp(12)}px {_dp(14)}px; border-bottom: 1px solid #f0f4fa;
}}
QTableView#admin_users_tbl::item:selected {{ background: #bbdefb; color: #0d47a1; }}

/* FIX: header más alto y texto más grande */
QHeaderView::section {{
    background: #1565c0; color: #ffffff;
    font-weight: 900; font-family: 'Segoe UI';
    letter-spacing: 2px; font-size: {_dp(14)}px;
    padding: {_dp(14)}px {_dp(16)}px; border: none;
    border-right: 1px solid rgba(255,255,255,0.18);
    min-height: {_dp(56)}px;
}}
QHeaderView::section:last  {{ border-right: none; }}
QHeaderView::section:hover {{ background: #1976d2; }}

/* ── Scrollbars ── */
QScrollBar:vertical   {{ background: #e8f0fb; width: {_dp(8)}px; margin: 0; }}
QScrollBar::handle:vertical   {{ background: #90c4f0; border-radius: {_dp(4)}px; min-height: {_dp(32)}px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: #e8f0fb; height: {_dp(8)}px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: #90c4f0; border-radius: {_dp(4)}px; min-width: {_dp(32)}px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Paginación ── */
QFrame#page_bar {{
    background: #ffffff; border: 1px solid #cfd8e3; border-radius: {r10}px;
}}
QPushButton#btn_page {{
    background: #e3f0ff; color: #1565c0;
    border: 2px solid #90c4f0; border-radius: {_dp(8)}px;
    font-family: 'Segoe UI'; font-size: {_dp(14)}px; font-weight: 900;
    min-width: {_dp(60)}px; min-height: {TH}px; padding: 0 {_dp(8)}px;
}}
QPushButton#btn_page:hover   {{ background: #bbdefb; border-color: #1565c0; }}
QPushButton#btn_page:pressed {{ background: #90c4f0; }}
QPushButton#btn_page:disabled {{ background: #f4f8ff; color: #b0bec5; border-color: #e0e8f0; }}
QLabel#page_lbl {{
    color: #1565c0; font-family: 'Segoe UI';
    font-size: {_dp(13)}px; font-weight: 800; min-width: {_dp(110)}px;
}}
QLabel#count_lbl {{
    color: #546e7a; font-family: 'Segoe UI'; font-size: {_dp(12)}px;
}}

/* ── FIX: Botones de acción dentro de la tabla — más grandes para touch ── */
QPushButton#btn_edit {{
    background: #e3f0ff; color: #1565c0;
    border: 2px solid #90c4f0; border-radius: {_dp(9)}px;
    font-family: 'Segoe UI'; font-weight: 800; font-size: {_dp(12)}px;
    min-height: {_dp(48)}px; min-width: {_dp(90)}px; padding: 0 {_dp(12)}px;
}}
QPushButton#btn_edit:hover   {{ background: #bbdefb; border-color: #1565c0; }}
QPushButton#btn_edit:pressed {{ background: #90c4f0; }}

QPushButton#btn_activate {{
    background: #e8f5e9; color: #1b5e20;
    border: 2px solid #a5d6a7; border-radius: {_dp(9)}px;
    font-family: 'Segoe UI'; font-weight: 800; font-size: {_dp(12)}px;
    min-height: {_dp(48)}px; min-width: {_dp(110)}px; padding: 0 {_dp(12)}px;
}}
QPushButton#btn_activate:hover   {{ background: #c8e6c9; }}
QPushButton#btn_activate:pressed {{ background: #a5d6a7; }}
QPushButton#btn_activate:disabled {{ background: #f5f5f5; color: #b0bec5; border-color: #e0e0e0; }}

QPushButton#btn_deactivate {{
    background: #ffebee; color: #c62828;
    border: 2px solid #ef9a9a; border-radius: {_dp(9)}px;
    font-family: 'Segoe UI'; font-weight: 800; font-size: {_dp(12)}px;
    min-height: {_dp(48)}px; min-width: {_dp(110)}px; padding: 0 {_dp(12)}px;
}}
QPushButton#btn_deactivate:hover   {{ background: #ffcdd2; }}
QPushButton#btn_deactivate:pressed {{ background: #ef9a9a; }}
QPushButton#btn_deactivate:disabled {{ background: #f5f5f5; color: #b0bec5; border-color: #e0e0e0; }}

/* ── Diálogos ── */
QDialog#admin_dlg {{ background: #f0f6ff; }}
QLabel#dlg_title {{
    color: #1565c0; font-weight: 900; font-family: 'Segoe UI';
    letter-spacing: 2px; font-size: {_dp(14)}px;
}}
QLabel#dlg_sub {{
    color: #546e7a; font-family: 'Segoe UI'; font-size: {_dp(11)}px;
}}
QLabel#field_lbl {{
    color: #37474f; font-family: 'Segoe UI';
    font-weight: 700; font-size: {_dp(12)}px; letter-spacing: 1px;
}}
QLineEdit#dlg_inp {{
    background: #ffffff; border: 2px solid #cfd8e3;
    border-radius: {_dp(8)}px; color: #1a237e;
    font-family: 'Segoe UI'; font-size: {_dp(13)}px;
    padding: 0 {_dp(14)}px; min-height: {INP_H}px;
    selection-background-color: #bbdefb;
}}
QLineEdit#dlg_inp:focus  {{ border-color: #1976d2; background: #f4f8ff; }}
QLineEdit#dlg_inp:hover  {{ border-color: #90c4f0; }}
QComboBox#dlg_combo {{
    background: #ffffff; border: 2px solid #cfd8e3;
    border-radius: {_dp(8)}px; color: #1a237e;
    font-family: 'Segoe UI'; font-size: {_dp(13)}px;
    padding: 0 {_dp(14)}px; min-height: {INP_H}px;
}}
QComboBox#dlg_combo:focus {{ border-color: #1976d2; }}
QComboBox#dlg_combo::drop-down {{ border: none; width: {_dp(32)}px; }}
QComboBox QAbstractItemView {{
    background: #ffffff; border: 1px solid #cfd8e3;
    selection-background-color: #e3f0ff; color: #1a237e;
    font-family: 'Segoe UI'; font-size: {_dp(13)}px;
    min-height: {_dp(48)}px;
}}
QLabel#dlg_err {{
    color: #c62828; font-family: 'Segoe UI';
    font-size: {_dp(12)}px; font-weight: 700;
}}
QPushButton#dlg_ok {{
    background: #1565c0; color: #ffffff; border: none;
    border-radius: {_dp(10)}px; font-family: 'Segoe UI';
    font-weight: 800; font-size: {_dp(13)}px;
    min-height: {_dp(58)}px; min-width: {_dp(150)}px; padding: 0 {_dp(24)}px;
}}
QPushButton#dlg_ok:hover   {{ background: #1976d2; }}
QPushButton#dlg_ok:pressed {{ background: #0d47a1; }}
QPushButton#dlg_cancel {{
    background: #ffffff; color: #546e7a;
    border: 2px solid #cfd8e3; border-radius: {_dp(10)}px;
    font-family: 'Segoe UI'; font-weight: 700; font-size: {_dp(13)}px;
    min-height: {_dp(58)}px; min-width: {_dp(130)}px; padding: 0 {_dp(20)}px;
}}
QPushButton#dlg_cancel:hover   {{ background: #e3f0ff; border-color: #90c4f0; }}
QPushButton#dlg_cancel:pressed {{ background: #bbdefb; }}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Formulario base compartido
# ─────────────────────────────────────────────────────────────────────────────
class _BaseAdminDialog(QDialog):
    ROLES = ["empleado", "supervisor", "administrador"]

    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.setObjectName("admin_dlg")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setMinimumWidth(_dp(420))
        self.setMaximumWidth(_dp(560))
        self.setStyleSheet(_build_style())
        self.data = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Cabecera ──────────────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet(f"""
            QFrame {{
                background: #1565c0;
                border-top-left-radius: {_dp(12)}px;
                border-top-right-radius: {_dp(12)}px;
            }}
        """)
        hdr_lay = QVBoxLayout(hdr)
        hdr_lay.setContentsMargins(_dp(20), _dp(18), _dp(20), _dp(18))
        hdr_lay.setSpacing(_dp(4))
        ttl_lbl = QLabel(title)
        ttl_lbl.setStyleSheet(
            f"color:#ffffff;font-weight:900;font-family:'Segoe UI';"
            f"font-size:{_dp(15)}px;letter-spacing:2px;background:transparent;"
        )
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(
            f"color:rgba(255,255,255,0.78);font-family:'Segoe UI';"
            f"font-size:{_dp(11)}px;background:transparent;"
        )
        hdr_lay.addWidget(ttl_lbl)
        hdr_lay.addWidget(sub_lbl)
        root.addWidget(hdr)

        # ── Cuerpo ────────────────────────────────────────────────────────────
        body_bg = QFrame()
        body_bg.setStyleSheet(
            f"QFrame{{background:#f0f6ff;"
            f"border-bottom-left-radius:{_dp(12)}px;"
            f"border-bottom-right-radius:{_dp(12)}px;}}"
        )
        body_outer = QVBoxLayout(body_bg)
        body_outer.setContentsMargins(_dp(20), _dp(18), _dp(20), _dp(22))
        body_outer.setSpacing(_dp(14))

        # FIX: scroll táctil — usar QScrollArea con QScroller correctamente
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{border:none;background:transparent;}"
            f"QScrollBar:vertical{{background:#e8f0fb;width:{_dp(8)}px;margin:0;}}"
            f"QScrollBar::handle:vertical{{background:#90c4f0;border-radius:{_dp(4)}px;min-height:{_dp(32)}px;}}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        # FIX: activar touch events ANTES de grabGesture
        scroll.viewport().setAttribute(Qt.WA_AcceptTouchEvents, True)
        QScroller.grabGesture(scroll.viewport(), QScroller.TouchGesture)
        # También habilitar con mouse para pruebas en escritorio
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        fields_w = QWidget()
        fields_w.setStyleSheet("background:transparent;")
        # FIX: permitir que el widget de campos crezca verticalmente
        fields_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.fields_lay = QVBoxLayout(fields_w)
        self.fields_lay.setContentsMargins(_dp(2), _dp(4), _dp(10), _dp(8))
        self.fields_lay.setSpacing(_dp(14))
        scroll.setWidget(fields_w)
        body_outer.addWidget(scroll, 1)

        # Error
        self.err_lbl = QLabel("")
        self.err_lbl.setObjectName("dlg_err")
        self.err_lbl.setAlignment(Qt.AlignCenter)
        self.err_lbl.setWordWrap(True)
        self.err_lbl.setMinimumHeight(_dp(22))
        body_outer.addWidget(self.err_lbl)

        # Botones
        btn_row = QHBoxLayout()
        btn_row.setSpacing(_dp(12))
        self.btn_cancel = QPushButton(tr("common.cancel"))
        self.btn_cancel.setObjectName("dlg_cancel")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFocusPolicy(Qt.NoFocus)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok = QPushButton(tr("common.confirm"))
        self.btn_ok.setObjectName("dlg_ok")
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.setFocusPolicy(Qt.NoFocus)
        self.btn_ok.clicked.connect(self._save)
        btn_row.addWidget(self.btn_cancel, 1)
        btn_row.addWidget(self.btn_ok, 2)
        body_outer.addLayout(btn_row)

        root.addWidget(body_bg, 1)

    def _add_input(self, label: str, placeholder: str = "",
                   password: bool = False) -> QLineEdit:
        lbl = QLabel(label); lbl.setObjectName("field_lbl")
        inp = QLineEdit()
        inp.setObjectName("dlg_inp")
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(_dp(56))
        if password:
            inp.setEchoMode(QLineEdit.Password)
        self.fields_lay.addWidget(lbl)
        self.fields_lay.addWidget(inp)
        return inp

    def _add_combo(self, label: str, items: list[str]) -> QComboBox:
        lbl = QLabel(label); lbl.setObjectName("field_lbl")
        combo = QComboBox()
        combo.setObjectName("dlg_combo")
        combo.setFixedHeight(_dp(56))
        combo.addItems(items)
        self.fields_lay.addWidget(lbl)
        self.fields_lay.addWidget(combo)
        return combo

    def _set_error(self, msg: str):
        self.err_lbl.setText(msg)

    def _save(self):
        raise NotImplementedError

    def paintEvent(self, _):
        from PyQt5.QtGui import QPainterPath
        from PyQt5.QtCore import QRectF
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), _dp(12), _dp(12))
        p.fillPath(path, QBrush(QColor("#f0f6ff")))
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  Diálogo: Registrar admin
# ─────────────────────────────────────────────────────────────────────────────
class AdminRegisterDialog(_BaseAdminDialog):
    def __init__(self, admin_id=None, parent=None):
        super().__init__(
            title=tr("admin.users.register_title"),
            subtitle=tr("admin.users.register_head"),
            parent=parent,
        )
        self.admin_id = admin_id
        self.btn_ok.setText(tr("common.confirm"))

        self.e_nombre  = self._add_input(tr("admin.users.field.name"),    tr("admin.users.placeholder.first"))
        self.e_ap      = self._add_input(tr("admin.users.field.ap"),       tr("admin.users.placeholder.last"))
        self.e_am      = self._add_input(tr("admin.users.field.am"),       tr("admin.users.placeholder.mother"))
        self.e_usuario = self._add_input(tr("admin.users.field.user"),     tr("admin.users.placeholder.user"))
        self.c_rol     = self._add_combo(tr("admin.users.field.role"),     self.ROLES)
        self.fields_lay.addWidget(_divider())
        self.e_pass    = self._add_input(tr("admin.users.field.pass"),     tr("admin.users.placeholder.pass"),    password=True)
        self.e_pass2   = self._add_input(tr("admin.users.field.confirm"),  tr("admin.users.placeholder.pass"),    password=True)

    def _save(self):
        nombre  = self.e_nombre.text().strip()
        ap      = self.e_ap.text().strip()
        am      = self.e_am.text().strip()
        usuario = self.e_usuario.text().strip()
        rol     = self.c_rol.currentText()
        pw      = self.e_pass.text()
        pw2     = self.e_pass2.text()
        self._set_error("")

        if not all([nombre, ap, usuario, pw]):
            self._set_error(tr("admin.users.err.required")); return
        if len(pw) < 4:
            self._set_error(tr("admin.users.err.pass_min")); return
        if pw != pw2:
            self._set_error(tr("admin.users.err.pass_mismatch")); return
        if db_admin_exists(usuario):
            self._set_error(tr("admin.users.err.exists")); return

        self.data = dict(nombre=nombre, apellido_paterno=ap,
                         apellido_materno=am or None, usuario=usuario,
                         rol=rol, contrasena=pw)
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  Diálogo: Editar admin
# ─────────────────────────────────────────────────────────────────────────────
class AdminEditDialog(_BaseAdminDialog):
    def __init__(self, admin: dict, parent=None):
        super().__init__(
            title=tr("admin.users.edit_title"),
            subtitle=tr("admin.users.edit_head"),
            parent=parent,
        )
        self.admin = admin
        self.btn_ok.setText(tr("common.update"))

        self.e_nombre  = self._add_input(tr("admin.users.field.name"),      tr("admin.users.placeholder.first"))
        self.e_ap      = self._add_input(tr("admin.users.field.ap"),         tr("admin.users.placeholder.last"))
        self.e_am      = self._add_input(tr("admin.users.field.am"),         tr("admin.users.placeholder.mother"))
        self.e_usuario = self._add_input(tr("admin.users.field.user"),       tr("admin.users.placeholder.user"))
        self.c_rol     = self._add_combo(tr("admin.users.field.role"),       self.ROLES)
        self.fields_lay.addWidget(_divider())
        self.e_pass    = self._add_input(tr("admin.users.field.new_pass"),   tr("admin.users.placeholder.new_pass"),    password=True)
        self.e_pass2   = self._add_input(tr("admin.users.field.confirm"),    tr("admin.users.placeholder.confirm_pass"), password=True)

        self.e_nombre.setText(admin.get("t_nombre", ""))
        self.e_ap.setText(admin.get("t_apellido_paterno", ""))
        self.e_am.setText(admin.get("t_apellido_materno", "") or "")
        self.e_usuario.setText(admin.get("t_usuario", ""))
        self.c_rol.setCurrentText((admin.get("t_rol", "empleado") or "empleado").lower())

    def _save(self):
        nombre  = self.e_nombre.text().strip()
        ap      = self.e_ap.text().strip()
        am      = self.e_am.text().strip()
        usuario = self.e_usuario.text().strip()
        rol     = self.c_rol.currentText().strip().lower()
        pw      = self.e_pass.text()
        pw2     = self.e_pass2.text()
        self._set_error("")

        if not all([nombre, ap, usuario, rol]):
            self._set_error(tr("admin.users.err.required_role")); return
        if pw or pw2:
            if len(pw) < 4:
                self._set_error(tr("admin.users.err.pass_min")); return
            if pw != pw2:
                self._set_error(tr("admin.users.err.pass_mismatch")); return

        self.data = dict(id_admin=self.admin.get("ID_admin"),
                         nombre=nombre, apellido_paterno=ap,
                         apellido_materno=am or None, usuario=usuario,
                         rol=rol, contrasena=pw or None)
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  Panel principal
# ─────────────────────────────────────────────────────────────────────────────
class _AdminUsersPanel(QWidget):

    _PAGE_STEPS = [25, 50, 100]
    _PAGE_SIZE  = 25

    def __init__(self, admin_id=None):
        super().__init__()
        self.admin_id        = admin_id
        self.role            = "empleado"
        self._current_admin  = {}
        self._all_rows:  list[dict] = []
        self._estado_filter  = ""
        self._page           = 0
        self._page_size      = self._PAGE_SIZE

        self.setObjectName("admin_users_panel")
        self.setStyleSheet(_build_style())

        root = QVBoxLayout(self)
        m = _dp(12)
        root.setContentsMargins(m, _dp(8), m, _dp(8))
        root.setSpacing(_dp(7))

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(_dp(10))
        col = QVBoxLayout(); col.setSpacing(_dp(2))
        self.title_lbl = QLabel(tr("admin.users.title"))
        self.title_lbl.setObjectName("section_title")
        self.sub_lbl = QLabel(tr("admin.users.subtitle"))
        self.sub_lbl.setObjectName("section_sub")
        col.addWidget(self.title_lbl); col.addWidget(self.sub_lbl)
        hdr.addLayout(col); hdr.addStretch()

        self.btn_add = QPushButton("＋  " + tr("admin.users.add"))
        self.btn_add.setObjectName("btn_add")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setFocusPolicy(Qt.NoFocus)
        self.btn_add.clicked.connect(self._agregar)
        hdr.addWidget(self.btn_add)

        self.btn_ref = QPushButton("↻  " + tr("admin.users.refresh"))
        self.btn_ref.setObjectName("btn_refresh")
        self.btn_ref.setCursor(Qt.PointingHandCursor)
        self.btn_ref.setFocusPolicy(Qt.NoFocus)
        self.btn_ref.clicked.connect(self.refresh)
        hdr.addWidget(self.btn_ref)
        root.addLayout(hdr)
        root.addWidget(_divider())

        # ── FIX: Contadores de usuarios más grandes y visibles ─────────────
        stats_row = QHBoxLayout(); stats_row.setSpacing(_dp(12))
        self._stat_labels = {}
        stat_defs = [
            ("total",    tr("admin.users.total")    if hasattr(self, '_tr_ready') else "TOTAL",    "#1565c0", "#e3f0ff", "#1565c0"),
            ("activo",   tr("admin.users.active")   if hasattr(self, '_tr_ready') else "ACTIVOS",  "#1b5e20", "#e8f5e9", "#2e7d32"),
            ("inactivo", tr("admin.users.inactive") if hasattr(self, '_tr_ready') else "INACTIVOS","#78909c", "#f5f5f5", "#546e7a"),
        ]
        for key, lbl_text, fg, bg, border in stat_defs:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background: {bg};
                    border: 2px solid {border};
                    border-radius: {_dp(10)}px;
                }}
            """)
            _shadow(card, _dp(8), 14, _dp(2))
            card_lay = QHBoxLayout(card)
            card_lay.setContentsMargins(_dp(16), _dp(10), _dp(16), _dp(10))
            card_lay.setSpacing(_dp(10))

            num_lbl = QLabel("0")
            num_lbl.setStyleSheet(
                f"color:{fg};font-family:'Segoe UI';font-weight:900;"
                f"font-size:{_dp(28)}px;background:transparent;border:none;"
            )
            num_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            txt_lbl = QLabel(lbl_text)
            txt_lbl.setStyleSheet(
                f"color:{fg};font-family:'Segoe UI';font-weight:700;"
                f"font-size:{_dp(11)}px;letter-spacing:2px;"
                f"background:transparent;border:none;"
            )
            txt_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            card_lay.addWidget(num_lbl)
            card_lay.addWidget(txt_lbl)
            card_lay.addStretch()
            stats_row.addWidget(card, 1)
            self._stat_labels[key] = num_lbl

        root.addLayout(stats_row)
        root.addWidget(_divider())

        # ── Tabla ─────────────────────────────────────────────────────────────
        self._model = AdminTableModel()
        self.table = QTableView()
        self.table.setObjectName("admin_users_tbl")
        self.table.setModel(self._model)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        # FIX: alto de fila más generoso para que los botones de acción quepan
        self.table.verticalHeader().setDefaultSectionSize(_dp(64))
        self.table.verticalScrollBar().setSingleStep(_dp(64))
        # FIX: touch en la tabla también
        self.table.viewport().setAttribute(Qt.WA_AcceptTouchEvents, True)
        QScroller.grabGesture(self.table.viewport(), QScroller.TouchGesture)
        QScroller.grabGesture(self.table.viewport(), QScroller.LeftMouseButtonGesture)
        hh = self.table.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setMinimumSectionSize(_dp(50))
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setStretchLastSection(False)
        self.table.setSortingEnabled(False)
        root.addWidget(self.table, 1)

        # ── Paginación ────────────────────────────────────────────────────────
        pg_bar = QFrame(); pg_bar.setObjectName("page_bar")
        _shadow(pg_bar, _dp(8), 10, _dp(1))
        pg_lay = QHBoxLayout(pg_bar)
        pg_lay.setContentsMargins(_dp(14), _dp(8), _dp(14), _dp(8))
        pg_lay.setSpacing(_dp(10))

        self.count_lbl = QLabel(""); self.count_lbl.setObjectName("count_lbl")
        pg_lay.addWidget(self.count_lbl, 1)

        self.btn_first = QPushButton("«")
        self.btn_prev  = QPushButton(tr("admin.pag.prev"))
        self.page_lbl  = QLabel("1 / 1")
        self.btn_next  = QPushButton(tr("admin.pag.next"))
        self.btn_last  = QPushButton("»")

        for b, w in ((self.btn_first,_dp(58)),(self.btn_prev,_dp(120)),
                     (self.btn_next,_dp(120)),(self.btn_last,_dp(58))):
            b.setObjectName("btn_page")
            b.setFixedSize(w, _dp(_TOUCH_H))
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            pg_lay.addWidget(b)
            if b is self.btn_prev:
                self.page_lbl.setObjectName("page_lbl")
                self.page_lbl.setAlignment(Qt.AlignCenter)
                pg_lay.addWidget(self.page_lbl)

        self.btn_first.clicked.connect(lambda: self._go_page(0))
        self.btn_prev.clicked.connect(lambda:  self._go_page(self._page - 1))
        self.btn_next.clicked.connect(lambda:  self._go_page(self._page + 1))
        self.btn_last.clicked.connect(lambda:  self._go_page(self._total_pages() - 1))
        root.addWidget(pg_bar)

        self.set_language(get_language())
        self.refresh()

    # ── Fondo ─────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        W, H = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0.0, QColor(232, 240, 251))
        g.setColorAt(1.0, QColor(214, 230, 248))
        p.fillRect(0, 0, W, H, QBrush(g))
        p.end()

    # ── Filtro estado ─────────────────────────────────────────────────────────
    def _apply_estado_filter(self, val: str):
        self._estado_filter = val
        if hasattr(self, "_tbtn_all"):
            self._tbtn_all.set_active(val == "")
        if hasattr(self, "_tbtn_active"):
            self._tbtn_active.set_active(val == "activo")
        if hasattr(self, "_tbtn_inactive"):
            self._tbtn_inactive.set_active(val == "inactivo")
        self._page = 0
        self._render_page()

    # ── Paginación ────────────────────────────────────────────────────────────
    def _filtered_rows(self) -> list[dict]:
        if not self._estado_filter:
            return self._all_rows
        return [r for r in self._all_rows
                if (r.get("t_estado", "activo") or "activo").lower() == self._estado_filter]

    def _total_pages(self) -> int:
        return max(1, (len(self._filtered_rows()) + self._page_size - 1) // self._page_size)

    def _go_page(self, page: int):
        self._page = max(0, min(page, self._total_pages() - 1))
        self._render_page()

    def _render_page(self):
        rows  = self._filtered_rows()
        start = self._page * self._page_size
        end   = start + self._page_size
        chunk = rows[start:end]
        self._model.load(chunk)

        active_count = db_count_active_admins()
        for r, admin in enumerate(chunk):
            if self.role != "administrador":
                continue
            estado = (admin.get("t_estado", "activo") or "activo").lower()
            cell = QWidget()
            cell.setStyleSheet("background: transparent;")
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(_dp(6), _dp(8), _dp(6), _dp(8))
            cl.setSpacing(_dp(8))

            btn_edit = QPushButton(tr("common.edit"))
            btn_edit.setObjectName("btn_edit")
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setFocusPolicy(Qt.NoFocus)
            btn_edit.clicked.connect(lambda _, a=admin: self._editar(a))
            cl.addWidget(btn_edit)

            if estado == "inactivo":
                btn_tog = QPushButton(tr("admin.users.confirm.activate_btn"))
                btn_tog.setObjectName("btn_activate")
            else:
                btn_tog = QPushButton(tr("admin.users.confirm.deactivate_btn"))
                btn_tog.setObjectName("btn_deactivate")

            can_toggle = not (estado == "activo" and active_count <= 1) \
                         and admin.get("ID_admin") != self.admin_id
            btn_tog.setEnabled(can_toggle)
            btn_tog.setCursor(Qt.PointingHandCursor)
            btn_tog.setFocusPolicy(Qt.NoFocus)
            target = "activo" if estado == "inactivo" else "inactivo"
            btn_tog.clicked.connect(lambda _, a=admin, t=target: self._set_admin_status(a, t))
            cl.addWidget(btn_tog)

            self.table.setIndexWidget(self._model.index(r, 5), cell)

        pages = self._total_pages()
        total = len(rows)
        s0 = start + 1 if total else 0
        s1 = min(end, total)
        self.count_lbl.setText(f"{s0}–{s1}  de  {total}")
        self.page_lbl.setText(f"{self._page + 1} / {pages}")
        self.btn_first.setEnabled(self._page > 0)
        self.btn_prev.setEnabled(self._page > 0)
        self.btn_next.setEnabled(self._page < pages - 1)
        self.btn_last.setEnabled(self._page < pages - 1)

    # ── Datos ─────────────────────────────────────────────────────────────────
    def refresh(self):
        admins = db_get_all_admins()
        _ord = {"activo": 0, "inactivo": 1}
        self._all_rows = sorted(
            admins,
            key=lambda a: (
                _ord.get((a.get("t_estado", "") or "").lower(), 9),
                (a.get("t_apellido_paterno", "") or "").lower(),
                (a.get("t_apellido_materno", "") or "").lower(),
                (a.get("t_nombre", "") or "").lower(),
            ),
        )
        # FIX: actualizar contadores
        total    = len(self._all_rows)
        activos  = sum(1 for a in self._all_rows if (a.get("t_estado","activo") or "activo").lower() == "activo")
        inactivos = total - activos
        if hasattr(self, "_stat_labels"):
            self._stat_labels["total"].setText(str(total))
            self._stat_labels["activo"].setText(str(activos))
            self._stat_labels["inactivo"].setText(str(inactivos))

        self._page = 0
        self._render_page()

    # ── Idioma ────────────────────────────────────────────────────────────────
    def set_language(self, _lang: str):
        self.title_lbl.setText(tr("admin.users.title"))
        self.sub_lbl.setText(tr("admin.users.subtitle"))
        self.btn_add.setText("＋  " + tr("admin.users.add"))
        self.btn_ref.setText("↻  " + tr("admin.users.refresh"))
        self.btn_prev.setText(tr("admin.pag.prev"))
        self.btn_next.setText(tr("admin.pag.next"))
        self._model.layoutChanged.emit()

    def set_current_admin(self, admin_data: dict):
        self._current_admin = admin_data or {}
        self.admin_id = self._current_admin.get("ID_admin")
        self.role = (self._current_admin.get("t_rol", "empleado") or "empleado").lower()
        can = self.role == "administrador"
        self.btn_add.setEnabled(can)
        self.btn_add.setToolTip(
            tr("admin.users.role_hint") if not can else tr("admin.users.role_register")
        )
        self.refresh()

    # ── Acciones ──────────────────────────────────────────────────────────────
    def _agregar(self):
        if self.role != "administrador":
            DlgError.show(tr("admin.users.err.no_perm"), parent=self); return
        dlg = AdminRegisterDialog(self.admin_id, parent=self)
        if dlg.exec_() != QDialog.Accepted or not dlg.data: return
        d = dlg.data
        try:
            new_id = db_register_admin(
                d["nombre"], d["apellido_paterno"], d["apellido_materno"],
                d["usuario"], d["contrasena"], d["rol"], self.admin_id,
            )
            if new_id:
                DlgInfo.show(tr("admin.users.msg.registered", user=d["usuario"]), parent=self)
                self.refresh()
            else:
                DlgError.show(tr("admin.users.msg.fail_register"), parent=self)
        except Exception as ex:
            DlgError.show(str(ex), parent=self)

    def _editar(self, admin: dict):
        if self.role != "administrador":
            DlgError.show(tr("admin.users.err.no_perm_edit"), parent=self); return
        dlg = AdminEditDialog(admin, parent=self)
        if dlg.exec_() != QDialog.Accepted or not dlg.data: return
        d = dlg.data
        try:
            db_update_admin(
                id_admin=d["id_admin"], nombre=d["nombre"],
                ap_paterno=d["apellido_paterno"], ap_materno=d["apellido_materno"],
                username=d["usuario"], rol=d["rol"],
                password=d["contrasena"], id_admin_actual=self.admin_id,
            )
            DlgInfo.show(tr("admin.users.msg.updated", user=d["usuario"]), parent=self)
        except Exception as ex:
            DlgError.show(str(ex), parent=self)
        finally:
            self.refresh()

    def _set_admin_status(self, admin: dict, target: str):
        if self.role != "administrador":
            DlgError.show(tr("admin.users.err.no_perm_mod"), parent=self); return
        usuario = admin.get("t_usuario", "")
        nombre = "{} {} {}".format(
            admin.get("t_nombre", ""), admin.get("t_apellido_paterno", ""),
            admin.get("t_apellido_materno", ""),
        ).strip()

        if target == "inactivo":
            if admin.get("ID_admin") == self.admin_id:
                DlgError.show(tr("admin.users.err.self_delete"), parent=self); return
            if db_count_active_admins() <= 1:
                DlgError.show(tr("admin.users.err.need_one"), parent=self); return

        accion = tr("admin.users.confirm.activate_btn") if target == "activo" \
                 else tr("admin.users.confirm.deactivate_btn")
        if not DlgConfirm.ask(
            tr("admin.users.confirm.deactivate", name=nombre, user=usuario),
            title=tr("admin.users.confirm.activate_title") if target == "activo"
                  else tr("admin.users.confirm.deactivate_title"),
            confirm_label=accion,
            danger=(target == "inactivo"),
            parent=self,
        ):
            return
        try:
            db_set_admin_estado(usuario, target, self.admin_id)
            msg = tr("admin.users.msg.activated", user=usuario) if target == "activo" \
                  else tr("admin.users.msg.deactivated", user=usuario)
            DlgInfo.show(msg, parent=self)
        except Exception as ex:
            DlgError.show(str(ex), parent=self)
        finally:
            self.refresh()