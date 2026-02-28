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

class _AdminLockersPanel(QWidget):
    def __init__(self):
        super().__init__()
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(16)

        # Stats
        self.stats_row = QHBoxLayout(); self.stats_row.setSpacing(12)
        vl.addLayout(self.stats_row)

        # Grid con scroll
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        inner  = QWidget(); inner.setObjectName("page")
        il     = QVBoxLayout(inner); il.setContentsMargins(0, 0, 0, 0)
        self.grid = QGridLayout(); self.grid.setSpacing(12)
        il.addLayout(self.grid); il.addStretch()
        scroll.setWidget(inner)
        vl.addWidget(scroll, 1)

        # Acciones
        acts = QHBoxLayout(); acts.setSpacing(12)
        btn_lib = QPushButton("LIBERAR LOCKER"); btn_lib.setObjectName("btn_outline")
        btn_lib.setCursor(Qt.PointingHandCursor); btn_lib.clicked.connect(self._liberar)
        btn_add = QPushButton("AGREGAR LOCKER"); btn_add.setObjectName("btn_blue")
        btn_add.setCursor(Qt.PointingHandCursor); btn_add.clicked.connect(self._agregar)
        btn_ref = QPushButton("Actualizar"); btn_ref.setObjectName("btn_sm")
        btn_ref.setCursor(Qt.PointingHandCursor); btn_ref.clicked.connect(self.refresh)
        acts.addWidget(btn_lib); acts.addWidget(btn_add); acts.addWidget(btn_ref); acts.addStretch()
        vl.addLayout(acts)
        self.refresh()

    def _liberar(self):
        num, ok = QInputDialog.getText(None, "Liberar Locker", "Numero del locker a liberar:")
        if not ok or not num.strip():
            return
        # Buscar locker por numero
        lockers = [l for l in db_get_all_lockers() if l["t_numero_locker"] == num.strip()]
        if not lockers:
            QMessageBox.warning(None, "Error", "Locker no encontrado.")
            return
        locker = lockers[0]
        if locker["t_estado"] == "libre":
            QMessageBox.information(None, "Info", "El locker ya esta libre.")
            return
        # Cerrar sesion activa si existe
        sesiones = db_get_all_sesiones_activas()
        for s in sesiones:
            if s["ID_locker"] == locker["ID_locker"]:
                db_close_sesion(s["ID_sesion"])
                face_uid = s["b_vector_biometrico_temp"]
                if isinstance(face_uid, bytes):
                    face_uid = face_uid.decode("utf-8")
                delete_face_data(face_uid)
                db_log_intento(
                    locker["ID_locker"], "liberacion_admin", "exitoso",
                    "Admin libero locker #{} manualmente.".format(num.strip()),
                    id_sesion=s["ID_sesion"]
                )
        db_set_locker_estado(locker["ID_locker"], "libre")
        train_model()
        QMessageBox.information(None, "OK", "Locker #{} liberado.".format(num.strip()))
        self.refresh()

    def _agregar(self):
        num, ok = QInputDialog.getText(None, "Agregar Locker", "Numero del nuevo locker:")
        if not ok or not num.strip():
            return
        try:
            db_insert_locker(num.strip())
            QMessageBox.information(None, "OK", "Locker #{} creado.".format(num.strip()))
            self.refresh()
        except Exception as ex:
            QMessageBox.warning(None, "Error", str(ex))

    def refresh(self):
        # Limpiar stats
        for i in reversed(range(self.stats_row.count())):
            item = self.stats_row.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        lockers = db_get_all_lockers()
        total   = len(lockers)
        free    = sum(1 for l in lockers if l["t_estado"] == "libre")
        busy    = total - free

        for text, val, color in [
            ("LIBRES",   free,  "#3de8a0"),
            ("OCUPADOS", busy,  "#f0b429"),
            ("TOTAL",    total, "#4d8ec4"),
        ]:
            sf = QFrame(); sf.setObjectName("card")
            sl = QHBoxLayout(sf); sl.setContentsMargins(20, 12, 20, 12); sl.setSpacing(10)
            n  = QLabel(str(val))
            n.setStyleSheet(
                "color:{}; font-size:24px; font-weight:900; font-family:'Segoe UI';".format(color)
            )
            t = lbl(text, "small")
            sl.addWidget(n); sl.addWidget(t)
            self.stats_row.addWidget(sf)
        self.stats_row.addStretch()

        # Limpiar grid
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        cols = 4
        for i, locker in enumerate(lockers):
            is_libre = locker["t_estado"] == "libre"
            fr = QFrame()
            fr.setObjectName("lk_free" if is_libre else "lk_busy")
            fl = QVBoxLayout(fr); fl.setContentsMargins(8, 8, 8, 8); fl.setAlignment(Qt.AlignCenter)
            color = "#4d8ec4" if is_libre else "#f0b429"

            n_lbl = QLabel("#{}".format(locker["t_numero_locker"]))
            n_lbl.setStyleSheet(
                "color:{}; font-size:18px; font-weight:900; font-family:'Segoe UI';".format(color)
            )
            n_lbl.setAlignment(Qt.AlignCenter)

            zona_txt = locker.get("t_zona") or ""
            s_txt    = "LIBRE" if is_libre else "OCUPADO"
            s_lbl    = lbl("{} {}".format(s_txt, zona_txt).strip()[:14], "small", Qt.AlignCenter)
            fl.addWidget(n_lbl); fl.addWidget(s_lbl)
            row, col = divmod(i, cols)
            self.grid.addWidget(fr, row, col)
