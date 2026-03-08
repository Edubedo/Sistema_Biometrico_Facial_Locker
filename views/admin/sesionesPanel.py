from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy,
    QApplication, QGraphicsDropShadowEffect
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

/* ===== TÍTULOS ===== */
QLabel#page_title {
    color: #ffffff;
    font-size: 24px;
    font-weight: 900;
    font-family: 'Montserrat', 'Segoe UI', sans-serif;
    letter-spacing: 2px;
    padding: 10px 24px 0 24px;
}

QLabel#section_title {
    color: #ffffff;
    font-size: 18px;
    font-weight: 800;
    font-family: 'Montserrat', 'Segoe UI', sans-serif;
    letter-spacing: 1px;
}

QLabel#section_sub {
    color: #7aa9d9;
    font-size: 14px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 500;
}

/* ===== TARJETA DE SESIÓN ===== */
QFrame#session_card {
    background: #11223b;
    border: 1px solid #1e3a5a;
    border-radius: 16px;
    min-height: 100px;
}

QLabel#session_id {
    color: #ffffff;
    font-size: 16px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#session_locker {
    color: #7aa9d9;
    font-size: 14px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
}

QLabel#session_time {
    color: #a0c0e0;
    font-size: 13px;
    font-family: 'Roboto Mono', 'Courier New', monospace;
    background: #0a1a2f;
    padding: 6px 12px;
    border-radius: 20px;
}

QLabel#badge_active {
    background: #1a4a3a;
    color: #ffffff;
    border: none;
    border-radius: 20px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}

/* ===== TARJETA DE CONTADOR ===== */
QFrame#stats_card {
    background: #11223b;
    border: 1px solid #1e3a5a;
    border-radius: 20px;
    min-height: 100px;
    /* QUITAR SOMBRA si no quieres sombra */
    /* Si quieres mantenerla, reduce el alpha */
}

QLabel#stats_number {
    color: #ffffff;
    font-size: 42px;
    font-weight: 900;
    font-family: 'Montserrat', 'Segoe UI', sans-serif;
}

QLabel#stats_label {
    color: #7aa9d9;
    font-size: 16px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 0.5px;
    padding: 4px 0;  /* Añadido padding vertical */
}

QLabel#status_dot {
    color: #3de8a0;
    font-size: 24px;
}

QLabel#status_text {
    color: #a0c0e0;
    font-size: 14px;
    font-weight: 500;
    font-family: 'Segoe UI', sans-serif;
    padding: 4px 0;  /* Añadido padding vertical */
}

/* ===== BOTÓN ACTUALIZAR ===== */
QPushButton#btn_refresh {
    background: #1e3a5a;
    color: #ffffff;
    border: none;
    border-radius: 30px;
    padding: 12px 28px;  /* Aumentado padding */
    font-size: 13px;
    font-weight: 600;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
}

QPushButton#btn_refresh:hover {
    background: #2b4a70;
}

QPushButton#btn_refresh:pressed {
    background: #0f2a44;
}

/* ===== DIVISOR ===== */
QFrame#h_divider {
    background: #1e3a5a;
    min-height: 2px;
    max-height: 2px;
    margin: 16px 0;  /* Aumentado margen */
}

/* ===== MENSAJE VACÍO ===== */
QLabel#empty_message {
    color: #5f7fa0;
    font-size: 16px;
    font-style: italic;
    font-family: 'Segoe UI', sans-serif;
    padding: 60px 0;
}

/* ===== SCROLLBAR ===== */
QScrollArea { 
    border: none; 
    background: transparent; 
}
QScrollBar:vertical { 
    background: #0a1a2f; 
    width: 8px; 
    margin: 0; 
    border-radius: 4px;
}
QScrollBar::handle:vertical { 
    background: #2b4a70; 
    border-radius: 4px; 
    min-height: 30px; 
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { 
    height: 0; 
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION CARD - REDISEÑADA
# ─────────────────────────────────────────────────────────────────────────────
class SessionCard(QFrame):
    def __init__(self, sesion: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("session_card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Sombra más sutil o quitarla si molesta
        _shadow(self, blur=12, alpha=10, dy=1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(15)

        # Columna izquierda: ícono de candado
        locker_icon = QLabel("🔒")
        locker_icon.setStyleSheet("font-size: 28px; padding: 0;")
        layout.addWidget(locker_icon)

        # Línea vertical divisoria
        v_line = QFrame()
        v_line.setFrameShape(QFrame.VLine)
        v_line.setStyleSheet("background: #1e3a5a; min-width: 1px; max-width: 1px;")
        layout.addWidget(v_line)

        # Columna central: información de la sesión
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        # ID de sesión
        session_id = QLabel(f"SESIÓN #{sesion['ID_sesion']}")
        session_id.setObjectName("session_id")
        info_layout.addWidget(session_id)

        # Número de locker
        locker_num = QLabel(f"Locker #{sesion['t_numero_locker']}")
        locker_num.setObjectName("session_locker")
        info_layout.addWidget(locker_num)

        layout.addLayout(info_layout, 1)

        # Columna derecha: fecha/hora y badge
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Fecha y hora
        ts = sesion.get("d_fecha_hora_entrada", "")
        if ts:
            time_str = str(ts).replace("T", "  ")[:19]
            time_lbl = QLabel(f"⏱️ {time_str}")
            time_lbl.setObjectName("session_time")
            right_layout.addWidget(time_lbl)

        # Badge ACTIVA
        badge = QLabel("● ACTIVA")
        badge.setObjectName("badge_active")
        badge.setAlignment(Qt.AlignRight)
        right_layout.addWidget(badge)

        layout.addLayout(right_layout)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN PANEL - REDISEÑADO
# ─────────────────────────────────────────────────────────────────────────────
class _AdminSesionesPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("admin_sessions_panel")
        self.setStyleSheet(STYLE)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # ── TÍTULO DE LA PÁGINA ────────────────────────────────────────────
        title = QLabel("SESIONES ACTIVAS")
        title.setObjectName("page_title")
        main_layout.addWidget(title)

        # ── HEADER CON CONTADOR Y BOTÓN ────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Tarjeta de estadísticas - SIN SOMBRA para evitar el fondo extraño
        stats_card = QFrame()
        stats_card.setObjectName("stats_card")
        # _shadow(stats_card, blur=20, alpha=15, dy=3)  # COMENTADO para quitar sombra

        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(24, 20, 24, 20)  # Aumentado padding vertical
        stats_layout.setSpacing(15)

        # Número de sesiones activas
        self.sessions_count = QLabel("0")
        self.sessions_count.setObjectName("stats_number")
        stats_layout.addWidget(self.sessions_count)

        # Texto explicativo con padding mejorado
        stats_text = QLabel("sesiones activas\nen este momento")
        stats_text.setObjectName("stats_label")
        stats_text.setWordWrap(True)
        stats_layout.addWidget(stats_text)

        stats_layout.addStretch()

        # Indicador de estado
        status_dot = QLabel("●")
        status_dot.setObjectName("status_dot")
        stats_layout.addWidget(status_dot)

        status_text = QLabel("Sistema operativo")
        status_text.setObjectName("status_text")
        stats_layout.addWidget(status_text)

        header_layout.addWidget(stats_card, 1)

        # Botón actualizar
        self.refresh_btn = QPushButton("↻ ACTUALIZAR")
        self.refresh_btn.setObjectName("btn_refresh")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        self.refresh_btn.setFixedWidth(160)
        header_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(header_layout)

        # ── DIVISOR ────────────────────────────────────────────────────────
        divider = QFrame()
        divider.setObjectName("h_divider")
        main_layout.addWidget(divider)

        # ── LISTA DE SESIONES ──────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.inner = QWidget()
        self.inner.setObjectName("admin_sessions_inner")
        self.inner_layout = QVBoxLayout(self.inner)
        self.inner_layout.setContentsMargins(0, 8, 8, 0)  # Aumentado margen superior
        self.inner_layout.setSpacing(12)
        self.inner_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(self.inner)
        main_layout.addWidget(scroll, 1)

        # Cargar datos iniciales
        self.refresh()

    def paintEvent(self, event):
        p = QPainter(self)
        W, H = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0.0, QColor(10, 26, 47))
        g.setColorAt(0.5, QColor(15, 34, 59))
        g.setColorAt(1.0, QColor(17, 34, 59))
        p.fillRect(0, 0, W, H, QBrush(g))
        p.end()

    def refresh(self):
        # Limpiar layout actual
        for i in reversed(range(self.inner_layout.count())):
            item = self.inner_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        # Obtener sesiones activas
        sesiones = db_get_all_sesiones_activas()

        # Actualizar contador
        self.sessions_count.setText(str(len(sesiones)))

        if not sesiones:
            # Mensaje cuando no hay sesiones activas
            empty_msg = QLabel("⚡ No hay sesiones activas en este momento")
            empty_msg.setObjectName("empty_message")
            empty_msg.setAlignment(Qt.AlignCenter)
            self.inner_layout.addWidget(empty_msg)
        else:
            # Crear una tarjeta por cada sesión
            for sesion in sesiones:
                card = SessionCard(sesion)
                self.inner_layout.addWidget(card)