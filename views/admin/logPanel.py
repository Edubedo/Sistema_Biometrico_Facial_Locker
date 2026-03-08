from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QApplication, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QFont

from db.models.intentos_acceso import db_get_intentos_recientes


def _dp(value: float) -> int:
    screen = QApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else 96
    return max(1, round(value * dpi / 96))


def _shadow(widget, blur=10, alpha=30, offset=2):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur)
    shadow.setColor(QColor(0, 0, 0, alpha))
    shadow.setOffset(0, offset)
    widget.setGraphicsEffect(shadow)


class _AdminLogPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("admin_log_panel")
        self.setStyleSheet("""
            QWidget#admin_log_panel, QWidget#admin_log_inner {
                background: transparent;
            }
            
            /* ===== TÍTULO ===== */
            QLabel#page_title {
                color: #0a1a2f;
                font-size: 24px;
                font-weight: 900;
                font-family: 'Montserrat', 'Segoe UI', sans-serif;
                letter-spacing: 2px;
                padding: 10px 24px 0 24px;
                background: transparent;
            }
            
            /* ===== TARJETA DE REGISTRO ===== */
            QFrame#log_card {
                background: #ffffff;
                border: none;
                border-radius: 18px;
                min-height: 90px;
            }
            
            QLabel#log_timestamp {
                color: #0a1a2f;
                font-size: 15px;
                font-family: 'Roboto Mono', 'Courier New', monospace;
                font-weight: 600;
                background: #f0f7ff;
                padding: 6px 14px;
                border-radius: 20px;
                min-width: 110px;
            }
            
            QLabel#log_type {
                color: #0a1a2f;
                font-size: 15px;
                font-weight: 700;
                font-family: 'Segoe UI', sans-serif;
                background: #f5f5f5;
                padding: 6px 16px;
                border-radius: 20px;
                min-width: 170px;
            }
            
            QLabel#log_locker {
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
                background: #2b6eb0;
                padding: 6px 14px;
                border-radius: 25px;
                min-width: 50px;
                text-align: center;
            }
            
            QLabel#log_success {
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
                background: #1a7a50;
                padding: 6px 16px;
                border-radius: 25px;
                min-width: 80px;
                text-align: center;
            }
            
            QLabel#log_fail {
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
                background: #c05a5a;
                padding: 6px 16px;
                border-radius: 25px;
                min-width: 80px;
                text-align: center;
            }
            
            QLabel#log_description {
                color: #5f7fa0;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
                font-style: italic;
                margin-top: 8px;
                padding-left: 8px;
            }
            
            /* ===== BOTÓN ACTUALIZAR ===== */
            QPushButton#btn_refresh {
                background: #ffffff;
                color: #0a1a2f;
                border: none;
                border-radius: 30px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton#btn_refresh:hover {
                background: #f0f7ff;
            }
            QPushButton#btn_refresh:pressed {
                background: #e0ecff;
            }
            
            /* ===== DIVISOR ===== */
            QFrame#h_divider {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #d0e4ff, stop:0.5 #b0c8ff, stop:1 #d0e4ff);
                min-height: 2px;
                max-height: 2px;
                margin: 16px 0;
            }
            
            /* ===== SCROLLBAR ===== */
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #f0f5ff;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #b8d6ff;
                border-radius: 4px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: #7aa9d9;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header con título y botón
        header = QHBoxLayout()
        
        # Título
        title = QLabel("REGISTRO DE ACCESOS")
        title.setObjectName("page_title")
        header.addWidget(title)
        
        header.addStretch()
        
        # Botón actualizar con sombra
        self.btn_refresh = QPushButton("↻ ACTUALIZAR")
        self.btn_refresh.setObjectName("btn_refresh")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_refresh.setFixedWidth(140)
        _shadow(self.btn_refresh, blur=8, alpha=20, offset=2)
        header.addWidget(self.btn_refresh)

        main_layout.addLayout(header)

        # Divisor
        div = QFrame()
        div.setObjectName("h_divider")
        main_layout.addWidget(div)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.inner = QWidget()
        self.inner.setObjectName("admin_log_inner")
        self.inner_layout = QVBoxLayout(self.inner)
        self.inner_layout.setContentsMargins(8, 8, 8, 8)
        self.inner_layout.setSpacing(16)
        self.inner_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(self.inner)
        main_layout.addWidget(scroll, 1)

        self.refresh()

    def paintEvent(self, event):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, QColor(248, 250, 255))
        g.setColorAt(0.5, QColor(240, 245, 255))
        g.setColorAt(1.0, QColor(235, 240, 255))
        p.fillRect(0, 0, self.width(), self.height(), QBrush(g))

    def refresh(self):
        # Limpiar
        for i in reversed(range(self.inner_layout.count())):
            item = self.inner_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        intentos = db_get_intentos_recientes(50)

        if not intentos:
            empty = QLabel("No hay registros de acceso")
            empty.setStyleSheet("color: #7aa9d9; font-size: 16px; font-style: italic; padding: 60px 0;")
            empty.setAlignment(Qt.AlignCenter)
            self.inner_layout.addWidget(empty)
            return

        for it in intentos:
            # Tarjeta de registro con sombra principal
            card = QFrame()
            card.setObjectName("log_card")
            _shadow(card, blur=12, alpha=25, offset=3)

            layout = QVBoxLayout(card)
            layout.setContentsMargins(18, 14, 18, 14)
            layout.setSpacing(8)

            # Primera fila: timestamp, tipo, locker, resultado
            row1 = QHBoxLayout()
            row1.setSpacing(12)

            # Timestamp con sombra
            ts = it.get("d_fecha_hora_acceso", "")
            if ts:
                if len(ts) >= 16:
                    ts_formatted = f"{ts[8:10]}/{ts[5:7]} {ts[11:16]}"
                else:
                    ts_formatted = ts
                ts_lbl = QLabel(ts_formatted)
                ts_lbl.setObjectName("log_timestamp")
                _shadow(ts_lbl, blur=5, alpha=15, offset=1)
                row1.addWidget(ts_lbl)

            # Tipo con sombra
            tipo = it.get("t_tipo_intento", "").upper()
            tipo_lbl = QLabel(tipo)
            tipo_lbl.setObjectName("log_type")
            _shadow(tipo_lbl, blur=5, alpha=15, offset=1)
            row1.addWidget(tipo_lbl)

            # Locker con sombra
            locker = it.get("t_numero_locker")
            if locker:
                locker_lbl = QLabel(f"#{locker}")
                locker_lbl.setObjectName("log_locker")
                _shadow(locker_lbl, blur=6, alpha=25, offset=1)
                row1.addWidget(locker_lbl)

            # Resultado con sombra
            resultado = it.get("t_resultado_acceso", "")
            res_lbl = QLabel("✔ ÉXITO" if resultado == "exitoso" else "✗ FALLO")
            res_lbl.setObjectName("log_success" if resultado == "exitoso" else "log_fail")
            _shadow(res_lbl, blur=6, alpha=25, offset=1)
            row1.addWidget(res_lbl)

            row1.addStretch()
            layout.addLayout(row1)

            # Segunda fila: descripción
            desc = it.get("t_descripcion_acceso", "")
            if desc:
                desc_lbl = QLabel(desc[:60] + ("..." if len(desc) > 60 else ""))
                desc_lbl.setObjectName("log_description")
                layout.addWidget(desc_lbl)

            self.inner_layout.addWidget(card)