"""
admin_dialogs.py
Custom styled dialogs for the admin panel.
Replaces all QMessageBox / QInputDialog native OS dialogs.

Usage:
    from views.admin.admin_dialogs import DlgError, DlgInfo, DlgConfirm, DlgInput, DlgLiberar
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QTextEdit, QLineEdit,
    QApplication,
)
from PyQt5.QtGui import QColor, QFont

from utils.i18n import tr

# ── DPI ───────────────────────────────────────────────────────────────────────
def _dp(v):
    s = QApplication.primaryScreen()
    return max(1, round(v * (s.logicalDotsPerInch() if s else 96) / 96))


# ── Shared stylesheet ─────────────────────────────────────────────────────────
# Tamaños base aumentados para display táctil 7" (800×480)
_STYLE = """
QDialog { background: #f0f6ff; }

QFrame#h_div {
    background: #cfd8e3; border: none;
    min-height: 2px; max-height: 2px;
}

QLabel#dlg_icon_error  { color: #e53935; font-size: 36px; }
QLabel#dlg_icon_info   { color: #1976d2; font-size: 36px; }
QLabel#dlg_icon_warn   { color: #ef6c00; font-size: 36px; }
QLabel#dlg_icon_ask    { color: #1565c0; font-size: 36px; }

QLabel#dlg_title {
    color: #1565c0; font-weight: 900;
    font-family: 'Segoe UI'; letter-spacing: 2px;
}
QLabel#dlg_msg {
    color: #37474f; font-family: 'Segoe UI'; line-height: 1.6;
}
QLabel#dlg_opt_label {
    color: #546e7a; font-family: 'Segoe UI';
    font-weight: 700; letter-spacing: 1px;
}

QLineEdit#dlg_input {
    background: #fff; border: 2px solid #cfd8e3;
    border-radius: 10px; padding: 10px 14px;
    color: #1565c0; font-family: 'Segoe UI';
}
QLineEdit#dlg_input:focus { border-color: #1976d2; }

QTextEdit#dlg_textarea {
    background: #fff; border: 2px solid #cfd8e3;
    border-radius: 10px; padding: 10px 14px;
    color: #37474f; font-family: 'Segoe UI';
}
QTextEdit#dlg_textarea:focus { border-color: #1976d2; }

/* ── Buttons ── */
QPushButton#btn_primary {
    background: #1976d2; color: #fff;
    border: none; border-radius: 12px;
    font-family: 'Segoe UI'; font-weight: 700; letter-spacing: 1px;
}
QPushButton#btn_primary:hover   { background: #1565c0; }
QPushButton#btn_primary:pressed { background: #0d47a1; }

QPushButton#btn_danger {
    background: #e53935; color: #fff;
    border: none; border-radius: 12px;
    font-family: 'Segoe UI'; font-weight: 700; letter-spacing: 1px;
}
QPushButton#btn_danger:hover   { background: #c62828; }
QPushButton#btn_danger:pressed { background: #b71c1c; }

QPushButton#btn_ghost {
    background: transparent; color: #78909c;
    border: 2px solid #cfd8e3; border-radius: 12px;
    font-family: 'Segoe UI'; letter-spacing: 1px;
}
QPushButton#btn_ghost:hover   { color: #546e7a; border-color: #90a4ae; background: #eceff1; }
QPushButton#btn_ghost:pressed { background: #cfd8e3; }
"""

_ICONS = {
    "error": ("✕", "dlg_icon_error"),
    "info":  ("ℹ", "dlg_icon_info"),
    "warn":  ("⚠", "dlg_icon_warn"),
    "ask":   ("?", "dlg_icon_ask"),
}


# ─────────────────────────────────────────────────────────────────────────────
#  BASE DIALOG
# ─────────────────────────────────────────────────────────────────────────────
class _BaseDialog(QDialog):
    def __init__(self, title: str, message: str, kind: str = "info",
                 parent=None, width: int = 460):
        super().__init__(parent)
        self.setStyleSheet(_STYLE)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setMinimumWidth(_dp(width))
        self.setMinimumHeight(_dp(240))
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(_dp(28), _dp(24), _dp(28), _dp(24))
        self._root.setSpacing(_dp(16))

        # Title bar
        bar = QHBoxLayout(); bar.setSpacing(_dp(12))
        icon_char, icon_obj = _ICONS.get(kind, _ICONS["info"])
        ic = QLabel(icon_char); ic.setObjectName(icon_obj)
        ic.setStyleSheet(f"font-size:{_dp(28)}px;")
        bar.addWidget(ic)

        ttl = QLabel(title.upper()); ttl.setObjectName("dlg_title")
        ttl.setStyleSheet(f"font-size:{_dp(16)}px;")
        bar.addWidget(ttl); bar.addStretch()

        # Close X — más grande para el dedo
        bx = QPushButton("✕"); bx.setObjectName("btn_ghost")
        bx.setFixedSize(_dp(44), _dp(44))
        bx.setStyleSheet(
            f"font-size:{_dp(14)}px;"
            f"border-radius:{_dp(22)}px;"
            f"border:2px solid #cfd8e3;"
        )
        bx.setCursor(Qt.PointingHandCursor)
        bx.clicked.connect(self.reject)
        bar.addWidget(bx)
        self._root.addLayout(bar)

        div = QFrame(); div.setObjectName("h_div")
        self._root.addWidget(div)

        # Message
        msg = QLabel(message); msg.setObjectName("dlg_msg")
        msg.setWordWrap(True)
        msg.setStyleSheet(f"font-size:{_dp(14)}px;")
        self._root.addWidget(msg)

    def _btn_row(self):
        row = QHBoxLayout()
        row.setSpacing(_dp(12))
        row.addStretch()
        return row

    def _make_btn(self, text, obj, callback, size=None):
        b = QPushButton(text); b.setObjectName(obj)
        # Botones grandes para el dedo: 64px de alto mínimo
        fs      = _dp(14)
        pad_v   = _dp(0)
        pad_h   = _dp(28)
        min_h   = _dp(64)
        b.setStyleSheet(
            f"font-size:{fs}px;"
            f"padding:{pad_v}px {pad_h}px;"
            f"min-height:{min_h}px;"
        )
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(callback)
        if size:
            b.setMinimumWidth(_dp(size))
        return b

    # Allow dragging the frameless dialog
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(e.globalPos() - self._drag_pos)


# ─────────────────────────────────────────────────────────────────────────────
#  DlgError  —  replaces QMessageBox.warning / critical
# ─────────────────────────────────────────────────────────────────────────────
class DlgError(_BaseDialog):
    def __init__(self, message: str, title: str = "Error", parent=None):
        super().__init__(title, message, kind="error", parent=parent)
        row = self._btn_row()
        row.addWidget(self._make_btn(tr("dlg.accept"), "btn_danger", self.accept, 140))
        self._root.addLayout(row)

    @staticmethod
    def show(message, title=None, parent=None):
        if title is None:
            title = tr("dlg.error")
        DlgError(message, title, parent).exec_()


# ─────────────────────────────────────────────────────────────────────────────
#  DlgInfo  —  replaces QMessageBox.information
# ─────────────────────────────────────────────────────────────────────────────
class DlgInfo(_BaseDialog):
    def __init__(self, message: str, title: str = "Información", parent=None):
        super().__init__(title, message, kind="info", parent=parent)
        row = self._btn_row()
        row.addWidget(self._make_btn(tr("dlg.accept"), "btn_primary", self.accept, 140))
        self._root.addLayout(row)

    @staticmethod
    def show(message, title=None, parent=None):
        if title is None:
            title = tr("dlg.info")
        DlgInfo(message, title, parent).exec_()


# ─────────────────────────────────────────────────────────────────────────────
#  DlgConfirm  —  replaces QMessageBox.question  →  returns bool
# ─────────────────────────────────────────────────────────────────────────────
class DlgConfirm(_BaseDialog):
    def __init__(self, message: str, title: str = "Confirmar",
                 confirm_label: str = "CONFIRMAR", danger: bool = False,
                 parent=None):
        super().__init__(title, message, kind="ask", parent=parent)
        row = self._btn_row()
        row.addWidget(self._make_btn(tr("dlg.cancel"), "btn_ghost",  self.reject, 140))
        obj = "btn_danger" if danger else "btn_primary"
        row.addWidget(self._make_btn(confirm_label,    obj,          self.accept, 160))
        self._root.addLayout(row)

    @staticmethod
    def ask(message, title=None, confirm_label=None,
            danger=False, parent=None) -> bool:
        if title is None:
            title = tr("dlg.confirm")
        if confirm_label is None:
            confirm_label = tr("dlg.confirm_btn")
        return DlgConfirm(message, title, confirm_label, danger, parent).exec_() == QDialog.Accepted


# ─────────────────────────────────────────────────────────────────────────────
#  DlgInput  —  replaces QInputDialog.getText  →  returns (str | None)
# ─────────────────────────────────────────────────────────────────────────────
class DlgInput(_BaseDialog):
    def __init__(self, message: str, title: str = "Ingresar valor",
                 placeholder: str = "", parent=None):
        super().__init__(title, message, kind="info", parent=parent)
        self._inp = QLineEdit(); self._inp.setObjectName("dlg_input")
        self._inp.setPlaceholderText(placeholder)
        self._inp.setMinimumHeight(_dp(60))
        self._inp.setStyleSheet(
            f"font-size:{_dp(15)}px;"
            f"min-height:{_dp(60)}px;"
            f"border-radius:{_dp(10)}px;"
            f"padding:0 {_dp(14)}px;"
        )
        self._inp.returnPressed.connect(self._ok)
        self._root.addWidget(self._inp)

        row = self._btn_row()
        row.addWidget(self._make_btn(tr("dlg.cancel"), "btn_ghost",   self.reject, 140))
        row.addWidget(self._make_btn(tr("dlg.accept"), "btn_primary", self._ok,    140))
        self._root.addLayout(row)

    def _ok(self):
        if self._inp.text().strip():
            self.accept()

    def value(self) -> str:
        return self._inp.text().strip()

    @staticmethod
    def ask(message, title=None, placeholder="", parent=None):
        """Returns the string entered, or None if cancelled."""
        if title is None:
            title = tr("dlg.input")
        d = DlgInput(message, title, placeholder, parent)
        return d.value() if d.exec_() == QDialog.Accepted else None


# ─────────────────────────────────────────────────────────────────────────────
#  DlgLiberar  —  confirm + optional audit reason  →  returns (bool, str)
# ─────────────────────────────────────────────────────────────────────────────
class DlgLiberar(_BaseDialog):
    """
    Confirm dialog for releasing a locker.
    Includes an optional textarea for the admin to enter an audit reason.
    Returns (confirmed: bool, reason: str)
    """

    def __init__(self, locker_num: str, parent=None):
        super().__init__(
            tr("dlg.release_title", n=locker_num),
            tr("dlg.release_msg", n=locker_num),
            kind="warn",
            parent=parent,
            width=480,
        )
        self._reason = ""

        # Optional reason label
        lbl = QLabel(tr("admin.lockers.dialog.remove_reason"))
        lbl.setObjectName("dlg_opt_label")
        lbl.setStyleSheet(f"font-size:{_dp(13)}px;")
        self._root.addWidget(lbl)

        # Textarea más alto para que quepa el dedo
        self._ta = QTextEdit(); self._ta.setObjectName("dlg_textarea")
        self._ta.setPlaceholderText(tr("admin.lockers.dialog.remove_placeholder"))
        self._ta.setMinimumHeight(_dp(90))
        self._ta.setStyleSheet(
            f"font-size:{_dp(14)}px;"
            f"min-height:{_dp(90)}px;"
        )
        self._root.addWidget(self._ta)

        row = self._btn_row()
        row.addWidget(self._make_btn(tr("dlg.cancel"),     "btn_ghost",  self.reject, 140))
        row.addWidget(self._make_btn(tr("dlg.release_btn"), "btn_danger", self._ok,   160))
        self._root.addLayout(row)

    def _ok(self):
        self._reason = self._ta.toPlainText().strip()
        self.accept()

    def reason(self) -> str:
        return self._reason

    @staticmethod
    def ask(locker_num: str, parent=None):
        """Returns (confirmed: bool, reason: str)"""
        d = DlgLiberar(locker_num, parent)
        confirmed = d.exec_() == QDialog.Accepted
        return confirmed, d.reason() if confirmed else ""