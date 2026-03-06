from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame

from views.style.widgets.widgets import AutoTimer, AUTO_HOME_SEC

STYLE = """
QWidget#result_page { background: #060d1a; color: #c8dff5; }
QLabel#body { color: #7ca8d0; font-size: 14px; font-family: 'Segoe UI',sans-serif; }
QLabel#small { color: #3a5f84; font-size: 11px; font-family: 'Courier New'; letter-spacing: 1px; }
QFrame#card_green { background: #041a12; border: 1px solid #1a7a50; border-radius: 16px; }
QFrame#card_yellow { background: #1a1204; border: 1px solid #7a5a1a; border-radius: 16px; }
QFrame#card_red { background: #1a0409; border: 1px solid #7a1a2a; border-radius: 16px; }
QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a6ef5, stop:1 #0f4fd4);
    color: #fff; border: none; border-radius: 12px; padding: 16px 36px;
    font-size: 15px; font-weight: 800; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_blue:hover { background: #2b7cff; }
QPushButton#btn_sm {
    background: #0a1628; color: #4d8ec4; border: 1px solid #1a3a5c; border-radius: 8px;
    padding: 10px 24px; font-size: 12px; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_sm:hover { color: #c8dff5; border-color: #4d8ec4; }
"""

class ResultPage(QWidget):
    go_home = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("result_page")
        self.setStyleSheet(STYLE)
        self._vl  = QVBoxLayout(self)
        self._vl.setContentsMargins(80, 80, 80, 80)
        self._vl.setAlignment(Qt.AlignCenter)
        self._card    = None
        self._timer_w = AutoTimer(AUTO_HOME_SEC)
        self._timer_w.timeout.connect(self.go_home.emit)

    def show_result(self, kind, title, subtitle, detail=""):
        """
        kind: 'ok' | 'warn' | 'err'
        """
        if self._card:
            self._vl.removeWidget(self._card)
            self._card.deleteLater()
        if self._vl.indexOf(self._timer_w) >= 0:
            self._vl.removeWidget(self._timer_w)

        frame_map = {"ok": "card_green", "warn": "card_yellow", "err": "card_red"}
        color_map  = {"ok": "#3de8a0",    "warn": "#f0b429",     "err": "#f03d5a"}
        icon_map   = {"ok": "[  OK  ]",   "warn": "[ ! ]",       "err": "[ X ]"}

        fn    = frame_map.get(kind, "card")
        color = color_map.get(kind, "#c8dff5")
        icon  = icon_map.get(kind, "[ ? ]")

        card = QFrame(); card.setObjectName(fn)
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(70, 60, 70, 60); cl.setSpacing(24)
        cl.setAlignment(Qt.AlignCenter)

        i_lbl = QLabel(icon); i_lbl.setAlignment(Qt.AlignCenter)
        i_lbl.setStyleSheet(
            "font-size:42px; color:{}; font-family:'Courier New'; font-weight:900;".format(color)
        )
        t_lbl = QLabel(title); t_lbl.setAlignment(Qt.AlignCenter)
        t_lbl.setStyleSheet(
            "font-size:30px; font-weight:900; color:{};"
            "font-family:'Segoe UI'; letter-spacing:-1px;".format(color)
        )
        s_lbl = QLabel(subtitle); s_lbl.setAlignment(Qt.AlignCenter)
        s_lbl.setObjectName("body"); s_lbl.setWordWrap(True)

        cl.addWidget(i_lbl); cl.addWidget(t_lbl); cl.addWidget(s_lbl)

        if detail:
            d_lbl = QLabel(detail); d_lbl.setAlignment(Qt.AlignCenter)
            d_lbl.setStyleSheet(
                "font-size:38px; font-weight:900; color:{}; font-family:'Courier New';".format(color)
            )
            cl.addWidget(d_lbl)

        btn = QPushButton("VOLVER AL INICIO")
        btn.setObjectName("btn_blue" if kind == "ok" else "btn_sm")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self._manual_home)
        cl.addSpacing(10)
        cl.addWidget(btn, alignment=Qt.AlignCenter)

        self._card = card
        self._vl.addWidget(card)
        self._vl.addSpacing(16)
        self._vl.addWidget(self._timer_w, alignment=Qt.AlignCenter)
        self._timer_w.start()

    def _manual_home(self):
        self._timer_w.stop()
        self.go_home.emit()
