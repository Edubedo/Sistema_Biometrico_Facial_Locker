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

class RetirarPage(QWidget):
    go_back      = pyqtSignal()
    retirar_done = pyqtSignal(str, str, int)   # (face_uid, num_locker, id_sesion)
    seguir_done  = pyqtSignal(str, str, int)

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self.cam_thread  = None
        self._face_uid   = None
        self._id_sesion  = None
        self._id_locker  = None

        vl = QVBoxLayout(self)
        vl.setContentsMargins(60, 40, 60, 40)
        vl.setSpacing(16)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        back = QPushButton("< Volver"); back.setObjectName("btn_sm")
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self._cancel)
        htxt = QVBoxLayout(); htxt.setSpacing(4)
        htxt.addWidget(lbl("RETIRAR / CONTINUAR", "h2"))
        htxt.addWidget(lbl("VERIFICACION BIOMETRICA", "tag"))
        hdr.addWidget(back); hdr.addSpacing(20); hdr.addLayout(htxt); hdr.addStretch()
        vl.addLayout(hdr)
        vl.addWidget(sep_line())

        # ── Cuerpo ───────────────────────────────────────────────────────────
        body = QHBoxLayout(); body.setSpacing(32)

        # Panel izquierdo
        left = QFrame(); left.setObjectName("card")
        ll   = QVBoxLayout(left)
        ll.setContentsMargins(30, 30, 30, 30); ll.setSpacing(18)

        ll.addWidget(lbl("VERIFICACION DE IDENTIDAD", "tag"))
        for n, t in [("1", "Acerca tu rostro a la camara"),
                     ("2", "Mantén una expresion neutra"),
                     ("3", "Escoge tu opcion")]:
            ll.addWidget(_step_bullet(n, t))

        ll.addStretch()

        self.scan_btn = QPushButton("INICIAR ESCANEO")
        self.scan_btn.setObjectName("btn_outline")
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self._start_scan)
        ll.addWidget(self.scan_btn)

        self.scan_lbl = lbl("", "small", Qt.AlignCenter)
        ll.addWidget(self.scan_lbl)

        ll.addWidget(sep_line())

        # Opciones post-reconocimiento (ocultas hasta identificar)
        self.opts = QFrame()
        ol = QVBoxLayout(self.opts)
        ol.setContentsMargins(0, 0, 0, 0); ol.setSpacing(12)
        self.id_lbl     = lbl("", "ok")
        self.locker_lbl = lbl("", "h3")
        self.locker_lbl.setStyleSheet(
            "color:#4d8ec4; font-size:20px; font-weight:900; font-family:'Segoe UI';"
        )
        ol.addWidget(self.id_lbl)
        ol.addWidget(self.locker_lbl)

        self.btn_retirar = QPushButton("RETIRAR COSAS Y SALIR")
        self.btn_retirar.setObjectName("btn_red")
        self.btn_retirar.setCursor(Qt.PointingHandCursor)
        self.btn_retirar.clicked.connect(self._do_retirar)

        self.btn_seguir = QPushButton("SEGUIR COMPRANDO")
        self.btn_seguir.setObjectName("btn_green")
        self.btn_seguir.setCursor(Qt.PointingHandCursor)
        self.btn_seguir.clicked.connect(self._do_seguir)

        ol.addWidget(self.btn_retirar)
        ol.addWidget(self.btn_seguir)
        self.opts.setVisible(False)
        ll.addWidget(self.opts)

        # Panel derecho: camara
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(12)
        rl.addWidget(lbl("ESCANER BIOMETRICO", "tag", Qt.AlignCenter))
        self.cam = CamWidget(460, 340)
        rl.addWidget(self.cam)
        rl.addStretch()

        body.addWidget(left, 1)
        body.addWidget(right, 2)
        vl.addLayout(body, 1)

    def _start_scan(self):
        labels = train_model()
        if not labels:
            self.scan_lbl.setText("No hay biometrias registradas.")
            return
        self.scan_btn.setEnabled(False)
        self.opts.setVisible(False)
        self.scan_lbl.setText("Escaneando...")
        self.cam_thread = CamThread(CamThread.RECOGNIZE, labels=labels)
        self.cam_thread.frame_sig.connect(self.cam.update_frame)
        self.cam_thread.rec_done.connect(self._on_recognized)
        self.cam_thread.start()

    def _on_recognized(self, face_uid):
        self.scan_btn.setEnabled(True)
        self.cam.idle()

        if not face_uid:
            # Intento fallido: loguear contra el primer locker ocupado (sin sesion especifica)
            db_log_intento(
                1, "retirar", "fallido",
                "Rostro no reconocido en escaneo de retirar"
            )
            self.scan_lbl.setText("No se reconocio el rostro. Intenta de nuevo.")
            self.scan_lbl.setStyleSheet(
                "color:#f03d5a; font-size:12px; font-family:'Segoe UI';"
            )
            return

        # Buscar sesion activa vinculada a esta biometria
        sesion = db_get_active_sesion_by_face(face_uid)
        if not sesion:
            self.scan_lbl.setText("No tienes una sesion activa.")
            return

        self._face_uid  = face_uid
        self._id_sesion = sesion["ID_sesion"]
        self._id_locker = sesion["ID_locker"]
        num_locker      = db_get_locker_num_by_id(self._id_locker)

        self.scan_lbl.setText("")
        self.id_lbl.setText("Identidad verificada")
        self.locker_lbl.setText("Tu locker: #{}".format(num_locker))
        self.opts.setVisible(True)

    def _do_retirar(self):
        if not self._id_sesion:
            return

        num_locker = db_get_locker_num_by_id(self._id_locker)

        # Cerrar sesion
        db_close_sesion(self._id_sesion)
        # Liberar locker
        db_set_locker_estado(self._id_locker, "libre")
        # Borrar biometria
        delete_face_data(self._face_uid)
        # Reentrenar modelo
        train_model()
        # Log
        db_log_intento(
            self._id_locker, "retirar", "exitoso",
            "Cliente retiro sus cosas. Sesion {} cerrada.".format(self._id_sesion),
            id_sesion=self._id_sesion
        )

        self.retirar_done.emit(self._face_uid, num_locker, self._id_sesion)

    def _do_seguir(self):
        if not self._id_sesion:
            return

        num_locker = db_get_locker_num_by_id(self._id_locker)

        # Log: el cliente sigue comprando, sesion permanece activa
        db_log_intento(
            self._id_locker, "seguir_comprando", "exitoso",
            "Cliente consulto locker y continuo comprando. Sesion {} activa.".format(
                self._id_sesion
            ),
            id_sesion=self._id_sesion
        )

        self.seguir_done.emit(self._face_uid, num_locker, self._id_sesion)

    def _cancel(self):
        if self.cam_thread:
            self.cam_thread.stop()
        self.go_back.emit()

    def reset(self):
        if self.cam_thread:
            self.cam_thread.stop()
        self._face_uid  = None
        self._id_sesion = None
        self._id_locker = None
        self.opts.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.scan_lbl.setText("")
        self.scan_lbl.setStyleSheet("")
        self.cam.idle()

