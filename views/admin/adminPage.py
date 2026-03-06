from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget

from views.admin.lockersPanel import _AdminLockersPanel 
from views.admin.sesionesPanel import _AdminSesionesPanel 
from views.admin.usuariosPanel import _AdminUsersPanel 
from views.admin.logPanel import _AdminLogPanel 
from views.style.widgets.widgets import lbl, sep_line

STYLE = """
QWidget#admin_page { background: #060d1a; color: #c8dff5; }
QLabel#h2 { color: #e2f0ff; font-size: 22px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#badge_blue {
    background: #071833; color: #4d8ec4; border: 1px solid #1a4a8a; border-radius: 14px;
    padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px;
}
QFrame#sep { background: #0f2035; min-height: 1px; max-height: 1px; }
QPushButton#btn_sm {
    background: #0a1628; color: #4d8ec4; border: 1px solid #1a3a5c; border-radius: 8px;
    padding: 8px 18px; font-size: 12px; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_sm:hover { color: #c8dff5; border-color: #4d8ec4; }
QPushButton#tab {
    background: transparent; color: #3a5f84; border: none; border-bottom: 3px solid transparent;
    padding: 12px 24px; font-size: 13px; font-weight: 700; font-family: 'Segoe UI',sans-serif; border-radius: 0;
}
QPushButton#tab:hover { color: #7ca8d0; border-bottom-color: #1a3a5c; }
QPushButton#tab:checked { color: #4d8ec4; border-bottom-color: #1a6ef5; }
"""

class AdminPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("admin_page")
        self.setStyleSheet(STYLE)
        self._admin_data = {}
        vl = QVBoxLayout(self)
        vl.setContentsMargins(48, 36, 48, 36)
        vl.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        bk  = QPushButton("< Cerrar sesion"); bk.setObjectName("btn_sm")
        bk.setCursor(Qt.PointingHandCursor); bk.clicked.connect(self.go_back.emit)
        tit = lbl("Panel de Administracion", "h2")
        self.badge = lbl("", "badge_blue")
        hdr.addWidget(bk); hdr.addSpacing(16)
        hdr.addWidget(tit); hdr.addStretch(); hdr.addWidget(self.badge)
        vl.addLayout(hdr)
        vl.addSpacing(12)
        vl.addWidget(sep_line())
        vl.addSpacing(4)

        # ── Tabs ─────────────────────────────────────────────────────────────
        tab_row = QHBoxLayout(); tab_row.setSpacing(0)
        self.t_lock  = QPushButton("LOCKERS");        self.t_lock.setObjectName("tab");  self.t_lock.setCheckable(True);  self.t_lock.setChecked(True)
        self.t_ses   = QPushButton("SESIONES");       self.t_ses.setObjectName("tab");   self.t_ses.setCheckable(True)
        self.t_log   = QPushButton("REGISTRO ACCESO");self.t_log.setObjectName("tab");   self.t_log.setCheckable(True)
        self.t_adm   = QPushButton("ADMINISTRADORES");self.t_adm.setObjectName("tab");   self.t_adm.setCheckable(True)
        for i, b in enumerate([self.t_lock, self.t_ses, self.t_log, self.t_adm]):
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, x=i: self._tab(x))
            tab_row.addWidget(b)
        tab_row.addStretch()
        vl.addLayout(tab_row)
        vl.addWidget(sep_line())
        vl.addSpacing(16)

        # ── Sub-paneles ───────────────────────────────────────────────────────
        self.stack      = QStackedWidget()
        self.p_lockers  = _AdminLockersPanel()
        self.p_sesiones = _AdminSesionesPanel()
        self.p_log      = _AdminLogPanel()
        self.p_admins   = _AdminUsersPanel()
        for p in [self.p_lockers, self.p_sesiones, self.p_log, self.p_admins]:
            self.stack.addWidget(p)
        vl.addWidget(self.stack, 1)

    def _tab(self, i):
        self.stack.setCurrentIndex(i)
        tabs = [self.t_lock, self.t_ses, self.t_log, self.t_adm]
        for j, b in enumerate(tabs):
            b.setChecked(j == i)
        refresh_map = {
            0: self.p_lockers.refresh,
            1: self.p_sesiones.refresh,
            2: self.p_log.refresh,
            3: self.p_admins.refresh
        }
        refresh_map[i]()

    def set_admin(self, admin_data):
        self._admin_data = admin_data
        self.badge.setText("  {}  ".format(admin_data.get("t_usuario", "").upper()))
        self.p_admins.set_current_admin(admin_data)

    def showEvent(self, e):
        super().showEvent(e)
        self._tab(0)

