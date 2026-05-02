from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QFrame, QApplication, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient

from views.admin.lockersPanel import _AdminLockersPanel
from views.admin.sesionesPanel import _AdminSesionesPanel
from views.admin.usuariosPanel import _AdminUsersPanel
from views.admin.logPanel import _AdminLogPanel
from views.style.widgets.widgets import lbl, sep_line
from utils.i18n import tr, get_language


def _dp(value: float) -> int:
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    scale = min(dpi / 96, 1.25)
    return max(1, round(value * scale))


STYLE = """
QWidget#admin_page { background: transparent; color: #1a2a3a; }

QFrame#admin_header {
    background-color: #1565c0;
    border: none;
}
QLabel#brand_icon {
    color: #ffffff;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#brand_name {
    color: #ffffff;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
}
QLabel#page_title {
    color: #ffffff;
    font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
}
QLabel#badge_blue {
    background: rgba(255,255,255,0.15);
    color: #ffffff;
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 10px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
    font-weight: 600;
}
QPushButton#btn_back {
    background: rgba(255,255,255,0.12);
    color: #ffffff;
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 6px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
    font-weight: 600;
}
QPushButton#btn_back:hover   { background: rgba(255,255,255,0.22); }
QPushButton#btn_back:pressed { background: rgba(255,255,255,0.08); }

QFrame#tab_bar {
    background: #ffffff;
    border: none;
    border-bottom: 1px solid #cfd8e3;
}
QPushButton#tab {
    background: transparent;
    color: #90a4ae;
    border: none;
    border-bottom: 3px solid transparent;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 700;
    letter-spacing: 1px;
    border-radius: 0;
}
QPushButton#tab:hover   { color: #1976d2; border-bottom-color: #90c4f0; }
QPushButton#tab:checked { color: #1565c0; border-bottom-color: #1565c0; }

QFrame#h_divider {
    background: #cfd8e3;
    border: none;
    min-height: 1px;
    max-height: 1px;
}
"""


class AdminPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._admin_data = {}
        self.setObjectName("admin_page")
        self.setStyleSheet(STYLE)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("admin_header")
        header.setFixedHeight(_dp(44))          # era 54

        hl = QHBoxLayout(header)
        hl.setContentsMargins(_dp(10), 0, _dp(10), 0)
        hl.setSpacing(_dp(8))

        # Botón cerrar sesión
        self.bk = QPushButton("")
        bk = self.bk
        bk.setObjectName("btn_back")
        bk.setFixedHeight(_dp(28))
        bk.setStyleSheet(
            bk.styleSheet() +
            f"font-size: {_dp(8)}px; padding: 0px {_dp(10)}px;"
        )
        bk.setCursor(Qt.PointingHandCursor)
        bk.clicked.connect(self.go_back.emit)
        hl.addWidget(bk, 0, Qt.AlignVCenter)

        hl.addSpacing(_dp(6))

        # Branding
        bicon = lbl("🔒", "brand_icon", Qt.AlignLeft)
        bicon.setStyleSheet(f"font-size: {_dp(13)}px;")
        bname = lbl("SUPERLOCKER", "brand_name", Qt.AlignLeft)
        bname.setStyleSheet(f"font-size: {_dp(10)}px;")
        hl.addWidget(bicon, 0, Qt.AlignVCenter)
        hl.addWidget(bname, 0, Qt.AlignVCenter)

        hl.addStretch()

        # Título centrado
        self.tit = lbl("", "page_title")
        tit = self.tit
        tit.setStyleSheet(
            f"color: #ffffff; font-size: {_dp(11)}px; font-weight: 800;"
            f"font-family: 'Segoe UI'; letter-spacing: 2px;"
        )
        hl.addWidget(tit, 0, Qt.AlignVCenter)

        hl.addStretch()

        # Badge usuario
        self.badge = lbl("", "badge_blue")
        self.badge.setStyleSheet(
            f"background: rgba(255,255,255,0.15); color: #ffffff;"
            f"border: 1px solid rgba(255,255,255,0.3); border-radius: {_dp(10)}px;"
            f"font-size: {_dp(8)}px; padding: {_dp(3)}px {_dp(10)}px;"
            f"font-family: 'Segoe UI'; letter-spacing: 2px; font-weight: 600;"
        )
        hl.addWidget(self.badge, 0, Qt.AlignVCenter)

        vl.addWidget(header)

        # ── Tab bar ───────────────────────────────────────────────────────────
        # En 800px de ancho con 4 tabs, aumentamos tamaño para mejor visibilidad
        tab_bar = QFrame()
        tab_bar.setObjectName("tab_bar")
        tab_bar.setFixedHeight(_dp(56))         # aumentado de 40

        tbl = QHBoxLayout(tab_bar)
        tbl.setContentsMargins(_dp(4), 0, _dp(4), 0)
        tbl.setSpacing(0)

        tab_font_size = _dp(11)                  # aumentado de 9
        tab_padding   = f"padding: {_dp(14)}px {_dp(18)}px;"  # aumentado de 10px 14px

        self.t_lock = QPushButton("")
        self.t_lock.setObjectName("tab"); self.t_lock.setCheckable(True); self.t_lock.setChecked(True)

        self.t_ses  = QPushButton("")
        self.t_ses.setObjectName("tab");  self.t_ses.setCheckable(True)

        self.t_log  = QPushButton("")
        self.t_log.setObjectName("tab");  self.t_log.setCheckable(True)

        self.t_adm  = QPushButton("")
        self.t_adm.setObjectName("tab");  self.t_adm.setCheckable(True)

        for i, b in enumerate([self.t_lock, self.t_ses, self.t_log, self.t_adm]):
            b.setStyleSheet(b.styleSheet() + f"font-size: {tab_font_size}px; {tab_padding}")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, x=i: self._tab(x))
            tbl.addWidget(b)

        tbl.addStretch()
        vl.addWidget(tab_bar)

        # Línea divisora
        div = QFrame(); div.setObjectName("h_divider")
        vl.addWidget(div)

        # ── Sub-paneles ───────────────────────────────────────────────────────
        self.stack      = QStackedWidget()
        self.p_lockers  = _AdminLockersPanel()
        self.p_sesiones = _AdminSesionesPanel()
        self.p_log      = _AdminLogPanel()
        self.p_admins   = _AdminUsersPanel()

        for p in [self.p_lockers, self.p_sesiones, self.p_log, self.p_admins]:
            self.stack.addWidget(p)

        vl.addWidget(self.stack, 1)
        self.set_language(get_language())

    def set_language(self, _lang: str):
        self.bk.setText(tr("admin.logout"))
        self.tit.setText(tr("admin.panel"))
        self.t_lock.setText("🔒  " + tr("admin.tab.lockers"))
        self.t_ses.setText("🧾  " + tr("admin.tab.sessions"))
        self.t_log.setText("📝  " + tr("admin.tab.log"))
        self.t_adm.setText("👤  " + tr("admin.tab.admins"))
        for panel in (self.p_lockers, self.p_sesiones, self.p_log, self.p_admins):
            if hasattr(panel, "set_language"):
                panel.set_language(_lang)

    def paintEvent(self, event):
        p = QPainter(self)
        W, H = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0.0, QColor(232, 240, 251))
        g.setColorAt(1.0, QColor(214, 230, 248))
        p.fillRect(0, 0, W, H, QBrush(g))
        p.end()

    def _tab(self, i):
        self.stack.setCurrentIndex(i)
        for j, b in enumerate([self.t_lock, self.t_ses, self.t_log, self.t_adm]):
            b.setChecked(j == i)
        refresh_map = {
            0: self.p_lockers.refresh,
            1: self.p_sesiones.refresh,
            2: self.p_log.refresh,
            3: self.p_admins.refresh,
        }
        refresh_map[i]()

    def set_admin(self, admin_data):
        self._admin_data = admin_data
        self.badge.setText("  {}  ".format(admin_data.get("t_usuario", "").upper()))
        self.p_admins.set_current_admin(admin_data)

        # Solo llama set_admin_context si el panel lo implementa
        if hasattr(self.p_lockers, "set_admin_context"):
            self.p_lockers.set_admin_context(admin_data)

        role = (admin_data.get("t_rol", "empleado") or "empleado").lower()
        self.t_adm.setEnabled(True)
        self.t_adm.setToolTip(
            tr("admin.read_only") if role != "administrador" else tr("admin.manage_admins")
        )
    def showEvent(self, e):
        super().showEvent(e)
        self._tab(0)