from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy
)
from PyQt5.QtGui import QFont, QPainter, QColor, QPen, QBrush

from db.models.lockers import db_get_all_lockers
from views.style.widgets.widgets import lbl, sep_line


STYLE = """
/* ── Fondo general ── */
QWidget#home_page {
    background: #8fafc8;
}

/* ── Tarjeta central ── */
QFrame#main_card {
    background: #b8ccdc;
    border: 3px solid #2a6db5;
    border-radius: 18px;
}

/* ── Encabezado de tarjeta ── */
QLabel#card_title {
    color: #0d1f3c;
    font-size: 22px;
    font-weight: 900;
    font-family: 'Segoe UI', 'Trebuchet MS', sans-serif;
    letter-spacing: 3px;
    text-decoration: underline;
}

/* ── Subtítulo lockers libres ── */
QLabel#lockers_label {
    color: #0d1f3c;
    font-size: 15px;
    font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
}

/* ── Número grande de lockers ── */
QLabel#lockers_count {
    color: #1a5fc8;
    font-size: 42px;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
}

/* ── Botón circular GUARDAR ── */
QPushButton#btn_guardar {
    background: #d4a96a;
    color: #3d1f00;
    border: 3px solid #1a1a1a;
    border-radius: 60px;
    font-size: 11px;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
    min-width:  120px;
    max-width:  120px;
    min-height: 120px;
    max-height: 120px;
}
QPushButton#btn_guardar:hover {
    background: #e8c080;
    border-color: #2a6db5;
}
QPushButton#btn_guardar:pressed {
    background: #b8904a;
}

/* ── Botón circular RECOGER ── */
QPushButton#btn_recoger {
    background: #d4a96a;
    color: #3d1f00;
    border: 3px solid #1a1a1a;
    border-radius: 60px;
    font-size: 11px;
    font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
    min-width:  120px;
    max-width:  120px;
    min-height: 120px;
    max-height: 120px;
}
QPushButton#btn_recoger:hover {
    background: #e8c080;
    border-color: #2a6db5;
}
QPushButton#btn_recoger:pressed {
    background: #b8904a;
}

/* ── Botón admin discreto ── */
QPushButton#btn_admin {
    background: transparent;
    color: #5a7a9a;
    border: 1px solid #7a9ab8;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 10px;
    font-family: 'Courier New';
    letter-spacing: 2px;
}
QPushButton#btn_admin:hover {
    color: #0d1f3c;
    border-color: #2a6db5;
    background: #9fbdd4;
}

/* ── Ícono ilustración ── */
QLabel#icon_label {
    color: #2a6db5;
    font-size: 72px;
    font-family: 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif;
}

/* ── Info stats pequeños ── */
QLabel#stat_small {
    color: #2a4a6a;
    font-size: 11px;
    font-family: 'Courier New';
    letter-spacing: 1px;
}
"""


class HomePage(QWidget):
    go_guardar = pyqtSignal()
    go_retirar = pyqtSignal()
    go_admin   = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("home_page")
        self.setStyleSheet(STYLE)

        # ── Layout raíz ─────────────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setAlignment(Qt.AlignCenter)

        # ── Tarjeta central ──────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("main_card")
        card.setFixedWidth(340)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 28)
        card_layout.setSpacing(0)
        card_layout.setAlignment(Qt.AlignCenter)

        # Título ACCESO
        title = QLabel("ACCESO")
        title.setObjectName("card_title")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)
        card_layout.addSpacing(16)

        # Ilustración (emoji como placeholder visual)
        icon = QLabel("🔒🛡️")
        icon.setObjectName("icon_label")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            "color: #2a6db5; font-size: 64px;"
            "font-family: 'Segoe UI Emoji', sans-serif;"
        )
        card_layout.addWidget(icon)
        card_layout.addSpacing(18)

        # Texto LOCKERS LIBRES
        lbl_lockers = QLabel("LOCKERS LIBRES")
        lbl_lockers.setObjectName("lockers_label")
        lbl_lockers.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_lockers)
        card_layout.addSpacing(2)

        # Número grande
        self.count_lbl = QLabel("—")
        self.count_lbl.setObjectName("lockers_count")
        self.count_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.count_lbl)
        card_layout.addSpacing(22)

        # ── Fila de botones circulares ───────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(32)
        btn_row.setAlignment(Qt.AlignCenter)

        # Botón GUARDAR
        col_g = QVBoxLayout()
        col_g.setSpacing(6)
        col_g.setAlignment(Qt.AlignCenter)
        self.btn_guardar = QPushButton("🔐\nGUARDAR")
        self.btn_guardar.setObjectName("btn_guardar")
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.clicked.connect(self.go_guardar.emit)
        col_g.addWidget(self.btn_guardar)
        btn_row.addLayout(col_g)

        # Botón RECOGER
        col_r = QVBoxLayout()
        col_r.setSpacing(6)
        col_r.setAlignment(Qt.AlignCenter)
        self.btn_recoger = QPushButton("🚪\nRECOGER")
        self.btn_recoger.setObjectName("btn_recoger")
        self.btn_recoger.setCursor(Qt.PointingHandCursor)
        self.btn_recoger.clicked.connect(self.go_retirar.emit)
        col_r.addWidget(self.btn_recoger)
        btn_row.addLayout(col_r)

        card_layout.addLayout(btn_row)
        card_layout.addSpacing(16)

        # Stats pequeños debajo de los botones
        self.stat_lbl = QLabel("")
        self.stat_lbl.setObjectName("stat_small")
        self.stat_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.stat_lbl)

        root.addWidget(card, alignment=Qt.AlignCenter)
        root.addSpacing(18)

        # ── Botón admin discreto (fuera de la tarjeta) ───────────────────────
        adm = QPushButton("ADMINISTRACION")
        adm.setObjectName("btn_admin")
        adm.setCursor(Qt.PointingHandCursor)
        adm.clicked.connect(self.go_admin.emit)
        root.addWidget(adm, alignment=Qt.AlignCenter)

    def refresh(self):
        """Actualiza las estadísticas desde la base de datos."""
        lockers = db_get_all_lockers()
        total   = len(lockers)
        free    = sum(1 for l in lockers if l["t_estado"] == "libre")
        busy    = total - free

        self.count_lbl.setText(str(free))
        self.stat_lbl.setText(
            "Ocupados: {}   |   Total: {}".format(busy, total)
        )