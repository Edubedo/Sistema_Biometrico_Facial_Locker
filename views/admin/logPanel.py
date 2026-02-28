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

class _AdminLogPanel(QWidget):
    def __init__(self):
        super().__init__()
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(lbl("Registro de accesos (ultimos 50)", "body"))
        top.addStretch()
        btn_ref = QPushButton("Actualizar"); btn_ref.setObjectName("btn_sm")
        btn_ref.setCursor(Qt.PointingHandCursor); btn_ref.clicked.connect(self.refresh)
        top.addWidget(btn_ref)
        vl.addLayout(top)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.inner = QWidget(); self.inner.setObjectName("page")
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

