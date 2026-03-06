from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QScrollArea

from db.models.intentos_acceso import db_get_intentos_recientes
from views.style.widgets.widgets import lbl

STYLE = """
QWidget#admin_log_panel, QWidget#admin_log_inner { background: #060d1a; color: #c8dff5; }
QLabel#body { color: #7ca8d0; font-size: 14px; font-family: 'Segoe UI',sans-serif; }
QLabel#small { color: #3a5f84; font-size: 11px; font-family: 'Courier New'; letter-spacing: 1px; }
QLabel#log_ok { color: #3de8a0; font-size: 12px; font-family: 'Courier New'; }
QLabel#log_fail { color: #f03d5a; font-size: 12px; font-family: 'Courier New'; }
QFrame#card_log { background: #060d1a; border: 1px solid #0f2035; border-radius: 8px; }
QPushButton#btn_sm {
    background: #0a1628; color: #4d8ec4; border: 1px solid #1a3a5c; border-radius: 8px;
    padding: 8px 18px; font-size: 12px; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_sm:hover { color: #c8dff5; border-color: #4d8ec4; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #060d1a; width: 6px; margin: 0; }
QScrollBar::handle:vertical { background: #0f2035; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

class _AdminLogPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("admin_log_panel")
        self.setStyleSheet(STYLE)
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(lbl("Registro de accesos (ultimos 50)", "body"))
        top.addStretch()
        btn_ref = QPushButton("Actualizar"); btn_ref.setObjectName("btn_sm")
        btn_ref.setCursor(Qt.PointingHandCursor); btn_ref.clicked.connect(self.refresh)
        top.addWidget(btn_ref)
        vl.addLayout(top)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.inner = QWidget(); self.inner.setObjectName("admin_log_inner")
        self.il = QVBoxLayout(self.inner)
        self.il.setContentsMargins(0, 0, 0, 0); self.il.setSpacing(6)
        scroll.setWidget(self.inner)
        vl.addWidget(scroll, 1)
        self.refresh()

    def refresh(self):
        for i in reversed(range(self.il.count())):
            item = self.il.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        intentos = db_get_intentos_recientes(50)
        if not intentos:
            self.il.addWidget(lbl("Sin registros.", "small"))
        else:
            for it in intentos:
                row = QFrame(); row.setObjectName("card_log")
                rl  = QHBoxLayout(row); rl.setContentsMargins(16, 10, 16, 10); rl.setSpacing(12)

                # Color por resultado
                resultado = it.get("t_resultado_acceso", "")
                lbl_obj   = "log_ok" if resultado == "exitoso" else "log_fail"

                ts   = lbl(it.get("d_fecha_hora_acceso", "")[:16], "small")
                tipo = lbl(it.get("t_tipo_intento", ""), lbl_obj)
                lk   = lbl("L#{}".format(it.get("t_numero_locker") or "-"), "small")
                res  = lbl(resultado, lbl_obj)
                desc = lbl((it.get("t_descripcion_acceso") or "")[:40], "small")

                rl.addWidget(ts); rl.addWidget(tipo); rl.addWidget(lk)
                rl.addWidget(res); rl.addStretch(); rl.addWidget(desc)
                self.il.addWidget(row)
        self.il.addStretch()

