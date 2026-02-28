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

# ──────────────────────────────────────────────────────────────────────────────
# [SECCION: PAGINA_HOME]
# Pantalla principal del cliente con opciones Guardar y Retirar.
# ──────────────────────────────────────────────────────────────────────────────

class HomePage(QWidget):
    go_guardar = pyqtSignal()
    go_retirar = pyqtSignal()
    go_admin   = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        vl = QVBoxLayout(self)
        vl.setContentsMargins(80, 60, 80, 60)
        vl.setSpacing(0)
        vl.setAlignment(Qt.AlignCenter)

        # ── Titulo ──────────────────────────────────────────────────────────
        vl.addWidget(lbl("SUPERMERCADO", "tag", Qt.AlignCenter))
        vl.addSpacing(6)

        title = lbl("Sistema de Lockers", "h1", Qt.AlignCenter)
        title.setStyleSheet(
            "color:#ffffff; font-size:44px; font-weight:900;"
            "font-family:'Segoe UI','Trebuchet MS',sans-serif; letter-spacing:-2px;"
        )
        vl.addWidget(title)
        vl.addSpacing(8)
        vl.addWidget(lbl("Guarda tus pertenencias de forma segura y biometrica.", "body", Qt.AlignCenter))
        vl.addSpacing(18)
        vl.addWidget(sep_line())
        vl.addSpacing(50)

        # ── Tarjetas de accion ──────────────────────────────────────────────
        cards = QHBoxLayout()
        cards.setSpacing(32)

        # GUARDAR
        cg = QFrame(); cg.setObjectName("card_blue")
        lg = QVBoxLayout(cg)
        lg.setContentsMargins(44, 44, 44, 44); lg.setSpacing(20)
        lg.setAlignment(Qt.AlignCenter)
        ig = QLabel("[ G ]")
        ig.setStyleSheet("color:#1a6ef5; font-size:54px; font-weight:900; font-family:'Courier New';")
        ig.setAlignment(Qt.AlignCenter)
        tg = lbl("GUARDAR", "h2", Qt.AlignCenter)
        tg.setStyleSheet("color:#c8dff5; font-size:26px; font-weight:900; font-family:'Segoe UI';")
        dg = lbl("Deja tus cosas en un\nlocker seguro mientras\ncompras.", "body", Qt.AlignCenter)
        bg = QPushButton("CONTINUAR"); bg.setObjectName("btn_blue")
        bg.setCursor(Qt.PointingHandCursor)
        bg.clicked.connect(self.go_guardar.emit)
        lg.addWidget(ig); lg.addWidget(tg); lg.addWidget(dg)
        lg.addSpacing(16); lg.addWidget(bg)

        # RETIRAR
        cr = QFrame(); cr.setObjectName("card_yellow")
        lr = QVBoxLayout(cr)
        lr.setContentsMargins(44, 44, 44, 44); lr.setSpacing(20)
        lr.setAlignment(Qt.AlignCenter)
        ir = QLabel("[ R ]")
        ir.setStyleSheet("color:#f0b429; font-size:54px; font-weight:900; font-family:'Courier New';")
        ir.setAlignment(Qt.AlignCenter)
        tr = lbl("RETIRAR", "h2", Qt.AlignCenter)
        tr.setStyleSheet("color:#c8dff5; font-size:26px; font-weight:900; font-family:'Segoe UI';")
        dr = lbl("Recoge tus pertenencias\no sigue comprando con\ntu locker activo.", "body", Qt.AlignCenter)
        br = QPushButton("CONTINUAR"); br.setObjectName("btn_outline")
        br.setCursor(Qt.PointingHandCursor)
        br.clicked.connect(self.go_retirar.emit)
        lr.addWidget(ir); lr.addWidget(tr); lr.addWidget(dr)
        lr.addSpacing(16); lr.addWidget(br)

        cards.addWidget(cg); cards.addWidget(cr)
        vl.addLayout(cards)
        vl.addSpacing(36)

        # ── Stats ────────────────────────────────────────────────────────────
        stats_card = QFrame(); stats_card.setObjectName("card")
        sl = QHBoxLayout(stats_card)
        sl.setContentsMargins(30, 16, 30, 16); sl.setSpacing(0)
        self.free_lbl  = lbl("", "body")
        self.busy_lbl  = lbl("", "body")
        self.total_lbl = lbl("", "small")
        sl.addWidget(self.free_lbl)
        sl.addStretch()
        sl.addWidget(self.busy_lbl)
        sl.addStretch()
        sl.addWidget(self.total_lbl)
        vl.addWidget(stats_card)
        vl.addSpacing(20)

        # ── Admin discreto ───────────────────────────────────────────────────
        adm = QPushButton("ADMINISTRACION"); adm.setObjectName("btn_admin")
        adm.setCursor(Qt.PointingHandCursor)
        adm.clicked.connect(self.go_admin.emit)
        row_adm = QHBoxLayout()
        row_adm.addStretch(); row_adm.addWidget(adm)
        vl.addLayout(row_adm)

    def refresh(self):
        """Actualiza las estadisticas desde la base de datos."""
        lockers = db_get_all_lockers()
        total   = len(lockers)
        free    = sum(1 for l in lockers if l["t_estado"] == "libre")
        busy    = total - free

        self.free_lbl.setText("Lockers libres: {}".format(free))
        self.free_lbl.setStyleSheet("color:#3de8a0; font-size:14px; font-family:'Segoe UI';")
        self.busy_lbl.setText("Lockers ocupados: {}".format(busy))
        self.busy_lbl.setStyleSheet("color:#f0b429; font-size:14px; font-family:'Segoe UI';")
        self.total_lbl.setText("Total: {}".format(total))



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


# ──────────────────────────────────────────────────────────────────────────────
# [SECCION: PAGINA_RETIRAR]
# Reconocimiento facial, busqueda de sesion activa y opciones al cliente.
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# [SECCION: PAGINA_RESULT]
# Pantalla de confirmacion con auto-redireccion al inicio.
# ──────────────────────────────────────────────────────────────────────────────

class ResultPage(QWidget):
    go_home = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self._vl  = QVBoxLayout(self)
        self._vl.setContentsMargins(80, 80, 80, 80)
        self._vl.setAlignment(Qt.AlignCenter)
        self._card    = None
        self._timer_w = AutoTimer(AUTO_HOME_SEC)
        self._timer_w.timeout.connect(self.go_home.emit)

    def show_result(self, kind, title, subtitle, detail=""):
        """
        kind: 'ok' | 'warn' | 'err'
        """
        if self._card:
            self._vl.removeWidget(self._card)
            self._card.deleteLater()
        if self._vl.indexOf(self._timer_w) >= 0:
            self._vl.removeWidget(self._timer_w)

        frame_map = {"ok": "card_green", "warn": "card_yellow", "err": "card_red"}
        color_map  = {"ok": "#3de8a0",    "warn": "#f0b429",     "err": "#f03d5a"}
        icon_map   = {"ok": "[  OK  ]",   "warn": "[ ! ]",       "err": "[ X ]"}

        fn    = frame_map.get(kind, "card")
        color = color_map.get(kind, "#c8dff5")
        icon  = icon_map.get(kind, "[ ? ]")

        card = QFrame(); card.setObjectName(fn)
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(70, 60, 70, 60); cl.setSpacing(24)
        cl.setAlignment(Qt.AlignCenter)

        i_lbl = QLabel(icon); i_lbl.setAlignment(Qt.AlignCenter)
        i_lbl.setStyleSheet(
            "font-size:42px; color:{}; font-family:'Courier New'; font-weight:900;".format(color)
        )
        t_lbl = QLabel(title); t_lbl.setAlignment(Qt.AlignCenter)
        t_lbl.setStyleSheet(
            "font-size:30px; font-weight:900; color:{};"
            "font-family:'Segoe UI'; letter-spacing:-1px;".format(color)
        )
        s_lbl = QLabel(subtitle); s_lbl.setAlignment(Qt.AlignCenter)
        s_lbl.setObjectName("body"); s_lbl.setWordWrap(True)

        cl.addWidget(i_lbl); cl.addWidget(t_lbl); cl.addWidget(s_lbl)

        if detail:
            d_lbl = QLabel(detail); d_lbl.setAlignment(Qt.AlignCenter)
            d_lbl.setStyleSheet(
                "font-size:38px; font-weight:900; color:{}; font-family:'Courier New';".format(color)
            )
            cl.addWidget(d_lbl)

        btn = QPushButton("VOLVER AL INICIO")
        btn.setObjectName("btn_blue" if kind == "ok" else "btn_sm")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self._manual_home)
        cl.addSpacing(10)
        cl.addWidget(btn, alignment=Qt.AlignCenter)

        self._card = card
        self._vl.addWidget(card)
        self._vl.addSpacing(16)
        self._vl.addWidget(self._timer_w, alignment=Qt.AlignCenter)
        self._timer_w.start()

    def _manual_home(self):
        self._timer_w.stop()
        self.go_home.emit()
