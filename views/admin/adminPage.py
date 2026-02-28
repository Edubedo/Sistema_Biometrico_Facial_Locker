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

from views.admin.lockersPanel import _AdminLockersPanel 
from views.admin.sesionesPanel import _AdminSesionesPanel 
from views.admin.usuariosPanel import _AdminUsersPanel 
from views.admin.logPanel import _AdminLogPanel 

class AdminPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self._admin_data = {}
        vl = QVBoxLayout(self)
        vl.setContentsMargins(48, 36, 48, 36)
        vl.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        bk  = QPushButton("< Cerrar sesion"); bk.setObjectName("btn_sm")
        bk.setCursor(Qt.PointingHandCursor); bk.clicked.connect(self.go_back.emit)
        tit = lbl("Panel de Administracion", "h2")
        self.badge = lbl("", "badge_blue")
        hdr.addWidget(bk); hdr.addSpacing(16)
        hdr.addWidget(tit); hdr.addStretch(); hdr.addWidget(self.badge)
        vl.addLayout(hdr)
        vl.addSpacing(12)
        vl.addWidget(sep_line())
        vl.addSpacing(4)

        # ── Tabs ─────────────────────────────────────────────────────────────
        tab_row = QHBoxLayout(); tab_row.setSpacing(0)
        self.t_lock  = QPushButton("LOCKERS");        self.t_lock.setObjectName("tab");  self.t_lock.setCheckable(True);  self.t_lock.setChecked(True)
        self.t_ses   = QPushButton("SESIONES");       self.t_ses.setObjectName("tab");   self.t_ses.setCheckable(True)
        self.t_log   = QPushButton("REGISTRO ACCESO");self.t_log.setObjectName("tab");   self.t_log.setCheckable(True)
        self.t_adm   = QPushButton("ADMINISTRADORES");self.t_adm.setObjectName("tab");   self.t_adm.setCheckable(True)
        for i, b in enumerate([self.t_lock, self.t_ses, self.t_log, self.t_adm]):
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, x=i: self._tab(x))
            tab_row.addWidget(b)
        tab_row.addStretch()
        vl.addLayout(tab_row)
        vl.addWidget(sep_line())
        vl.addSpacing(16)

        # ── Sub-paneles ───────────────────────────────────────────────────────
        self.stack      = QStackedWidget()
        self.p_lockers  = _AdminLockersPanel()
        self.p_sesiones = _AdminSesionesPanel()
        self.p_log      = _AdminLogPanel()
        self.p_admins   = _AdminUsersPanel()
        for p in [self.p_lockers, self.p_sesiones, self.p_log, self.p_admins]:
            self.stack.addWidget(p)
        vl.addWidget(self.stack, 1)

    def _tab(self, i):
        self.stack.setCurrentIndex(i)
        tabs = [self.t_lock, self.t_ses, self.t_log, self.t_adm]
        for j, b in enumerate(tabs):
            b.setChecked(j == i)
        refresh_map = {
            0: self.p_lockers.refresh,
            1: self.p_sesiones.refresh,
            2: self.p_log.refresh,
            3: self.p_admins.refresh
        }
        refresh_map[i]()

    def set_admin(self, admin_data):
        self._admin_data = admin_data
        self.badge.setText("  {}  ".format(admin_data.get("t_usuario", "").upper()))
        self.p_admins.set_current_admin(admin_data)

    def showEvent(self, e):
        super().showEvent(e)
        self._tab(0)

