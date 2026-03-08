from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,  # ← AGREGADO
    QStackedWidget, QFrame, QApplication, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient

from views.admin.lockersPanel import _AdminLockersPanel
from views.admin.sesionesPanel import _AdminSesionesPanel
from views.admin.usuariosPanel import _AdminUsersPanel
from views.admin.logPanel import _AdminLogPanel
from views.style.widgets.widgets import sep_line 
from views.style.style import STYLE as GLOBAL_STYLE


# ─────────────────────────────────────────────────────────────────────────────
#  SCALE HELPER — same as home.py
# ─────────────────────────────────────────────────────────────────────────────
def _dp(value: float) -> int:
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    return max(1, round(value * dpi / 96))


def _shadow(widget, blur=16, alpha=20, dy=3):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setColor(QColor(21, 101, 192, alpha))
    s.setOffset(0, dy)
    widget.setGraphicsEffect(s)


class AdminPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("admin_page")
        self.setStyleSheet(GLOBAL_STYLE)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # ── Header strip ──────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("admin_header")
        header.setFixedHeight(_dp(64))
        header.setStyleSheet("""
            QFrame#admin_header {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0d2b4e, stop:0.7 #1a3f66, stop:1 #2b4a70);
                border-bottom: 3px solid #4a7db0;
            }
        """)
        
        hl = QHBoxLayout(header)
        hl.setContentsMargins(_dp(24), 0, _dp(24), 0)
        hl.setSpacing(_dp(16))

        # Botón volver/cerrar sesión
        bk = QPushButton("←  CERRAR SESIÓN")
        bk.setObjectName("btn_back")
        bk.setStyleSheet("""
            QPushButton#btn_back {
                background: #1e3a5a;
                color: #ffffff;
                border: 2px solid #7aa9d9;
                border-radius: 30px;
                font-family: 'Montserrat', 'Segoe UI', sans-serif;
                letter-spacing: 2px;
                font-weight: 700;
                text-transform: uppercase;
                padding: 8px 20px;
                font-size: 10px;
            }
            QPushButton#btn_back:hover {
                background: #2b4a70;
                border-color: #a0c0e0;
            }
        """)
        bk.setCursor(Qt.PointingHandCursor)
        bk.clicked.connect(self.go_back.emit)
        hl.addWidget(bk)

        # Título
        tit = QLabel("PANEL DE ADMINISTRACIÓN")
        tit.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: 900;
                font-family: 'Montserrat', 'Segoe UI', sans-serif;
                letter-spacing: 4px;
                text-transform: uppercase;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
                font-size: 16px;
                background: transparent; 
                border: none;    
            }
        """)
        hl.addWidget(tit)

        hl.addStretch()

        # Badge de admin
        self.badge = QLabel("")
        self.badge.setObjectName("badge_blue")
        self.badge.setStyleSheet("""
            QLabel#badge_blue {
                background: #0a1a2f;
                color: #ffffff;
                border: 2px solid #7aa9d9;
                border-radius: 14px;
                padding: 4px 14px;
                font-size: 11px;
                font-family: 'Courier New';
                letter-spacing: 2px;
                font-weight: 700;
            }
        """)
        hl.addWidget(self.badge)

        vl.addWidget(header)

        # ── Tab bar ───────────────────────────────────────────────────────────
        tab_bar = QFrame()
        tab_bar.setObjectName("tab_bar")
        tab_bar.setFixedHeight(_dp(52))
        tab_bar.setStyleSheet("""
            QFrame#tab_bar {
                background: #f0f5ff;
                border-bottom: 2px solid #2b4a70;
            }
        """)
        
        tbl = QHBoxLayout(tab_bar)
        tbl.setContentsMargins(_dp(12), 0, _dp(12), 0)
        tbl.setSpacing(_dp(4))

        tab_font_size = _dp(11)
        tab_padding = f"padding: {_dp(8)}px {_dp(20)}px;"

        self.t_lock = QPushButton("LOCKERS")
        self.t_lock.setObjectName("tab")
        self.t_lock.setCheckable(True)
        self.t_lock.setChecked(True)
        self.t_lock.setStyleSheet("""
            QPushButton#tab {
                background: transparent;
                color: #1e3a5a;
                border: none;
                border-bottom: 3px solid transparent;
                padding: 12px 24px;
                font-size: 13px;
                font-weight: 700;
                font-family: 'Segoe UI', sans-serif;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QPushButton#tab:hover {
                color: #0d2b4e;
                background: rgba(43, 75, 112, 0.1);
                border-bottom-color: #2b4a70;
            }
            QPushButton#tab:checked {
                color: #0d2b4e;
                font-weight: 800;
                border-bottom-color: #1a6ef5;
                background: rgba(26, 110, 245, 0.05);
            }
        """)
        
        self.t_ses = QPushButton("SESIONES")
        self.t_ses.setObjectName("tab")
        self.t_ses.setCheckable(True)
        self.t_ses.setStyleSheet(self.t_lock.styleSheet())
        
        self.t_log = QPushButton("REGISTRO ACCESO")
        self.t_log.setObjectName("tab")
        self.t_log.setCheckable(True)
        self.t_log.setStyleSheet(self.t_lock.styleSheet())
        
        self.t_adm = QPushButton("ADMINISTRADORES")
        self.t_adm.setObjectName("tab")
        self.t_adm.setCheckable(True)
        self.t_adm.setStyleSheet(self.t_lock.styleSheet())

        for i, b in enumerate([self.t_lock, self.t_ses, self.t_log, self.t_adm]):
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, x=i: self._tab(x))
            tbl.addWidget(b)

        tbl.addStretch()
        vl.addWidget(tab_bar)

        # ── Thin accent line under tabs ───────────────────────────────────────
        div = QFrame()
        div.setObjectName("h_divider")
        div.setFixedHeight(_dp(2))
        div.setStyleSheet("""
            QFrame#h_divider {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a6ef5, stop:0.5 #7aa9d9, stop:1 #1a6ef5);
                min-height: 2px;
                max-height: 2px;
            }
        """)
        vl.addWidget(div)

        # ── Sub-panels ────────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.p_lockers = _AdminLockersPanel()
        self.p_sesiones = _AdminSesionesPanel()
        self.p_log = _AdminLogPanel()
        self.p_admins = _AdminUsersPanel()

        for p in [self.p_lockers, self.p_sesiones, self.p_log, self.p_admins]:
            p.layout().setContentsMargins(_dp(24), _dp(24), _dp(24), _dp(24))
            self.stack.addWidget(p)

        vl.addWidget(self.stack, 1)

        _shadow(header, blur=12, alpha=25, dy=2)

    def paintEvent(self, event):
        p = QPainter(self)
        W, H = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0.0, QColor(240, 245, 255))
        g.setColorAt(0.5, QColor(225, 235, 250))
        g.setColorAt(1.0, QColor(210, 225, 245))
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
        user_type = admin_data.get("t_usuario", "").upper()
        self.badge.setText(f"  {user_type}  ")
        self.p_admins.set_current_admin(admin_data)

    def showEvent(self, e):
        super().showEvent(e)
        self._tab(0)