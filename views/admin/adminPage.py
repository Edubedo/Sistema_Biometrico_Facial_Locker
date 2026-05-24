import os

from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QSize, QRect, QPropertyAnimation, QEasingCurve, pyqtProperty, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QFrame, QApplication, QGraphicsOpacityEffect
)
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QLinearGradient,
    QRadialGradient, QPixmap, QPainterPath, QPen, QFont, QFontMetrics
)

from views.admin.lockersPanel import _AdminLockersPanel
from views.admin.sesionesPanel import _AdminSesionesPanel
from views.admin.usuariosPanel import _AdminUsersPanel
from views.admin.logPanel import _AdminLogPanel
from views.style.widgets.widgets import lbl, sep_line
from utils.i18n import tr, get_language
from utils.ui_touch import touch_height


def _dp(value: float) -> int:
    """Escala para display de 7 pulgadas (~170 DPI, resolución típica 1024×600)."""
    screen = QApplication.primaryScreen()
    if screen:
        scale = screen.logicalDotsPerInch() / 96
    else:
        scale = 1.77
    return max(1, round(value * scale))


# ── Paleta ────────────────────────────────────────────────────────────────────
BG_TOP       = QColor(18,  45,  95)
BG_BOT       = QColor(24,  60, 120)
HEADER_TOP   = QColor(12,  32,  72)
HEADER_BOT   = QColor(18,  48, 100)
ACCENT_BLUE  = QColor(70, 160, 255)
CARD_BG      = QColor(30,  65, 130)
CARD_BORDER  = QColor(70, 130, 210)
TEXT_PRIMARY = QColor(230, 242, 255)
TEXT_MUTED   = QColor(150, 185, 230)
LOGOUT_BG    = QColor(220,  55,  55)

# ── Configuración header ──────────────────────────────────────────────────────
HEADER_H = 80   # píxeles lógicos — adaptado para touch de 7"

STYLE = """
QWidget#admin_page  { background: transparent; color: #e6f2ff; }

/* ── Header ────────────────────────────────── */
QFrame#admin_header {
    background: transparent;
    border: none;
}

/* ── Logout btn ────────────────────────────── */
QPushButton#btn_back {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #e85555, stop:1 #c62828);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 0 14px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
    font-weight: 700;
}
QPushButton#btn_back:pressed {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #c62828, stop:1 #b71c1c);
}

/* ── Badge usuario ─────────────────────────── */
QLabel#badge_user {
    background: rgba(70,160,255,0.15);
    color: #90caf9;
    border: 1px solid rgba(70,160,255,0.30);
    border-radius: 10px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
    font-weight: 700;
}

/* ── Tabs ──────────────────────────────────── */
QPushButton#tab {
    background: transparent;
    color: rgba(180,210,255,0.70);
    border: none;
    border-radius: 0px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 700;
    letter-spacing: 0.8px;
}
QPushButton#tab:hover {
    color: #ffffff;
    background: rgba(70,160,255,0.10);
    border-radius: 6px;
}
QPushButton#tab:checked {
    color: #ffffff;
    background: transparent;
    border-radius: 0px;
}

/* ── Stack ─────────────────────────────────── */
QStackedWidget#content_stack {
    background: transparent;
    border: none;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  _TabButton — botón con indicador inferior animado
# ─────────────────────────────────────────────────────────────────────────────
class _TabButton(QPushButton):
    """Tab con línea indicadora inferior que se pinta sobre el QPushButton."""

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self._icon  = icon
        self._label = label
        self.setObjectName("tab")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self._indicator = 0.0   # 0.0 → 1.0 (animación manual en paintEvent)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.isChecked():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        bar_h = _dp(3)
        bar_w = max(_dp(28), W - _dp(20))
        x     = (W - bar_w) // 2
        y     = H - bar_h
        grad  = QLinearGradient(x, 0, x + bar_w, 0)
        grad.setColorAt(0.0, QColor(70, 160, 255, 0))
        grad.setColorAt(0.3, QColor(100, 180, 255, 255))
        grad.setColorAt(0.7, QColor(100, 180, 255, 255))
        grad.setColorAt(1.0, QColor(70, 160, 255, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(x, y, bar_w, bar_h, _dp(2), _dp(2))
        p.end()

    def setText_composed(self, icon: str, text: str):
        self._icon  = icon
        self._label = text
        self.setText(f"{icon}  {text}")


# ─────────────────────────────────────────────────────────────────────────────
#  WelcomeToast — notificación de bienvenida mejorada
# ─────────────────────────────────────────────────────────────────────────────
_DISPLAY_MS   = 4200
_SLIDE_IN_MS  = 480
_SLIDE_OUT_MS = 360


class _ProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(_dp(3))
        self._progress = 1.0

    def get_progress(self): return self._progress
    def set_progress(self, v):
        self._progress = max(0.0, min(1.0, v)); self.update()
    progress = pyqtProperty(float, get_progress, set_progress)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 25)))
        p.drawRoundedRect(0, 0, W, H, _dp(2), _dp(2))
        fill_w = int(W * self._progress)
        if fill_w > 0:
            grad = QLinearGradient(0, 0, W, 0)
            grad.setColorAt(0.0, QColor(100, 200, 255))
            grad.setColorAt(1.0, QColor(60, 130, 255))
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(0, 0, fill_w, H, _dp(2), _dp(2))
        p.end()


class _AvatarCircle(QWidget):
    def __init__(self, initials: str, size: int, parent=None):
        super().__init__(parent)
        self._initials = initials[:2].upper()
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W = self.width()
        # Outer glow
        glow = QRadialGradient(W/2, W/2, W/2)
        glow.setColorAt(0.6, QColor(70, 160, 255, 0))
        glow.setColorAt(1.0, QColor(70, 160, 255, 40))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(-_dp(4), -_dp(4), W + _dp(8), W + _dp(8))
        # Circle
        grad = QLinearGradient(0, 0, W, W)
        grad.setColorAt(0.0, QColor(40, 110, 230))
        grad.setColorAt(1.0, QColor(70, 170, 255))
        p.setBrush(QBrush(grad))
        p.drawEllipse(_dp(2), _dp(2), W - _dp(4), W - _dp(4))
        # Initials
        font = QFont("Segoe UI", _dp(14)); font.setWeight(QFont.Black)
        p.setFont(font)
        p.setPen(QPen(QColor(255, 255, 255, 240)))
        p.drawText(0, 0, W, W, Qt.AlignCenter, self._initials)
        p.end()


class _ToastWidget(QWidget):
    """
    Notificación de bienvenida: aparece desde arriba (slide-down),
    centrada horizontalmente, con estética dark-glass premium.
    """

    def __init__(self, nombre_completo: str, rol: str, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)

        W = _dp(460); H = _dp(96)
        self.setFixedSize(W, H)

        parts    = nombre_completo.strip().split()
        initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else (parts[0][1] if len(parts[0]) > 1 else 'X'))).upper()

        # ── Layout ────────────────────────────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        card_widget = QWidget(self)
        card_widget.setFixedSize(W, H)

        hl = QHBoxLayout(card_widget)
        hl.setContentsMargins(_dp(18), _dp(14), _dp(20), _dp(18))
        hl.setSpacing(_dp(16))

        hl.addWidget(_AvatarCircle(initials, _dp(52)), 0, Qt.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(_dp(2))
        text_col.setContentsMargins(0, 0, 0, 0)

        tag = QLabel("PANEL ADMINISTRADOR")
        tag.setStyleSheet(
            f"color: rgba(100,180,255,0.80); font-family:'Segoe UI'; "
            f"font-weight:800; font-size:{_dp(8)}px; letter-spacing:3px; background:transparent;"
        )

        name_label = QLabel(f"Bienvenid@, <b style='color:#ffffff;'>{nombre_completo}</b>")
        name_label.setTextFormat(Qt.RichText)
        name_label.setStyleSheet(
            f"color: rgba(210,235,255,0.95); font-family:'Segoe UI'; "
            f"font-size:{_dp(13)}px; background:transparent;"
        )

        sub = QLabel(f"✦  {rol.capitalize()} · Sesión activa")
        sub.setStyleSheet(
            f"color: rgba(140,185,230,0.80); font-family:'Segoe UI'; "
            f"font-size:{_dp(10)}px; background:transparent;"
        )

        text_col.addWidget(tag)
        text_col.addWidget(name_label)
        text_col.addWidget(sub)
        hl.addLayout(text_col, 1)

        check_lbl = QLabel("✓")
        check_lbl.setStyleSheet(
            f"color: #4caf50; font-family:'Segoe UI'; font-weight:900; "
            f"font-size:{_dp(22)}px; background:transparent;"
        )
        hl.addWidget(check_lbl, 0, Qt.AlignVCenter)

        # Progress bar en la parte inferior
        self._bar = _ProgressBar(self)
        self._bar.setGeometry(0, H - _dp(3), W, _dp(3))

        # ── Posición inicial (FUERA DE PANTALLA POR ARRIBA) ───────────────────
        self._place()
        self.setGeometry(QRect(self._x, self._y_hidden(), W, H))

        # ── Animaciones ───────────────────────────────────────────────────────
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setEasingCurve(QEasingCurve.OutBack)
        self._anim.setDuration(_SLIDE_IN_MS)
        self._anim.finished.connect(self._on_in_done)

        self._bar_anim = QPropertyAnimation(self._bar, b"progress")
        self._bar_anim.setStartValue(1.0)
        self._bar_anim.setEndValue(0.0)
        self._bar_anim.setDuration(_DISPLAY_MS)
        self._bar_anim.finished.connect(self._slide_out)

        self._out_anim = QPropertyAnimation(self, b"geometry")
        self._out_anim.setEasingCurve(QEasingCurve.InCubic)
        self._out_anim.setDuration(_SLIDE_OUT_MS)
        self._out_anim.finished.connect(self.deleteLater)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _place(self):
        pw = self.parent().width()  if self.parent() else 1024
        ph = self.parent().height() if self.parent() else 600
        self._x          = (pw - self.width()) // 2
        # Aparece justo debajo del header
        self._y_visible_ = _dp(HEADER_H) + _dp(12)
        self._y_hidden_  = -self.height() - _dp(10)

    def _y_visible(self): return self._y_visible_
    def _y_hidden(self):  return self._y_hidden_

    def start(self):
        self.show(); self.raise_()
        self._anim.setStartValue(QRect(self._x, self._y_hidden(),  self.width(), self.height()))
        self._anim.setEndValue  (QRect(self._x, self._y_visible(), self.width(), self.height()))
        self._anim.start()

    def _on_in_done(self):  self._bar_anim.start()
    def _slide_out(self):
        self._out_anim.setStartValue(QRect(self._x, self._y_visible(), self.width(), self.height()))
        self._out_anim.setEndValue  (QRect(self._x, self._y_hidden(),  self.width(), self.height()))
        self._out_anim.start()

    # ── Pintura del toast ─────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        # Sombra difusa
        for i in range(6, 0, -1):
            alpha = int(60 / i)
            shadow = QPainterPath()
            shadow.addRoundedRect(
                _dp(i), _dp(i + 2),
                W - _dp(i * 2), H - _dp(i),
                _dp(16), _dp(16)
            )
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(5, 15, 40, alpha)))
            p.drawPath(shadow)

        # Fondo principal (dark glass)
        card = QPainterPath()
        card.addRoundedRect(0, 0, W - _dp(3), H - _dp(5), _dp(16), _dp(16))
        bg_grad = QLinearGradient(0, 0, 0, H)
        bg_grad.setColorAt(0.0, QColor(20,  50, 105, 242))
        bg_grad.setColorAt(1.0, QColor(14,  36,  80, 242))
        p.setBrush(QBrush(bg_grad))
        p.drawPath(card)

        # Borde luminoso superior
        top_line = QPainterPath()
        top_line.addRoundedRect(0, 0, W - _dp(3), _dp(1), _dp(1), _dp(1))
        tg = QLinearGradient(0, 0, W, 0)
        tg.setColorAt(0.0, QColor(70, 160, 255, 0))
        tg.setColorAt(0.3, QColor(70, 160, 255, 160))
        tg.setColorAt(0.7, QColor(70, 160, 255, 160))
        tg.setColorAt(1.0, QColor(70, 160, 255, 0))
        p.setBrush(QBrush(tg))
        p.drawPath(top_line)

        # Borde exterior sutil
        border = QPainterPath()
        border.addRoundedRect(0.5, 0.5, W - _dp(3) - 1, H - _dp(5) - 1, _dp(16), _dp(16))
        p.setPen(QPen(QColor(70, 140, 255, 55), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(border)

        # Acento lateral izquierdo
        accent = QPainterPath()
        accent.addRoundedRect(0, _dp(12), _dp(4), H - _dp(22), _dp(2), _dp(2))
        ag = QLinearGradient(0, _dp(12), 0, H - _dp(10))
        ag.setColorAt(0.0, QColor(100, 200, 255, 0))
        ag.setColorAt(0.5, QColor(100, 200, 255, 220))
        ag.setColorAt(1.0, QColor(100, 200, 255, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(ag))
        p.drawPath(accent)

        p.end()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._bar.setGeometry(0, self.height() - _dp(3), self.width(), _dp(3))


class WelcomeToast:
    @staticmethod
    def show(parent: QWidget, nombre_completo: str, rol: str = "Empleado"):
        toast = _ToastWidget(nombre_completo, rol, parent)
        toast.start()


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
        header.setFixedHeight(_dp(HEADER_H))

        hl = QHBoxLayout(header)
        hl.setContentsMargins(_dp(16), 0, _dp(16), 0)
        hl.setSpacing(0)

        # Logo
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        logo_path    = os.path.join(project_root, "lockztar.png")
        logo_lbl     = QLabel()
        logo_lbl.setFixedSize(_dp(200), _dp(HEADER_H))
        logo_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        logo_px = QPixmap(logo_path)
        if not logo_px.isNull():
            logo_lbl.setPixmap(logo_px.scaled(_dp(200), _dp(HEADER_H - 20), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_lbl.setText("LOCKZTAR")
            logo_lbl.setStyleSheet(
                f"color:#e6f2ff;font-size:{_dp(18)}px;font-weight:900;font-family:'Segoe UI';"
            )
        hl.addWidget(logo_lbl, 0, Qt.AlignVCenter)

        # Divisor vertical logo / tabs
        hl.addWidget(_VLine(), 0, Qt.AlignVCenter)
        hl.addSpacing(_dp(8))

        # ── Tabs (tamaño uniforme, centrados verticalmente) ───────────────────
        tab_h  = _dp(HEADER_H)          # ocupa todo el alto del header
        tab_fs = _dp(13)                # 10 → 13 (legible para touch)

        self.t_lock = _TabButton("🔒", "")
        self.t_ses  = _TabButton("🧾", "")
        self.t_log  = _TabButton("📝", "")
        self.t_adm  = _TabButton("👤", "")
        self.t_lock.setChecked(True)

        for i, b in enumerate([self.t_lock, self.t_ses, self.t_log, self.t_adm]):
            b.setFixedHeight(tab_h)
            b.setMinimumWidth(_dp(110))   # 90 → 110 (más área táctil)
            b.setMaximumWidth(_dp(160))   # 130 → 160
            b.setStyleSheet(
                b.styleSheet() +
                f"font-size:{tab_fs}px; padding:0 {_dp(10)}px;"
            )
            b.clicked.connect(lambda _, x=i: self._tab(x))
            hl.addWidget(b, 0, Qt.AlignVCenter)

        hl.addStretch(1)

        # Divisor vertical tabs / right area
        hl.addWidget(_VLine(), 0, Qt.AlignVCenter)
        hl.addSpacing(_dp(12))

        # Badge usuario
        self.badge = QLabel("")
        self.badge.setObjectName("badge_user")
        self.badge.setFixedHeight(_dp(40))   # 28 → 40
        self.badge.setStyleSheet(
            self.badge.styleSheet() +
            f"font-size:{_dp(12)}px; padding:0 {_dp(14)}px;"   # 9 → 12
        )
        hl.addWidget(self.badge, 0, Qt.AlignVCenter)

        hl.addSpacing(_dp(10))

        # Botón salir
        self.logout_btn = QPushButton(tr("admin.logout"))
        self.logout_btn.setObjectName("btn_back")
        self.logout_btn.setFixedHeight(_dp(48))    # 34 → 48 (mínimo táctil WCAG)
        self.logout_btn.setMinimumWidth(_dp(110))  # 90 → 110
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.setFocusPolicy(Qt.NoFocus)
        self.logout_btn.setStyleSheet(
            self.logout_btn.styleSheet() +
            f"font-size:{_dp(13)}px;"              # 10 → 13
        )
        self.logout_btn.clicked.connect(self.go_back.emit)
        hl.addWidget(self.logout_btn, 0, Qt.AlignVCenter)

        vl.addWidget(header)
        vl.addWidget(_HLinePainted())

        # ── Stack ─────────────────────────────────────────────────────────────
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

    # ── Fondo pintado ─────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        # Gradiente de fondo
        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0.0, BG_TOP); bg.setColorAt(1.0, BG_BOT)
        p.fillRect(0, 0, W, H, QBrush(bg))

        # Grid sutil
        p.setPen(QPen(QColor(80, 140, 220, 14), _dp(1)))
        step = _dp(52)
        for x in range(0, W + step, step): p.drawLine(x, 0, x, H)
        for y in range(0, H + step, step): p.drawLine(0, y, W, y)

        # Luces ambientales
        rg = QRadialGradient(W * 0.85, 0, _dp(280))
        rg.setColorAt(0.0, QColor(70, 160, 255, 22)); rg.setColorAt(1.0, QColor(0,0,0,0))
        p.setPen(Qt.NoPen); p.setBrush(QBrush(rg)); p.drawRect(0, 0, W, H)

        rg2 = QRadialGradient(W * 0.1, H, _dp(180))
        rg2.setColorAt(0.0, QColor(50, 130, 255, 15)); rg2.setColorAt(1.0, QColor(0,0,0,0))
        p.setBrush(QBrush(rg2)); p.drawRect(0, 0, W, H)

        # Header oscuro
        hh = _dp(HEADER_H)
        hg = QLinearGradient(0, 0, 0, hh)
        hg.setColorAt(0.0, HEADER_TOP); hg.setColorAt(1.0, HEADER_BOT)
        p.setBrush(QBrush(hg)); p.drawRect(0, 0, W, hh)

        p.end()

    # ── Idioma ────────────────────────────────────────────────────────────────
    def set_language(self, lang: str):
        self.logout_btn.setText("  ← " + tr("admin.logout"))
        self.t_lock.setText_composed("🔒", tr("admin.tab.lockers"))
        self.t_ses.setText_composed ("🧾", tr("admin.tab.sessions"))
        self.t_log.setText_composed ("📝", tr("admin.tab.log"))
        self.t_adm.setText_composed ("👤", tr("admin.tab.admins"))
        for panel in (self.p_lockers, self.p_sesiones, self.p_log, self.p_admins):
            if hasattr(panel, "set_language"):
                panel.set_language(lang)

    # ── Cambio de tab ─────────────────────────────────────────────────────────
    def _tab(self, i: int):
        self.stack.setCurrentIndex(i)
        for j, b in enumerate([self.t_lock, self.t_ses, self.t_log, self.t_adm]):
            b.setChecked(j == i)
            b.update()   # forzar repintado del indicador
        {
            0: self.p_lockers.refresh,
            1: self.p_sesiones.refresh,
            2: self.p_log.refresh,
            3: self.p_admins.refresh,
        }[i]()

    # ── Admin data ────────────────────────────────────────────────────────────
    def set_admin(self, admin_data: dict):
        self._admin_data = admin_data
        self.badge.setText("  {}  ".format(admin_data.get("t_usuario", "").upper()))
        self.p_admins.set_current_admin(admin_data)
        if hasattr(self.p_lockers, "set_admin_context"):
            self.p_lockers.set_admin_context(admin_data)
        role = (admin_data.get("t_rol", "empleado") or "empleado").lower()
        self.t_adm.setEnabled(True)
        self.t_adm.setToolTip(
            tr("admin.read_only") if role != "administrador"
            else tr("admin.manage_admins")
        )
        nombre = "{} {} {}".format(
            admin_data.get("t_nombre", ""),
            admin_data.get("t_apellido_paterno", ""),
            admin_data.get("t_apellido_materno", "") or "",
        ).strip()
        rol_display = (admin_data.get("t_rol", "Empleado") or "Empleado").capitalize()
        WelcomeToast.show(parent=self, nombre_completo=nombre, rol=rol_display)

    def showEvent(self, e):
        super().showEvent(e)
        self._tab(0)


# ─────────────────────────────────────────────────────────────────────────────
#  Widgets auxiliares
# ─────────────────────────────────────────────────────────────────────────────
class _HLinePainted(QWidget):
    """Línea horizontal con gradiente de opacidad."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(_dp(1))
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, _):
        p = QPainter(self); W = self.width()
        grad = QLinearGradient(0, 0, W, 0)
        grad.setColorAt(0.00, QColor(70, 160, 255, 0))
        grad.setColorAt(0.15, QColor(70, 160, 255, 80))
        grad.setColorAt(0.85, QColor(70, 160, 255, 80))
        grad.setColorAt(1.00, QColor(70, 160, 255, 0))
        p.fillRect(0, 0, W, 1, QBrush(grad)); p.end()


class _VLine(QWidget):
    """Divisor vertical sutil para el header."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(_dp(1))
        self.setFixedHeight(_dp(36))   # 28 → 36 (acompaña al header más alto)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, _):
        p = QPainter(self); H = self.height()
        grad = QLinearGradient(0, 0, 0, H)
        grad.setColorAt(0.0, QColor(70, 160, 255, 0))
        grad.setColorAt(0.5, QColor(70, 160, 255, 70))
        grad.setColorAt(1.0, QColor(70, 160, 255, 0))
        p.fillRect(0, 0, 1, H, QBrush(grad)); p.end()