from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QScrollArea

from db.models.sesiones import db_get_all_sesiones_activas
from views.style.widgets.widgets import lbl

STYLE = """
QWidget#admin_sessions_panel, QWidget#admin_sessions_inner { background: #060d1a; color: #c8dff5; }
QLabel#body { color: #7ca8d0; font-size: 14px; font-family: 'Segoe UI',sans-serif; }
QLabel#small { color: #3a5f84; font-size: 11px; font-family: 'Courier New'; letter-spacing: 1px; }
QLabel#badge_green {
    background: #041a12; color: #3de8a0; border: 1px solid #1a7a50; border-radius: 14px;
    padding: 3px 12px; font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px;
}
QFrame#card { background: #0a1628; border: 1px solid #0f2035; border-radius: 16px; }
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

class _AdminSesionesPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("admin_sessions_panel")
        self.setStyleSheet(STYLE)
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(lbl("Sesiones activas (lockers en uso)", "body"))
        top.addStretch()
        btn_ref = QPushButton("Actualizar"); btn_ref.setObjectName("btn_sm")
        btn_ref.setCursor(Qt.PointingHandCursor); btn_ref.clicked.connect(self.refresh)
        top.addWidget(btn_ref)
        vl.addLayout(top)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.inner = QWidget(); self.inner.setObjectName("admin_sessions_inner")
        self.il = QVBoxLayout(self.inner)
        self.il.setContentsMargins(0, 0, 0, 0); self.il.setSpacing(8)
        scroll.setWidget(self.inner)
        vl.addWidget(scroll, 1)
        self.refresh()

    def refresh(self):
        for i in reversed(range(self.il.count())):
            item = self.il.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        sesiones = db_get_all_sesiones_activas()
        if not sesiones:
            self.il.addWidget(lbl("No hay sesiones activas.", "small"))
        else:
            for s in sesiones:
                row = QFrame(); row.setObjectName("card")
                rl  = QHBoxLayout(row); rl.setContentsMargins(20, 14, 20, 14); rl.setSpacing(16)

                id_lbl = QLabel("Sesion #{}".format(s["ID_sesion"]))
                id_lbl.setStyleSheet(
                    "color:#c8dff5; font-size:14px; font-weight:700; font-family:'Segoe UI';"
                )
                lk_lbl = lbl("Locker #{}".format(s["t_numero_locker"]), "body")
                ts_lbl = lbl(s.get("d_fecha_hora_entrada", ""), "small")
                badge  = lbl("ACTIVA", "badge_green")

                rl.addWidget(id_lbl); rl.addWidget(lk_lbl)
                rl.addWidget(ts_lbl); rl.addStretch(); rl.addWidget(badge)
                self.il.addWidget(row)
        self.il.addStretch()

