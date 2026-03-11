from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy, QApplication, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient

from db.models.intentos_acceso import db_get_intentos_recientes


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


STYLE = """
QWidget#admin_log_panel,
QWidget#admin_log_inner {
    background: transparent;
}

QLabel#section_title {
    color: #1565c0;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 3px;
}
QLabel#section_sub {
    color: #90a4ae;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
}

QFrame#card {
    background: #ffffff;
    border: none;
    border-left: 4px solid #1976d2;
    border-radius: 10px;
}

QLabel#card_id {
    color: #1565c0;
    font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#card_locker {
    color: #546e7a;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
}
QLabel#card_time {
    color: #90a4ae;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#badge_active {
    background: #e3f0ff;
    color: #1565c0;
    border: 1px solid #90c4f0;
    border-radius: 10px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
    font-weight: 700;
}
QLabel#card_idx {
    color: #bbdefb;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#empty_lbl {
    color: #b0bec5;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 3px;
}

QPushButton#btn_refresh {
    background: transparent;
    color: #90a4ae;
    border: 1px solid #cfd8e3;
    border-radius: 6px;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
}
QPushButton#btn_refresh:hover   { color: #1565c0; border-color: #1976d2; background: #e3f0ff; }
QPushButton#btn_refresh:pressed { background: #bbdefb; }

QFrame#counter_block {
    background: #ffffff;
    border: none;
    border-left: 4px solid #1565c0;
    border-radius: 10px;
}
QLabel#counter_num {
    color: #1565c0;
    font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#counter_key {
    color: #90a4ae;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
}
QLabel#status_text {
    color: #1976d2;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
    font-weight: 600;
}

QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #e8f0fb; width: 4px; margin: 0; }
QScrollBar::handle:vertical { background: #90c4f0; border-radius: 2px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QFrame#h_divider {
    background: #cfd8e3; border: none;
    min-height: 1px; max-height: 1px;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  STATUS DOT (igual que en sesionesPanel.py)
# ─────────────────────────────────────────────────────────────────────────────
class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        sz = _dp(10)
        self.setFixedSize(sz, sz)
        self._alpha = 255
        self._growing = False
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(40)

    def _tick(self):
        self._alpha += -5 if not self._growing else 5
        if self._alpha <= 80:
            self._growing = True
        if self._alpha >= 255:
            self._growing = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor(25, 118, 210)
        c.setAlpha(self._alpha)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c))
        m = _dp(1)
        p.drawEllipse(m, m, self.width() - m * 2, self.height() - m * 2)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  LOG CARD (idéntica estructura a SessionCard)
# ─────────────────────────────────────────────────────────────────────────────
class LogCard(QFrame):
    def __init__(self, intento: dict, index: int, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        _shadow(self, _dp(10), 15, _dp(2))

        lay = QHBoxLayout(self)
        lay.setContentsMargins(_dp(14), _dp(10), _dp(14), _dp(10))
        lay.setSpacing(_dp(14))

        # Índice numerado (01, 02, 03...)
        idx_lbl = QLabel(f"{index:02d}")
        idx_lbl.setObjectName("card_idx")
        idx_lbl.setStyleSheet(
            f"color: #bbdefb; font-size: {_dp(16)}px; font-weight: 900;"
            f"font-family: 'Segoe UI'; min-width: {_dp(26)}px;"
        )
        idx_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(idx_lbl)

        # Divisor vertical
        div = QFrame()
        div.setFrameShape(QFrame.VLine)
        div.setStyleSheet(
            f"background: #e3f0ff; border: none;"
            f"min-width: {_dp(1)}px; max-width: {_dp(1)}px;"
        )
        lay.addWidget(div)

        # Columna de información principal
        info_col = QVBoxLayout()
        info_col.setSpacing(_dp(2))

        # Primera línea: tipo de intento (como si fuera ID de sesión)
        tipo = intento.get("t_tipo_intento", "").upper()
        tipo_text = f"INTENTO  #{tipo}" if tipo else "INTENTO  #DESCONOCIDO"
        tipo_lbl = QLabel(tipo_text)
        tipo_lbl.setObjectName("card_id")
        tipo_lbl.setStyleSheet(f"font-size: {_dp(12)}px;")
        info_col.addWidget(tipo_lbl)

        # Segunda línea: locker (igual que en sesiones)
        locker = intento.get("t_numero_locker")
        locker_text = f"LOCKER  ·  #{locker}" if locker else "LOCKER  ·  #—"
        locker_lbl = QLabel(locker_text)
        locker_lbl.setObjectName("card_locker")
        locker_lbl.setStyleSheet(f"font-size: {_dp(9)}px;")
        info_col.addWidget(locker_lbl)

        # Tercera línea: descripción (si existe)
        desc = intento.get("t_descripcion_acceso", "")
        if desc:
            desc_lbl = QLabel(desc[:60] + ("..." if len(desc) > 60 else ""))
            desc_lbl.setObjectName("card_locker")  # Reusamos el estilo de locker
            desc_lbl.setStyleSheet(f"color: #78909c; font-size: {_dp(8)}px; font-style: italic;")
            info_col.addWidget(desc_lbl)

        lay.addLayout(info_col)
        lay.addStretch()

        # Timestamp (como en sesiones)
        ts = intento.get("d_fecha_hora_acceso", "")
        if ts:
            if len(ts) >= 16:
                ts_formatted = f"{ts[8:10]}/{ts[5:7]} {ts[11:16]}"
            else:
                ts_formatted = ts
            ts_lbl = QLabel(ts_formatted)
            ts_lbl.setObjectName("card_time")
            ts_lbl.setStyleSheet(f"font-size: {_dp(8)}px;")
            ts_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lay.addWidget(ts_lbl)

        # Dot de estado (igual que en sesiones)
        dot = StatusDot()
        lay.addWidget(dot)

        # Badge de resultado (EXITOSO/FALLIDO) con el mismo estilo que "ACTIVA"
        resultado = intento.get("t_resultado_acceso", "")
        badge_text = "EXITOSO" if resultado == "exitoso" else "FALLIDO"
        badge = QLabel(badge_text)
        badge.setObjectName("badge_active")  # Mismo estilo que el badge de sesiones
        badge.setStyleSheet(
            f"font-size: {_dp(8)}px; padding: {_dp(3)}px {_dp(10)}px; "
            f"background: {'#e3f0ff' if resultado == 'exitoso' else '#ffe3e3'}; "
            f"color: {'#1565c0' if resultado == 'exitoso' else '#c62828'}; "
            f"border: 1px solid {'#90c4f0' if resultado == 'exitoso' else '#f0b0b0'};"
        )
        lay.addWidget(badge)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN PANEL
# ─────────────────────────────────────────────────────────────────────────────
class _AdminLogPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("admin_log_panel")
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        m = _dp(14)
        root.setContentsMargins(m, _dp(10), m, _dp(10))
        root.setSpacing(_dp(8))

        # ── Header row ────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(0)

        title_col = QVBoxLayout()
        title_col.setSpacing(_dp(2))
        t = QLabel("REGISTRO DE ACCESOS")
        t.setObjectName("section_title")
        t.setStyleSheet(f"font-size: {_dp(12)}px;")
        s = QLabel("ÚLTIMOS 50 INTENTOS")
        s.setObjectName("section_sub")
        s.setStyleSheet(f"font-size: {_dp(8)}px;")
        title_col.addWidget(t)
        title_col.addWidget(s)
        header_row.addLayout(title_col)
        header_row.addStretch()

        btn_ref = QPushButton("↺  ACTUALIZAR")
        btn_ref.setObjectName("btn_refresh")
        btn_ref.setStyleSheet(f"font-size: {_dp(8)}px; padding: {_dp(5)}px {_dp(16)}px;")
        btn_ref.setCursor(Qt.PointingHandCursor)
        btn_ref.clicked.connect(self.refresh)
        header_row.addWidget(btn_ref)
        root.addLayout(header_row)

        # ── Divisor ───────────────────────────────────────────────────────────
        div = QFrame()
        div.setObjectName("h_divider")
        root.addWidget(div)

        # ── Counter block ─────────────────────────────────────────────────────
        counter_block = QFrame()
        counter_block.setObjectName("counter_block")
        _shadow(counter_block, _dp(12), 15, _dp(2))

        cb_lay = QHBoxLayout(counter_block)
        cb_lay.setContentsMargins(_dp(14), _dp(8), _dp(14), _dp(8))
        cb_lay.setSpacing(_dp(8))

        self.counter_lbl = QLabel("0")
        self.counter_lbl.setObjectName("counter_num")
        self.counter_lbl.setStyleSheet(f"font-size: {_dp(28)}px;")
        cb_lay.addWidget(self.counter_lbl)

        key_lbl = QLabel("REGISTROS\nEN PANTALLA")
        key_lbl.setObjectName("counter_key")
        key_lbl.setStyleSheet(f"font-size: {_dp(7)}px;")
        cb_lay.addWidget(key_lbl)
        cb_lay.addStretch()

        # Dot de estado y texto (igual que en sesiones)
        dot2 = StatusDot()
        status_lbl = QLabel("MONITOREO ACTIVO")
        status_lbl.setObjectName("status_text")
        status_lbl.setStyleSheet(f"font-size: {_dp(8)}px;")
        cb_lay.addWidget(dot2)
        cb_lay.addWidget(status_lbl)
        root.addWidget(counter_block)

        # ── Scroll area ───────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.inner = QWidget()
        self.inner.setObjectName("admin_log_inner")
        self.il = QVBoxLayout(self.inner)
        self.il.setContentsMargins(0, _dp(4), _dp(4), 0)
        self.il.setSpacing(_dp(6))
        self.il.setAlignment(Qt.AlignTop)

        scroll.setWidget(self.inner)
        root.addWidget(scroll, 1)

        self.refresh()

    def paintEvent(self, event):
        p = QPainter(self)
        W, H = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0.0, QColor(232, 240, 251))
        g.setColorAt(1.0, QColor(214, 230, 248))
        p.fillRect(0, 0, W, H, QBrush(g))
        p.end()

    def refresh(self):
        for i in reversed(range(self.il.count())):
            item = self.il.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        intentos = db_get_intentos_recientes(50)
        self.counter_lbl.setText(str(len(intentos)))

        if not intentos:
            empty = QLabel("·  SIN REGISTROS DE ACCESO  ·")
            empty.setObjectName("empty_lbl")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"font-size: {_dp(9)}px;")
            empty.setContentsMargins(0, _dp(20), 0, _dp(20))
            self.il.addWidget(empty)
        else:
            for i, it in enumerate(intentos, start=1):
                self.il.addWidget(LogCard(it, i))