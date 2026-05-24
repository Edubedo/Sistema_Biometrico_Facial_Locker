import os

from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QSize
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


# ── Paleta ────────────────────────────────────────────────────────────────────
BG_TOP       = QColor(18,  45,  95)
BG_BOT       = QColor(24,  60, 120)
HEADER_TOP   = QColor(25,  60, 130)
HEADER_BOT   = QColor(35,  80, 165)
ACCENT_BLUE  = QColor(70, 160, 255)
CARD_BG      = QColor(30,  65, 130)
CARD_BORDER  = QColor(70, 130, 210)
TEXT_PRIMARY = QColor(230, 242, 255)
TEXT_MUTED   = QColor(150, 185, 230)
LOGOUT_BG    = QColor(220,  55,  55)


STYLE = """
QWidget#admin_page  { background: transparent; color: #e6f2ff; }
QFrame#admin_header {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 rgba(18,45,95,1), stop:1 rgba(24,60,120,1));
    border-bottom: 1px solid rgba(255,255,255,0.04);
}

/* ── Botón cerrar sesión ─────────────────────────────────────────────────── */
QPushButton#btn_back {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #ef6b6b, stop:1 #d83b3b);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 8px 12px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 0.5px;
    font-weight: 700;
    min-width: 120px;
}
QPushButton#btn_back:pressed { opacity: 0.95; }

/* ── Badge usuario ───────────────────────────────────────────────────────── */
QLabel#badge_user {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 rgba(70,160,255,0.24), stop:1 rgba(70,160,255,0.18));
    color: #ffffff;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
    font-weight: 800;
}

/* ── Tabs dentro del header ──────────────────────────────────────────────── */
/* Tab inactivo */
QPushButton#tab {
    background: rgba(255,255,255,0.06);
    color: rgba(200,220,255,0.90);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 900;
    letter-spacing: 1px;
}
QPushButton#tab:hover {
    background: rgba(70,160,255,0.22);
    color: #ffffff;
    border-color: rgba(70,160,255,0.45);
}

/* Tab activo */
QPushButton#tab:checked {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 rgba(70,160,255,0.90), stop:1 rgba(35,110,230,0.90));
    color: #ffffff;
    border: 1.5px solid rgba(120,190,255,0.95);
}

/* ── Área de contenido ───────────────────────────────────────────────────── */
QStackedWidget#content_stack {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 rgba(255,255,255,0.03), stop:1 rgba(255,255,255,0.01));
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.03);
    padding: 12px;
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
        # FIX: header más alto para acomodar el logo agrandado (84 → 100px)
        header.setFixedHeight(_dp(100))

        hl = QHBoxLayout(header)
        hl.setContentsMargins(_dp(14), _dp(6), _dp(14), _dp(6))
        hl.setSpacing(_dp(10))

        # Logo — FIX: de 200×70 a 280×90 para que se vea más grande
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        logo_path = os.path.join(project_root, "lockztar.png")
        logo_lbl = QLabel()
        logo_lbl.setFixedSize(_dp(280), _dp(90))
        logo_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        logo_px = QPixmap(logo_path)
        if not logo_px.isNull():
            logo_lbl.setPixmap(
                logo_px.scaled(_dp(280), _dp(90),
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            logo_lbl.setText("LOCKZTAR")
            logo_lbl.setStyleSheet(
                f"color:#e6f2ff; font-size:{_dp(20)}px;"
                f"font-weight:900; font-family:'Segoe UI';"
            )
        hl.addWidget(logo_lbl, 0, Qt.AlignVCenter)

        hl.addSpacing(_dp(10))

        # ── Tabs ──────────────────────────────────────────────────────────────
        tab_fs = _dp(12)
        tab_h  = _dp(62)   # un poco más alto también al subir el header
        tab_w  = _dp(130)

        self.t_lock = QPushButton("")
        self.t_lock.setObjectName("tab")
        self.t_lock.setCheckable(True)
        self.t_lock.setChecked(True)
        self.t_lock.setFixedHeight(tab_h)
        self.t_lock.setMinimumWidth(tab_w)

        self.t_ses = QPushButton("")
        self.t_ses.setObjectName("tab")
        self.t_ses.setCheckable(True)
        self.t_ses.setFixedHeight(tab_h)
        self.t_ses.setMinimumWidth(tab_w)

        self.t_log = QPushButton("")
        self.t_log.setObjectName("tab")
        self.t_log.setCheckable(True)
        self.t_log.setFixedHeight(tab_h)
        self.t_log.setMinimumWidth(tab_w)

        self.t_adm = QPushButton("")
        self.t_adm.setObjectName("tab")
        self.t_adm.setCheckable(True)
        self.t_adm.setFixedHeight(tab_h)
        self.t_adm.setMinimumWidth(tab_w)

        for i, b in enumerate([self.t_lock, self.t_ses, self.t_log, self.t_adm]):
            b.setStyleSheet(
                b.styleSheet() +
                f"font-size:{tab_fs}px; padding:0 {_dp(10)}px;"
            )
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _, x=i: self._tab(x))
            hl.addWidget(b, 0, Qt.AlignVCenter)

        hl.addStretch()

        # Badge usuario
        self.badge = QLabel("")
        self.badge.setObjectName("badge_user")
        self.badge.setStyleSheet(
            self.badge.styleSheet() +
            f"font-size:{_dp(11)}px; padding:{_dp(6)}px {_dp(12)}px;"
        )
        hl.addWidget(self.badge, 0, Qt.AlignVCenter)

        # Logout
        self.logout_btn = QPushButton(tr("admin.logout"))
        self.logout_btn.setObjectName("btn_back")
        self.logout_btn.setFixedHeight(touch_height(56))
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.setFocusPolicy(Qt.NoFocus)
        self.logout_btn.clicked.connect(self.go_back.emit)
        hl.addWidget(self.logout_btn, 0, Qt.AlignVCenter)

        vl.addWidget(header)

        # Línea de acento
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

        # Gradiente de fondo
        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0.0, BG_TOP)
        bg.setColorAt(1.0, BG_BOT)
        p.fillRect(0, 0, W, H, QBrush(bg))

        # Cuadrícula decorativa
        p.setPen(QPen(QColor(80, 140, 220, 22), _dp(1)))
        step = _dp(48)
        for x in range(0, W + step, step):
            p.drawLine(x, 0, x, H)
        for y in range(0, H + step, step):
            p.drawLine(0, y, W, y)

        # Resplandores
        rg = QRadialGradient(W, 0, _dp(320))
        rg.setColorAt(0.0, QColor(70, 160, 255, 28))
        rg.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen); p.setBrush(QBrush(rg))
        p.drawRect(0, 0, W, H)

        rg2 = QRadialGradient(0, H, _dp(200))
        rg2.setColorAt(0.0, QColor(50, 130, 255, 18))
        rg2.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(rg2))
        p.drawRect(0, 0, W, H)

        # Header con gradiente propio — FIX: altura actualizada a 100px
        hh = _dp(100)
        hg = QLinearGradient(0, 0, 0, hh)
        hg.setColorAt(0.0, HEADER_TOP)
        hg.setColorAt(1.0, HEADER_BOT)
        p.setBrush(QBrush(hg))
        p.drawRect(0, 0, W, hh)

        # Línea de acento azul bajo el header
        p.setPen(QPen(ACCENT_BLUE, _dp(2)))
        p.drawLine(0, hh, W, hh)

        p.end()

    # ── Idioma ────────────────────────────────────────────────────────────────
    def set_language(self, lang: str):
        self.logout_btn.setText(tr("admin.logout"))
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
#  Separador horizontal pintado (2 px, color del acento)
# ─────────────────────────────────────────────────────────────────────────────
class _HLinePainted(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(_dp(2))
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, _):
        p = QPainter(self)
        W = self.width()
        grad = QLinearGradient(0, 0, W, 0)
        grad.setColorAt(0.0,  QColor(70, 160, 255, 0))
        grad.setColorAt(0.15, QColor(70, 160, 255, 130))
        grad.setColorAt(0.85, QColor(70, 160, 255, 130))
        grad.setColorAt(1.0,  QColor(70, 160, 255, 0))
        p.fillRect(0, 0, W, 2, QBrush(grad))
        p.end()