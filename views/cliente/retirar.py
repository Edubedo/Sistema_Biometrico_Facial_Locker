from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QSizePolicy, QLabel

from biometria.biometria import delete_face_data, train_model
from PyQt5.QtSvg import QSvgWidget
from db.models.intentos_acceso import db_log_intento
from db.models.lockers import db_set_locker_estado
from db.models.sesiones import db_close_sesion, db_get_active_sesion_by_face
from utils.camera import CamThread
from utils.helpers import db_get_locker_num_by_id
from views.style.widgets.widgets import _step_bullet, lbl, sep_line, CamWidget

STYLE = """
QWidget#retirar_page { background: #e7e7e7; color: #1f2a44 }
QLabel#h2 { color: #305bab; font-size: 24px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#h3 { color: #305bab; font-size: 18px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QLabel#tag { color: #305bab; font-size: 22px; font-weight: 700; font-family: 'Courier New'; letter-spacing: 4px; }
QLabel#body { color: #2c3e50; font-size: 20px; font-family: 'Segoe UI',sans-serif; }
QLabel#small { color: #3a5f84; font-size: 16px; font-family: 'Courier New'; letter-spacing: 1px; }
QLabel#ok { color: #b9ea89; font-size: 14px; font-weight: 700; font-family: 'Segoe UI',sans-serif; }
QFrame#sep { background: #305bab; min-height: 1px; max-height: 1px; }
QFrame#card { background: #c6dcff; border: 2px solid #305bab; border-radius: 14px; }
QFrame#status_box { background: #c6dcff; border-radius: 12px; padding: 20px; border: 2px solid #305bab; }

QLabel#cam {
    background: #0c1530; border: 4px solid #305bab; border-radius: 10px;
    color: #1a3a5c; font-family: 'Courier New'; font-size: 0px;
}

QPushButton#btn_outline {
     background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4a90d9, stop:1 #7ec8f5); color: black;
    border: none; border-radius: 11px; padding: 20px 30px; font-size: 19px;
    font-weight: 750; font-family: 'Segoe UI', sans-serif; letter-spacing: 1px;
}

QPushButton#btn_outline:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #5ba3e8, stop:1 #90d4ff); }

QPushButton#btn_outline:pressed { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a3a6b, stop:0.5 #305bab, stop:1 #678dd3); }

QPushButton#btn_outline:disabled { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8ab8e0, stop:1 #aad0f0); color:  #e0eef8; }

QPushButton#btn_green {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #b9ea89, stop:1 #0fa860);
    color: #0a1628; border: none; border-radius: 12px; padding: 14px 30px;
    font-size: 16px; font-weight: 800; font-family: 'Segoe UI',sans-serif;
}

QPushButton#btn_red {
    background: #bd0a0a; color: #fff; border: none; border-radius: 12px;
    padding: 14px 30px; font-size: 16px; font-weight: 800; font-family: 'Segoe UI',sans-serif;
}

QPushButton#btn_sm {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #96bfe9, stop:1 #b8e1fa); color: #1d3767; border: 3px solid #305bab; border-radius: 8px;
    padding: 8px 18px; font-size: 19px; font-family: 'Segoe UI',sans-serif;
}

QPushButton#btn_sm:hover { color: #305bab; border-color: #838383; }
QPushButton#btn_sm:pressed { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #95a49f, stop:0.5 #c1cac7, stop:1 #5681cf); }

"""

class RetirarPage(QWidget):

    go_back      = pyqtSignal()
    retirar_done = pyqtSignal(str, str, int)   # (face_uid, num_locker, id_sesion)
    seguir_done  = pyqtSignal(str, str, int)

    def __init__(self):
        super().__init__()

        self.setObjectName("retirar_page")
        self.setStyleSheet(STYLE)

        self.cam_thread  = None
        self._face_uid   = None
        self._id_sesion  = None
        self._id_locker  = None

        vl = QVBoxLayout(self)
        vl.setContentsMargins(60, 40, 60, 40)
        vl.setSpacing(16)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QHBoxLayout()

        back = QPushButton("< Volver")
        back.setObjectName("btn_sm")
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self._cancel)

        htxt = QVBoxLayout()
        htxt.setSpacing(4)
        htxt.addWidget(lbl("RETIRAR / CONTINUAR", "h2"))
        htxt.addWidget(lbl("VERIFICACION BIOMETRICA", "tag"))

        hdr.addWidget(back)
        hdr.addSpacing(20)
        hdr.addLayout(htxt)
        hdr.addStretch()

        vl.addLayout(hdr)
        vl.addWidget(sep_line())

        # ── Cuerpo ───────────────────────────────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(32)

        # Panel izquierdo
        left = QFrame()
        left.setObjectName("card")

        ll = QVBoxLayout(left)
        ll.setContentsMargins(30, 20, 30, 30)

        ll.addWidget(lbl("VERIFICACION DE IDENTIDAD", "tag", Qt.AlignCenter))
        ll.setSpacing(20)
        
        ll.addStretch(1)
        for n, t in [
            ("1", "Acerca tu rostro a la camara"),
            ("2", "Mantén una expresion neutra"),
            ("3", "Escoge tu opcion"),
            ("4", "Sus imágenes solo están siendo usadas en este momento y las borraremos en cuanto finalice sus compras")
        ]:
             step = _step_bullet(n, t)
             step.setFixedWidth(420)
             for child in step.findChildren(QLabel):
                child.setWordWrap(True)
             ll.addWidget(step, alignment=Qt.AlignCenter)
        ll.addStretch(1)

        # Boton iniciar escaneo
        status_box = QFrame()
        status_box.setObjectName("status_box")
        sb_layout = QVBoxLayout(status_box)
        sb_layout.setSpacing(10)
        sb_layout.setAlignment(Qt.AlignCenter)
        
        
        self.scan_btn = QPushButton("INICIAR ESCANEO")
        self.scan_btn.setObjectName("btn_outline")
        self.scan_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self._start_scan)
        
        self.scan_lbl = lbl("", "small", Qt.AlignCenter)

        sb_layout.addWidget(self.scan_btn)
        sb_layout.addWidget(self.scan_lbl)
        
        ll.addWidget(status_box)

        # Texto estado escaneo
        self.scan_lbl = lbl("", "small", Qt.AlignCenter)
        ll.addWidget(self.scan_lbl)

        # ll.addWidget(sep_line())

        # Opciones post-reconocimiento (ocultas hasta identificar)
        self.opts = QFrame()

        ol = QVBoxLayout(self.opts)
        ol.setContentsMargins(0,0,0,0)
        ol.setSpacing(12)

        self.id_lbl = lbl("", "ok")
        self.locker_lbl = lbl("", "h3")

        self.btn_retirar = QPushButton("RETIRAR COSAS Y SALIR")
        self.btn_retirar.setObjectName("btn_red")
        self.btn_retirar.clicked.connect(self._do_retirar)

        self.btn_seguir = QPushButton("SEGUIR COMPRANDO")
        self.btn_seguir.setObjectName("btn_green")
        self.btn_seguir.clicked.connect(self._do_seguir)

        ol.addWidget(self.id_lbl)
        ol.addWidget(self.locker_lbl)
        ol.addWidget(self.btn_retirar)
        ol.addWidget(self.btn_seguir)

        self.opts.setVisible(False)

        ll.addWidget(self.opts)

        # ── Panel derecho: camara ───────────────────────────────────────────
        right = QWidget()

        rl = QVBoxLayout(right)
        rl.setContentsMargins(0,0,0,0)
        rl.setSpacing(12)

        rl.addWidget(lbl("ESCANER BIOMETRICO", "tag", Qt.AlignCenter))

        self.cam = CamWidget(500,760)
        self.cam.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rl.addWidget(self.cam,1)

        # ── Overlay biometrico ─────────────────────────

        # icono guia rostro
        self.face_guide = QSvgWidget(self.cam)
        self.face_guide.load(b"""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120">
            <circle cx="50" cy="28" r="20" fill="#305bab" opacity="0.5"/>
            <path d="M8 108 Q8 65 50 65 Q92 65 92 108 Z" fill="#305bab" opacity="0.5"/>
            </svg>""")
        self.face_guide.setStyleSheet("background: transparent;")
        self.face_guide.setAttribute(Qt.WA_TransparentForMouseEvents)

        # marco de escaneo
        self.scan_frame = QFrame(self.cam)
        self.scan_frame.setStyleSheet("""
        border: 4px solid #B9EA89;
        border-radius: 10px;
        background: transparent;
        """)
        self.scan_frame.setAttribute(Qt.WA_TransparentForMouseEvents)

        body.addWidget(left,1)
        body.addWidget(right,2)
        vl.addLayout(body,1)

    # ── Centrar marco e icono ─────────────────────────────────────────────
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

    # ── Iniciar reconocimiento ─────────────────────────────────────────────
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

    # ── Resultado reconocimiento ───────────────────────────────────────────
    def _on_recognized(self, face_uid):

        self.scan_btn.setEnabled(True)
        self.cam.idle()

        if not face_uid:

            db_log_intento(
                1,"retirar","fallido",
                "Rostro no reconocido en escaneo de retirar"
            )

            self.scan_lbl.setText("No se reconocio el rostro. Intenta de nuevo.")
            return

        sesion = db_get_active_sesion_by_face(face_uid)

        if not sesion:
            self.scan_lbl.setText("No tienes una sesion activa.")
            return

        self._face_uid = face_uid
        self._id_sesion = sesion["ID_sesion"]
        self._id_locker = sesion["ID_locker"]

        num_locker = db_get_locker_num_by_id(self._id_locker)

        self.scan_lbl.setText("")
        self.id_lbl.setText("Identidad verificada")
        self.locker_lbl.setText("Tu locker: #{}".format(num_locker))

        self.opts.setVisible(True)

    # ── Retirar cosas ──────────────────────────────────────────────────────
    def _do_retirar(self):

        if not self._id_sesion:
            return

        num_locker = db_get_locker_num_by_id(self._id_locker)

        db_close_sesion(self._id_sesion)
        db_set_locker_estado(self._id_locker, "libre")
        delete_face_data(self._face_uid)
        train_model()

        db_log_intento(
            self._id_locker,"retirar","exitoso",
            "Cliente retiro sus cosas. Sesion {} cerrada.".format(self._id_sesion),
            id_sesion=self._id_sesion
        )

        self.retirar_done.emit(self._face_uid, num_locker, self._id_sesion)

    # ── Seguir comprando ───────────────────────────────────────────────────
    def _do_seguir(self):

        if not self._id_sesion:
            return

        num_locker = db_get_locker_num_by_id(self._id_locker)

        db_log_intento(
            self._id_locker,"seguir_comprando","exitoso",
            "Cliente consulto locker y continuo comprando.",
            id_sesion=self._id_sesion
        )

        self.seguir_done.emit(self._face_uid, num_locker, self._id_sesion)

    # ── Cancelar ───────────────────────────────────────────────────────────
    def _cancel(self):

        if self.cam_thread:
            self.cam_thread.stop()

        self.go_back.emit()

    # ── Reset vista ────────────────────────────────────────────────────────
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