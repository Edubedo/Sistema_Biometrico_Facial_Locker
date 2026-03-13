from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QApplication
)
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont,
    QLinearGradient
)

from db.models.lockers import db_get_all_lockers


# ─────────────────────────────────────────────────────────────────────────────
#  SCALE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _screen_size():
    screen = QApplication.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        return geo.width(), geo.height()
    return 1280, 720


def _dp(value: float) -> int:
    """DPI-aware pixel conversion."""
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    return max(1, round(value * dpi / 96))


def _sw(fraction: float) -> int:
    """Fraction of screen width."""
    w, _ = _screen_size()
    return max(1, round(w * fraction))


def _sh(fraction: float) -> int:
    """Fraction of screen height."""
    _, h = _screen_size()
    return max(1, round(h * fraction))


def _sf(fraction: float) -> int:
    """Font size as fraction of screen height, DPI-corrected."""
    _, h = _screen_size()
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    base = h * fraction
    return max(8, round(base * 96 / dpi))


# ─────────────────────────────────────────────────────────────────────────────
#  DYNAMIC STYLESHEET  (re-built on each instantiation so sizes are current)
# ─────────────────────────────────────────────────────────────────────────────
def _build_style() -> str:
    return f"""
QWidget#home_page {{ background: transparent; }}

QFrame#header_strip {{
    background-color: #1565c0;
    border: none;
}}
QLabel#sys_title {{
    color: #ffffff;
    font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
    font-size: {_sf(0.030)}px;
    letter-spacing: 4px;
}}
QLabel#sys_label {{
    color: rgba(255,255,255,0.65);
    font-family: 'Segoe UI', sans-serif;
    font-size: {_sf(0.014)}px;
    letter-spacing: 3px;
}}
QLabel#clock_lbl {{
    color: #ffffff;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
    font-size: {_sf(0.026)}px;
}}
QLabel#date_lbl {{
    color: rgba(255,255,255,0.65);
    font-family: 'Segoe UI', sans-serif;
    font-size: {_sf(0.014)}px;
}}
QPushButton#btn_admin {{
    background: transparent;
    color: #90a4ae;
    border: 1px solid #cfd8e3;
    border-radius: {_dp(6)}px;
    font-family: 'Segoe UI', sans-serif;
    font-size: {_sf(0.014)}px;
    letter-spacing: 2px;
    padding: {_sh(0.008)}px {_sw(0.018)}px;
}}
QPushButton#btn_admin:hover   {{ color: #1565c0; border-color: #1976d2; background: #e3f0ff; }}
QPushButton#btn_admin:pressed {{ background: #bbdefb; }}
QLabel#footer_lbl {{
    color: #b0bec5;
    font-family: 'Segoe UI', sans-serif;
}}
QFrame#h_divider {{
    background: #cfd8e3; border: none;
    min-height: 1px; max-height: 1px;
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  STATUS DOT
# ─────────────────────────────────────────────────────────────────────────────
class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        sz = max(8, _sw(0.010))
        self.setFixedSize(sz, sz)
        self._alpha = 255
        self._growing = False
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(40)

    def _tick(self):
        self._alpha += -5 if not self._growing else 5
        if self._alpha <= 80:  self._growing = True
        if self._alpha >= 255: self._growing = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor(25, 118, 210)
        c.setAlpha(self._alpha)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c))
        m = max(1, _dp(1))
        p.drawEllipse(m, m, self.width() - m * 2, self.height() - m * 2)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  BIG LOCKER BUTTON  — fully responsive via relative sizing
# ─────────────────────────────────────────────────────────────────────────────
class BigLockerButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, mode: str, label: str, sublabel: str = "", parent=None):
        super().__init__(parent)
        self.mode     = mode
        self.label    = label
        self.sublabel = sublabel

        if mode == "store":
            self._door_color   = QColor("#1976d2")
            self._door_dark    = QColor("#1250a0")
            self._arrow_color  = QColor("#ffffff")
            self._circle_color = QColor("#cfe3f5")
            self._label_color  = QColor("#1a2a3a")
        else:
            self._door_color   = QColor("#f5c518")
            self._door_dark    = QColor("#c49a10")
            self._arrow_color  = QColor("#ffffff")
            self._circle_color = QColor("#d8ede0")
            self._label_color  = QColor("#1a2a3a")

        self._hovered = False
        self._pressed = False
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, e):  self._hovered = True;  self.update()
    def leaveEvent(self, e):  self._hovered = False; self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pressed = True
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pressed = False
            self.update()
            if self.rect().contains(e.pos()):
                self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        # Hover / press tint
        if self._pressed:
            p.fillRect(0, 0, W, H, QColor(21, 101, 192, 18))
        elif self._hovered:
            p.fillRect(0, 0, W, H, QColor(21, 101, 192, 9))

        # ── Circle (size relative to widget dimensions) ──
        short_side = min(W, H)
        circle_r   = int(short_side * 0.28)   # scales with whichever axis is smaller
        cx = W // 2
        cy = int(H * 0.36)

        cc = QColor(self._circle_color)
        if self._pressed:
            cc = cc.darker(108)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(cc))
        p.drawEllipse(cx - circle_r, cy - circle_r, circle_r * 2, circle_r * 2)

        # ── Door icon ──
        door_w = int(circle_r * 0.72)
        door_h = int(circle_r * 0.90)
        door_x = cx - door_w // 2
        door_y = cy - door_h // 2

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self._door_dark))
        p.drawRoundedRect(door_x, door_y, door_w, door_h, 3, 3)

        panel_w = int(door_w * 0.70)
        panel_h = int(door_h * 0.92)
        panel_x = door_x + door_w - panel_w - int(door_w * 0.06)
        panel_y = door_y + int(door_h * 0.04)
        p.setBrush(QBrush(self._door_color))
        p.drawRoundedRect(panel_x, panel_y, panel_w, panel_h, 2, 2)

        # ── Arrow ──
        arr_len  = int(circle_r * 0.28)
        arr_head = int(arr_len * 0.55)
        ax = cx + int(circle_r * 0.04)
        ay = cy

        pen_w = max(2, int(short_side * 0.006))
        pen = QPen(self._arrow_color, pen_w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        if self.mode == "store":
            p.drawLine(ax + arr_len, ay, ax - arr_len, ay)
            p.drawLine(ax - arr_len, ay, ax - arr_len + arr_head, ay - arr_head)
            p.drawLine(ax - arr_len, ay, ax - arr_len + arr_head, ay + arr_head)
        else:
            p.drawLine(ax - arr_len, ay, ax + arr_len, ay)
            p.drawLine(ax + arr_len, ay, ax + arr_len - arr_head, ay - arr_head)
            p.drawLine(ax + arr_len, ay, ax + arr_len - arr_head, ay + arr_head)

        # ── Main label ──
        label_top     = cy + circle_r + int(H * 0.04)
        font_size_raw = H * 0.075          # ~7.5% of widget height
        screen        = QApplication.primaryScreen()
        dpi           = screen.logicalDotsPerInch() if screen else 96
        font_size     = max(12, round(font_size_raw * 96 / dpi))

        font = QFont("Segoe UI", font_size, QFont.Bold)
        p.setFont(font)
        p.setPen(QPen(self._label_color))
        p.drawText(0, label_top, W, H - label_top,
                   Qt.AlignHCenter | Qt.AlignTop, self.label)

        # ── Sub-label ──
        if self.sublabel:
            sub_top      = label_top + int(H * 0.12)
            sub_size_raw = H * 0.048
            sub_size     = max(8, round(sub_size_raw * 96 / dpi))
            sfont = QFont("Segoe UI", sub_size)
            p.setFont(sfont)
            p.setPen(QPen(QColor("#78909c")))
            p.drawText(0, sub_top, W, H - sub_top,
                       Qt.AlignHCenter | Qt.AlignTop, self.sublabel)

        p.end()

    def set_sublabel(self, text: str):
        self.sublabel = text
        self.update()


# ─────────────────────────────────────────────────────────────────────────────
#  HOME PAGE
# ─────────────────────────────────────────────────────────────────────────────
class HomePage(QWidget):
    go_guardar = pyqtSignal()
    go_retirar = pyqtSignal()
    go_admin   = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("home_page")
        self.setStyleSheet(_build_style())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ───────────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("header_strip")
        header.setMinimumHeight(_sh(0.06))
        header.setMaximumHeight(_sh(0.10))

        hl = QHBoxLayout(header)
        pad_h = _sw(0.012)
        hl.setContentsMargins(pad_h, 0, pad_h, 0)
        hl.setSpacing(_sw(0.010))

        # Title column
        tcol = QVBoxLayout()
        tcol.setSpacing(_sh(0.004))
        sl = QLabel("SISTEMA DE CONTROL")
        sl.setObjectName("sys_label")
        tl = QLabel("ACCESO")
        tl.setObjectName("sys_title")
        tcol.addWidget(sl)
        tcol.addWidget(tl)
        hl.addLayout(tcol)
        hl.addStretch()

        # Clock column
        ccol = QVBoxLayout()
        ccol.setSpacing(_sh(0.004))
        ccol.setAlignment(Qt.AlignRight)
        self.clock_lbl = QLabel("00:00:00")
        self.clock_lbl.setObjectName("clock_lbl")
        self.clock_lbl.setAlignment(Qt.AlignRight)
        self.date_lbl = QLabel("---")
        self.date_lbl.setObjectName("date_lbl")
        self.date_lbl.setAlignment(Qt.AlignRight)
        ccol.addWidget(self.clock_lbl)
        ccol.addWidget(self.date_lbl)
        hl.addLayout(ccol)

        root.addWidget(header)

        # ── Button area ───────────────────────────────────────────────────────
        btn_area = QWidget()
        bl = QVBoxLayout(btn_area)
        pad = _sw(0.018)
        bl.setContentsMargins(pad, _sh(0.012), pad, _sh(0.008))
        bl.setSpacing(0)

        self.btn_guardar = BigLockerButton(
            "store", "Guardar", "Lockers desocupados: —"
        )
        self.btn_recoger = BigLockerButton("retrieve", "Recoger")

        self.btn_guardar.clicked.connect(self.go_guardar.emit)
        self.btn_recoger.clicked.connect(self.go_retirar.emit)

        bl.addWidget(self.btn_guardar, 1)
        bl.addWidget(self.btn_recoger, 1)

        root.addWidget(btn_area, 1)

        # ── Divider ───────────────────────────────────────────────────────────
        div = QFrame()
        div.setObjectName("h_divider")
        root.addWidget(div)

        # ── Footer ────────────────────────────────────────────────────────────
        fw = QWidget()
        fw.setMinimumHeight(_sh(0.040))
        fw.setMaximumHeight(_sh(0.065))
        fwl = QHBoxLayout(fw)
        pad_f = _sw(0.011)
        fwl.setContentsMargins(pad_f, 0, pad_f, 0)
        fwl.setSpacing(_sw(0.008))

        # Online indicator
        sr = QHBoxLayout()
        sr.setSpacing(_sw(0.005))
        sr.addWidget(StatusDot())
        stl = QLabel("EN LÍNEA")
        stl.setStyleSheet(
            f"color: #1976d2;"
            f"font-size: {_sf(0.014)}px;"
            f"font-family: 'Segoe UI';"
            f"font-weight: 600;"
            f"letter-spacing: 2px;"
        )
        sr.addWidget(stl)
        fwl.addLayout(sr)
        fwl.addStretch()

        adm = QPushButton("⚙  ADMIN")
        adm.setObjectName("btn_admin")
        adm.setCursor(Qt.PointingHandCursor)
        adm.clicked.connect(self.go_admin.emit)
        fwl.addWidget(adm)

        root.addWidget(fw)

        # ── Clock timer ───────────────────────────────────────────────────────
        ct = QTimer(self)
        ct.timeout.connect(self._tick_clock)
        ct.start(1000)
        self._tick_clock()

    # ── Background gradient ───────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        W, H = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0.0, QColor(232, 240, 251))
        g.setColorAt(1.0, QColor(210, 228, 248))
        p.fillRect(0, 0, W, H, QBrush(g))
        p.end()

    # Re-apply stylesheet when resized so font sizes stay accurate
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setStyleSheet(_build_style())

    def _tick_clock(self):
        from PyQt5.QtCore import QDateTime
        dt = QDateTime.currentDateTime()
        self.clock_lbl.setText(dt.toString("HH:mm:ss"))
        self.date_lbl.setText(dt.toString("ddd dd MMM").upper())

    # ── Public API ────────────────────────────────────────────────────────────
    def refresh(self):
        lockers = db_get_all_lockers()
        total   = len(lockers)
        free    = sum(1 for l in lockers if l["t_estado"] == "libre")

        self.btn_guardar.set_sublabel(f"Lockers desocupados:  {free}")