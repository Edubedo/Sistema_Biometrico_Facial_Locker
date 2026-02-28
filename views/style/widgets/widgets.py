from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import  QPixmap

AUTO_HOME_SEC = 6

def sep_line():
    f = QFrame()
    f.setObjectName("sep")
    f.setFrameShape(QFrame.HLine)
    return f


def lbl(text, obj="body", align=None):
    l = QLabel(text)
    l.setObjectName(obj)
    if align is not None:
        l.setAlignment(align)
    return l


def _step_bullet(num, text):
    """Widget de paso numerado con circulo azul."""
    w  = QWidget()
    hl = QHBoxLayout(w)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(12)
    n  = QLabel(str(num))
    n.setStyleSheet(
        "background:#1a6ef5; color:#fff; border-radius:12px;"
        "font-weight:800; font-family:'Segoe UI'; font-size:13px;"
        "min-width:24px; max-width:24px; min-height:24px; max-height:24px;"
    )
    n.setAlignment(Qt.AlignCenter)
    t  = lbl(text, "body")
    hl.addWidget(n)
    hl.addWidget(t)
    return w


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

        # Barra de progreso (visible solo durante captura)
        self.prog_bg = QFrame()
        self.prog_bg.setObjectName("prog_bg")
        self.prog_bg.setFixedHeight(12)
        pl = QHBoxLayout(self.prog_bg)
        pl.setContentsMargins(0, 0, 0, 0)
        self.prog_fill = QFrame()
        self.prog_fill.setObjectName("prog_fill")
        self.prog_fill.setFixedHeight(12)
        self.prog_fill.setFixedWidth(0)
        pl.addWidget(self.prog_fill)
        pl.addStretch()
        self.prog_bg.setVisible(False)
        vl.addWidget(self.prog_bg)

    def update_frame(self, qimg):
        pix = QPixmap.fromImage(qimg).scaled(
            self.view.width(), self.view.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.view.setPixmap(pix)

    def set_progress(self, n, total=20):
        self.prog_bg.setVisible(True)
        pct = min(n / total, 1.0)
        self.prog_fill.setFixedWidth(max(int(self.prog_bg.width() * pct), 0))
        self.status.setText("Capturando biometria... {}/{}".format(n, total))
        self.status.setStyleSheet("color:#4d8ec4; font-size:13px; font-family:'Segoe UI';")

    def set_status(self, text, color="#7ca8d0"):
        self.status.setText(text)
        self.status.setStyleSheet(
            "color:{}; font-size:13px; font-family:'Segoe UI';".format(color)
        )

    def idle(self):
        self.view.clear()
        self.view.setText("Camara inactiva")
        self.status.setText("")
        self.prog_bg.setVisible(False)
        self.prog_fill.setFixedWidth(0)


class AutoTimer(QWidget):
    """Cuenta regresiva que emite timeout() al llegar a 0."""

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
        self._refresh()
        self._timer.start(1000)

    def stop(self):
        self._timer.stop()

    def _tick(self):
        self._left -= 1
        self._refresh()
        if self._left <= 0:
            self._timer.stop()
            self.timeout.emit()

    def _refresh(self):
        self._lbl.setText("Regresando al inicio en {}s...".format(self._left))

