import os
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRectF, QPointF
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QApplication
)
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont,
    QLinearGradient, QRadialGradient, QPixmap,
    QPainterPath, QFontMetrics
)

from db.models.lockers import db_get_all_lockers
from utils.i18n import tr, get_language


def _dp(value: float) -> int:
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    scale = min(dpi / 96, 1.25)
    return max(1, round(value * scale))


# ─── Paleta ───────────────────────────────────────────────────────────────────
BG_TOP        = QColor(10,  20,  45)
BG_BOT        = QColor(16,  32,  68)
HEADER_TOP    = QColor(12,  26,  60)
HEADER_BOT    = QColor(18,  40,  90)
ACCENT_BLUE   = QColor(41, 128, 255)
ACCENT_GOLD   = QColor(255, 185,  40)
CARD_BG       = QColor(20,  38,  78)
CARD_BORDER   = QColor(40,  70, 140)
CARD_HOVER    = QColor(26,  48,  96)
TEXT_PRIMARY  = QColor(220, 235, 255)
TEXT_MUTED    = QColor(110, 140, 190)
GLOW_BLUE     = QColor(41, 128, 255, 55)
GLOW_GOLD     = QColor(255, 185, 40,  50)


STYLE = """
QWidget#home_page { background: transparent; }

QPushButton#btn_admin {
    background: rgba(41,128,255,0.18);
    color: #ddeeff;
    border: 1.5px solid rgba(41,128,255,0.55);
    border-radius: 12px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
    font-weight: 800;
    font-size: 15px;
    padding: 6px 14px;
}
QPushButton#btn_admin:hover   {
    background: rgba(41,128,255,0.36);
    border-color: rgba(41,128,255,0.95);
    color: #ffffff;
}
QPushButton#btn_admin:pressed { background: rgba(41,128,255,0.12); }

QFrame#h_divider {
    background: rgba(41,128,255,0.18);
    border: none;
    min-height: 1px; max-height: 1px;
}

QFrame#home_actions_card {
    background: rgba(16, 30, 62, 0.62);
    border: 1.5px solid rgba(73, 118, 190, 0.42);
    border-radius: 18px;
}
QLabel#home_actions_title {
    color: #eef5ff;
    font-size: 15px;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
}
QLabel#home_actions_subtitle {
    color: rgba(190, 212, 242, 0.88);
    font-size: 10px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
}

QFrame#lang_switch {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 12px;
}
QPushButton#lang_btn {
    background: transparent;
    color: rgba(180,210,255,0.9);
    border: none;
    border-radius: 10px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 800;
    letter-spacing: 1px;
    font-size: 15px;
    padding: 6px 8px;
}
QPushButton#lang_btn:hover { background: rgba(255,255,255,0.12); color: #ffffff; }
QPushButton#lang_btn_active {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 rgba(41,128,255,0.98), stop:1 rgba(20,90,210,0.98));
    color: #ffffff;
    border: none;
    border-radius: 10px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 900;
    letter-spacing: 1px;
    font-size: 15px;
    padding: 6px 8px;
}
QPushButton#btn_admin_handle {
    background: transparent;
    border: none;
    color: rgba(220,235,255,0.95);
    font-family: 'Segoe UI', sans-serif;
    font-weight: 800;
    font-size: 18px;
    border-radius: 10px;
}
QPushButton#btn_admin_handle:hover { background: rgba(255,255,255,0.06); }
"""


# ─────────────────────────────────────────────────────────────────────────────
#  STATUS DOT — versión premium con anillo pulsante
# ─────────────────────────────────────────────────────────────────────────────
class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0.0
        self.setFixedSize(_dp(12), _dp(12))
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(30)

    def _tick(self):
        self._phase = (self._phase + 0.06) % (2 * 3.14159)
        self.update()

    def paintEvent(self, _):
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx = self.width() / 2
        cy = self.height() / 2
        pulse = 0.5 + 0.5 * math.sin(self._phase)

        # Halo exterior
        halo = QColor(41, 200, 100, int(60 * pulse))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(halo))
        r_halo = _dp(6)
        p.drawEllipse(QRectF(cx - r_halo, cy - r_halo, r_halo * 2, r_halo * 2))

        # Núcleo verde brillante
        core = QColor(40, 210, 100)
        p.setBrush(QBrush(core))
        r_core = _dp(3.5)
        p.drawEllipse(QRectF(cx - r_core, cy - r_core, r_core * 2, r_core * 2))
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  BIG LOCKER BUTTON — tarjeta premium con pintado propio
# ─────────────────────────────────────────────────────────────────────────────
class BigLockerButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, mode: str, label: str, sublabel: str = "", parent=None):
        super().__init__(parent)
        self.mode     = mode          # "store" | "retrieve"
        self.label    = label
        self.sublabel = sublabel

        self._hovered = False
        self._pressed = False
        self._label = label
        self._sublabel = sublabel
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)

        # Colores según modo
        if mode == "store":
            self._accent      = ACCENT_BLUE
            self._glow        = GLOW_BLUE
            self._icon_bg     = QColor(25, 65, 150)
            self._icon_bg2    = QColor(41, 100, 220)
        else:
            self._accent      = ACCENT_GOLD
            self._glow        = GLOW_GOLD
            self._icon_bg     = QColor(120, 80, 10)
            self._icon_bg2    = QColor(200, 140, 20)

    def enterEvent(self, e):  self._hovered = True;  self.update()
    def leaveEvent(self, e):  self._hovered = False; self.update()
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pressed = True; self.update()
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pressed = False; self.update()
            if self.rect().contains(e.pos()):
                self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        pad  = _dp(10)

        # ── Sombra de la tarjeta ──────────────────────────────────────────────
        shadow_col = QColor(0, 0, 0, 80 if not self._pressed else 40)
        for off in range(4, 0, -1):
            shadow_col.setAlpha(int(80 * (off / 4)))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(shadow_col))
            p.drawRoundedRect(
                pad + off, pad + off * 2,
                W - pad * 2, H - pad * 2,
                _dp(18), _dp(18)
            )

        # ── Cuerpo de la tarjeta ──────────────────────────────────────────────
        card_rect = QRectF(pad, pad, W - pad * 2, H - pad * 2)
        card_bg = CARD_HOVER if self._hovered else CARD_BG
        if self._pressed:
            card_bg = QColor(14, 28, 58)

        path = QPainterPath()
        path.addRoundedRect(card_rect, _dp(18), _dp(18))
        p.setClipPath(path)

        # Gradiente de fondo de tarjeta
        cg = QLinearGradient(0, pad, 0, H - pad)
        cg.setColorAt(0.0, card_bg.lighter(115))
        cg.setColorAt(1.0, card_bg)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(cg))
        p.drawPath(path)

        # Shimmer superior (borde brillante)
        shim = QLinearGradient(pad, pad, W - pad, pad)
        shim.setColorAt(0.0, QColor(255, 255, 255, 0))
        shim.setColorAt(0.5, QColor(255, 255, 255, 18))
        shim.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(shim))
        p.drawRect(QRectF(pad, pad, W - pad * 2, _dp(2)))

        p.setClipping(False)

        # Borde de la tarjeta
        border_col = self._accent if self._hovered else CARD_BORDER
        border_pen = QPen(border_col, _dp(1.5) if not self._hovered else _dp(2))
        p.setPen(border_pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(card_rect.adjusted(0.5, 0.5, -0.5, -0.5), _dp(18), _dp(18))

        # ── Resplandor de acento ──────────────────────────────────────────────
        if self._hovered:
            glow_r = int(min(W, H) * 0.55)
            cx = int(W // 2)
            cy = int(H * 0.38)
            rg = QRadialGradient(cx, cy, glow_r)
            rg.setColorAt(0.0, self._glow)
            rg.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(rg))
            p.drawRect(pad, pad, W - pad * 2, H - pad * 2)

        # ── Ícono central ─────────────────────────────────────────────────────
        icon_r  = int(min(W, H) * 0.22)
        cx      = W // 2
        cy      = int(H * 0.38)
        icon_rect = QRectF(cx - icon_r, cy - icon_r, icon_r * 2, icon_r * 2)

        # Fondo del ícono: gradiente radial
        ig = QRadialGradient(cx - icon_r * 0.15, cy - icon_r * 0.15, icon_r * 1.3)
        ig.setColorAt(0.0, self._icon_bg2)
        ig.setColorAt(1.0, self._icon_bg)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(ig))
        p.drawRoundedRect(icon_rect, _dp(16), _dp(16))

        # Brillo interior del ícono
        shim2 = QLinearGradient(cx - icon_r, cy - icon_r, cx + icon_r, cy - icon_r)
        shim2.setColorAt(0.0, QColor(255, 255, 255, 0))
        shim2.setColorAt(0.5, QColor(255, 255, 255, 35))
        shim2.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(shim2))
        p.drawRoundedRect(icon_rect, _dp(16), _dp(16))

        # Contorno del ícono
        p.setPen(QPen(self._accent.lighter(130), _dp(1.2)))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(icon_rect.adjusted(0.5, 0.5, -0.5, -0.5), _dp(16), _dp(16))

        # ── Candado SVG-style ─────────────────────────────────────────────────
        self._draw_lock_icon(p, cx, cy, icon_r)

        # ── Texto principal ───────────────────────────────────────────────────
        label_top = cy + icon_r + int(H * 0.055)
        fs = max(13, int(H * 0.095))
        font = QFont("Segoe UI", fs, QFont.Bold)
        p.setFont(font)
        p.setPen(QPen(TEXT_PRIMARY))
        p.drawText(QRectF(pad, label_top, W - pad * 2, int(H * 0.15)),
               Qt.AlignHCenter | Qt.AlignTop, self._label)

        # ── Subtexto ──────────────────────────────────────────────────────────
        if self._sublabel:
            sub_top = label_top + int(H * 0.13)
            sfs = max(6, int(H * 0.040))
            sfont = QFont("Segoe UI", sfs)
            p.setFont(sfont)

            # Píldora de fondo para el subtexto
            fm = QFontMetrics(sfont)
            tw = fm.horizontalAdvance(self._sublabel) + _dp(18)
            th = fm.height() + _dp(8)
            pill_x = (W - tw) // 2
            pill_rect = QRectF(pill_x, sub_top, tw, th)
            pill_bg = QColor(self._accent)
            pill_bg.setAlpha(35)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(pill_bg))
            p.drawRoundedRect(pill_rect, th / 2, th / 2)

            p.setPen(QPen(self._accent.lighter(140)))
            p.drawText(pill_rect, Qt.AlignCenter, self._sublabel)

        p.end()

    def _draw_lock_icon(self, p: QPainter, cx: int, cy: int, r: int):
        """Dibuja una puerta (abierta para guardar, cerrada para recoger)."""
        dw = int(r * 0.55)   # ancho de la puerta
        dh = int(r * 0.60)   # alto de la puerta
        dx = cx - dw // 2
        dy = cy - dh // 2

        pen = QPen(QColor(255, 255, 255, 230), max(2, _dp(2.5)),
                   Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        if self.mode == "store":
            # ── PUERTA ABIERTA (para guardar) ────────────────────────────────
            # Marco exterior de la puerta
            frame = QPainterPath()
            frame.addRoundedRect(QRectF(dx, dy, dw, dh), _dp(4), _dp(4))
            p.setPen(Qt.NoPen)
            frame_fill = QColor(255, 255, 255, 40)
            p.setBrush(QBrush(frame_fill))
            p.drawPath(frame)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(frame)

            # Puerta abierta: línea diagonal desde esquina superior izquierda a inferior derecha
            door_left = dx + _dp(2)
            door_top = dy + _dp(2)
            door_right = dx + dw - _dp(2)
            door_bottom = dy + dh - _dp(2)

            # Línea de la puerta abierta (rotada ~45 grados hacia la derecha)
            p.setPen(pen)
            p.drawLine(int(door_left), int(door_top), int(door_right), int(door_bottom))

            # Arco indicando movimiento hacia adelante (apertura)
            arc_start_x = cx
            arc_start_y = dy - _dp(4)
            arc_w = int(r * 0.35)
            arc_h = int(r * 0.25)
            p.drawArc(QRectF(arc_start_x - arc_w, arc_start_y, arc_w * 2, arc_h * 2),
                      45 * 16, 90 * 16)

            # Punta de flecha indicando entrada
            arrow_x = cx + int(r * 0.40)
            arrow_y = dy - int(r * 0.10)
            arrow_size = _dp(4)
            arrow_pen = QPen(self._accent.lighter(150), max(2, _dp(2.2)),
                           Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(arrow_pen)
            p.drawLine(int(arrow_x), int(arrow_y), int(arrow_x - arrow_size), int(arrow_y - arrow_size))
            p.drawLine(int(arrow_x), int(arrow_y), int(arrow_x - arrow_size), int(arrow_y + arrow_size))

        else:
            # ── PUERTA CERRADA (para recoger) ────────────────────────────────
            # Marco exterior de la puerta
            frame = QPainterPath()
            frame.addRoundedRect(QRectF(dx, dy, dw, dh), _dp(4), _dp(4))
            p.setPen(Qt.NoPen)
            frame_fill = QColor(255, 255, 255, 40)
            p.setBrush(QBrush(frame_fill))
            p.drawPath(frame)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(frame)

            # Línea vertical central (puerta cerrada)
            mid_x = cx
            door_top = dy + _dp(2)
            door_bottom = dy + dh - _dp(2)
            p.setPen(pen)
            p.drawLine(int(mid_x), int(door_top), int(mid_x), int(door_bottom))

            # Dos líneas pequeñas formando un tirador (asa de la puerta)
            handle_y = cy
            handle_left = mid_x - _dp(6)
            handle_right = mid_x + _dp(6)
            p.drawLine(int(handle_left), int(handle_y - _dp(2)), int(handle_left), int(handle_y + _dp(2)))
            p.drawLine(int(handle_right), int(handle_y - _dp(2)), int(handle_right), int(handle_y + _dp(2)))

            # Punto/círculo en el tirador indicando cerradura
            dot_r = _dp(2)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(self._accent))
            p.drawEllipse(QRectF(mid_x - dot_r, handle_y - dot_r, dot_r * 2, dot_r * 2))

    def set_sublabel(self, text: str):
        self._sublabel = text
        self.update()

    def set_label(self, text: str):
        self._label = text
        self.update()


# ─────────────────────────────────────────────────────────────────────────────
#  HOME PAGE
# ─────────────────────────────────────────────────────────────────────────────
class HomePage(QWidget):
    go_guardar = pyqtSignal()
    go_retirar = pyqtSignal()
    go_admin   = pyqtSignal()
    language_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("home_page")
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("header_strip")
        header.setFixedHeight(_dp(108))
        header.setStyleSheet("background: transparent;")

        hl = QHBoxLayout(header)
        hl.setContentsMargins(_dp(18), _dp(8), _dp(18), _dp(8))
        hl.setSpacing(_dp(12))

        # Logo
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        logo_path = os.path.join(project_root, "lockztar.png")
        logo_lbl = QLabel()
        logo_lbl.setFixedSize(_dp(300), _dp(120))
        logo_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        logo_px = QPixmap(logo_path)
        if not logo_px.isNull():
            logo_lbl.setPixmap(
                logo_px.scaled(_dp(280), _dp(110), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        hl.addWidget(logo_lbl, 0, Qt.AlignVCenter)

        hl.addStretch()

        # Derecha: selector de idioma + ADMIN (panel colapsable)
        rhl = QHBoxLayout()
        rhl.setSpacing(_dp(8))
        rhl.setAlignment(Qt.AlignVCenter)

        # Columna con selector de idioma (visible)
        lcol = QVBoxLayout()
        lcol.setSpacing(_dp(6))
        lcol.setAlignment(Qt.AlignVCenter)

        self.lang_switch = QFrame()
        self.lang_switch.setObjectName("lang_switch")
        self.lang_switch.setFixedSize(_dp(220), _dp(70))
        swl = QHBoxLayout(self.lang_switch)
        swl.setContentsMargins(_dp(4), _dp(4), _dp(4), _dp(4))
        swl.setSpacing(_dp(4))

        self.btn_lang_es = QPushButton("ES")
        self.btn_lang_es.setCursor(Qt.PointingHandCursor)
        self.btn_lang_es.clicked.connect(lambda: self._set_lang("es", emit=True))
        self.btn_lang_es.setFixedSize(_dp(104), _dp(58))

        self.btn_lang_en = QPushButton("EN")
        self.btn_lang_en.setCursor(Qt.PointingHandCursor)
        self.btn_lang_en.clicked.connect(lambda: self._set_lang("en", emit=True))
        self.btn_lang_en.setFixedSize(_dp(104), _dp(58))

        swl.addWidget(self.btn_lang_es)
        swl.addWidget(self.btn_lang_en)
        lcol.addWidget(self.lang_switch, 0, Qt.AlignRight)

        # Admin button (kept large) but placed inside a collapsable panel
        self.adm = QPushButton("")
        self.adm.setObjectName("btn_admin")
        self.adm.setFixedSize(_dp(240), _dp(70))
        self.adm.setStyleSheet(
            self.adm.styleSheet() +
            f"font-size:{_dp(16)}px; padding:0 {_dp(16)}px;"
        )
        self.adm.setCursor(Qt.PointingHandCursor)
        self.adm.clicked.connect(self.go_admin.emit)
        self.adm.setFocusPolicy(Qt.NoFocus)

        # Panel para admin (siempre visible)
        self.admin_panel = QFrame()
        self.admin_panel.setObjectName("admin_panel")
        self.admin_panel.setFixedWidth(_dp(250))
        ap_layout = QHBoxLayout(self.admin_panel)
        ap_layout.setContentsMargins(0, 0, 0, 0)
        ap_layout.addWidget(self.adm)

        rhl.addLayout(lcol)
        rhl.addWidget(self.admin_panel, 0, Qt.AlignRight)
        hl.addLayout(rhl)

        root.addWidget(header)

        # Línea separadora con gradiente (se pinta en paintEvent)
        sep = QFrame()
        sep.setObjectName("h_divider")
        root.addWidget(sep)

        # ── Área de botones ────────────────────────────────────────────────────
        btn_area = QFrame()
        btn_area.setObjectName("home_actions_card")
        btn_area.setMinimumHeight(_dp(270))
        bl = QVBoxLayout(btn_area)
        bl.setContentsMargins(_dp(16), _dp(14), _dp(16), _dp(16))
        bl.setSpacing(_dp(12))

        actions_hdr = QVBoxLayout()
        actions_hdr.setSpacing(_dp(2))
        actions_hdr.setAlignment(Qt.AlignCenter)
        self.actions_title = QLabel(tr("home.actions.title"))
        self.actions_title.setObjectName("home_actions_title")
        self.actions_title.setAlignment(Qt.AlignCenter)
        self.actions_subtitle = QLabel(tr("home.actions.subtitle"))
        self.actions_subtitle.setObjectName("home_actions_subtitle")
        self.actions_subtitle.setAlignment(Qt.AlignCenter)
        actions_hdr.addWidget(self.actions_title)
        actions_hdr.addWidget(self.actions_subtitle)
        bl.addLayout(actions_hdr)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(_dp(14))
        actions_row.setContentsMargins(0, _dp(2), 0, 0)

        self.btn_guardar = BigLockerButton("store", "", "")
        self.btn_recoger = BigLockerButton("retrieve", "")
        self.btn_guardar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.btn_recoger.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.btn_guardar.setMinimumHeight(_dp(190))
        self.btn_recoger.setMinimumHeight(_dp(190))

        self.btn_guardar.clicked.connect(self.go_guardar.emit)
        self.btn_recoger.clicked.connect(self.go_retirar.emit)

        actions_row.addWidget(self.btn_guardar, 1)
        actions_row.addWidget(self.btn_recoger, 1)
        bl.addLayout(actions_row, 1)
        root.addWidget(btn_area, 1)

        # ── Footer ─────────────────────────────────────────────────────────────
        div2 = QFrame()
        div2.setObjectName("h_divider")
        root.addWidget(div2)

        fw = QWidget()
        fw.setStyleSheet("background: transparent;")
        fwl = QHBoxLayout(fw)
        fwl.setContentsMargins(_dp(14), _dp(5), _dp(14), _dp(5))

        sr = QHBoxLayout()
        sr.setSpacing(_dp(6))
        sr.addWidget(StatusDot())
        stl = QLabel("")
        stl.setStyleSheet(
            f"color:rgba(110,180,120,0.90); font-size:{_dp(9)}px;"
            f"font-family:'Segoe UI'; font-weight:700; letter-spacing:2px;"
        )
        sr.addWidget(stl)
        self.status_lbl = stl
        fwl.addLayout(sr)
        fwl.addStretch()

        # Versión / info pequeña
        
        root.addWidget(fw)

        # ── Reloj ──────────────────────────────────────────────────────────────
        # (Reloj y fecha deshabilitados)
        self.set_language(get_language())

    # ── Fondo global ────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        # Gradiente principal oscuro
        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0.0, BG_TOP)
        bg.setColorAt(1.0, BG_BOT)
        p.fillRect(0, 0, W, H, QBrush(bg))

        # Header con gradiente propio
        hh = _dp(108)
        hg = QLinearGradient(0, 0, 0, hh)
        hg.setColorAt(0.0, HEADER_TOP)
        hg.setColorAt(1.0, HEADER_BOT)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(hg))
        p.drawRect(0, 0, W, hh)

        # Línea de acento azul en la parte inferior del header
        accent_pen = QPen(ACCENT_BLUE, _dp(2))
        p.setPen(accent_pen)
        p.drawLine(0, hh - 1, W, hh - 1)

        # Sutiles líneas de cuadrícula decorativas en el fondo
        grid_pen = QPen(QColor(40, 70, 140, 28), _dp(1))
        p.setPen(grid_pen)
        step = _dp(48)
        for x in range(0, W + step, step):
            p.drawLine(x, hh, x, H)
        for y in range(hh, H + step, step):
            p.drawLine(0, y, W, y)

        # Destellos de luz radial en esquinas
        for (rx, ry, col) in [
            (W, hh + _dp(40), QColor(41, 128, 255, 20)),
            (0,  H,            QColor(41, 100, 200, 14)),
        ]:
            rg = QRadialGradient(rx, ry, _dp(250))
            rg.setColorAt(0.0, col)
            rg.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(rg))
            p.setPen(Qt.NoPen)
            p.drawRect(0, 0, W, H)

        p.end()

    # ── Idioma ───────────────────────────────────────────────────────────────
    def _set_lang(self, lang: str, emit: bool = False):
        lang = "en" if lang == "en" else "es"
        self._lang = lang
        self.btn_lang_es.setObjectName("lang_btn_active" if lang == "es" else "lang_btn")
        self.btn_lang_en.setObjectName("lang_btn_active" if lang == "en" else "lang_btn")
        for btn in (self.btn_lang_es, self.btn_lang_en):
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if emit:
            self.language_changed.emit(lang)

    def set_language(self, lang: str):
        self._set_lang(lang, emit=False)
        self.adm.setText(tr("home.admin"))
        self.btn_guardar.set_label(tr("home.store"))
        self.btn_recoger.set_label(tr("home.pickup"))
        self.actions_title.setText(tr("home.actions.title"))
        self.actions_subtitle.setText(tr("home.actions.subtitle"))
        self.status_lbl.setText(tr("home.online"))
        # actualizar reloj/fecha inmediatamente según nuevo idioma
        try:
            self._tick_clock()
        except Exception:
            pass

    def refresh(self):
        lockers = db_get_all_lockers()
        free = sum(1 for l in lockers if l["t_estado"] == "libre")
        self.btn_guardar.set_sublabel(tr("home.free_lockers", n=free))