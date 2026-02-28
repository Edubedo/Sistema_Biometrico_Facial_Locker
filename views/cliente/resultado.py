from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
     QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from views.style.widgets.widgets import lbl, sep_line
from db.models.lockers import db_get_all_lockers
from views.style.widgets.widgets import _step_bullet
import datetime
from utils.camera import CamThread
from utils.helpers import db_get_locker_num_by_id
import os 
from db.connection import connectionDB
from biometria.biometria import delete_face_data, train_model, face_dir_for
from db.models.intentos_acceso import db_log_intento
from db.models.lockers import db_set_locker_estado, db_next_free_locker
from db.models.sesiones import db_create_sesion, db_close_sesion, db_get_active_sesion_by_face

from views.style.widgets.widgets import CamWidget, AutoTimer, AUTO_HOME_SEC

class ResultPage(QWidget):
    go_home = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
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
