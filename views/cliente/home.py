from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
    QApplication
)
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont,
    QLinearGradient, QRadialGradient
)

from db.models.lockers import db_get_all_lockers
from views.style.style import STYLE as GLOBAL_STYLE

# ─────────────────────────────────────────────────────────────────────────────
#  SCALE HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _dp(value: float) -> int:
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    return max(1, round(value * dpi / 96))


STYLE = """
QWidget#home_page { background: transparent; }

QFrame#header_strip {
    background-color: #1565c0;
    border: none;
}
QLabel#sys_title {
    color: #ffffff;
    font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 4px;
}
QLabel#sys_label {
    color: rgba(255,255,255,0.65);
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 3px;
}
QLabel#clock_lbl {
    color: #ffffff;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#date_lbl {
    color: rgba(255,255,255,0.65);
    font-family: 'Segoe UI', sans-serif;
}
QLabel#free_count_lbl {
    color: #e53935;
    font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#free_prefix_lbl {
    color: #546e7a;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#btn_admin {
    background: transparent;
    color: #90a4ae;
    border: 1px solid #cfd8e3;
    border-radius: 6px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
}
QPushButton#btn_admin:hover   { color: #1565c0; border-color: #1976d2; background: #e3f0ff; }
QPushButton#btn_admin:pressed { background: #bbdefb; }
QLabel#footer_lbl {
    color: #b0bec5;
    font-family: 'Segoe UI', sans-serif;
}
QFrame#h_divider {
    background: #cfd8e3; border: none;
    min-height: 1px; max-height: 1px;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  STATUS DOT
# ─────────────────────────────────────────────────────────────────────────────
class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        sz = _dp(10); self.setFixedSize(sz, sz)
        self._alpha = 255; self._growing = False
        t = QTimer(self); t.timeout.connect(self._tick); t.start(40)

    def _tick(self):
        self._alpha += -5 if not self._growing else 5
        if self._alpha <= 80:  self._growing = True
        if self._alpha >= 255: self._growing = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = QColor(25, 118, 210); c.setAlpha(self._alpha)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c))
        m = _dp(1)
        p.drawEllipse(m, m, self.width()-m*2, self.height()-m*2)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  BIG LOCKER BUTTON  — circle icon + label + sublabel, fills half the screen
# ─────────────────────────────────────────────────────────────────────────────
class BigLockerButton(QWidget):
    clicked = pyqtSignal()

    # mode: "store" (blue door, arrow in) | "retrieve" (yellow door, arrow out)
    def __init__(self, mode: str, label: str, sublabel: str = "", parent=None):
        super().__init__(parent)
        self.mode     = mode
        self.label    = label
        self.sublabel = sublabel

        # Palette
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
        if e.button() == Qt.LeftButton: self._pressed = True;  self.update()
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pressed = False; self.update()
            if self.rect().contains(e.pos()): self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        # ── Subtle hover tint on background ──
        if self._pressed:
            p.fillRect(0, 0, W, H, QColor(21, 101, 192, 18))
        elif self._hovered:
            p.fillRect(0, 0, W, H, QColor(21, 101, 192, 9))

        # ── Circle ──
        circle_r = int(min(W, H) * 0.30)   # radius relative to button size
        cx = W // 2
        cy = int(H * 0.38)                  # circle center sits in upper 40%

        # Circle fill
        cc = QColor(self._circle_color)
        if self._pressed: cc = cc.darker(108)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(cc))
        p.drawEllipse(cx - circle_r, cy - circle_r, circle_r * 2, circle_r * 2)

        # ── Door icon inside circle ──
        # Door body (two rectangles: frame + door panel)
        door_w  = int(circle_r * 0.72)
        door_h  = int(circle_r * 0.90)
        door_x  = cx - door_w // 2
        door_y  = cy - door_h // 2

        # Frame (slightly darker)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self._door_dark))
        frame_pad = int(door_w * 0.12)
        p.drawRoundedRect(door_x, door_y, door_w, door_h, 3, 3)

        # Door panel
        panel_w = int(door_w * 0.70)
        panel_h = int(door_h * 0.92)
        panel_x = door_x + door_w - panel_w - int(door_w * 0.06)
        panel_y = door_y + int(door_h * 0.04)
        p.setBrush(QBrush(self._door_color))
        p.drawRoundedRect(panel_x, panel_y, panel_w, panel_h, 2, 2)

        # Arrow on door
        arr_len  = int(circle_r * 0.28)
        arr_head = int(arr_len * 0.55)
        ax = cx + int(circle_r * 0.04)
        ay = cy

        pen = QPen(self._arrow_color, max(2, _dp(2)), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen); p.setBrush(Qt.NoBrush)

        if self.mode == "store":
            # Arrow pointing LEFT (into locker)
            p.drawLine(ax + arr_len, ay, ax - arr_len, ay)
            p.drawLine(ax - arr_len, ay, ax - arr_len + arr_head, ay - arr_head)
            p.drawLine(ax - arr_len, ay, ax - arr_len + arr_head, ay + arr_head)
        else:
            # Arrow pointing RIGHT (out of locker)
            p.drawLine(ax - arr_len, ay, ax + arr_len, ay)
            p.drawLine(ax + arr_len, ay, ax + arr_len - arr_head, ay - arr_head)
            p.drawLine(ax + arr_len, ay, ax + arr_len - arr_head, ay + arr_head)

        # ── Main label ──
        label_top = cy + circle_r + int(H * 0.04)
        font_size  = max(14, int(H * 0.10))
        font = QFont("Segoe UI", font_size, QFont.Bold)
        p.setFont(font)
        p.setPen(QPen(self._label_color))
        p.drawText(0, label_top, W, int(H * 0.16),
                   Qt.AlignHCenter | Qt.AlignTop, self.label)

        # ── Sub-label (e.g. "Lockers desocupados: 5") ──
        if self.sublabel:
            sub_top = label_top + int(H * 0.13)
            sub_font_size = max(9, int(H * 0.055))
            sfont = QFont("Segoe UI", sub_font_size)
            p.setFont(sfont)
            p.setPen(QPen(QColor("#78909c")))
            p.drawText(0, sub_top, W, int(H * 0.10),
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
        self.setStyleSheet(GLOBAL_STYLE + STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ───────────────────────────────────────────────────────────
        header = QFrame(); header.setObjectName("header_strip")
        header.setFixedHeight(_dp(54))
        hl = QHBoxLayout(header)
        hl.setContentsMargins(_dp(16), 0, _dp(16), 0)

        tcol = QVBoxLayout(); tcol.setSpacing(_dp(1))
        sl = QLabel("SISTEMA DE CONTROL"); sl.setObjectName("sys_label")
        sl.setStyleSheet(f"font-size: {_dp(8)}px;")
        tl = QLabel("ACCESO"); tl.setObjectName("sys_title")
        tl.setStyleSheet(f"font-size: {_dp(18)}px;")
        tcol.addWidget(sl); tcol.addWidget(tl)
        hl.addLayout(tcol); hl.addStretch()

        ccol = QVBoxLayout(); ccol.setSpacing(_dp(1))
        ccol.setAlignment(Qt.AlignRight)
        self.clock_lbl = QLabel("00:00:00"); self.clock_lbl.setObjectName("clock_lbl")
        self.clock_lbl.setAlignment(Qt.AlignRight)
        self.clock_lbl.setStyleSheet(f"font-size: {_dp(15)}px;")
        self.date_lbl = QLabel("---"); self.date_lbl.setObjectName("date_lbl")
        self.date_lbl.setAlignment(Qt.AlignRight)
        self.date_lbl.setStyleSheet(f"font-size: {_dp(8)}px;")
        ccol.addWidget(self.clock_lbl); ccol.addWidget(self.date_lbl)
        hl.addLayout(ccol)
        root.addWidget(header)

        # ── Buttons area (takes all remaining space) ──────────────────────────
        btn_area = QWidget()
        bl = QVBoxLayout(btn_area)
        bl.setContentsMargins(_dp(24), _dp(16), _dp(24), _dp(8))
        bl.setSpacing(0)

        self.btn_guardar = BigLockerButton("store",    "Guardar",
                                           "Lockers desocupados: —")
        self.btn_recoger = BigLockerButton("retrieve", "Recoger")

        self.btn_guardar.clicked.connect(self.go_guardar.emit)
        self.btn_recoger.clicked.connect(self.go_retirar.emit)

        bl.addWidget(self.btn_guardar, 1)
        bl.addWidget(self.btn_recoger, 1)

        root.addWidget(btn_area, 1)

        # ── Footer ────────────────────────────────────────────────────────────
        div = QFrame(); div.setObjectName("h_divider"); root.addWidget(div)

        fw = QWidget()
        fwl = QHBoxLayout(fw)
        fwl.setContentsMargins(_dp(14), _dp(6), _dp(14), _dp(6))

        # Status dot + text
        sr = QHBoxLayout(); sr.setSpacing(_dp(5))
        sr.addWidget(StatusDot())
        stl = QLabel("EN LÍNEA")
        stl.setStyleSheet(
            f"color: #1976d2; font-size: {_dp(8)}px;"
            f"font-family: 'Segoe UI'; font-weight: 600; letter-spacing: 2px;"
        )
        sr.addWidget(stl)
        fwl.addLayout(sr)
        fwl.addStretch()

        adm = QPushButton("⚙  ADMIN"); adm.setObjectName("btn_admin")
        adm.setStyleSheet(
            adm.styleSheet() +
            f"font-size: {_dp(8)}px; padding: {_dp(5)}px {_dp(16)}px;"
        )
        adm.setCursor(Qt.PointingHandCursor)
        adm.clicked.connect(self.go_admin.emit)
        fwl.addWidget(adm)
        root.addWidget(fw)

        # ── Clock ─────────────────────────────────────────────────────────────
        ct = QTimer(self); ct.timeout.connect(self._tick_clock); ct.start(1000)
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
        busy    = total - free

        # Update sublabel on store button with free count (red number like reference)
        self.btn_guardar.set_sublabel(f"Lockers desocupados:  {free}")