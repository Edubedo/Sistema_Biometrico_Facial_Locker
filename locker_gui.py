"""
Sistema de Lockers - Supermercado
Rediseno completo: sin barra lateral, UI azul centrada, asignacion automatica,
redireccion automatica al inicio, admins con usuario/contrasena.
"""
import sys, os, cv2, json, datetime, hashlib, importlib.util, site, shutil
import pathlib
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFrame, QStackedWidget,
    QSizePolicy, QSpacerItem, QScrollArea, QGridLayout,
    QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap


# ══════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
FACES_DIR     = os.path.join(BASE_DIR, 'locker_faces')
DATA_FILE     = os.path.join(BASE_DIR, 'locker_data.json')
TOTAL_LOCKERS = 12
AUTO_HOME_SEC = 6          # segundos antes de volver al inicio

os.makedirs(FACES_DIR, exist_ok=True)
IMG_W, IMG_H = 112, 92


# ══════════════════════════════════════════════════════
#  PERSISTENCIA
# ══════════════════════════════════════════════════════
def _default_db():
    return {
        "lockers": {
            str(i): {"status": "libre", "user": None, "since": None}
            for i in range(1, TOTAL_LOCKERS + 1)
        },
        "face_users": {},          # uid -> {locker, created}
        "admins": {}               # username -> hashed_password
    }

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return _default_db()

def save_db():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(DB, f, ensure_ascii=False, indent=2)

DB = load_db()

def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def admin_exists(username):
    return username in DB["admins"]

def admin_valid(username, password):
    return DB["admins"].get(username) == _hash(password)

def admin_register(username, password):
    DB["admins"][username] = _hash(password)
    save_db()

def admin_delete(username):
    if username in DB["admins"]:
        del DB["admins"][username]
        save_db()

def next_free_locker():
    for n, info in sorted(DB["lockers"].items(), key=lambda x: int(x[0])):
        if info["status"] == "libre":
            return n
    return None

def assign_locker(uid, locker_num):
    DB["lockers"][locker_num] = {
        "status": "ocupado",
        "user": uid,
        "since": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    DB["face_users"][uid] = {
        "locker": locker_num,
        "created": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    save_db()

def release_user(uid):
    locker = DB["face_users"].get(uid, {}).get("locker")
    if locker and locker in DB["lockers"]:
        DB["lockers"][locker] = {"status": "libre", "user": None, "since": None}
    if uid in DB["face_users"]:
        del DB["face_users"][uid]
    face_dir = os.path.join(FACES_DIR, uid)
    if os.path.exists(face_dir):
        shutil.rmtree(face_dir)
    save_db()
    return locker

def get_user_locker(uid):
    return DB["face_users"].get(uid, {}).get("locker")

def free_locker_admin(locker_num):
    uid = DB["lockers"].get(locker_num, {}).get("user")
    DB["lockers"][locker_num] = {"status": "libre", "user": None, "since": None}
    if uid and uid in DB["face_users"]:
        del DB["face_users"][uid]
    save_db()


# ══════════════════════════════════════════════════════
#  HAARCASCADE
# ══════════════════════════════════════════════════════
def _find_cascade():
    fn = 'haarcascade_frontalface_default.xml'
    try:
        p = cv2.data.haarcascades + fn
        if os.path.exists(p): return p
    except AttributeError:
        pass
    try:
        spec = importlib.util.find_spec('cv2')
        if spec and spec.submodule_search_locations:
            for loc in spec.submodule_search_locations:
                for c in pathlib.Path(loc).rglob(fn):
                    return str(c)
    except Exception:
        pass
    try:
        for sp in site.getsitepackages():
            p = os.path.join(sp, 'cv2', 'data', fn)
            if os.path.exists(p): return p
    except Exception:
        pass
    return fn

CASCADE = _find_cascade()


# ══════════════════════════════════════════════════════
#  MODELO FACIAL
# ══════════════════════════════════════════════════════
face_model = cv2.face.LBPHFaceRecognizer_create()
face_labels = {}   # int -> uid

def train_model():
    global face_labels
    images, labels, names, idx = [], [], {}, 0
    for uid in os.listdir(FACES_DIR):
        sub = os.path.join(FACES_DIR, uid)
        if not os.path.isdir(sub): continue
        names[idx] = uid
        for fn in os.listdir(sub):
            img = cv2.imread(os.path.join(sub, fn), 0)
            if img is not None:
                images.append(cv2.resize(img, (IMG_W, IMG_H)))
                labels.append(idx)
        idx += 1
    if len(images) > 1:
        face_model.train(np.array(images), np.array(labels))
    face_labels = names
    return names


# ══════════════════════════════════════════════════════
#  CAMERA THREAD
# ══════════════════════════════════════════════════════
class CamThread(QThread):
    frame_sig  = pyqtSignal(QImage)
    cap_done   = pyqtSignal(bool, str)   # ok, uid
    rec_done   = pyqtSignal(str)          # uid o ""
    progress   = pyqtSignal(int)

    CAPTURE   = 'capture'
    RECOGNIZE = 'recognize'

    def __init__(self, mode, uid='', labels=None):
        super().__init__()
        self.mode   = mode
        self.uid    = uid
        self.labels = labels or {}
        self._on    = True

    def stop(self):
        self._on = False
        self.wait(3000)

    def run(self):
        cap = cv2.VideoCapture(0)
        fc  = cv2.CascadeClassifier(CASCADE)
        cnt = 0
        sdir = os.path.join(FACES_DIR, self.uid) if self.mode == self.CAPTURE else None
        if sdir: os.makedirs(sdir, exist_ok=True)

        while self._on:
            ret, frame = cap.read()
            if not ret: break
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = fc.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces:
                roi = cv2.resize(gray[y:y+h, x:x+w], (IMG_W, IMG_H))
                cv2.rectangle(frame, (x, y), (x+w, y+h), (80, 180, 255), 2)

                if self.mode == self.CAPTURE:
                    cv2.imwrite(os.path.join(sdir, '{}.png'.format(cnt)), roi)
                    cnt += 1
                    self.progress.emit(cnt)
                    cv2.putText(frame, '{}/20'.format(cnt), (x, y-8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 180, 255), 2)
                    if cnt >= 20:
                        self._on = False; break

                elif self.mode == self.RECOGNIZE:
                    try:
                        lbl, conf = face_model.predict(roi)
                        if conf < 100 and lbl in self.labels:
                            uid = self.labels[lbl]
                            cv2.putText(frame, uid, (x, y-8),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 180, 255), 2)
                            self._emit(frame)
                            self.rec_done.emit(uid)
                            cap.release(); return
                    except Exception:
                        pass

            self._emit(frame)

        cap.release()
        if self.mode == self.CAPTURE:
            self.cap_done.emit(cnt >= 20, self.uid)
        elif self.mode == self.RECOGNIZE:
            self.rec_done.emit('')

    def _emit(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        self.frame_sig.emit(QImage(rgb.data, w, h, ch*w, QImage.Format_RGB888))


# ══════════════════════════════════════════════════════
#  PALETA DE COLORES (azul oscuro industrial)
# ══════════════════════════════════════════════════════
STYLE = """
/* BASE */
QMainWindow, QWidget { background: #060d1a; color: #c8dff5; }
QWidget#page  { background: #060d1a; }
QWidget#modal { background: #0a1628; }

/* TIPOGRAFIA */
QLabel#h1 {
    color: #ffffff;
    font-size: 38px; font-weight: 900;
    font-family: 'Segoe UI', 'Trebuchet MS', sans-serif;
    letter-spacing: -1px;
}
QLabel#h2 {
    color: #e2f0ff;
    font-size: 22px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#h3 {
    color: #e2f0ff;
    font-size: 16px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
}
QLabel#tag {
    color: #4d8ec4;
    font-size: 11px; font-weight: 600;
    font-family: 'Courier New';
    letter-spacing: 4px;
}
QLabel#body  { color: #7ca8d0; font-size: 14px; font-family: 'Segoe UI', sans-serif; }
QLabel#small { color: #3a5f84; font-size: 11px; font-family: 'Courier New'; letter-spacing: 1px; }
QLabel#ok    { color: #3de8a0; font-size: 14px; font-weight: 700; font-family: 'Segoe UI', sans-serif; }
QLabel#warn  { color: #f0b429; font-size: 14px; font-weight: 700; font-family: 'Segoe UI', sans-serif; }
QLabel#err   { color: #f03d5a; font-size: 14px; font-weight: 700; font-family: 'Segoe UI', sans-serif; }

/* LINEA DIVISORIA */
QFrame#sep { background: #0f2035; min-height: 1px; max-height: 1px; }

/* TARJETAS */
QFrame#card {
    background: #0a1628;
    border: 1px solid #0f2035;
    border-radius: 16px;
}
QFrame#card_blue {
    background: #071833;
    border: 1px solid #1a4a8a;
    border-radius: 16px;
}
QFrame#card_green {
    background: #041a12;
    border: 1px solid #1a7a50;
    border-radius: 16px;
}
QFrame#card_yellow {
    background: #1a1204;
    border: 1px solid #7a5a1a;
    border-radius: 16px;
}
QFrame#card_red {
    background: #1a0409;
    border: 1px solid #7a1a2a;
    border-radius: 16px;
}

/* BOTON PRIMARIO AZUL */
QPushButton#btn_blue {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1a6ef5, stop:1 #0f4fd4);
    color: #ffffff;
    border: none; border-radius: 12px;
    padding: 20px 48px;
    font-size: 17px; font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
    min-width: 220px;
}
QPushButton#btn_blue:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #3a84ff, stop:1 #2060f0);
}
QPushButton#btn_blue:pressed {
    background: #0e3eb8;
}
QPushButton#btn_blue:disabled {
    background: #0d1f3a; color: #1a3a5c;
}

/* BOTON SECUNDARIO */
QPushButton#btn_outline {
    background: transparent;
    color: #4d8ec4;
    border: 2px solid #1a3a5c;
    border-radius: 12px;
    padding: 18px 44px;
    font-size: 16px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
    min-width: 200px;
}
QPushButton#btn_outline:hover {
    border-color: #4d8ec4;
    color: #c8dff5;
    background: #071833;
}

/* BOTON VERDE */
QPushButton#btn_green {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1ac87a, stop:1 #0fa860);
    color: #000d08;
    border: none; border-radius: 12px;
    padding: 16px 36px;
    font-size: 15px; font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
}
QPushButton#btn_green:hover { background: #22e88a; }
QPushButton#btn_green:disabled { background: #0a2018; color: #0a3020; }

/* BOTON ROJO */
QPushButton#btn_red {
    background: #c0122a;
    color: #ffffff;
    border: none; border-radius: 12px;
    padding: 16px 36px;
    font-size: 15px; font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
}
QPushButton#btn_red:hover { background: #e01535; }

/* BOTON PEQUENO */
QPushButton#btn_sm {
    background: #0a1628;
    color: #4d8ec4;
    border: 1px solid #1a3a5c;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 12px;
    font-family: 'Segoe UI', sans-serif;
}
QPushButton#btn_sm:hover { color: #c8dff5; border-color: #4d8ec4; }

/* BOTON ADMIN (discreto) */
QPushButton#btn_admin {
    background: transparent;
    color: #1a3a5c;
    border: 1px solid #0f2035;
    border-radius: 8px;
    padding: 10px 22px;
    font-size: 12px;
    font-family: 'Courier New';
    letter-spacing: 2px;
}
QPushButton#btn_admin:hover { color: #4d8ec4; border-color: #1a3a5c; }

/* INPUT */
QLineEdit#inp {
    background: #060d1a;
    border: 1.5px solid #0f2035;
    border-radius: 10px;
    color: #e2f0ff;
    padding: 14px 18px;
    font-size: 14px;
    font-family: 'Segoe UI', sans-serif;
    selection-background-color: #1a6ef5;
}
QLineEdit#inp:focus { border-color: #1a6ef5; }

/* CAMARA */
QLabel#cam {
    background: #030810;
    border: 2px solid #0f2035;
    border-radius: 14px;
    color: #1a3a5c;
    font-family: 'Courier New';
    font-size: 12px;
}

/* BARRA DE PROGRESO MANUAL */
QFrame#progress_bar_bg {
    background: #0a1628;
    border-radius: 6px;
    min-height: 12px; max-height: 12px;
}
QFrame#progress_bar_fill {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1a6ef5, stop:1 #3de8a0);
    border-radius: 6px;
    min-height: 12px; max-height: 12px;
}

/* LOCKERS */
QFrame#lk_free {
    background: #041228;
    border: 2px solid #1a4a8a;
    border-radius: 12px;
    min-width: 110px; min-height: 90px;
}
QFrame#lk_busy {
    background: #1a1204;
    border: 2px solid #5a3a08;
    border-radius: 12px;
    min-width: 110px; min-height: 90px;
}

/* BADGES */
QLabel#badge_blue {
    background: #071833; color: #4d8ec4;
    border: 1px solid #1a4a8a;
    border-radius: 14px; padding: 3px 12px;
    font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px;
}
QLabel#badge_green {
    background: #041a12; color: #3de8a0;
    border: 1px solid #1a7a50;
    border-radius: 14px; padding: 3px 12px;
    font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px;
}
QLabel#badge_yellow {
    background: #1a1204; color: #f0b429;
    border: 1px solid #7a5a1a;
    border-radius: 14px; padding: 3px 12px;
    font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px;
}
QLabel#badge_red {
    background: #1a0409; color: #f03d5a;
    border: 1px solid #7a1a2a;
    border-radius: 14px; padding: 3px 12px;
    font-size: 10px; font-family: 'Courier New'; letter-spacing: 2px;
}

/* SCROLL */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical   { background: #060d1a; width: 6px; margin: 0; }
QScrollBar::handle:vertical { background: #0f2035; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ADMIN NAV */
QPushButton#tab {
    background: transparent; color: #3a5f84;
    border: none; border-bottom: 3px solid transparent;
    padding: 12px 24px;
    font-size: 13px; font-weight: 700;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px;
    border-radius: 0;
}
QPushButton#tab:hover   { color: #7ca8d0; border-bottom-color: #1a3a5c; }
QPushButton#tab:checked { color: #4d8ec4; border-bottom-color: #1a6ef5; }
"""


# ══════════════════════════════════════════════════════
#  WIDGET AUXILIARES
# ══════════════════════════════════════════════════════
def sep_line():
    f = QFrame(); f.setObjectName("sep"); f.setFrameShape(QFrame.HLine)
    return f

def lbl(text, obj="body", align=None):
    l = QLabel(text); l.setObjectName(obj)
    if align: l.setAlignment(align)
    return l

class CamWidget(QWidget):
    """Vista de camara con barra de progreso integrada."""
    def __init__(self, w=460, h=320):
        super().__init__()
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)

        self.view = QLabel("Camara inactiva")
        self.view.setObjectName("cam")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setMinimumSize(w, h)
        vl.addWidget(self.view)

        self.status = QLabel("")
        self.status.setObjectName("body")
        self.status.setAlignment(Qt.AlignCenter)
        vl.addWidget(self.status)

        # Barra de progreso (solo en modo captura)
        self.prog_bg = QFrame(); self.prog_bg.setObjectName("progress_bar_bg")
        self.prog_bg.setFixedHeight(12)
        prog_layout = QHBoxLayout(self.prog_bg)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        self.prog_fill = QFrame(); self.prog_fill.setObjectName("progress_bar_fill")
        self.prog_fill.setFixedHeight(12)
        prog_layout.addWidget(self.prog_fill)
        prog_layout.addStretch()
        self.prog_bg.setVisible(False)
        vl.addWidget(self.prog_bg)

    def update_frame(self, qimg):
        pix = QPixmap.fromImage(qimg).scaled(
            self.view.width(), self.view.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.view.setPixmap(pix)

    def set_progress(self, n, total=20):
        self.prog_bg.setVisible(True)
        pct = min(n / total, 1.0)
        w   = int(self.prog_bg.width() * pct)
        self.prog_fill.setFixedWidth(max(w, 0))
        self.status.setText("Capturando biometria... {}/{}".format(n, total))
        self.status.setStyleSheet("color:#4d8ec4; font-size:13px; font-family:'Segoe UI';")

    def set_status(self, text, color="#7ca8d0"):
        self.status.setText(text)
        self.status.setStyleSheet(
            "color:{}; font-size:13px; font-family:'Segoe UI';".format(color))

    def idle(self):
        self.view.clear()
        self.view.setText("Camara inactiva")
        self.status.setText("")
        self.prog_bg.setVisible(False)


class AutoTimer(QWidget):
    """Etiqueta con cuenta regresiva. Emite timeout cuando llega a 0."""
    timeout = pyqtSignal()

    def __init__(self, seconds=AUTO_HOME_SEC):
        super().__init__()
        self.secs  = seconds
        self._left = seconds
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        self._lbl = QLabel()
        self._lbl.setObjectName("small")
        self._lbl.setAlignment(Qt.AlignCenter)
        hl.addWidget(self._lbl)
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._left = self.secs
        self._update_lbl()
        self._timer.start(1000)

    def stop(self):
        self._timer.stop()

    def _tick(self):
        self._left -= 1
        self._update_lbl()
        if self._left <= 0:
            self._timer.stop()
            self.timeout.emit()

    def _update_lbl(self):
        self._lbl.setText("Regresando al inicio en {}s...".format(self._left))


# ══════════════════════════════════════════════════════
#  PAGINA: HOME
# ══════════════════════════════════════════════════════
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

        # Logo / titulo
        logo_lbl = lbl("SUPERMERCADO", "tag", Qt.AlignCenter)
        title    = lbl("Sistema de Lockers", "h1", Qt.AlignCenter)
        title.setStyleSheet(
            "color:#ffffff; font-size:44px; font-weight:900;"
            "font-family:'Segoe UI','Trebuchet MS',sans-serif; letter-spacing:-2px;")
        sub = lbl("Guarda tus pertenencias de forma segura y biometrica.", "body", Qt.AlignCenter)

        vl.addWidget(logo_lbl)
        vl.addSpacing(4)
        vl.addWidget(title)
        vl.addSpacing(8)
        vl.addWidget(sub)
        vl.addSpacing(16)
        vl.addWidget(sep_line())
        vl.addSpacing(50)

        # Tarjetas de accion principales
        cards = QHBoxLayout(); cards.setSpacing(32)

        # GUARDAR
        cg = QFrame(); cg.setObjectName("card_blue")
        lg = QVBoxLayout(cg); lg.setContentsMargins(44, 44, 44, 44); lg.setSpacing(20)
        lg.setAlignment(Qt.AlignCenter)
        ig = QLabel("[ G ]")
        ig.setStyleSheet(
            "color:#1a6ef5; font-size:54px; font-weight:900; font-family:'Courier New';")
        ig.setAlignment(Qt.AlignCenter)
        tg = lbl("GUARDAR", "h2", Qt.AlignCenter)
        tg.setStyleSheet(
            "color:#c8dff5; font-size:26px; font-weight:900; font-family:'Segoe UI';")
        dg = lbl("Deja tus cosas en un\nlocker seguro mientras\ncompras.", "body", Qt.AlignCenter)
        bg = QPushButton("CONTINUAR"); bg.setObjectName("btn_blue")
        bg.setCursor(Qt.PointingHandCursor)
        bg.clicked.connect(self.go_guardar.emit)
        lg.addWidget(ig); lg.addWidget(tg); lg.addWidget(dg)
        lg.addSpacing(16); lg.addWidget(bg)

        # RETIRAR
        cr = QFrame(); cr.setObjectName("card_yellow")
        lr = QVBoxLayout(cr); lr.setContentsMargins(44, 44, 44, 44); lr.setSpacing(20)
        lr.setAlignment(Qt.AlignCenter)
        ir = QLabel("[ R ]")
        ir.setStyleSheet(
            "color:#f0b429; font-size:54px; font-weight:900; font-family:'Courier New';")
        ir.setAlignment(Qt.AlignCenter)
        tr = lbl("RETIRAR", "h2", Qt.AlignCenter)
        tr.setStyleSheet(
            "color:#c8dff5; font-size:26px; font-weight:900; font-family:'Segoe UI';")
        dr = lbl("Recoge tus pertenencias\no sigue comprando con\ntu locker activo.", "body", Qt.AlignCenter)
        br = QPushButton("CONTINUAR"); br.setObjectName("btn_outline")
        br.setCursor(Qt.PointingHandCursor)
        br.clicked.connect(self.go_retirar.emit)
        lr.addWidget(ir); lr.addWidget(tr); lr.addWidget(dr)
        lr.addSpacing(16); lr.addWidget(br)

        cards.addWidget(cg); cards.addWidget(cr)
        vl.addLayout(cards)
        vl.addSpacing(40)

        # Estadisticas
        self.stats_frame = QFrame(); self.stats_frame.setObjectName("card")
        sl = QHBoxLayout(self.stats_frame)
        sl.setContentsMargins(30, 16, 30, 16); sl.setSpacing(0)
        self.free_lbl = lbl("", "body")
        self.busy_lbl = lbl("", "body")
        self.total_lbl= lbl("Total: {}".format(TOTAL_LOCKERS), "small")
        sl.addWidget(self.free_lbl); sl.addStretch()
        sl.addWidget(self.busy_lbl); sl.addStretch()
        sl.addWidget(self.total_lbl)
        vl.addWidget(self.stats_frame)
        vl.addSpacing(20)

        # Admin discreto
        adm = QPushButton("ADMINISTRACION"); adm.setObjectName("btn_admin")
        adm.setCursor(Qt.PointingHandCursor)
        adm.clicked.connect(self.go_admin.emit)
        adm_row = QHBoxLayout()
        adm_row.addStretch(); adm_row.addWidget(adm)
        vl.addLayout(adm_row)

    def refresh(self):
        DB.update(load_db())
        free = sum(1 for v in DB["lockers"].values() if v["status"] == "libre")
        busy = TOTAL_LOCKERS - free
        self.free_lbl.setText("Lockers libres: {}".format(free))
        self.free_lbl.setStyleSheet("color:#3de8a0; font-size:14px; font-family:'Segoe UI';")
        self.busy_lbl.setText("Lockers ocupados: {}".format(busy))
        self.busy_lbl.setStyleSheet("color:#f0b429; font-size:14px; font-family:'Segoe UI';")


# ══════════════════════════════════════════════════════
#  PAGINA: GUARDAR  (solo captura facial, asignacion automatica)
# ══════════════════════════════════════════════════════
class GuardarPage(QWidget):
    done   = pyqtSignal(str, str)   # uid, locker_num
    failed = pyqtSignal(str)         # mensaje error
    go_back= pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self.cam_thread = None
        self._uid = None

        vl = QVBoxLayout(self)
        vl.setContentsMargins(60, 40, 60, 40)
        vl.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        back = QPushButton("< Volver"); back.setObjectName("btn_sm")
        back.setCursor(Qt.PointingHandCursor); back.clicked.connect(self._cancel)
        tit = lbl("GUARDAR PERTENENCIAS", "h2")
        sub2= lbl("ASIGNACION AUTOMATICA DE LOCKER", "tag")
        htxt = QVBoxLayout(); htxt.setSpacing(4)
        htxt.addWidget(tit); htxt.addWidget(sub2)
        hdr.addWidget(back); hdr.addSpacing(20); hdr.addLayout(htxt); hdr.addStretch()
        vl.addLayout(hdr)
        vl.addWidget(sep_line())

        # Cuerpo
        body = QHBoxLayout(); body.setSpacing(32)

        # Izquierda: info
        left = QFrame(); left.setObjectName("card")
        ll   = QVBoxLayout(left); ll.setContentsMargins(30, 30, 30, 30); ll.setSpacing(18)

        ll.addWidget(lbl("COMO FUNCIONA", "tag"))
        for n, t in [("1", "Mira directamente a la camara"),
                     ("2", "El sistema captura tu biometria"),
                     ("3", "Se te asigna un locker disponible"),
                     ("4", "Guarda tus cosas y a comprar")]:
            ll.addWidget(_step(n, t))

        ll.addStretch()

        self.avail_lbl = lbl("", "body")
        ll.addWidget(self.avail_lbl)

        self.start_btn = QPushButton("REGISTRAR BIOMETRIA")
        self.start_btn.setObjectName("btn_blue")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self._start)
        ll.addWidget(self.start_btn)

        self.err_lbl = lbl("", "err"); self.err_lbl.setWordWrap(True)
        ll.addWidget(self.err_lbl)

        # Derecha: camara
        right = QWidget()
        rl    = QVBoxLayout(right); rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(12)
        rl.addWidget(lbl("ESCANER BIOMETRICO", "tag", Qt.AlignCenter))
        self.cam = CamWidget(460, 340)
        rl.addWidget(self.cam)
        rl.addStretch()

        body.addWidget(left, 1)
        body.addWidget(right, 2)
        vl.addLayout(body, 1)

    def showEvent(self, e):
        super().showEvent(e)
        free = next_free_locker()
        if free:
            self.avail_lbl.setText("Lockers disponibles. Se te asignara el #{:02d}.".format(int(free)))
            self.avail_lbl.setStyleSheet("color:#3de8a0; font-size:13px; font-family:'Segoe UI';")
            self.start_btn.setEnabled(True)
        else:
            self.avail_lbl.setText("No hay lockers disponibles en este momento.")
            self.avail_lbl.setStyleSheet("color:#f03d5a; font-size:13px; font-family:'Segoe UI';")
            self.start_btn.setEnabled(False)

    def _start(self):
        locker = next_free_locker()
        if not locker:
            self.err_lbl.setText("Sin lockers disponibles.")
            return
        uid = "user_{}".format(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        self._uid = uid
        self.start_btn.setEnabled(False)
        self.err_lbl.setText("")
        self.cam_thread = CamThread(CamThread.CAPTURE, uid=uid)
        self.cam_thread.frame_sig.connect(self.cam.update_frame)
        self.cam_thread.progress.connect(self.cam.set_progress)
        self.cam_thread.cap_done.connect(lambda ok, u=uid: self._on_done(ok, u))
        self.cam_thread.start()

    def _on_done(self, ok, uid):
        self.cam.idle()
        self.start_btn.setEnabled(True)
        if ok:
            locker = next_free_locker()
            if locker:
                assign_locker(uid, locker)
                train_model()
                self.done.emit(uid, locker)
            else:
                # Borrar biometria ya que no hay locker
                shutil.rmtree(os.path.join(FACES_DIR, uid), ignore_errors=True)
                self.failed.emit("Sin lockers disponibles.")
        else:
            shutil.rmtree(os.path.join(FACES_DIR, uid), ignore_errors=True)
            self.err_lbl.setText("Error al capturar. Intenta de nuevo.")

    def _cancel(self):
        if self.cam_thread: self.cam_thread.stop()
        self.go_back.emit()

    def reset(self):
        if self.cam_thread: self.cam_thread.stop()
        self.err_lbl.setText("")
        self.cam.idle()
        self.start_btn.setEnabled(True)
        self._uid = None


# ══════════════════════════════════════════════════════
#  PAGINA: RETIRAR
# ══════════════════════════════════════════════════════
class RetirarPage(QWidget):
    go_back      = pyqtSignal()
    retirar_done = pyqtSignal(str, str)
    seguir_done  = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self.cam_thread = None
        self._uid = None

        vl = QVBoxLayout(self)
        vl.setContentsMargins(60, 40, 60, 40)
        vl.setSpacing(16)

        hdr = QHBoxLayout()
        back = QPushButton("< Volver"); back.setObjectName("btn_sm")
        back.setCursor(Qt.PointingHandCursor); back.clicked.connect(self._cancel)
        tit  = lbl("RETIRAR / CONTINUAR", "h2")
        sub2 = lbl("VERIFICACION BIOMETRICA", "tag")
        htxt = QVBoxLayout(); htxt.setSpacing(4)
        htxt.addWidget(tit); htxt.addWidget(sub2)
        hdr.addWidget(back); hdr.addSpacing(20); hdr.addLayout(htxt); hdr.addStretch()
        vl.addLayout(hdr)
        vl.addWidget(sep_line())

        body = QHBoxLayout(); body.setSpacing(32)

        # Izquierda
        left = QFrame(); left.setObjectName("card")
        ll   = QVBoxLayout(left); ll.setContentsMargins(30, 30, 30, 30); ll.setSpacing(18)

        ll.addWidget(lbl("VERIFICACION DE IDENTIDAD", "tag"))
        for n, t in [("1","Acerca tu rostro a la camara"),
                     ("2","Mantén expresion neutra"),
                     ("3","Escoge tu opcion")]:
            ll.addWidget(_step(n, t))

        ll.addStretch()

        self.scan_btn = QPushButton("INICIAR ESCANEO")
        self.scan_btn.setObjectName("btn_outline")
        self.scan_btn.setCursor(Qt.PointingHandCursor)
        self.scan_btn.clicked.connect(self._start_scan)
        ll.addWidget(self.scan_btn)

        self.scan_lbl = lbl("", "small", Qt.AlignCenter)
        ll.addWidget(self.scan_lbl)

        ll.addWidget(sep_line())

        # Opciones post-reconocimiento
        self.opts = QFrame()
        ol = QVBoxLayout(self.opts); ol.setContentsMargins(0, 0, 0, 0); ol.setSpacing(12)
        self.user_lbl   = lbl("", "ok")
        self.locker_lbl = lbl("", "h3")
        self.locker_lbl.setStyleSheet("color:#4d8ec4; font-size:20px; font-weight:900; font-family:'Segoe UI';")
        ol.addWidget(self.user_lbl)
        ol.addWidget(self.locker_lbl)
        self.btn_ret = QPushButton("RETIRAR COSAS Y SALIR")
        self.btn_ret.setObjectName("btn_red")
        self.btn_ret.setCursor(Qt.PointingHandCursor)
        self.btn_ret.clicked.connect(self._do_retirar)
        self.btn_seg = QPushButton("SEGUIR COMPRANDO")
        self.btn_seg.setObjectName("btn_green")
        self.btn_seg.setCursor(Qt.PointingHandCursor)
        self.btn_seg.clicked.connect(self._do_seguir)
        ol.addWidget(self.btn_ret)
        ol.addWidget(self.btn_seg)
        self.opts.setVisible(False)
        ll.addWidget(self.opts)

        # Derecha: camara
        right = QWidget()
        rl    = QVBoxLayout(right); rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(12)
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
        self.cam_thread.rec_done.connect(self._on_rec)
        self.cam_thread.start()

    def _on_rec(self, uid):
        self.scan_btn.setEnabled(True)
        self.cam.idle()
        if not uid:
            self.scan_lbl.setText("No se reconocio el rostro. Intenta de nuevo.")
            self.scan_lbl.setStyleSheet("color:#f03d5a; font-size:12px; font-family:'Segoe UI';")
            return
        self._uid = uid
        locker = get_user_locker(uid)
        self.scan_lbl.setText("")
        self.user_lbl.setText("Identidad verificada")
        self.locker_lbl.setText(
            "Locker #{:02d}".format(int(locker)) if locker else "Sin locker activo")
        self.btn_ret.setVisible(bool(locker))
        self.btn_seg.setVisible(bool(locker))
        self.opts.setVisible(True)

    def _do_retirar(self):
        uid = self._uid
        locker = get_user_locker(uid)
        if locker:
            release_user(uid)
            self.retirar_done.emit(uid, locker)

    def _do_seguir(self):
        uid = self._uid
        locker = get_user_locker(uid) or ""
        self.seguir_done.emit(uid, locker)

    def _cancel(self):
        if self.cam_thread: self.cam_thread.stop()
        self.go_back.emit()

    def reset(self):
        if self.cam_thread: self.cam_thread.stop()
        self._uid = None
        self.opts.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.scan_lbl.setText("")
        self.scan_lbl.setStyleSheet("")
        self.cam.idle()


# ══════════════════════════════════════════════════════
#  PAGINA: RESULTADO (con auto-redireccion)
# ══════════════════════════════════════════════════════
class ResultPage(QWidget):
    go_home = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self._vl = QVBoxLayout(self)
        self._vl.setContentsMargins(80, 80, 80, 80)
        self._vl.setAlignment(Qt.AlignCenter)
        self._card = None
        self._timer_w = AutoTimer(AUTO_HOME_SEC)
        self._timer_w.timeout.connect(self.go_home.emit)

    def show_result(self, kind, title, subtitle, detail=""):
        if self._card:
            self._vl.removeWidget(self._card)
            self._card.deleteLater()
        if self._vl.indexOf(self._timer_w) >= 0:
            self._vl.removeWidget(self._timer_w)

        frame_map = {"ok":"card_green","warn":"card_yellow","err":"card_red"}
        color_map  = {"ok":"#3de8a0","warn":"#f0b429","err":"#f03d5a"}
        icon_map   = {"ok":"[  OK  ]","warn":"[ ! ]","err":"[ X ]"}

        fn    = frame_map.get(kind, "card")
        color = color_map.get(kind, "#c8dff5")
        icon  = icon_map.get(kind, "[ ? ]")

        card = QFrame(); card.setObjectName(fn)
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(70, 60, 70, 60); cl.setSpacing(24)
        cl.setAlignment(Qt.AlignCenter)

        i_lbl = QLabel(icon); i_lbl.setAlignment(Qt.AlignCenter)
        i_lbl.setStyleSheet(
            "font-size:42px; color:{}; font-family:'Courier New'; font-weight:900;".format(color))
        t_lbl = QLabel(title); t_lbl.setAlignment(Qt.AlignCenter)
        t_lbl.setStyleSheet(
            "font-size:30px; font-weight:900; color:{};"
            "font-family:'Segoe UI'; letter-spacing:-1px;".format(color))
        s_lbl = QLabel(subtitle); s_lbl.setAlignment(Qt.AlignCenter)
        s_lbl.setObjectName("body"); s_lbl.setWordWrap(True)

        cl.addWidget(i_lbl); cl.addWidget(t_lbl); cl.addWidget(s_lbl)

        if detail:
            d_lbl = QLabel(detail); d_lbl.setAlignment(Qt.AlignCenter)
            d_lbl.setStyleSheet(
                "font-size:38px; font-weight:900; color:{};"
                "font-family:'Courier New';".format(color))
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


# ══════════════════════════════════════════════════════
#  ADMIN LOGIN
# ══════════════════════════════════════════════════════
class AdminLoginPage(QWidget):
    go_back  = pyqtSignal()
    login_ok = pyqtSignal(str)   # username

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setAlignment(Qt.AlignCenter)

        card = QFrame(); card.setObjectName("card_blue")
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(56, 48, 56, 48); cl.setSpacing(18)
        card.setFixedWidth(440)

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
        if not admin_exists(u):
            self.err_lbl.setText("Usuario no encontrado.")
            return
        if not admin_valid(u, p):
            self.err_lbl.setText("Contrasena incorrecta.")
            self.pass_inp.clear()
            return
        self.err_lbl.setText("")
        self.user_inp.clear(); self.pass_inp.clear()
        self.login_ok.emit(u)

    def reset(self):
        self.user_inp.clear(); self.pass_inp.clear(); self.err_lbl.setText("")


# ══════════════════════════════════════════════════════
#  ADMIN PANEL
# ══════════════════════════════════════════════════════
class AdminPage(QWidget):
    go_back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("page")
        self._current_admin = ""
        vl = QVBoxLayout(self)
        vl.setContentsMargins(48, 36, 48, 36)
        vl.setSpacing(0)

        # Header
        hdr = QHBoxLayout()
        bk   = QPushButton("< Cerrar sesion"); bk.setObjectName("btn_sm")
        bk.setCursor(Qt.PointingHandCursor); bk.clicked.connect(self.go_back.emit)
        tit  = lbl("Panel de Administracion", "h2")
        self.admin_badge = lbl("", "badge_blue")
        hdr.addWidget(bk); hdr.addSpacing(16)
        hdr.addWidget(tit); hdr.addStretch(); hdr.addWidget(self.admin_badge)
        vl.addLayout(hdr)
        vl.addSpacing(12)
        vl.addWidget(sep_line())
        vl.addSpacing(4)

        # Tabs
        tab_row = QHBoxLayout(); tab_row.setSpacing(0); tab_row.setContentsMargins(0,0,0,0)
        self.t_lockers = QPushButton("LOCKERS");     self.t_lockers.setObjectName("tab"); self.t_lockers.setCheckable(True); self.t_lockers.setChecked(True)
        self.t_users   = QPushButton("USUARIOS FACIALES"); self.t_users.setObjectName("tab");   self.t_users.setCheckable(True)
        self.t_admins  = QPushButton("ADMINISTRADORES");  self.t_admins.setObjectName("tab");  self.t_admins.setCheckable(True)
        for b, i in [(self.t_lockers,0),(self.t_users,1),(self.t_admins,2)]:
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _, x=i: self._tab(x))
            tab_row.addWidget(b)
        tab_row.addStretch()
        vl.addLayout(tab_row)
        vl.addWidget(sep_line())
        vl.addSpacing(16)

        self.stack = QStackedWidget()
        self.p_lockers = _LockerPanel()
        self.p_users   = _UsersPanel()
        self.p_admins  = _AdminsPanel()
        self.stack.addWidget(self.p_lockers)
        self.stack.addWidget(self.p_users)
        self.stack.addWidget(self.p_admins)
        vl.addWidget(self.stack, 1)

    def _tab(self, i):
        self.stack.setCurrentIndex(i)
        for j, b in enumerate([self.t_lockers, self.t_users, self.t_admins]):
            b.setChecked(j == i)
        if i == 0: self.p_lockers.refresh()
        if i == 1: self.p_users.refresh()
        if i == 2: self.p_admins.refresh()

    def set_admin(self, username):
        self._current_admin = username
        self.admin_badge.setText("  {}  ".format(username.upper()))

    def showEvent(self, e):
        super().showEvent(e)
        self._tab(0)


class _LockerPanel(QWidget):
    def __init__(self):
        super().__init__()
        vl = QVBoxLayout(self); vl.setContentsMargins(0,0,0,0); vl.setSpacing(16)

        self.stats_row = QHBoxLayout(); self.stats_row.setSpacing(12)
        vl.addLayout(self.stats_row)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        inner  = QWidget(); inner.setObjectName("page")
        il     = QVBoxLayout(inner); il.setContentsMargins(0,0,0,0)
        self.grid = QGridLayout(); self.grid.setSpacing(12)
        il.addLayout(self.grid); il.addStretch()
        scroll.setWidget(inner)
        vl.addWidget(scroll, 1)

        acts = QHBoxLayout(); acts.setSpacing(12)
        btn_lib = QPushButton("LIBERAR LOCKER"); btn_lib.setObjectName("btn_outline")
        btn_lib.setCursor(Qt.PointingHandCursor); btn_lib.clicked.connect(self._liberar)
        btn_ref = QPushButton("Actualizar"); btn_ref.setObjectName("btn_sm")
        btn_ref.setCursor(Qt.PointingHandCursor); btn_ref.clicked.connect(self.refresh)
        acts.addWidget(btn_lib); acts.addWidget(btn_ref); acts.addStretch()
        vl.addLayout(acts)
        self.refresh()

    def _liberar(self):
        num, ok = QInputDialog.getText(None, "Liberar Locker", "Numero de locker:")
        if ok and num.strip():
            n = num.strip()
            if n in DB["lockers"] and DB["lockers"][n]["status"] == "ocupado":
                free_locker_admin(n)
                QMessageBox.information(None, "OK", "Locker #{} liberado.".format(n))
                self.refresh()
            else:
                QMessageBox.warning(None, "Error", "Locker no encontrado o ya libre.")

    def refresh(self):
        DB.update(load_db())
        # Stats
        for i in reversed(range(self.stats_row.count())):
            item = self.stats_row.itemAt(i)
            if item and item.widget(): item.widget().deleteLater()
        free = sum(1 for v in DB["lockers"].values() if v["status"] == "libre")
        busy = TOTAL_LOCKERS - free
        for text, val, color, badge in [
            ("LIBRES",   free,          "#3de8a0","badge_green"),
            ("OCUPADOS", busy,          "#f0b429","badge_yellow"),
            ("TOTAL",    TOTAL_LOCKERS, "#4d8ec4","badge_blue"),
        ]:
            sf = QFrame(); sf.setObjectName("card")
            sl = QHBoxLayout(sf); sl.setContentsMargins(20,12,20,12); sl.setSpacing(10)
            n = QLabel(str(val))
            n.setStyleSheet("color:{}; font-size:24px; font-weight:900; font-family:'Segoe UI';".format(color))
            t = lbl(text, "small")
            sl.addWidget(n); sl.addWidget(t)
            self.stats_row.addWidget(sf)
        self.stats_row.addStretch()

        # Grid
        for i in reversed(range(self.grid.count())):
            item = self.grid.itemAt(i)
            if item and item.widget(): item.widget().deleteLater()

        cols = 4
        for i, (num, info) in enumerate(sorted(DB["lockers"].items(), key=lambda x: int(x[0]))):
            fr = QFrame()
            fr.setObjectName("lk_free" if info["status"] == "libre" else "lk_busy")
            fl = QVBoxLayout(fr); fl.setContentsMargins(10,10,10,10); fl.setAlignment(Qt.AlignCenter)
            color = "#4d8ec4" if info["status"] == "libre" else "#f0b429"
            n_lbl = QLabel("#{:02d}".format(int(num)))
            n_lbl.setStyleSheet("color:{}; font-size:18px; font-weight:900; font-family:'Segoe UI';".format(color))
            n_lbl.setAlignment(Qt.AlignCenter)
            s_lbl_text = "LIBRE" if info["status"] == "libre" else (info["user"] or "OCUPADO")
            s_lbl = lbl(s_lbl_text[:12], "small", Qt.AlignCenter)
            fl.addWidget(n_lbl); fl.addWidget(s_lbl)
            row, col = divmod(i, cols)
            self.grid.addWidget(fr, row, col)


class _UsersPanel(QWidget):
    def __init__(self):
        super().__init__()
        vl = QVBoxLayout(self); vl.setContentsMargins(0,0,0,0); vl.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(lbl("Usuarios con biometria registrada", "body"))
        top.addStretch()
        btn_ref = QPushButton("Actualizar"); btn_ref.setObjectName("btn_sm")
        btn_ref.setCursor(Qt.PointingHandCursor); btn_ref.clicked.connect(self.refresh)
        top.addWidget(btn_ref)
        vl.addLayout(top)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.inner = QWidget(); self.inner.setObjectName("page")
        self.il = QVBoxLayout(self.inner)
        self.il.setContentsMargins(0,0,0,0); self.il.setSpacing(8)
        scroll.setWidget(self.inner)
        vl.addWidget(scroll, 1)

        acts = QHBoxLayout()
        btn_del = QPushButton("ELIMINAR USUARIO"); btn_del.setObjectName("btn_red")
        btn_del.setCursor(Qt.PointingHandCursor); btn_del.clicked.connect(self._delete)
        acts.addWidget(btn_del); acts.addStretch()
        vl.addLayout(acts)
        self.refresh()

    def _delete(self):
        uid, ok = QInputDialog.getText(None, "Eliminar Usuario", "ID del usuario:")
        if ok and uid.strip():
            uid = uid.strip()
            if uid in DB["face_users"]:
                release_user(uid)
                train_model()
                QMessageBox.information(None, "OK", "Usuario eliminado.")
                self.refresh()
            else:
                QMessageBox.warning(None, "Error", "Usuario no encontrado.")

    def refresh(self):
        DB.update(load_db())
        for i in reversed(range(self.il.count())):
            item = self.il.itemAt(i)
            if item and item.widget(): item.widget().deleteLater()

        users = DB.get("face_users", {})
        if not users:
            self.il.addWidget(lbl("No hay usuarios registrados.", "small"))
        else:
            for uid, info in users.items():
                row = QFrame(); row.setObjectName("card")
                rl  = QHBoxLayout(row); rl.setContentsMargins(20,14,20,14); rl.setSpacing(16)
                n   = lbl(uid, "body")
                n.setStyleSheet("color:#c8dff5; font-size:14px; font-weight:700; font-family:'Segoe UI';")
                since = lbl(info.get("created",""), "small")
                loc   = info.get("locker","")
                loc_lbl_obj = "badge_blue" if loc else "badge_red"
                loc_text    = "Locker #{}".format(loc) if loc else "Sin locker"
                lk = lbl(loc_text, loc_lbl_obj)
                rl.addWidget(n); rl.addWidget(since); rl.addStretch(); rl.addWidget(lk)
                self.il.addWidget(row)
        self.il.addStretch()


class _AdminsPanel(QWidget):
    """Registro y gestion de administradores con usuario/contrasena."""
    def __init__(self):
        super().__init__()
        vl = QVBoxLayout(self); vl.setContentsMargins(0,0,0,0); vl.setSpacing(16)

        body = QHBoxLayout(); body.setSpacing(28)

        # Lista de admins
        left = QFrame(); left.setObjectName("card")
        ll   = QVBoxLayout(left); ll.setContentsMargins(24,24,24,24); ll.setSpacing(12)
        ll.addWidget(lbl("ADMINISTRADORES ACTIVOS", "tag"))
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.inner = QWidget(); self.inner.setObjectName("modal")
        self.il = QVBoxLayout(self.inner)
        self.il.setContentsMargins(0,0,0,0); self.il.setSpacing(8)
        scroll.setWidget(self.inner)
        ll.addWidget(scroll, 1)

        btn_del = QPushButton("ELIMINAR SELECCIONADO"); btn_del.setObjectName("btn_red")
        btn_del.setCursor(Qt.PointingHandCursor); btn_del.clicked.connect(self._delete)
        ll.addWidget(btn_del)

        # Formulario registro
        right = QFrame(); right.setObjectName("card_blue")
        rl    = QVBoxLayout(right); rl.setContentsMargins(28,28,28,28); rl.setSpacing(14)
        rl.addWidget(lbl("REGISTRAR NUEVO ADMIN", "tag"))
        rl.addWidget(sep_line())

        rl.addWidget(lbl("Nombre de usuario"))
        self.new_user = QLineEdit(); self.new_user.setObjectName("inp")
        self.new_user.setPlaceholderText("admin01")
        rl.addWidget(self.new_user)

        rl.addWidget(lbl("Contrasena"))
        self.new_pass = QLineEdit(); self.new_pass.setObjectName("inp")
        self.new_pass.setEchoMode(QLineEdit.Password)
        self.new_pass.setPlaceholderText("••••••••")
        rl.addWidget(self.new_pass)

        rl.addWidget(lbl("Confirmar contrasena"))
        self.new_pass2 = QLineEdit(); self.new_pass2.setObjectName("inp")
        self.new_pass2.setEchoMode(QLineEdit.Password)
        self.new_pass2.setPlaceholderText("••••••••")
        rl.addWidget(self.new_pass2)

        self.reg_err = lbl("", "err", Qt.AlignCenter)
        rl.addWidget(self.reg_err)

        self.reg_ok_lbl = lbl("", "ok", Qt.AlignCenter)
        rl.addWidget(self.reg_ok_lbl)

        btn_reg = QPushButton("REGISTRAR ADMINISTRADOR"); btn_reg.setObjectName("btn_blue")
        btn_reg.setCursor(Qt.PointingHandCursor); btn_reg.clicked.connect(self._register)
        rl.addWidget(btn_reg)
        rl.addStretch()

        body.addWidget(left, 1)
        body.addWidget(right, 1)
        vl.addLayout(body, 1)
        self.refresh()

    def _register(self):
        u  = self.new_user.text().strip()
        p  = self.new_pass.text()
        p2 = self.new_pass2.text()
        self.reg_err.setText(""); self.reg_ok_lbl.setText("")
        if not u or not p:
            self.reg_err.setText("Completa todos los campos."); return
        if len(p) < 4:
            self.reg_err.setText("La contrasena debe tener al menos 4 caracteres."); return
        if p != p2:
            self.reg_err.setText("Las contrasenas no coinciden."); return
        if admin_exists(u):
            self.reg_err.setText("Ya existe un admin con ese nombre."); return
        admin_register(u, p)
        self.new_user.clear(); self.new_pass.clear(); self.new_pass2.clear()
        self.reg_ok_lbl.setText("Admin '{}' registrado.".format(u))
        self.refresh()

    def _delete(self):
        u, ok = QInputDialog.getText(None, "Eliminar Admin", "Usuario a eliminar:")
        if ok and u.strip():
            if admin_exists(u.strip()):
                if len(DB["admins"]) <= 1:
                    QMessageBox.warning(None, "Error", "Debes tener al menos un administrador.")
                    return
                admin_delete(u.strip())
                QMessageBox.information(None, "OK", "Admin '{}' eliminado.".format(u.strip()))
                self.refresh()
            else:
                QMessageBox.warning(None, "Error", "Admin no encontrado.")

    def refresh(self):
        for i in reversed(range(self.il.count())):
            item = self.il.itemAt(i)
            if item and item.widget(): item.widget().deleteLater()
        admins = DB.get("admins", {})
        if not admins:
            self.il.addWidget(lbl("Sin administradores.", "small"))
        else:
            for u in admins:
                row = QFrame(); row.setObjectName("card")
                rl  = QHBoxLayout(row); rl.setContentsMargins(16,12,16,12)
                n   = lbl(u, "body")
                n.setStyleSheet("color:#c8dff5; font-size:14px; font-weight:700; font-family:'Segoe UI';")
                bk  = lbl("ADMIN", "badge_blue")
                rl.addWidget(n); rl.addStretch(); rl.addWidget(bk)
                self.il.addWidget(row)
        self.il.addStretch()


# ══════════════════════════════════════════════════════
#  HELPER: bullet paso
# ══════════════════════════════════════════════════════
def _step(num, text):
    w  = QWidget()
    hl = QHBoxLayout(w); hl.setContentsMargins(0,0,0,0); hl.setSpacing(12)
    n  = QLabel(num)
    n.setStyleSheet(
        "background:#1a6ef5; color:#fff; border-radius:12px;"
        "font-weight:800; font-family:'Segoe UI'; font-size:13px;"
        "min-width:24px; max-width:24px; min-height:24px; max-height:24px;")
    n.setAlignment(Qt.AlignCenter)
    t  = lbl(text, "body")
    hl.addWidget(n); hl.addWidget(t)
    return w


# ══════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════
class MainWindow(QMainWindow):
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
        ml = QVBoxLayout(cw); ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)

        self.stack = QStackedWidget()
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

        # Conexiones
        self.p_home.go_guardar.connect(lambda: self._nav(self.GUARD))
        self.p_home.go_retirar.connect(lambda: self._nav(self.RETIR))
        self.p_home.go_admin.connect(lambda: self._nav(self.ALOGIN))

        self.p_guard.go_back.connect(lambda: self._nav(self.HOME))
        self.p_guard.done.connect(self._on_guardado)
        self.p_guard.failed.connect(lambda msg: self._show_result("err","Sin espacio",msg))

        self.p_retir.go_back.connect(lambda: self._nav(self.HOME))
        self.p_retir.retirar_done.connect(self._on_retirado)
        self.p_retir.seguir_done.connect(self._on_seguir)

        self.p_result.go_home.connect(lambda: self._nav(self.HOME))

        self.p_alogin.go_back.connect(lambda: self._nav(self.HOME))
        self.p_alogin.login_ok.connect(self._on_login)

        self.p_admin.go_back.connect(lambda: self._nav(self.HOME))

        self._nav(self.HOME)

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

    def _on_guardado(self, uid, locker):
        self.p_guard.reset()
        self._show_result(
            "ok",
            "Locker Asignado",
            "Tus pertenencias quedaron seguras. Recuerda tu locker.",
            "LOCKER #{:02d}".format(int(locker))
        )

    def _on_retirado(self, uid, locker):
        self.p_retir.reset()
        self._show_result(
            "warn",
            "Hasta Pronto",
            "El locker #{:02d} ha sido liberado. Recoge tus cosas.".format(int(locker)),
            "LOCKER #{:02d}".format(int(locker))
        )

    def _on_seguir(self, uid, locker):
        self.p_retir.reset()
        detail = "LOCKER #{:02d}".format(int(locker)) if locker else ""
        self._show_result(
            "ok",
            "Que sigas comprando",
            "Tus cosas permanecen seguras en tu locker.",
            detail
        )

    def _on_login(self, username):
        self.p_admin.set_admin(username)
        self._nav(self.ADMIN)


# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════
if __name__ == '__main__':
    # Crear admin por defecto si no hay ninguno
    if not DB.get("admins"):
        admin_register("admin", "admin1234")
        print("[INFO] Admin por defecto creado: usuario='admin' contrasena='admin1234'")
        print("[INFO] Cambialo desde el panel de administracion.")

    train_model()
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())