from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy,
    QApplication, QGraphicsDropShadowEffect, QTableWidget, QTableWidgetItem
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QFont

from db.models.sesiones import db_get_all_sesiones_activas
from views.style.widgets.widgets import lbl


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


STYLE = """
QWidget#admin_sessions_panel,
QWidget#admin_sessions_inner {
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

/* ── Real table ───────────────────────────────────────────────────────── */
QTableWidget#admin_sessions_tbl {
    background: #ffffff;
    border: 1px solid #cfd8e3;
    border-radius: 10px;
    gridline-color: #e3f0ff;
}
QHeaderView::section {
    background: #e3f0ff;
    color: #1565c0;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
    padding: 8px 10px;
    border: none;
}
QTableWidget::item {
    padding: 8px 10px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
    color: #1a2a3a;
}
QTableWidget::item:selected { background: #bbdefb; }
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
#  SESSION CARD
# ─────────────────────────────────────────────────────────────────────────────
class SessionCard(QFrame):
    def __init__(self, sesion: dict, index: int, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        _shadow(self, _dp(10), 15, _dp(2))

        lay = QHBoxLayout(self)
        lay.setContentsMargins(_dp(14), _dp(10), _dp(14), _dp(10))
        lay.setSpacing(_dp(14))

        idx_lbl = QLabel(f"{index:02d}")
        idx_lbl.setStyleSheet(
            f"color: #bbdefb; font-size: {_dp(16)}px; font-weight: 900;"
            f"font-family: 'Segoe UI'; min-width: {_dp(26)}px;"
        )
        idx_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(idx_lbl)

        div = QFrame(); div.setFrameShape(QFrame.VLine)
        div.setStyleSheet(
            f"background: #e3f0ff; border: none;"
            f"min-width: {_dp(1)}px; max-width: {_dp(1)}px;"
        )
        lay.addWidget(div)

        info_col = QVBoxLayout(); info_col.setSpacing(_dp(2))
        id_lbl = QLabel(f"SESIÓN  #{sesion['ID_sesion']}")
        id_lbl.setObjectName("card_id")
        id_lbl.setStyleSheet(f"font-size: {_dp(12)}px;")
        locker_lbl = QLabel(f"LOCKER  ·  #{sesion['t_numero_locker']}")
        locker_lbl.setObjectName("card_locker")
        locker_lbl.setStyleSheet(f"font-size: {_dp(9)}px;")
        info_col.addWidget(id_lbl); info_col.addWidget(locker_lbl)
        lay.addLayout(info_col)
        lay.addStretch()

        ts = sesion.get("d_fecha_hora_entrada", "")
        if ts:
            ts_lbl = QLabel(str(ts).replace("T", "  "))
            ts_lbl.setObjectName("card_time")
            ts_lbl.setStyleSheet(f"font-size: {_dp(8)}px;")
            ts_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lay.addWidget(ts_lbl)

        dot = StatusDot(); lay.addWidget(dot)

        badge = QLabel("ACTIVA"); badge.setObjectName("badge_active")
        badge.setStyleSheet(f"font-size: {_dp(8)}px; padding: {_dp(3)}px {_dp(10)}px;")
        lay.addWidget(badge)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN PANEL
# ─────────────────────────────────────────────────────────────────────────────
class _AdminSesionesPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("admin_sessions_panel")
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        m = _dp(14)
        root.setContentsMargins(m, _dp(10), m, _dp(10))
        root.setSpacing(_dp(8))                          # ← spacing reducido

        # ── Header row ────────────────────────────────────────────────────────
        header_row = QHBoxLayout(); header_row.setSpacing(0)

        title_col = QVBoxLayout(); title_col.setSpacing(_dp(2))
        t = QLabel("SESIONES ACTIVAS"); t.setObjectName("section_title")
        t.setStyleSheet(f"font-size: {_dp(12)}px;")
        s = QLabel("LOCKERS ACTUALMENTE EN USO"); s.setObjectName("section_sub")
        s.setStyleSheet(f"font-size: {_dp(8)}px;")
        title_col.addWidget(t); title_col.addWidget(s)
        header_row.addLayout(title_col); header_row.addStretch()

        btn_ref = QPushButton("↺  ACTUALIZAR"); btn_ref.setObjectName("btn_refresh")
        btn_ref.setStyleSheet(
            btn_ref.styleSheet() +
            f"font-size: {_dp(10)}px; padding: {_dp(7)}px {_dp(20)}px;"
        )
        btn_ref.setCursor(Qt.PointingHandCursor)
        btn_ref.clicked.connect(self.refresh)
        header_row.addWidget(btn_ref)
        root.addLayout(header_row)

        div = QFrame(); div.setObjectName("h_divider"); root.addWidget(div)

        # ── Counter block — más compacto ──────────────────────────────────────
        counter_block = QFrame(); counter_block.setObjectName("counter_block")
        _shadow(counter_block, _dp(12), 15, _dp(2))
        cb_lay = QHBoxLayout(counter_block)
        cb_lay.setContentsMargins(_dp(14), _dp(8), _dp(14), _dp(8))  # ← menos padding
        cb_lay.setSpacing(_dp(8))

        self.counter_lbl = QLabel("0"); self.counter_lbl.setObjectName("counter_num")
        self.counter_lbl.setStyleSheet(f"font-size: {_dp(28)}px;")   # ← número más pequeño
        cb_lay.addWidget(self.counter_lbl)

        key_lbl = QLabel("SESIONES\nEN CURSO"); key_lbl.setObjectName("counter_key")
        key_lbl.setStyleSheet(f"font-size: {_dp(7)}px;")
        cb_lay.addWidget(key_lbl); cb_lay.addStretch()

        dot2 = StatusDot()
        status_lbl = QLabel("SISTEMA OPERATIVO"); status_lbl.setObjectName("status_text")
        status_lbl.setStyleSheet(f"font-size: {_dp(8)}px;")
        cb_lay.addWidget(dot2); cb_lay.addWidget(status_lbl)
        root.addWidget(counter_block)

        # ── Tabla ─────────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setObjectName("admin_sessions_tbl")
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "LOCKER", "FECHA/HORA", "ESTADO"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setMinimumSectionSize(_dp(90))
        root.addWidget(self.table, 1)

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
        sesiones = db_get_all_sesiones_activas()
        self.counter_lbl.setText(str(len(sesiones)))

        self.table.setRowCount(0)

        if not sesiones:
            self.table.setRowCount(1)
            itm = QTableWidgetItem("SIN SESIONES ACTIVAS")
            itm.setTextAlignment(Qt.AlignCenter)
            itm.setFlags(itm.flags() & ~Qt.ItemIsSelectable)
            self.table.setItem(0, 0, itm)
            # Unir visualmente sobre todo el ancho
            self.table.setSpan(0, 0, 1, 4)
            return

        self.table.setRowCount(len(sesiones))
        for r, s in enumerate(sesiones):
            id_sesion = s.get("ID_sesion", "")
            locker = s.get("t_numero_locker", "") or ""
            ts = s.get("d_fecha_hora_entrada", "") or ""
            ts_text = str(ts).replace("T", "  ")

            id_item = QTableWidgetItem(f"SESIÓN #{id_sesion}")
            id_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 0, id_item)

            locker_item = QTableWidgetItem(str(locker))
            locker_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 1, locker_item)

            ts_item = QTableWidgetItem(ts_text)
            ts_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(r, 2, ts_item)

            estado_item = QTableWidgetItem("ACTIVA")
            estado_item.setTextAlignment(Qt.AlignCenter)
            # Badge-like background
            estado_item.setBackground(QColor("#e3f0ff"))
            estado_item.setForeground(QColor("#1565c0"))
            estado_item.setFlags(estado_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, 3, estado_item)
