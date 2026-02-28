import sys
import os
import cv2
import json
import datetime
import importlib.util
import site
import shutil
import sqlite3
import pathlib
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFrame, QStackedWidget,
    QSizePolicy, QSpacerItem, QScrollArea, QGridLayout,
    QMessageBox, QInputDialog, QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage
# Importaciones
from db.connection import connectionDB
from utils.helpers import  hash_password, db_get_locker_num_by_id
from views.style.widgets.widgets import _step_bullet, lbl, sep_line, CamWidget, AutoTimer

from db.models.usuarios import *
from db.models.intentos_acceso import *

from db.models.lockers import *
from db.models.sesiones import *
from db.models.usuarios import *
from db.models.intentos_acceso import *
from biometria.biometria import *

class _AdminSesionesPanel(QWidget):
    def __init__(self):
        super().__init__()
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(lbl("Sesiones activas (lockers en uso)", "body"))
        top.addStretch()
        btn_ref = QPushButton("Actualizar"); btn_ref.setObjectName("btn_sm")
        btn_ref.setCursor(Qt.PointingHandCursor); btn_ref.clicked.connect(self.refresh)
        top.addWidget(btn_ref)
        vl.addLayout(top)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.inner = QWidget(); self.inner.setObjectName("page")
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

