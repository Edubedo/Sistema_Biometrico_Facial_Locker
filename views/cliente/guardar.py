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


class GuardarPage(QWidget):
    done    = pyqtSignal(str, str, int)  # (face_uid, numero_locker, id_sesion)
    failed  = pyqtSignal(str)
    go_back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self.cam_thread  = None
        self._face_uid   = None
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
        htxt.addWidget(lbl("GUARDAR PERTENENCIAS", "h2"))
        htxt.addWidget(lbl("ASIGNACION AUTOMATICA DE LOCKER", "tag"))
        hdr.addWidget(back); hdr.addSpacing(20); hdr.addLayout(htxt); hdr.addStretch()
        vl.addLayout(hdr)
        vl.addWidget(sep_line())

        # ── Cuerpo ───────────────────────────────────────────────────────────
        body = QHBoxLayout(); body.setSpacing(32)

        # Panel izquierdo: instrucciones y control
        left = QFrame(); left.setObjectName("card")
        ll   = QVBoxLayout(left)
        ll.setContentsMargins(30, 30, 30, 30); ll.setSpacing(18)

        ll.addWidget(lbl("COMO FUNCIONA", "tag"))
        for n, t in [("1", "Mira directamente a la camara"),
                     ("2", "El sistema captura tu biometria facial"),
                     ("3", "Se te asigna el siguiente locker libre"),
                     ("4", "Guarda tus cosas y disfruta comprando")]:
            ll.addWidget(_step_bullet(n, t))

        ll.addStretch()

        self.avail_lbl = lbl("", "body")
        ll.addWidget(self.avail_lbl)

        self.start_btn = QPushButton("REGISTRAR BIOMETRIA")
        self.start_btn.setObjectName("btn_blue")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._start_capture)
        ll.addWidget(self.start_btn)

        self.err_lbl = lbl("", "err")
        self.err_lbl.setWordWrap(True)
        ll.addWidget(self.err_lbl)

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

    def showEvent(self, e):
        super().showEvent(e)
        result = db_next_free_locker()
        if result:
            self._id_locker = result[0]
            self.avail_lbl.setText(
                "Locker disponible. Se te asignara el #{}.".format(result[1])
            )
            self.avail_lbl.setStyleSheet("color:#3de8a0; font-size:13px; font-family:'Segoe UI';")
            self.start_btn.setEnabled(True)
        else:
            self._id_locker = None
            self.avail_lbl.setText("No hay lockers disponibles en este momento.")
            self.avail_lbl.setStyleSheet("color:#f03d5a; font-size:13px; font-family:'Segoe UI';")
            self.start_btn.setEnabled(False)

    def _start_capture(self):
        if not self._id_locker:
            self.err_lbl.setText("Sin lockers disponibles.")
            return

        # Nombre temporal del uid biometrico (se sobreescribe tras crear sesion)
        tmp_uid = "tmp_{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        self._face_uid = tmp_uid
        self.start_btn.setEnabled(False)
        self.err_lbl.setText("")

        self.cam_thread = CamThread(CamThread.CAPTURE, face_uid=tmp_uid)
        self.cam_thread.frame_sig.connect(self.cam.update_frame)
        self.cam_thread.progress.connect(self.cam.set_progress)
        self.cam_thread.cap_done.connect(self._on_capture_done)
        self.cam_thread.start()

    def _on_capture_done(self, ok, tmp_uid):
        self.cam.idle()
        self.start_btn.setEnabled(True)

        if not ok:
            # Captura fallida: borrar imagenes temporales y loguear
            delete_face_data(tmp_uid)
            if self._id_locker:
                db_log_intento(
                    self._id_locker, "registro_biometrico", "fallido",
                    "Error durante la captura de imagenes"
                )
            self.err_lbl.setText("Error al capturar. Intenta de nuevo.")
            return

        # Verificar que el locker sigue libre (puede haber cambiado)
        locker = db_next_free_locker()
        if not locker:
            delete_face_data(tmp_uid)
            self.failed.emit("Sin lockers disponibles.")
            return

        id_locker, num_locker = locker

        # Crear sesion en BD → obtener ID_sesion definitivo
        id_sesion = db_create_sesion(id_locker, tmp_uid)

        # Renombrar carpeta de imagenes al face_uid definitivo
        face_uid = "sesion_{}".format(id_sesion)
        old_dir  = face_dir_for(tmp_uid)
        new_dir  = face_dir_for(face_uid)
        if os.path.exists(old_dir):
            os.rename(old_dir, new_dir)

        # Actualizar blob de referencia en la sesion
        with connectionDB() as con:
            con.execute(
                "UPDATE Sesiones SET b_vector_biometrico_temp=? WHERE ID_sesion=?",
                (face_uid.encode("utf-8"), id_sesion)
            )

        # Marcar locker como ocupado
        db_set_locker_estado(id_locker, "ocupado")

        # Registrar intento exitoso
        db_log_intento(
            id_locker, "registro_biometrico", "exitoso",
            "Sesion {} creada. Locker #{} asignado.".format(id_sesion, num_locker),
            id_sesion=id_sesion
        )

        # Reentrenar modelo con la nueva biometria
        train_model()

        self.done.emit(face_uid, num_locker, id_sesion)

    def _cancel(self):
        if self.cam_thread:
            self.cam_thread.stop()
        # Limpiar captura parcial si existia
        if self._face_uid:
            delete_face_data(self._face_uid)
        self.go_back.emit()

    def reset(self):
        if self.cam_thread:
            self.cam_thread.stop()
        self._face_uid  = None
        self._id_locker = None
        self.err_lbl.setText("")
        self.cam.idle()
        self.start_btn.setEnabled(True)

