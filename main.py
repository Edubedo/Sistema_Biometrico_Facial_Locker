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

# db models
from db.models.lockers import *
from db.models.sesiones import *
from db.models.usuarios import *
from db.models.intentos_acceso import *

# Style
from views.style.style import STYLE

# Widgets
from views.style.widgets.widgets import _step_bullet, lbl, sep_line, CamWidget, AutoTimer

# Views
from views.cliente.home import HomePage
from views.cliente.guardar import GuardarPage 
from views.cliente.retirar import RetirarPage
from views.cliente.resultado import ResultPage

from views.admin.adminPage import  AdminPage
from views.admin.loginPage import AdminLoginPage

# Biometrico
from biometria.biometria import *


# Ruta de la base de datos SQLite (cambiar si se mueve el archivo)
DB_PATH   = r"C:\Users\ezesc\Desktop\rasp\lockers.db"



# Dimensiones de imagen para el modelo LBPH
IMG_W, IMG_H = 112, 92

# Segundos de espera en pantalla de resultado antes de volver al inicio
AUTO_HOME_SEC = 6

class MainWindow(QMainWindow):
    # Indices del QStackedWidget
    HOME   = 0
    GUARD  = 1
    RETIR  = 2
    RESULT = 3
    ALOGIN = 4
    ADMIN  = 5

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Lockers - Supermercado")
        self.setMinimumSize(1050, 680)
        self.setStyleSheet(STYLE)

        cw = QWidget(); cw.setObjectName("page")
        self.setCentralWidget(cw)
        ml = QVBoxLayout(cw); ml.setContentsMargins(0, 0, 0, 0); ml.setSpacing(0)

        # ── Paginas ──────────────────────────────────────────────────────────
        self.stack    = QStackedWidget()
        self.p_home   = HomePage()
        self.p_guard  = GuardarPage()
        self.p_retir  = RetirarPage()
        self.p_result = ResultPage()
        self.p_alogin = AdminLoginPage()
        self.p_admin  = AdminPage()

        for p in [self.p_home, self.p_guard, self.p_retir,
                  self.p_result, self.p_alogin, self.p_admin]:
            self.stack.addWidget(p)
        ml.addWidget(self.stack)

        # ── Conexiones de navegacion ─────────────────────────────────────────
        self.p_home.go_guardar.connect(lambda: self._nav(self.GUARD))
        self.p_home.go_retirar.connect(lambda: self._nav(self.RETIR))
        self.p_home.go_admin.connect(lambda: self._nav(self.ALOGIN))

        self.p_guard.go_back.connect(lambda: self._nav(self.HOME))
        self.p_guard.done.connect(self._on_guardado)
        self.p_guard.failed.connect(
            lambda msg: self._show_result("err", "Sin espacio", msg)
        )

        self.p_retir.go_back.connect(lambda: self._nav(self.HOME))
        self.p_retir.retirar_done.connect(self._on_retirado)
        self.p_retir.seguir_done.connect(self._on_seguir)

        self.p_result.go_home.connect(lambda: self._nav(self.HOME))

        self.p_alogin.go_back.connect(lambda: self._nav(self.HOME))
        self.p_alogin.login_ok.connect(self._on_login)

        self.p_admin.go_back.connect(lambda: self._nav(self.HOME))

        self._nav(self.HOME)

    # ── Navegacion ────────────────────────────────────────────────────────────

    def _nav(self, idx):
        if idx == self.HOME:
            self.p_guard.reset()
            self.p_retir.reset()
            self.p_alogin.reset()
            self.p_home.refresh()
        self.stack.setCurrentIndex(idx)

    def _show_result(self, kind, title, subtitle, detail=""):
        self.p_result.show_result(kind, title, subtitle, detail)
        self._nav(self.RESULT)

    # ── Callbacks de flujo ────────────────────────────────────────────────────

    def _on_guardado(self, face_uid, num_locker, id_sesion):
        """El cliente registro biometria y se le asigno un locker."""
        self.p_guard.reset()
        self._show_result(
            "ok",
            "Locker Asignado",
            "Tus pertenencias quedaran seguras. Recuerda tu numero de locker.",
            "LOCKER  #{}".format(num_locker)
        )

    def _on_retirado(self, face_uid, num_locker, id_sesion):
        """El cliente retiro sus cosas, sesion cerrada, locker liberado."""
        self.p_retir.reset()
        self._show_result(
            "warn",
            "Hasta Pronto",
            "El locker #{} ha sido liberado. Recoge tus cosas.".format(num_locker),
            "LOCKER  #{}".format(num_locker)
        )

    def _on_seguir(self, face_uid, num_locker, id_sesion):
        """El cliente sigue comprando, locker permanece activo."""
        self.p_retir.reset()
        detail = "LOCKER  #{}".format(num_locker) if num_locker else ""
        self._show_result(
            "ok",
            "Que sigas comprando",
            "Tus cosas permanecen seguras. Tu locker sigue activo.",
            detail
        )

    def _on_login(self, admin_data):
        """Admin autenticado correctamente."""
        self.p_admin.set_admin(admin_data)
        self._nav(self.ADMIN)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Verificar que la base de datos existe
    if not os.path.exists(DB_PATH):
        print("[ERROR] No se encontro la base de datos en:")
        print("        {}".format(DB_PATH))
        print("[INFO]  Verifica la ruta en la variable DB_PATH al inicio del archivo.")
        sys.exit(1)

    # Crear admin por defecto si la tabla esta vacia
    try:
        if db_count_active_admins() == 0:
            db_register_admin(
                "Administrador", "Sistema", "Locker",
                "admin", "admin1234", rol="administrador"
            )
            print("[INFO] Admin por defecto creado.")
            print("[INFO] Usuario: admin | Contrasena: admin1234")
            print("[INFO] Cambialo desde el Panel de Administracion.")
    except Exception as e:
        print("[WARN] No se pudo verificar admins: {}".format(e))

    # Cargar modelo biometrico con imagenes existentes
    train_model()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())