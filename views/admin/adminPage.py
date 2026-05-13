import os

from PyQt5.QtCore import Qt, pyqtSignal, QRectF
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QFrame, QApplication
)
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QLinearGradient,
    QRadialGradient, QPixmap, QPainterPath, QPen
)

from views.admin.lockersPanel import _AdminLockersPanel
from views.admin.sesionesPanel import _AdminSesionesPanel
from views.admin.usuariosPanel import _AdminUsersPanel
from views.admin.logPanel import _AdminLogPanel
from views.style.widgets.widgets import lbl, sep_line
from utils.i18n import tr, get_language
from utils.ui_touch import touch_height


def _dp(value: float) -> int:
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    scale = min(dpi / 96, 1.25)
    return max(1, round(value * scale))


# ── Paleta — azules más claros y luminosos ────────────────────────────────────
BG_TOP       = QColor(18,  45,  95)   # azul medio-oscuro (antes muy oscuro)
BG_BOT       = QColor(24,  60, 120)   # azul más saturado
HEADER_TOP   = QColor(25,  60, 130)   # header más claro
HEADER_BOT   = QColor(35,  80, 165)   # bottom del header luminoso
ACCENT_BLUE  = QColor(70, 160, 255)   # acento más brillante
CARD_BG      = QColor(30,  65, 130)
CARD_BORDER  = QColor(70, 130, 210)
TEXT_PRIMARY = QColor(230, 242, 255)
TEXT_MUTED   = QColor(150, 185, 230)

# Color sólido para el botón de cerrar sesión
LOGOUT_BG    = QColor(220,  55,  55)  # rojo sólido — inconfundible para "salir"


STYLE = """
QWidget#admin_page  { background: transparent; color: #e6f2ff; }
QFrame#admin_header {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(18,45,95,1), stop:1 rgba(24,60,120,1));
    border-bottom: 1px solid rgba(255,255,255,0.04);
}

/* ── Botón cerrar sesión — color sólido único ─────────────────────────── */
/* Back button — compact, high-contrast */
QPushButton#btn_back {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ef6b6b, stop:1 #d83b3b);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 12px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 0.5px;
    font-weight: 700;
    min-width: 120px;
}
QPushButton#btn_back:hover { /* transform removed - unsupported by Qt QSS */ }
QPushButton#btn_back:pressed { opacity: 0.95; }

/* ── Badge usuario ───────────────────────────────────────────────────────── */
QLabel#badge_user {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(70,160,255,0.24), stop:1 rgba(70,160,255,0.18));
    color: #ffffff;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
    font-weight: 800;
}

/* ── Barra de tabs ───────────────────────────────────────────────────────── */
QFrame#tab_bar {
    background: transparent;
    border: none;
}

/* Tab inactivo */
QPushButton#tab {
    background: rgba(255,255,255,0.04);
    color: rgba(200,220,255,0.95);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 14px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 800;
    letter-spacing: 1px;
    min-height: 40px;
    min-width: 140px;
    padding: 8px 14px;
}
QPushButton#tab:hover {
    background: rgba(70,160,255,0.18);
    color: #ffffff;
    border-color: rgba(70,160,255,0.40);
}

/* Tab activo */
QPushButton#tab:checked {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(70,160,255,0.85), stop:1 rgba(35,110,230,0.85));
    color: #ffffff;
    border: 1.5px solid rgba(100,180,255,0.95);
    /* box-shadow removed - unsupported by Qt QSS; use QGraphicsDropShadowEffect if needed */
}

/* ── Área de contenido ───────────────────────────────────────────────────── */
QStackedWidget#content_stack {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(255,255,255,0.03), stop:1 rgba(255,255,255,0.01));
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.03);
    padding: 12px;
}

/* Make content area feel like a card */
QFrame#content_stack > QWidget {
    background: transparent;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  AdminPage
# ─────────────────────────────────────────────────────────────────────────────
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
        header.setFixedHeight(_dp(90))

        hl = QHBoxLayout(header)
        hl.setContentsMargins(_dp(16), _dp(8), _dp(16), _dp(8))
        hl.setSpacing(_dp(12))

        # Botón cerrar sesión — color sólido rojo
        self.bk = QPushButton("")
        self.bk.setObjectName("btn_back")
        self.bk.setFixedHeight(_dp(46))
        self.bk.setMinimumWidth(_dp(146))
        self.bk.setStyleSheet(
            self.bk.styleSheet() +
            f"font-size: {_dp(12)}px; padding: 0 {_dp(14)}px;"
        )
        self.bk.setCursor(Qt.PointingHandCursor)
        self.bk.clicked.connect(self.go_back.emit)
        hl.addWidget(self.bk, 0, Qt.AlignVCenter)

        hl.addSpacing(_dp(4))

        # Logo
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        logo_path = os.path.join(project_root, "lockztar.png")
        logo_lbl = QLabel()
        logo_lbl.setFixedSize(_dp(190), _dp(72))
        logo_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        logo_px = QPixmap(logo_path)
        if not logo_px.isNull():
            logo_lbl.setPixmap(
                logo_px.scaled(_dp(180), _dp(66),
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            logo_lbl.setText("LOCKZTAR")
            logo_lbl.setStyleSheet(
                f"color:#e6f2ff; font-size:{_dp(16)}px;"
                f"font-weight:900; font-family:'Segoe UI';"
            )
        hl.addWidget(logo_lbl, 0, Qt.AlignVCenter)

        hl.addStretch()

        # Título centrado
        self.tit = QLabel("")
        self.tit.setStyleSheet(
            f"color: #e6f2ff; font-size: {_dp(14)}px; font-weight: 900;"
            f"font-family: 'Segoe UI'; letter-spacing: 2px; background: transparent;"
        )
        hl.addWidget(self.tit, 0, Qt.AlignVCenter)

        hl.addStretch()

        # Badge usuario
        self.badge = QLabel("")
        self.badge.setObjectName("badge_user")
        self.badge.setStyleSheet(
            self.badge.styleSheet() +
            f"font-size: {_dp(10)}px; padding: {_dp(6)}px {_dp(14)}px;"
        )
        hl.addWidget(self.badge, 0, Qt.AlignVCenter)

        vl.addWidget(header)

        vl.addSpacing(_dp(2))

        # ── Tab bar ───────────────────────────────────────────────────────────
        tab_bar = QFrame()
        tab_bar.setObjectName("tab_bar")
        tab_bar.setFixedHeight(_dp(56))

        tbl = QHBoxLayout(tab_bar)
        tbl.setContentsMargins(_dp(12), _dp(6), _dp(12), _dp(6))
        tbl.setSpacing(_dp(8))

        tab_fs  = _dp(12)
        tab_pad = f"padding: {_dp(8)}px {_dp(14)}px;"

        self.t_lock = QPushButton("")
        self.t_lock.setObjectName("tab")
        self.t_lock.setCheckable(True)
        self.t_lock.setChecked(True)

        self.t_ses = QPushButton("")
        self.t_ses.setObjectName("tab")
        self.t_ses.setCheckable(True)

        self.t_log = QPushButton("")
        self.t_log.setObjectName("tab")
        self.t_log.setCheckable(True)

        self.t_adm = QPushButton("")
        self.t_adm.setObjectName("tab")
        self.t_adm.setCheckable(True)

        for i, b in enumerate([self.t_lock, self.t_ses, self.t_log, self.t_adm]):
            b.setStyleSheet(
                b.styleSheet() +
                f"font-size: {tab_fs}px; {tab_pad}"
            )
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _, x=i: self._tab(x))
            tbl.addWidget(b)

        tbl.addStretch()
        vl.addWidget(tab_bar)

        # Separador fino bajo los tabs
        sep = _HLinePainted()
        vl.addWidget(sep)

        # ── Contenido ─────────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setObjectName("content_stack")

        self.p_lockers  = _AdminLockersPanel()
        self.p_sesiones = _AdminSesionesPanel()
        self.p_log      = _AdminLogPanel()
        self.p_admins   = _AdminUsersPanel()

        for p in [self.p_lockers, self.p_sesiones, self.p_log, self.p_admins]:
            self.stack.addWidget(p)

        vl.addWidget(self.stack, 1)
        self.set_language(get_language())

    # ── Fondo global ──────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        # Gradiente de fondo — azules más claros
        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0.0, BG_TOP)
        bg.setColorAt(1.0, BG_BOT)
        p.fillRect(0, 0, W, H, QBrush(bg))

        # Cuadrícula decorativa más visible
        p.setPen(QPen(QColor(80, 140, 220, 22), _dp(1)))
        step = _dp(48)
        for x in range(0, W + step, step):
            p.drawLine(x, 0, x, H)
        for y in range(0, H + step, step):
            p.drawLine(0, y, W, y)

        # Resplandor esquina superior derecha — más luminoso
        rg = QRadialGradient(W, 0, _dp(320))
        rg.setColorAt(0.0, QColor(70, 160, 255, 28))
        rg.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(rg))
        p.drawRect(0, 0, W, H)

        # Resplandor adicional esquina inferior izquierda
        rg2 = QRadialGradient(0, H, _dp(200))
        rg2.setColorAt(0.0, QColor(50, 130, 255, 18))
        rg2.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(rg2))
        p.drawRect(0, 0, W, H)

        # ── Header con gradiente propio ───────────────────────────────────────
        hh = _dp(90)
        hg = QLinearGradient(0, 0, 0, hh)
        hg.setColorAt(0.0, HEADER_TOP)
        hg.setColorAt(1.0, HEADER_BOT)
        p.setBrush(QBrush(hg))
        p.drawRect(0, 0, W, hh)

        # Línea de acento azul bajo el header — más brillante
        p.setPen(QPen(ACCENT_BLUE, _dp(2)))
        p.drawLine(0, hh, W, hh)

        # ── Fondo de la tab bar ───────────────────────────────────────────────
        tab_y  = hh + _dp(2)
        tab_h  = _dp(56)
        tab_bg = QLinearGradient(0, tab_y, 0, tab_y + tab_h)
        tab_bg.setColorAt(0.0, QColor(22,  50, 105))
        tab_bg.setColorAt(1.0, QColor(18,  42,  88))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(tab_bg))
        p.drawRect(0, tab_y, W, tab_h)

        p.end()

    # ── Idioma ────────────────────────────────────────────────────────────────
    def set_language(self, lang: str):
        self.bk.setText("←  " + tr("admin.logout"))
        self.tit.setText(tr("admin.panel"))
        self.t_lock.setText("🔒  " + tr("admin.tab.lockers"))
        self.t_ses.setText("🧾  "  + tr("admin.tab.sessions"))
        self.t_log.setText("📝  "  + tr("admin.tab.log"))
        self.t_adm.setText("👤  "  + tr("admin.tab.admins"))
        for panel in (self.p_lockers, self.p_sesiones, self.p_log, self.p_admins):
            if hasattr(panel, "set_language"):
                panel.set_language(lang)

    # ── Tab switch ────────────────────────────────────────────────────────────
    def _tab(self, i: int):
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

    # ── Admin data ────────────────────────────────────────────────────────────
    def set_admin(self, admin_data: dict):
        self._admin_data = admin_data
        self.badge.setText(
            "  {}  ".format(admin_data.get("t_usuario", "").upper())
        )
        self.p_admins.set_current_admin(admin_data)
        if hasattr(self.p_lockers, "set_admin_context"):
            self.p_lockers.set_admin_context(admin_data)
        role = (admin_data.get("t_rol", "empleado") or "empleado").lower()
        self.t_adm.setEnabled(True)
        self.t_adm.setToolTip(
            tr("admin.read_only") if role != "administrador"
            else tr("admin.manage_admins")
        )

    def showEvent(self, e):
        super().showEvent(e)
        self._tab(0)


# ─────────────────────────────────────────────────────────────────────────────
#  Separador horizontal pintado (1 px, color del acento)
# ─────────────────────────────────────────────────────────────────────────────
class _HLinePainted(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(_dp(1))
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, _):
        p = QPainter(self)
        W = self.width()
        grad = QLinearGradient(0, 0, W, 0)
        grad.setColorAt(0.0,  QColor(70, 160, 255, 0))
        grad.setColorAt(0.15, QColor(70, 160, 255, 110))
        grad.setColorAt(0.85, QColor(70, 160, 255, 110))
        grad.setColorAt(1.0,  QColor(70, 160, 255, 0))
        p.fillRect(0, 0, W, 1, QBrush(grad))
        p.end()