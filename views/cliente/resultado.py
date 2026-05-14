from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QApplication
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QRadialGradient, QFont

from views.style.widgets.widgets import AutoTimer, AUTO_HOME_SEC
from utils.i18n import tr


def _dp(v):
    s = QApplication.primaryScreen()
    return max(1, round(v * (s.logicalDotsPerInch() if s else 96) / 96))


# ── Per-kind config ───────────────────────────────────────────────────────────
_KIND = {
    "ok": {
        "icon":        "✓",
        "bg_top":      QColor(232, 245, 233),
        "bg_bot":      QColor(200, 230, 201),
        "accent":      QColor(46,  125,  50),
        "accent_light":QColor(232, 245, 233),
        "border":      QColor(129, 199, 132),
        "badge_bg":    QColor(200, 230, 201),
        "badge_fg":    "#2e7d32",
        "label":       "ÉXITO",
    },
    "warn": {
        "icon":        "!",
        "bg_top":      QColor(255, 248, 225),
        "bg_bot":      QColor(255, 236, 179),
        "accent":      QColor(230, 108,   0),
        "accent_light":QColor(255, 243, 224),
        "border":      QColor(255, 183,  77),
        "badge_bg":    QColor(255, 236, 179),
        "badge_fg":    "#e65100",
        "label":       "ATENCIÓN",
    },
    "err": {
        "icon":        "✕",
        "bg_top":      QColor(255, 235, 238),
        "bg_bot":      QColor(255, 205, 210),
        "accent":      QColor(198,  40,  40),
        "accent_light":QColor(255, 235, 238),
        "border":      QColor(239, 154, 154),
        "badge_bg":    QColor(255, 205, 210),
        "badge_fg":    "#c62828",
        "label":       "ERROR",
    },
    "ok_blue": {
        "icon":        "✓",
        "bg_top":      QColor(230, 242, 255),
        "bg_bot":      QColor(205, 226, 250),
        "accent":      QColor(38,  103, 198),
        "accent_light":QColor(230, 242, 255),
        "border":      QColor(135, 178, 235),
        "badge_bg":    QColor(210, 229, 252),
        "badge_fg":    "#1f5fb8",
        "label":       "EXITO",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  ICON CIRCLE  — large colored circle with centered glyph
# ─────────────────────────────────────────────────────────────────────────────
class _IconCircle(QWidget):
    def __init__(self, glyph: str, accent: QColor, light: QColor, size: int = None, parent=None):
        super().__init__(parent)
        self._glyph  = glyph
        self._accent = accent
        self._light  = light
        # Allow caller to override size for small screens
        sz = size if size is not None else _dp(160)
        self.setFixedSize(sz, sz)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W = self.width()

        # Outer glow ring
        glow = QColor(self._accent); glow.setAlpha(30)
        p.setBrush(QBrush(glow)); p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, W, W)

        # Inner filled circle
        inner = _dp(14)
        p.setBrush(QBrush(self._accent)); p.setPen(Qt.NoPen)
        p.drawEllipse(inner, inner, W - inner*2, W - inner*2)

        # Glyph
        font = QFont("Segoe UI", _dp(48), QFont.Black)
        p.setFont(font)
        p.setPen(QColor("#ffffff"))
        p.drawText(self.rect(), Qt.AlignCenter, self._glyph)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  RESULT PAGE
# ─────────────────────────────────────────────────────────────────────────────
class ResultPage(QWidget):
    go_home = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("result_page")
        self._kind    = "ok"
        self._card    = None
        self._timer_w = AutoTimer(AUTO_HOME_SEC)
        self._timer_w.timeout.connect(self.go_home.emit)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setAlignment(Qt.AlignCenter)

    def _clear_root_layout(self):
        while self._root.count():
            item = self._root.takeAt(0)
            w = item.widget()
            if w is not None:
                if w == self._timer_w:
                    w.setParent(None)
                else:
                    w.deleteLater()

    # ── Background gradient (changes per kind) ────────────────────────────────
    def paintEvent(self, _):
        # Use the app's dark blue colorimetry for the background to match the UI
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        bg = QLinearGradient(0, 0, 0, H)
        bg.setColorAt(0.0, QColor(10, 20, 45))
        bg.setColorAt(1.0, QColor(16, 32, 68))
        p.fillRect(0, 0, W, H, QBrush(bg))

        # Accent radial glow using the current kind's accent color (subtle)
        cfg = _KIND.get(self._kind, _KIND["ok"])
        rg = QRadialGradient(W / 2, 0, H * 0.7)
        glow = QColor(cfg["accent"]); glow.setAlpha(18)
        rg.setColorAt(0.0, glow)
        rg.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, W, H, QBrush(rg))
        p.end()

    # ── Public API ────────────────────────────────────────────────────────────
    def show_result(self, kind: str, title: str, subtitle: str, detail: str = "", auto: bool = True):
        self._kind = kind
        cfg = _KIND.get(kind, _KIND["ok"])

        # Rebuild root content to avoid accumulated spacers after multiple results.
        self._clear_root_layout()
        self._card = None

        # Determine a simple scale factor for small screens (e.g., 7" / 800px wide)
        screen_w = self.width() or (QApplication.primaryScreen().size().width() if QApplication.primaryScreen() else 1024)
        sf = 1.0
        if screen_w <= 800:
            sf = 0.70
        elif screen_w <= 1024:
            sf = 0.86

        def s(v):
            return max(1, round(_dp(v) * sf))

        self._root.addStretch(1)

        # ── Card ──────────────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("result_card")
        # Responsive card width: cap to screen width while keeping min width
        screen_w_for_card = self.width() or (QApplication.primaryScreen().size().width() if QApplication.primaryScreen() else 1024)
        card_width = min(s(720), max(s(300), int(screen_w_for_card * 0.92)))
        card.setFixedWidth(card_width)
        border_color = cfg["border"].name()
        accent_hex   = cfg["accent"].name()
        card.setStyleSheet(f"""
            QFrame#result_card {{
                background: #ffffff;
                border: 1px solid {border_color};
                border-top: 4px solid {accent_hex};
                border-radius: {s(16)}px;
            }}
        """)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(s(56), s(48), s(56), s(48))
        cl.setSpacing(s(20))
        cl.setAlignment(Qt.AlignCenter)

        # Icon circle
        icon_w = _IconCircle(cfg["icon"], cfg["accent"], cfg["accent_light"], size=s(120))
        cl.addWidget(icon_w, alignment=Qt.AlignCenter)
        cl.addSpacing(s(4))

        # Status badge
        badge_key = {
            "ok": "result.ok",
            "ok_blue": "result.ok",
            "warn": "result.warn",
            "err": "result.err",
        }.get(kind, "result.ok")
        badge = QLabel(tr(badge_key))
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(f"""
            background: {cfg['badge_bg'].name()};
            color: {cfg['badge_fg']};
            border: 1px solid {border_color};
            border-radius: {s(10)}px;
            font-size: {s(8)}px;
            font-weight: 800;
            font-family: 'Segoe UI';
            letter-spacing: 3px;
            padding: {s(4)}px {s(16)}px;
        """)
        badge.setFixedHeight(s(30))
        cl.addWidget(badge, alignment=Qt.AlignCenter)

        # Title
        t_lbl = QLabel(title)
        t_lbl.setAlignment(Qt.AlignCenter)
        t_lbl.setWordWrap(True)
        t_lbl.setStyleSheet(f"""
            font-size: {s(36)}px;
            font-weight: 900;
            color: {accent_hex};
            font-family: 'Segoe UI';
            letter-spacing: -0.5px;
        """)
        cl.addWidget(t_lbl)

        # Subtitle
        s_lbl = QLabel(subtitle)
        s_lbl.setAlignment(Qt.AlignCenter)
        s_lbl.setWordWrap(True)
        s_lbl.setStyleSheet(f"""
            font-size: {s(13)}px;
            color: #000000;
            font-family: 'Segoe UI';
            line-height: 1.6;
        """)
        cl.addWidget(s_lbl)

        # Detail (locker number, etc.)
        if detail:
            div = QFrame()
            div.setStyleSheet(f"background:{border_color};border:none;min-height:1px;max-height:1px;")
            cl.addWidget(div)

            d_lbl = QLabel(detail)
            d_lbl.setAlignment(Qt.AlignCenter)
            d_lbl.setStyleSheet(f"""
                font-size: {s(72)}px;
                font-weight: 900;
                color: #000000;
                font-family: 'Segoe UI';
                letter-spacing: 2px;
            """)
            cl.addWidget(d_lbl)

        cl.addSpacing(s(8))

        # Button
        btn = QPushButton(tr("result.home"))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedWidth(s(260))
        btn.setFixedHeight(s(46))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: #2f80ed;
                color: #ffffff;
                border: none;
                border-radius: {s(10)}px;
                font-size: {s(14)}px;
                font-weight: 800;
                font-family: 'Segoe UI';
                letter-spacing: 2px;
            }}
            QPushButton:hover   {{ background: #1f6ed8; }}
            QPushButton:pressed {{ background: #1658b0; }}
        """)
        btn.clicked.connect(self._manual_home)
        cl.addWidget(btn, alignment=Qt.AlignCenter)

        self._card = card
        self._root.addWidget(card, alignment=Qt.AlignCenter)
        self._root.addSpacing(_dp(20))
        # Timer label (optional)
        if auto:
            self._timer_w.setFixedWidth(_dp(720))
            self._timer_w.setStyleSheet(f"""
                color: #2f80ed;
                font-size: {_dp(14)}px;
                font-weight: 700;
                font-family: 'Segoe UI';
                letter-spacing: 1px;
                opacity: 0.6;
            """)
            self._root.addWidget(self._timer_w, alignment=Qt.AlignCenter)
            self._root.addStretch(1)
            self._timer_w.start()
        else:
            # ensure timer isn't running and remains hidden
            try:
                self._timer_w.stop()
            except Exception:
                pass
            self._root.addStretch(1)

        self.update()   # repaint background

    def _manual_home(self):
        self._timer_w.stop()
        self.go_home.emit()