import datetime
import os

from PyQt5.QtCore import Qt, pyqtSignal,  QTimer
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QSizePolicy, QLabel

from biometria.biometria import delete_face_data, train_model, face_dir_for
from db.connection import connectionDB
from db.models.intentos_acceso import db_log_intento
from db.models.lockers import db_set_locker_estado, db_next_free_locker
from db.models.sesiones import db_create_sesion
from utils.camera import CamThread
from views.style.widgets.widgets import _step_bullet, lbl, sep_line, CamWidget

STYLE = """
QWidget#guardar_page { background: #E7E7E7; color: #1f2a44; }
QLabel#h2 { color: #305BAB; font-size: 24px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#tag { color: #305BAB; font-size: 22px; font-weight: 700; font-family: 'Courier New'; letter-spacing: 4px; }
QLabel#body { color: #2c3e50; font-size: 20px; font-family: 'Segoe UI',sans-serif; }
QLabel#small { color: #3a5f84; font-size: 16px; font-family: 'Courier New'; letter-spacing: 1px; }
QLabel#err { color: #BD0A0A; font-size: 17px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QFrame#sep { background: #305BAB; min-height: 1px; max-height: 1px; }
QFrame#card { background: #C6DCFF; border: 2px solid #305BAB; border-radius: 14px; }
QLabel#cam {
    background: #0c1530; border: 4px solid #305bab; border-radius: 10px;
    color: #1a3a5c; font-family: 'Courier New'; font-size: 0px;
}
QFrame#status_box { background: #c6dcff; border-radius: 12px; padding: 20px; border: 2px solid #305bab; }
QFrame#prog_bg { background: #0a1628; border-radius: 6px; min-height: 12px; max-height: 12px; }
QFrame#prog_fill {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #305bab, stop:1 #B9EA89);
    border-radius: 6px; min-height: 12px; max-height: 12px;
}
QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1a3a6b, stop:0.5 #305bab, stop:1 #678dd3); color: white; border: none; border-radius: 11px;
    padding: 20px 30px; font-size: 19px; font-weight: 750; font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
}
QPushButton#btn_blue:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #2952a3, stop:0.5 #3d6fd1, stop:1 #7aa3e8); }
QPushButton#btn_blue:pressed {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1a3a6b, stop:0.5 #305bab, stop:1 #5681cf);
}
QPushButton#btn_blue:disabled {  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #4a90d9, stop:1 #7ec8f5);
    color: black; }
QPushButton#btn_sm {
     background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #96bfe9, stop:1 #b8e1fa); color: #1d3767; border: 3px solid #305bab; border-radius: 8px;
    padding: 6px 16px; font-size: 19px; font-family: 'Segoe UI',sans-serif;
}
QPushButton#btn_sm:hover { color: #305bab; border-color: #838383; }
QPushButton#btn_sm:pressed { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #95a49f, stop:0.5 #c1cac7, stop:1 #5681cf); }
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
        vl.setContentsMargins(60, 60, 60, 20)
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
        # ll.setAlignment(Qt.AlignTop)
        ll.setContentsMargins(30, 20, 30, 20); 

        ll.addWidget(lbl("COMO FUNCIONA", "tag", Qt.AlignCenter))
        ll.addSpacing(20)
        ll.addStretch(1)
        for n, t in [("1", "Mira directamente a la camara"),
                     ("2", "El sistema captura tu biometria facial"),
                     ("3", "Se te asigna el siguiente locker libre"),
                     ("4", "Guarda tus cosas y disfruta comprando"),
                     ("5", "Sus imágenes solo están siendo usadas en este momento y las borraremos en cuanto finalice sus compras")
                     ]:
            # ll.addWidget(_step_bullet(n, t))
            step = _step_bullet(n, t)
            step.setFixedWidth(420) 
            for child in step.findChildren(QLabel):
                child.setWordWrap(True)
            ll.addWidget(step, alignment=Qt.AlignCenter)
        
        ll.addStretch(1)
        ll.addSpacing(20)
        status_box = QFrame()
        status_box.setObjectName("status_box")
        
        sb_layout = QVBoxLayout(status_box)
        sb_layout.setSpacing(10)
        sb_layout.setAlignment(Qt.AlignCenter)

        self.avail_lbl = lbl("", "body")
        self.avail_lbl.setAlignment(Qt.AlignCenter)

        self.start_btn = QPushButton("REGISTRAR BIOMETRIA")
        self.start_btn.setObjectName("btn_blue")
        self.start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._start_capture)
       
        sb_layout.addWidget(self.avail_lbl)
        sb_layout.addWidget(self.start_btn)
        
        ll.addWidget(status_box)

        self.err_lbl = lbl("", "err")
        self.err_lbl.setWordWrap(True)
        ll.addWidget(self.err_lbl)

        # Panel derecho: camara
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(12)
        rl.addWidget(lbl("ESCANER BIOMETRICO", "tag", Qt.AlignCenter))
        self.cam = CamWidget(500, 760)
        self.cam.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rl.addWidget(self.cam, 1)
        # rl.addStretch()
        
        #GUIA VISUAL (MONITO)
        self.face_guide = QSvgWidget(self.cam)
        self.face_guide.load(b"""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120">
            <circle cx="50" cy="28" r="20" fill="#305bab" opacity="0.5"/>
            <path d="M8 108 Q8 65 50 65 Q92 65 92 108 Z" fill="#305bab" opacity="0.5"/>
            </svg>""")
        self.face_guide.setStyleSheet("background: transparent;")
        self.face_guide.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        #MARCO VERDE (referencia)
        self.scan_frame = QFrame(self.cam)
        self.scan_frame.setStyleSheet("""border: 4px solid #B9EA89 ; border-radius: 10px; background: transparent;""")
        self.scan_frame.setAttribute(Qt.WA_TransparentForMouseEvents)

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
            self.avail_lbl.setStyleSheet("color:#B9EA89; font-size:15px; font-family:'Segoe UI';")
            self.start_btn.setEnabled(True)
        else:
            self._id_locker = None
            self.avail_lbl.setText("No hay lockers disponibles en este momento.")
            self.avail_lbl.setStyleSheet("color:#bd0a0a; font-size:15px; font-family:'Segoe UI';")
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
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_overlay)

    def _update_overlay(self):
        cam_w = self.cam.width()
        cam_h = self.cam.height()

        frame_w = int(cam_w * 0.45)
        frame_h = int(cam_h * 0.55)

        frame_x = (cam_w - frame_w) // 2
        frame_y = (cam_h - frame_h) // 2

        self.scan_frame.setGeometry(frame_x, frame_y, frame_w, frame_h)

        icon_w = int(frame_w * 0.40)
        icon_h = int(frame_h * 0.40)

        icon_x = frame_x + (frame_w - icon_w) // 2
        icon_y = frame_y + (frame_h - icon_h) // 2

        self.face_guide.setGeometry(icon_x, icon_y, icon_w, icon_h)

