from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFrame, QScrollArea, QApplication,
    QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient

from db.models.intentos_acceso import db_get_intentos_recientes


def _dp(value: float) -> int:
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    return max(1, round(value * dpi / 96))


STYLE = """
QWidget#admin_log_panel, QWidget#admin_log_inner { background: transparent; }
QLabel#page_title { color: #ffffff; font-size: 24px; font-weight: 900; font-family: 'Montserrat',sans-serif; padding: 10px 24px; }
QFrame#log_card { background: #11223b; border: 1px solid #1e3a5a; border-radius: 16px; min-height: 70px; }
QLabel#log_timestamp { color: #a0c0e0; font-size: 13px; font-family: monospace; background: #0a1a2f; padding: 6px 12px; border-radius: 20px; }
QLabel#log_type_ok { background: #1a4a3a; color: #fff; font-size: 13px; font-weight: 600; padding: 4px 12px; border-radius: 16px; }
QLabel#log_type_fail { background: #4a2a3a; color: #fff; font-size: 13px; font-weight: 600; padding: 4px 12px; border-radius: 16px; }
QLabel#log_locker { color: #7aa9d9; font-size: 13px; background: #0a1a2f; padding: 4px 12px; border-radius: 20px; }
QLabel#log_success { color: #3de8a0; font-size: 12px; font-weight: 700; text-transform: uppercase; }
QLabel#log_fail { color: #f06a8a; font-size: 12px; font-weight: 700; text-transform: uppercase; }
QPushButton#btn_refresh { background: #1e3a5a; color: #fff; border: none; border-radius: 30px; padding: 10px 24px; font-size: 14px; font-weight: 600; }
QPushButton#btn_refresh:hover { background: #2b4a70; }
QScrollArea { border: none; }
QScrollBar:vertical { background: #0a1a2f; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #2b4a70; border-radius: 4px; }
"""

class _AdminLogPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("admin_log_panel")
        self.setStyleSheet(STYLE)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Título
        layout.addWidget(QLabel("REGISTRO DE ACCESOS", objectName="page_title"))

        # Header con botón
        header = QHBoxLayout()
        header.addStretch()
        btn = QPushButton("↻ ACTUALIZAR", objectName="btn_refresh")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.refresh)
        btn.setFixedWidth(150)
        header.addWidget(btn)
        layout.addLayout(header)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner_layout = QVBoxLayout(self.inner)
        self.inner_layout.setSpacing(10)
        self.inner_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.inner)
        layout.addWidget(scroll, 1)

        self.refresh()

    def paintEvent(self, event):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, QColor(10, 26, 47))
        g.setColorAt(1.0, QColor(17, 34, 59))
        p.fillRect(0, 0, self.width(), self.height(), QBrush(g))

    def refresh(self):
        # Limpiar
        for i in reversed(range(self.inner_layout.count())):
            self.inner_layout.itemAt(i).widget().deleteLater()

        for it in db_get_intentos_recientes(50):
            card = QFrame(objectName="log_card")
            row = QHBoxLayout(card)
            row.setContentsMargins(16, 12, 16, 12)
            
            # Timestamp
            ts = it.get("d_fecha_hora_acceso", "")[:16]
            row.addWidget(QLabel(f"🕒 {ts}", objectName="log_timestamp"))
            
            # Tipo
            tipo = it.get("t_tipo_intento", "").upper()
            tipo_lbl = QLabel(tipo)
            tipo_lbl.setObjectName("log_type_ok" if it.get("t_resultado_acceso")=="exitoso" else "log_type_fail")
            row.addWidget(tipo_lbl)
            
            # Locker
            locker = it.get("t_numero_locker")
            if locker:
                row.addWidget(QLabel(f"🔒 #{locker}", objectName="log_locker"))
            
            # Resultado
            res = it.get("t_resultado_acceso", "")
            res_lbl = QLabel("✓ ÉXITO" if res=="exitoso" else "✗ FALLO")
            res_lbl.setObjectName("log_success" if res=="exitoso" else "log_fail")
            row.addWidget(res_lbl)
            
            row.addStretch()
            self.inner_layout.addWidget(card)