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

# Biometrico
from biometria.biometria import *

# Ruta de la base de datos SQLite (cambiar si se mueve el archivo)
DB_PATH   = r"C:\Users\ezesc\Desktop\rasp\lockers.db"



# Dimensiones de imagen para el modelo LBPH
IMG_W, IMG_H = 112, 92

# Segundos de espera en pantalla de resultado antes de volver al inicio
AUTO_HOME_SEC = 6




# ──────────────────────────────────────────────────────────────────────────────
# [SECCION: CAMARA_THREAD]
# QThread que maneja captura biometrica y reconocimiento facial.
# ──────────────────────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────────────────────
# [SECCION: ADMIN_LOGIN]
# Autenticacion de administradores con usuario y contrasena (tabla Usuarios).
# ──────────────────────────────────────────────────────────────────────────────

class AdminLoginPage(QWidget):
    go_back  = pyqtSignal()
    login_ok = pyqtSignal(dict)   # dict con datos del admin autenticado

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setAlignment(Qt.AlignCenter)

        card = QFrame(); card.setObjectName("card_blue")
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(56, 48, 56, 48); cl.setSpacing(18)
        card.setFixedWidth(460)

        hdr_row = QHBoxLayout()
        bk = QPushButton("< Volver"); bk.setObjectName("btn_sm")
        bk.setCursor(Qt.PointingHandCursor); bk.clicked.connect(self.go_back.emit)
        hdr_row.addWidget(bk); hdr_row.addStretch()
        cl.addLayout(hdr_row)

        cl.addWidget(lbl("ADMINISTRACION", "tag", Qt.AlignCenter))
        cl.addWidget(lbl("Acceso al Panel", "h2", Qt.AlignCenter))
        cl.addWidget(sep_line())

        cl.addWidget(lbl("Usuario"))
        self.user_inp = QLineEdit(); self.user_inp.setObjectName("inp")
        self.user_inp.setPlaceholderText("nombre de usuario")
        cl.addWidget(self.user_inp)

        cl.addWidget(lbl("Contrasena"))
        self.pass_inp = QLineEdit(); self.pass_inp.setObjectName("inp")
        self.pass_inp.setEchoMode(QLineEdit.Password)
        self.pass_inp.setPlaceholderText("••••••••")
        self.pass_inp.returnPressed.connect(self._check)
        cl.addWidget(self.pass_inp)

        self.err_lbl = lbl("", "err", Qt.AlignCenter)
        cl.addWidget(self.err_lbl)

        btn_in = QPushButton("INGRESAR"); btn_in.setObjectName("btn_blue")
        btn_in.setCursor(Qt.PointingHandCursor)
        btn_in.clicked.connect(self._check)
        cl.addWidget(btn_in)

        vl.addWidget(card)

    def _check(self):
        u = self.user_inp.text().strip()
        p = self.pass_inp.text()
        if not u or not p:
            self.err_lbl.setText("Completa los campos.")
            return
        if not db_admin_exists(u):
            self.err_lbl.setText("Usuario no encontrado.")
            # Loguear intento fallido (sin locker especifico, usamos 0)
            try:
                db_log_intento(0, "acceso_admin", "fallido",
                               "Intento con usuario: {}".format(u))
            except Exception:
                pass
            return
        if not db_admin_valid(u, p):
            self.err_lbl.setText("Contrasena incorrecta.")
            self.pass_inp.clear()
            try:
                db_log_intento(0, "acceso_admin", "fallido",
                               "Contrasena incorrecta para: {}".format(u))
            except Exception:
                pass
            return
        admin = db_get_admin_by_username(u)
        # Loguear acceso exitoso
        try:
            db_log_intento(0, "acceso_admin", "exitoso",
                           "Admin {} ingreso al panel.".format(u),
                           id_usuario=admin["ID_admin"])
        except Exception:
            pass
        self.err_lbl.setText("")
        self.user_inp.clear(); self.pass_inp.clear()
        self.login_ok.emit(admin)

    def reset(self):
        self.user_inp.clear(); self.pass_inp.clear(); self.err_lbl.setText("")


# ──────────────────────────────────────────────────────────────────────────────
# [SECCION: ADMIN_PANEL]
# Panel con tres pestanas: Lockers, Sesiones/Usuarios, Administradores.
# ──────────────────────────────────────────────────────────────────────────────

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


# ─── Sub-panel: Lockers ───────────────────────────────────────────────────────

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


# ─── Sub-panel: Sesiones activas ─────────────────────────────────────────────

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


# ─── Sub-panel: Log de intentos de acceso ────────────────────────────────────

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


# ─── Sub-panel: Administradores ──────────────────────────────────────────────

class _AdminUsersPanel(QWidget):
    """
    Permite registrar nuevos administradores con nombre completo,
    usuario y contrasena. Campos mapeados a la tabla Usuarios.
    """

    def __init__(self):
        super().__init__()
        self._current_admin = {}
        vl = QVBoxLayout(self); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(16)

        body = QHBoxLayout(); body.setSpacing(28)

        # ── Lista de admins ───────────────────────────────────────────────────
        left = QFrame(); left.setObjectName("card")
        ll   = QVBoxLayout(left); ll.setContentsMargins(24, 24, 24, 24); ll.setSpacing(12)
        ll.addWidget(lbl("ADMINISTRADORES ACTIVOS", "tag"))

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.inner = QWidget(); self.inner.setObjectName("inner_bg")
        self.il    = QVBoxLayout(self.inner)
        self.il.setContentsMargins(0, 0, 0, 0); self.il.setSpacing(8)
        scroll.setWidget(self.inner)
        ll.addWidget(scroll, 1)

        btn_del = QPushButton("DESACTIVAR ADMIN"); btn_del.setObjectName("btn_red")
        btn_del.setCursor(Qt.PointingHandCursor); btn_del.clicked.connect(self._delete)
        ll.addWidget(btn_del)

        # ── Formulario de registro ────────────────────────────────────────────
        right = QFrame(); right.setObjectName("card_blue")
        rl    = QVBoxLayout(right); rl.setContentsMargins(28, 28, 28, 28); rl.setSpacing(12)
        rl.addWidget(lbl("REGISTRAR NUEVO ADMIN", "tag"))
        rl.addWidget(sep_line())

        # Campos mapeados a Usuarios
        rl.addWidget(lbl("Nombre"))
        self.f_nombre = QLineEdit(); self.f_nombre.setObjectName("inp")
        self.f_nombre.setPlaceholderText("Juan")
        rl.addWidget(self.f_nombre)

        rl.addWidget(lbl("Apellido paterno"))
        self.f_ap = QLineEdit(); self.f_ap.setObjectName("inp")
        self.f_ap.setPlaceholderText("Garcia")
        rl.addWidget(self.f_ap)

        rl.addWidget(lbl("Apellido materno"))
        self.f_am = QLineEdit(); self.f_am.setObjectName("inp")
        self.f_am.setPlaceholderText("Lopez")
        rl.addWidget(self.f_am)

        rl.addWidget(lbl("Usuario"))
        self.f_user = QLineEdit(); self.f_user.setObjectName("inp")
        self.f_user.setPlaceholderText("jgarcia01")
        rl.addWidget(self.f_user)

        rl.addWidget(lbl("Rol"))
        self.f_rol = QComboBox(); self.f_rol.setObjectName("combo")
        self.f_rol.addItems(["empleado", "supervisor", "administrador"])
        rl.addWidget(self.f_rol)

        rl.addWidget(lbl("Contrasena"))
        self.f_pass = QLineEdit(); self.f_pass.setObjectName("inp")
        self.f_pass.setEchoMode(QLineEdit.Password)
        self.f_pass.setPlaceholderText("••••••••")
        rl.addWidget(self.f_pass)

        rl.addWidget(lbl("Confirmar contrasena"))
        self.f_pass2 = QLineEdit(); self.f_pass2.setObjectName("inp")
        self.f_pass2.setEchoMode(QLineEdit.Password)
        self.f_pass2.setPlaceholderText("••••••••")
        rl.addWidget(self.f_pass2)

        self.reg_err = lbl("", "err", Qt.AlignCenter)
        self.reg_ok  = lbl("", "ok",  Qt.AlignCenter)
        rl.addWidget(self.reg_err)
        rl.addWidget(self.reg_ok)

        btn_reg = QPushButton("REGISTRAR ADMINISTRADOR"); btn_reg.setObjectName("btn_blue")
        btn_reg.setCursor(Qt.PointingHandCursor); btn_reg.clicked.connect(self._register)
        rl.addWidget(btn_reg)
        rl.addStretch()

        body.addWidget(left, 1)
        body.addWidget(right, 1)
        vl.addLayout(body, 1)
        self.refresh()

    def set_current_admin(self, admin_data):
        self._current_admin = admin_data

    def _register(self):
        nombre = self.f_nombre.text().strip()
        ap     = self.f_ap.text().strip()
        am     = self.f_am.text().strip()
        user   = self.f_user.text().strip()
        rol    = self.f_rol.currentText()
        pw     = self.f_pass.text()
        pw2    = self.f_pass2.text()
        id_reg = self._current_admin.get("ID_admin")

        self.reg_err.setText(""); self.reg_ok.setText("")

        if not all([nombre, ap, user, pw]):
            self.reg_err.setText("Nombre, apellido, usuario y contrasena son obligatorios.")
            return
        if len(pw) < 4:
            self.reg_err.setText("La contrasena debe tener al menos 4 caracteres.")
            return
        if pw != pw2:
            self.reg_err.setText("Las contrasenas no coinciden.")
            return
        if db_admin_exists(user):
            self.reg_err.setText("Ya existe un admin con ese usuario.")
            return

        new_id = db_register_admin(nombre, ap, am, user, pw, rol, id_reg)
        if new_id:
            for f in [self.f_nombre, self.f_ap, self.f_am, self.f_user, self.f_pass, self.f_pass2]:
                f.clear()
            self.reg_ok.setText("Admin '{}' registrado correctamente.".format(user))
            self.refresh()
        else:
            self.reg_err.setText("No se pudo registrar. Intenta de nuevo.")

    def _delete(self):
        u, ok = QInputDialog.getText(None, "Desactivar Admin", "Usuario a desactivar:")
        if not ok or not u.strip():
            return
        if not db_admin_exists(u.strip()):
            QMessageBox.warning(None, "Error", "Admin no encontrado.")
            return
        if db_count_active_admins() <= 1:
            QMessageBox.warning(None, "Error", "Debe existir al menos un administrador activo.")
            return
        id_act = self._current_admin.get("ID_admin")
        db_delete_admin(u.strip(), id_act)
        QMessageBox.information(None, "OK", "Admin '{}' desactivado.".format(u.strip()))
        self.refresh()

    def refresh(self):
        for i in reversed(range(self.il.count())):
            item = self.il.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        admins = db_get_all_admins()
        if not admins:
            self.il.addWidget(lbl("Sin administradores.", "small"))
        else:
            for a in admins:
                row = QFrame(); row.setObjectName("card")
                rl  = QHBoxLayout(row); rl.setContentsMargins(16, 12, 16, 12); rl.setSpacing(12)

                nombre = "{} {} {}".format(
                    a.get("t_nombre", ""),
                    a.get("t_apellido_paterno", ""),
                    a.get("t_apellido_materno", "")
                ).strip()
                n_lbl = QLabel(nombre)
                n_lbl.setStyleSheet(
                    "color:#c8dff5; font-size:13px; font-weight:700; font-family:'Segoe UI';"
                )
                u_lbl  = lbl("@{}".format(a.get("t_usuario", "")), "small")
                r_lbl  = lbl(a.get("t_rol", ""), "badge_blue")
                st_obj = "badge_green" if a.get("t_estado") == "activo" else "badge_red"
                s_lbl  = lbl(a.get("t_estado", "").upper(), st_obj)

                rl.addWidget(n_lbl); rl.addWidget(u_lbl)
                rl.addStretch(); rl.addWidget(r_lbl); rl.addWidget(s_lbl)
                self.il.addWidget(row)
        self.il.addStretch()


# ──────────────────────────────────────────────────────────────────────────────
# [SECCION: VENTANA_MAIN]
# QMainWindow raiz que gestiona el stack de paginas y los flujos de navegacion.
# ──────────────────────────────────────────────────────────────────────────────

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