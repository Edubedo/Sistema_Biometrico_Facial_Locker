import datetime
import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame

from biometria.biometria import delete_face_data, train_model, face_dir_for
from db.connection import connectionDB
from db.models.intentos_acceso import db_log_intento
from db.models.lockers import db_set_locker_estado, db_next_free_locker
from db.models.sesiones import db_create_sesion
from utils.camera import CamThread
from views.style.widgets.widgets import _step_bullet, lbl, sep_line, CamWidget

STYLE = """
QWidget#guardar_page { background: #060d1a; color: #c8dff5; }
QLabel#h2 { color: #e2f0ff; font-size: 22px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#tag { color: #4d8ec4; font-size: 11px; font-weight: 600; font-family: 'Courier New'; letter-spacing: 4px; }
QLabel#body { color: #7ca8d0; font-size: 14px; font-family: 'Segoe UI',sans-serif; }
QLabel#small { color: #3a5f84; font-size: 11px; font-family: 'Courier New'; letter-spacing: 1px; }
QLabel#err { color: #f03d5a; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QFrame#sep { background: #0f2035; min-height: 1px; max-height: 1px; }
QFrame#card { background: #0a1628; border: 1px solid #0f2035; border-radius: 16px; }
QLabel#cam {
    background: #030810; border: 2px solid #0f2035; border-radius: 14px;
    color: #1a3a5c; font-family: 'Courier New'; font-size: 12px;
}
QFrame#prog_bg { background: #0a1628; border-radius: 6px; min-height: 12px; max-height: 12px; }
QFrame#prog_fill {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a6ef5, stop:1 #3de8a0);
    border-radius: 6px; min-height: 12px; max-height: 12px;
}
QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a6ef5, stop:1 #0f4fd4);
    color: #fff; border: none; border-radius: 12px; padding: 16px 36px;
    font-size: 15px; font-weight: 800; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_blue:hover { background: #2b7cff; }
QPushButton#btn_blue:disabled { background: #0d1f3a; color: #1a3a5c; }
QPushButton#btn_sm {
    background: #0a1628; color: #4d8ec4; border: 1px solid #1a3a5c; border-radius: 8px;
    padding: 8px 18px; font-size: 12px; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_sm:hover { color: #c8dff5; border-color: #4d8ec4; }
"""


class GuardarPage(QWidget):
    done    = pyqtSignal(str, str, int)  # (face_uid, numero_locker, id_sesion)
    failed  = pyqtSignal(str)
    go_back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("guardar_page")
        self.setStyleSheet(STYLE)
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

