from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QApplication,
    QDialog, QScroller, QLineEdit, QComboBox,
    QGraphicsDropShadowEffect,
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QPen

from db.models.lockers import (
    db_get_all_lockers, db_insert_locker,
    db_set_locker_estado, db_update_locker,
)
from db.models.sesiones import db_close_sesion, db_get_all_sesiones_activas
from db.models.intentos_acceso import db_log_intento
from biometria.biometria import train_model
from views.style.adminDialogs import DlgError, DlgInfo, DlgInput, DlgLiberar
from utils.i18n import tr, get_language


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _dp(v: float) -> int:
    s = QApplication.primaryScreen()
    scale = min((s.logicalDotsPerInch() if s else 96) / 96, 1.25)
    return max(1, round(v * scale))

_TOUCH_H = 52   # altura mínima táctil

def _shadow(w, blur=12, alpha=18, dy=2):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur); s.setColor(QColor(21, 101, 192, alpha)); s.setOffset(0, dy)
    w.setGraphicsEffect(s)


# ─────────────────────────────────────────────────────────────────────────────
#  Paleta
# ─────────────────────────────────────────────────────────────────────────────
BLUE_DARK  = "#1d4ed8"
BLUE_MID   = "#3b82f6"
BLUE_LIGHT = "#60a5fa"
BLUE_PALE  = "#93c5fd"
ORANGE     = "#f97316"
WHITE      = "#ffffff"
GRAY_CHIP  = "#e8eef8"
GRAY_TEXT  = "#64748b"
RED_BG     = "#fee2e2"
RED_TEXT   = "#b91c1c"

# (card_bg, accent_color, badge_bg, badge_fg)
_STATE = {
    "libre":         (WHITE,   BLUE_DARK,  "#e0f2fe",  "#1e3a8a"),
    "ocupado":       (WHITE,   ORANGE,     "#fff3e8",  "#c2410c"),
    "mantenimiento": (WHITE,   "#78909c",  "#eceff1",  "#546e7a"),
}


# ─────────────────────────────────────────────────────────────────────────────
#  Icono del locker  (sin cambios — solo se reusa)
# ─────────────────────────────────────────────────────────────────────────────
class LockerIcon(QWidget):
    def __init__(self, estado="ocupado", parent=None):
        super().__init__(parent)
        self.setFixedSize(72, 86)
        self.estado = estado
        self._bg = QColor(WHITE)

    def set_estado(self, estado, bg=WHITE):
        self.estado = estado; self._bg = QColor(bg); self.update()

    def _c(self, h): return QColor(h)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), self._bg)
        p.scale(self.width() / 54.0, self.height() / 64.0)
        if self.estado == "libre":      self._draw_open(p)
        elif self.estado == "mant":     self._draw_maint(p)
        else:                           self._draw_closed(p)
        p.end()

    def _draw_closed(self, p):
        c = self._c
        p.setPen(QPen(c(BLUE_DARK), 2)); p.setBrush(QBrush(c(BLUE_LIGHT)))
        p.drawRoundedRect(4, 6, 46, 54, 5, 5)
        p.setBrush(QBrush(c(BLUE_MID))); p.drawRoundedRect(4, 6, 46, 10, 5, 5)
        p.setPen(QPen(c(BLUE_DARK), 1)); p.setBrush(QBrush(c("#e0f2fe")))
        p.drawEllipse(20, 11, 14, 10)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c("#1e3a8a"))); p.drawEllipse(24, 14, 7, 4)
        p.setBrush(QBrush(c(WHITE))); p.drawEllipse(25, 13, 2, 2)
        p.setBrush(QBrush(c(BLUE_DARK)))
        for y in [26, 30, 34]: p.drawRoundedRect(19, y, 16, 3, 1, 1)
        p.setPen(QPen(c("#94a3b8"), 1)); p.setBrush(QBrush(c("#e2e8f0")))
        p.drawEllipse(38, 35, 7, 7)
        p.setPen(QPen(c("#94a3b8"), 2)); p.drawLine(41, 42, 41, 52)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c("#94a3b8"))); p.drawEllipse(38, 51, 6, 4)
        p.setBrush(QBrush(c(BLUE_DARK)))
        p.drawRoundedRect(2, 57, 8, 5, 2, 2); p.drawRoundedRect(44, 57, 8, 5, 2, 2)

    def _draw_open(self, p):
        c = self._c
        p.setPen(QPen(c(BLUE_DARK), 2)); p.setBrush(QBrush(c(BLUE_PALE)))
        p.drawRoundedRect(4, 6, 46, 54, 5, 5)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c("#d1e8ff")))
        p.drawRoundedRect(10, 14, 34, 44, 3, 3)
        p.setPen(QPen(c("#d97706"), 1)); p.setBrush(QBrush(c("#fbbf24")))
        p.drawRoundedRect(30, 36, 14, 20, 3, 3)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c("#d97706")))
        p.drawRoundedRect(33, 33, 8, 5, 2, 2)
        p.setBrush(QBrush(c(BLUE_PALE))); p.drawRoundedRect(28, 34, 16, 2, 1, 1)
        p.setPen(QPen(c(BLUE_DARK), 2)); p.setBrush(QBrush(c(BLUE_MID)))
        p.drawRoundedRect(4, 6, 22, 54, 5, 5)
        p.setPen(QPen(c(BLUE_DARK), 1)); p.setBrush(QBrush(c("#e0f2fe")))
        p.drawEllipse(9, 12, 12, 12)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c("#1e3a8a"))); p.drawEllipse(12, 15, 6, 6)
        p.setBrush(QBrush(c(WHITE))); p.drawEllipse(13, 13, 2, 2)
        p.setBrush(QBrush(c(BLUE_DARK)))
        for y in [27, 31, 35]: p.drawRoundedRect(9, y, 12, 2, 1, 1)
        p.setPen(QPen(c(BLUE_DARK), 1)); p.setBrush(QBrush(c(BLUE_PALE)))
        p.drawRoundedRect(23, 16, 4, 8, 2, 2); p.drawRoundedRect(23, 40, 4, 8, 2, 2)
        p.setPen(QPen(c("#94a3b8"), 1)); p.setBrush(QBrush(c("#e2e8f0")))
        p.drawEllipse(38, 19, 5, 5)
        p.setPen(QPen(c("#94a3b8"), 2)); p.drawLine(41, 24, 41, 33)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c("#94a3b8"))); p.drawEllipse(38, 32, 6, 4)
        p.setBrush(QBrush(c(BLUE_DARK)))
        p.drawRoundedRect(2, 57, 8, 5, 2, 2); p.drawRoundedRect(44, 57, 8, 5, 2, 2)

    def _draw_maint(self, p):
        c = self._c; GR="#78909c"; GRL="#b0bec5"; GRP="#eceff1"
        p.setPen(QPen(c(GR), 2)); p.setBrush(QBrush(c(GRL)))
        p.drawRoundedRect(4, 6, 46, 54, 5, 5)
        p.setBrush(QBrush(c(GR))); p.drawRoundedRect(4, 6, 46, 10, 5, 5)
        p.setPen(QPen(c(GR), 1)); p.setBrush(QBrush(c(GRP))); p.drawEllipse(20, 11, 14, 10)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c("#546e7a"))); p.drawEllipse(24, 14, 7, 4)
        p.setBrush(QBrush(c(WHITE))); p.drawEllipse(25, 13, 2, 2)
        p.setBrush(QBrush(c(GR)))
        for y in [26, 30, 34]: p.drawRoundedRect(19, y, 16, 3, 1, 1)
        p.setPen(QPen(c("#546e7a"), 3))
        p.drawLine(22, 42, 32, 52); p.drawLine(32, 42, 22, 52)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c(GR)))
        p.drawRoundedRect(2, 57, 8, 5, 2, 2); p.drawRoundedRect(44, 57, 8, 5, 2, 2)


# ─────────────────────────────────────────────────────────────────────────────
#  Diálogo de configuración — rediseñado para touch
# ─────────────────────────────────────────────────────────────────────────────
def _build_dlg_style():
    INP_H = _dp(52)
    r10   = _dp(10); r8 = _dp(8); r6 = _dp(6)
    TH    = _dp(_TOUCH_H)
    return f"""
QDialog#locker_dlg {{ background: #f0f6ff; }}
QLabel#dlg_title {{
    color: #ffffff; font-weight: 900; font-family: 'Segoe UI';
    letter-spacing: 2px; font-size: {_dp(14)}px; background: transparent;
}}
QLabel#dlg_sub {{
    color: rgba(255,255,255,0.75); font-family: 'Segoe UI';
    font-size: {_dp(10)}px; background: transparent;
}}
QLabel#field_lbl {{
    color: #37474f; font-family: 'Segoe UI';
    font-weight: 700; font-size: {_dp(11)}px; letter-spacing: 1px;
}}
QLineEdit#dlg_inp {{
    background: #ffffff; border: 2px solid #cfd8e3;
    border-radius: {r8}px; color: #1a237e;
    font-family: 'Segoe UI'; font-size: {_dp(12)}px;
    padding: 0 {_dp(14)}px; min-height: {INP_H}px;
    selection-background-color: #bbdefb;
}}
QLineEdit#dlg_inp:focus  {{ border-color: #1976d2; background: #f4f8ff; }}
QLineEdit#dlg_inp:hover  {{ border-color: #90c4f0; }}
QComboBox#dlg_combo {{
    background: #ffffff; border: 2px solid #cfd8e3;
    border-radius: {r8}px; color: #1a237e;
    font-family: 'Segoe UI'; font-size: {_dp(12)}px;
    padding: 0 {_dp(14)}px; min-height: {INP_H}px;
}}
QComboBox#dlg_combo:focus {{ border-color: #1976d2; }}
QComboBox#dlg_combo::drop-down {{ border: none; width: {_dp(28)}px; }}
QComboBox QAbstractItemView {{
    background: #ffffff; border: 1px solid #cfd8e3;
    selection-background-color: #e3f0ff; color: #1a237e;
    font-family: 'Segoe UI'; font-size: {_dp(12)}px;
    min-height: {_dp(44)}px;
}}
QLabel#dlg_err {{
    color: #c62828; font-family: 'Segoe UI';
    font-size: {_dp(11)}px; font-weight: 700;
}}
QPushButton#dlg_ok {{
    background: #1565c0; color: #ffffff; border: none;
    border-radius: {r10}px; font-family: 'Segoe UI';
    font-weight: 800; font-size: {_dp(12)}px;
    min-height: {_dp(54)}px; padding: 0 {_dp(24)}px;
}}
QPushButton#dlg_ok:hover   {{ background: #1976d2; }}
QPushButton#dlg_ok:pressed {{ background: #0d47a1; }}
QPushButton#dlg_cancel {{
    background: #ffffff; color: #546e7a;
    border: 2px solid #cfd8e3; border-radius: {r10}px;
    font-family: 'Segoe UI'; font-weight: 700; font-size: {_dp(12)}px;
    min-height: {_dp(54)}px; padding: 0 {_dp(20)}px;
}}
QPushButton#dlg_cancel:hover   {{ background: #e3f0ff; border-color: #90c4f0; }}
QPushButton#dlg_cancel:pressed {{ background: #bbdefb; }}
QFrame#h_div {{ background: #cfd8e3; border: none; min-height: 1px; max-height: 1px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: #e8f0fb; width: {_dp(6)}px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: #90c4f0; border-radius: {_dp(3)}px; min-height: {_dp(28)}px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


class LockerConfigDialog(QDialog):
    ESTADOS = ["libre", "ocupado", "mantenimiento"]
    TAMANOS = ["pequeño", "mediano", "grande", "extra-grande"]

    def __init__(self, locker, admin_id=None, parent=None):
        super().__init__(parent)
        self.locker = locker; self.admin_id = admin_id; self.data = None
        self.setObjectName("locker_dlg")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setMinimumWidth(_dp(400)); self.setMaximumWidth(_dp(520))
        self.setStyleSheet(_build_dlg_style())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # ── Cabecera azul ─────────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet(
            f"QFrame{{background:#1565c0;"
            f"border-top-left-radius:{_dp(12)}px;"
            f"border-top-right-radius:{_dp(12)}px;}}"
        )
        hdr_l = QVBoxLayout(hdr)
        hdr_l.setContentsMargins(_dp(20), _dp(16), _dp(20), _dp(16))
        hdr_l.setSpacing(_dp(3))
        ttl = QLabel(tr("admin.lockers.dialog.config_head",
                        n=locker["t_numero_locker"]))
        ttl.setObjectName("dlg_title")
        sub = QLabel(tr("admin.lockers.dialog.config",
                        n=locker["t_numero_locker"]))
        sub.setObjectName("dlg_sub")
        hdr_l.addWidget(ttl); hdr_l.addWidget(sub)
        root.addWidget(hdr)

        # ── Cuerpo ────────────────────────────────────────────────────────────
        body = QFrame()
        body.setStyleSheet(
            f"QFrame{{background:#f0f6ff;"
            f"border-bottom-left-radius:{_dp(12)}px;"
            f"border-bottom-right-radius:{_dp(12)}px;}}"
        )
        body_l = QVBoxLayout(body)
        body_l.setContentsMargins(_dp(20), _dp(16), _dp(20), _dp(20))
        body_l.setSpacing(_dp(12))

        def add_field(label, widget):
            lbl = QLabel(label); lbl.setObjectName("field_lbl")
            body_l.addWidget(lbl); body_l.addWidget(widget)

        self.e_num = QLineEdit(locker.get("t_numero_locker", ""))
        self.e_num.setObjectName("dlg_inp"); self.e_num.setFixedHeight(_dp(52))
        add_field(tr("admin.lockers.dialog.number"), self.e_num)

        self.e_zona = QLineEdit(locker.get("t_zona") or "")
        self.e_zona.setObjectName("dlg_inp"); self.e_zona.setFixedHeight(_dp(52))
        self.e_zona.setPlaceholderText(tr("admin.lockers.dialog.placeholder"))
        add_field(tr("admin.lockers.dialog.zone"), self.e_zona)

        self.c_tam = QComboBox(); self.c_tam.setObjectName("dlg_combo")
        self.c_tam.setFixedHeight(_dp(52)); self.c_tam.addItems(self.TAMANOS)
        if locker.get("t_tamano") in self.TAMANOS:
            self.c_tam.setCurrentText(locker["t_tamano"])
        add_field(tr("admin.lockers.dialog.size"), self.c_tam)

        self.c_est = QComboBox(); self.c_est.setObjectName("dlg_combo")
        self.c_est.setFixedHeight(_dp(52)); self.c_est.addItems(self.ESTADOS)
        if locker.get("t_estado") in self.ESTADOS:
            self.c_est.setCurrentText(locker["t_estado"])
        add_field(tr("admin.lockers.dialog.state"), self.c_est)

        # Botones
        btn_row = QHBoxLayout(); btn_row.setSpacing(_dp(10))
        self.btn_cancel = QPushButton(tr("common.cancel"))
        self.btn_cancel.setObjectName("dlg_cancel")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFocusPolicy(Qt.NoFocus)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok = QPushButton(tr("common.update"))
        self.btn_ok.setObjectName("dlg_ok")
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.setFocusPolicy(Qt.NoFocus)
        self.btn_ok.clicked.connect(self._save)
        btn_row.addWidget(self.btn_cancel, 1)
        btn_row.addWidget(self.btn_ok, 2)
        body_l.addLayout(btn_row)
        root.addWidget(body)

    def _save(self):
        num = self.e_num.text().strip()
        if not num:
            DlgError.show(tr("admin.lockers.dialog.error_empty"), parent=self); return
        self.data = dict(
            numero=num,
            zona=self.e_zona.text().strip() or None,
            tamano=self.c_tam.currentText(),
            estado=self.c_est.currentText(),
        )
        self.accept()

    def paintEvent(self, _):
        from PyQt5.QtCore import QRectF
        from PyQt5.QtGui import QPainterPath
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), _dp(12), _dp(12))
        p.fillPath(path, QBrush(QColor("#f0f6ff"))); p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  LockerCard  — rediseñada para touch en 7"
#
#  Cambio clave: los tres botones de acción (Configurar, Liberar, Eliminar)
#  son ahora botones de ancho completo apilados en una columna en la parte
#  inferior de la card, con min-height = _TOUCH_H (52 px).
#  La card es más alta para acomodarlos sin comprimir el contenido.
# ─────────────────────────────────────────────────────────────────────────────
class LockerCard(QFrame):
    CARD_W = _dp(260)
    # Altura calculada: icono(86) + nombre + chips + separador + 3 botones(52×3)
    # + márgenes + espaciados ≈ 420 px
    CARD_H = _dp(400)

    def __init__(self, locker, index, admin_id=None, on_refresh=None, parent=None):
        super().__init__(parent)
        self.locker = locker; self.admin_id = admin_id; self.on_refresh = on_refresh

        estado = locker.get("t_estado", "libre").lower()
        if estado not in _STATE:
            estado = "libre"
        _, accent, badge_bg, badge_fg = _STATE[estado]

        self._accent = QColor(accent)
        self.setFixedSize(self.CARD_W, self.CARD_H)
        _shadow(self, blur=_dp(14), alpha=22, dy=_dp(3))

        # ── Layout raíz ───────────────────────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Banda de color superior (10 px) — indica estado de un vistazo
        bar = QWidget(); bar.setFixedHeight(_dp(10))
        bar.setStyleSheet(
            f"background:{accent};"
            f"border-top-left-radius:{_dp(14)}px;"
            f"border-top-right-radius:{_dp(14)}px;"
        )
        outer.addWidget(bar)

        # Contenido
        body = QWidget(); body.setStyleSheet("background:transparent;")
        outer.addWidget(body, 1)
        vbox = QVBoxLayout(body)
        vbox.setContentsMargins(_dp(16), _dp(14), _dp(16), _dp(14))
        vbox.setSpacing(0)

        # ── Fila: icono + badge ───────────────────────────────────────────────
        top_row = QHBoxLayout(); top_row.setSpacing(_dp(10))
        icon = LockerIcon(estado="mant" if estado == "mantenimiento" else estado)
        top_row.addWidget(icon)
        top_row.addStretch()

        badge_txt = {
            "libre":         tr("admin.lockers.libres"),
            "ocupado":       tr("admin.lockers.ocupados"),
            "mantenimiento": "MANT.",
        }.get(estado, estado.upper())
        badge = QLabel(badge_txt)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"background:{badge_bg}; color:{badge_fg};"
            f"font-size:{_dp(9)}px; font-weight:800; font-family:'Segoe UI';"
            f"padding:{_dp(5)}px {_dp(12)}px; border-radius:{_dp(9)}px;"
        )
        top_row.addWidget(badge, alignment=Qt.AlignTop)
        vbox.addLayout(top_row)
        vbox.addSpacing(_dp(12))

        # ── Nombre ────────────────────────────────────────────────────────────
        num_lbl = QLabel(f"Locker  #{locker['t_numero_locker']}")
        num_lbl.setWordWrap(True)
        num_lbl.setStyleSheet(
            f"font-size:{_dp(15)}px; font-weight:900;"
            f"color:{badge_fg}; font-family:'Segoe UI';"
        )
        vbox.addWidget(num_lbl)
        vbox.addSpacing(_dp(6))

        # ── Chips zona / tamaño ───────────────────────────────────────────────
        zona   = locker.get("t_zona")   or "—"
        tamano = locker.get("t_tamano") or "—"
        chips  = QHBoxLayout(); chips.setSpacing(_dp(6))
        for txt in [f"Zona: {zona}", tamano.capitalize()]:
            ch = QLabel(txt)
            ch.setStyleSheet(
                f"background:{GRAY_CHIP}; color:{GRAY_TEXT};"
                f"font-size:{_dp(10)}px; padding:{_dp(4)}px {_dp(10)}px;"
                f"border-radius:{_dp(6)}px; font-family:'Segoe UI';"
            )
            chips.addWidget(ch)
        chips.addStretch()
        vbox.addLayout(chips)
        vbox.addSpacing(_dp(8))

        # ── Fecha ─────────────────────────────────────────────────────────────
        fecha = str(locker.get("d_fecha_registro", "") or "")[:10]
        date_lbl = QLabel(fecha or "—")
        date_lbl.setStyleSheet(
            f"font-size:{_dp(10)}px; color:#9ca3af; font-family:'Segoe UI';"
        )
        vbox.addWidget(date_lbl)
        vbox.addStretch()

        # ── Separador ─────────────────────────────────────────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#e5e7eb;")
        vbox.addWidget(sep)
        vbox.addSpacing(_dp(10))

        # ── Botones de acción — ancho completo, altura táctil ─────────────────
        # Botón Configurar
        btn_cfg = QPushButton("⚙   " + tr("admin.lockers.configure"))
        btn_cfg.setFixedHeight(_dp(_TOUCH_H))
        btn_cfg.setStyleSheet(self._btn_css(GRAY_CHIP, GRAY_TEXT, "#cbd5e1"))
        btn_cfg.setCursor(Qt.PointingHandCursor)
        btn_cfg.setFocusPolicy(Qt.NoFocus)
        btn_cfg.clicked.connect(self._config)
        vbox.addWidget(btn_cfg)
        vbox.addSpacing(_dp(6))

        # Botón Liberar (solo si está ocupado)
        if estado == "ocupado":
            btn_lib = QPushButton("↩   " + tr("admin.lockers.release"))
            btn_lib.setFixedHeight(_dp(_TOUCH_H))
            btn_lib.setStyleSheet(self._btn_css("#fff3e8", "#c2410c", "#fbbf24"))
            btn_lib.setCursor(Qt.PointingHandCursor)
            btn_lib.setFocusPolicy(Qt.NoFocus)
            btn_lib.clicked.connect(self._liberar)
            vbox.addWidget(btn_lib)
            vbox.addSpacing(_dp(6))

        # Botón Eliminar
        btn_del = QPushButton("✕   " + tr("admin.lockers.delete"))
        btn_del.setFixedHeight(_dp(_TOUCH_H))
        btn_del.setStyleSheet(self._btn_css(RED_BG, RED_TEXT, "#fca5a5"))
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setFocusPolicy(Qt.NoFocus)
        btn_del.clicked.connect(self._eliminar)
        vbox.addWidget(btn_del)

    # ── CSS compartido para botones de acción ─────────────────────────────────
    @staticmethod
    def _btn_css(bg, fg, border):
        r = _dp(9)
        fs = _dp(11)
        return (
            f"QPushButton{{background:{bg};color:{fg};"
            f"border:1.5px solid {border};border-radius:{r}px;"
            f"font-family:'Segoe UI';font-weight:700;font-size:{fs}px;"
            f"text-align:left;padding:0 {_dp(14)}px;}}"
            f"QPushButton:pressed{{opacity:0.85;background:{border};}}"
        )

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(self._accent, _dp(2)))
        p.setBrush(QBrush(QColor(WHITE)))
        p.drawRoundedRect(1, 1, self.width()-2, self.height()-2, _dp(14), _dp(14))
        p.end()

    # ── Lógica (sin cambios respecto al original) ─────────────────────────────
    def _log(self, tipo, resultado, desc, id_sesion=None):
        db_log_intento(
            id_locker=self.locker["ID_locker"], tipo=tipo,
            resultado=resultado, descripcion=desc or "",
            id_sesion=id_sesion, id_usuario=self.admin_id,
        )

    def _close_active_session(self, extra_desc=""):
        for s in db_get_all_sesiones_activas():
            if s["ID_locker"] != self.locker["ID_locker"]: continue
            db_close_sesion(s["ID_sesion"])
            desc = (f"Sesión #{s['ID_sesion']} cerrada al liberar "
                    f"locker #{self.locker['t_numero_locker']}.")
            if extra_desc: desc += f" Motivo: {extra_desc}"
            self._log("cierre_sesion_admin", "exitoso", desc, id_sesion=s["ID_sesion"])

    def _config(self):
        dlg = LockerConfigDialog(self.locker, self.admin_id, parent=self)
        if dlg.exec_() != QDialog.Accepted or not dlg.data: return
        d = dlg.data
        changes = []
        for nk, dk in [("numero","t_numero_locker"),("zona","t_zona"),
                        ("tamano","t_tamano"),("estado","t_estado")]:
            old = self.locker.get(dk)
            if str(old or "") != str(d[nk] or ""):
                changes.append(f"{dk}: '{old}'→'{d[nk]}'")
        try:
            db_update_locker(id_locker=self.locker["ID_locker"], numero=d["numero"],
                             zona=d["zona"], tamano=d["tamano"], estado=d["estado"],
                             id_admin=self.admin_id)
            self._log("configuracion_admin", "exitoso",
                      "Modificado: " + ("; ".join(changes) or "sin cambios"))
            if d["estado"] == "libre" and self.locker.get("t_estado") != "libre":
                self._close_active_session()
            DlgInfo.show(tr("admin.lockers.dialog.updated", n=d["numero"]), parent=self)
            if self.on_refresh: self.on_refresh()
        except Exception as ex:
            DlgError.show(str(ex), parent=self)

    def _liberar(self):
        num = self.locker["t_numero_locker"]
        confirmed, reason = DlgLiberar.ask(num, parent=self)
        if not confirmed: return
        try:
            self._close_active_session(extra_desc=reason)
            db_set_locker_estado(self.locker["ID_locker"], "libre", self.admin_id)
            desc = f"Admin liberó locker #{num} manualmente."
            if reason: desc += f" Motivo: {reason}"
            self._log("liberacion_admin", "exitoso", desc)
            train_model()
            if self.on_refresh: self.on_refresh()
        except Exception as ex:
            DlgError.show(str(ex), parent=self)

    def _eliminar(self):
        num = self.locker["t_numero_locker"]
        if self.locker.get("t_estado") == "ocupado":
            DlgError.show(tr("admin.lockers.dialog.too_full", n=num),
                          title=tr("common.error"), parent=self); return
        from views.style.adminDialogs import DlgConfirm
        if not DlgConfirm.ask(
            tr("admin.lockers.dialog.delete_confirm", n=num),
            title=tr("admin.lockers.dialog.delete_title", n=num),
            confirm_label=tr("admin.lockers.dialog.delete_confirm_btn"),
            danger=True, parent=self,
        ): return
        try:
            from db.models.lockers import db_delete_locker
            db_log_intento(id_locker=self.locker["ID_locker"],
                           tipo="eliminacion_admin", resultado="exitoso",
                           descripcion=f"Admin eliminó locker #{num}.",
                           id_usuario=self.admin_id)
            db_delete_locker(self.locker["ID_locker"])
            if self.on_refresh: self.on_refresh()
        except Exception as ex:
            DlgError.show(str(ex), parent=self)


# ─────────────────────────────────────────────────────────────────────────────
#  Panel principal
# ─────────────────────────────────────────────────────────────────────────────
def _build_panel_style():
    TH = _dp(_TOUCH_H); r10 = _dp(10)
    return f"""
QWidget#panel {{ background: transparent; }}
QLabel#ttl {{
    color: #1565c0; font-weight: 900; font-family: 'Segoe UI';
    letter-spacing: 3px; font-size: {_dp(13)}px;
}}
QLabel#sub {{
    color: #90a4ae; font-family: 'Segoe UI';
    letter-spacing: 2px; font-size: {_dp(10)}px;
}}
QFrame#h_div {{ background: #cfd8e3; border: none; min-height: 1px; max-height: 1px; }}
QFrame#cnt {{
    background: #ffffff; border: none;
    border-left: 4px solid #1565c0; border-radius: {_dp(8)}px;
}}
QLabel#cn_b {{ color: #1565c0; font-weight: 800; font-family: 'Segoe UI'; }}
QLabel#cn_o {{ color: #ef6c00; font-weight: 800; font-family: 'Segoe UI'; }}
QLabel#cn_g {{ color: #546e7a; font-weight: 800; font-family: 'Segoe UI'; }}
QLabel#ck   {{ color: #90a4ae; font-family: 'Segoe UI'; letter-spacing: 2px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: #e8f0fb; width: {_dp(6)}px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: #90c4f0; border-radius: {_dp(3)}px; min-height: {_dp(30)}px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QLabel#empty {{ color: #b0bec5; font-family: 'Segoe UI'; letter-spacing: 3px; }}

QPushButton#btn_add {{
    background: #1565c0; color: #ffffff; border: none;
    border-radius: {r10}px; font-family: 'Segoe UI';
    font-weight: 800; letter-spacing: 2px; font-size: {_dp(11)}px;
    min-height: {TH}px; min-width: {_dp(140)}px; padding: 0 {_dp(20)}px;
}}
QPushButton#btn_add:hover   {{ background: #1976d2; }}
QPushButton#btn_add:pressed {{ background: #0d47a1; }}

QPushButton#btn_ref {{
    background: #ffffff; color: #1565c0;
    border: 2px solid #90c4f0; border-radius: {r10}px;
    font-family: 'Segoe UI'; font-weight: 800;
    letter-spacing: 2px; font-size: {_dp(11)}px;
    min-height: {TH}px; min-width: {_dp(140)}px; padding: 0 {_dp(20)}px;
}}
QPushButton#btn_ref:hover   {{ background: #e3f0ff; border-color: #1565c0; }}
QPushButton#btn_ref:pressed {{ background: #bbdefb; }}
"""


class _AdminLockersPanel(QWidget):
    def __init__(self, admin_id=None):
        super().__init__()
        self.admin_id = admin_id
        self._cached_lockers = []
        self._cols = 2
        self.setObjectName("panel")
        self.setStyleSheet(_build_panel_style())

        root = QVBoxLayout(self)
        m = _dp(12)
        root.setContentsMargins(m, _dp(8), m, _dp(8))
        root.setSpacing(_dp(7))

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(_dp(10))
        tc = QVBoxLayout(); tc.setSpacing(_dp(2))
        self.title_lbl = QLabel(tr("admin.lockers.title"))
        self.title_lbl.setObjectName("ttl")
        self.subtitle_lbl = QLabel(tr("admin.lockers.subtitle"))
        self.subtitle_lbl.setObjectName("sub")
        tc.addWidget(self.title_lbl); tc.addWidget(self.subtitle_lbl)
        hdr.addLayout(tc); hdr.addStretch()

        self.btn_add = QPushButton("＋  " + tr("admin.lockers.new"))
        self.btn_add.setObjectName("btn_add")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setFocusPolicy(Qt.NoFocus)
        self.btn_add.clicked.connect(self._agregar)
        hdr.addWidget(self.btn_add)

        self.btn_ref = QPushButton("↻  " + tr("admin.lockers.refresh"))
        self.btn_ref.setObjectName("btn_ref")
        self.btn_ref.setCursor(Qt.PointingHandCursor)
        self.btn_ref.setFocusPolicy(Qt.NoFocus)
        self.btn_ref.clicked.connect(self.refresh)
        hdr.addWidget(self.btn_ref)
        root.addLayout(hdr)

        div = QFrame(); div.setObjectName("h_div"); root.addWidget(div)

        # ── Contadores ────────────────────────────────────────────────────────
        cr = QHBoxLayout(); cr.setSpacing(_dp(10))
        self._cnt = {}
        for key, label, obj in [
            ("libre",   tr("admin.lockers.libres"),   "cn_b"),
            ("ocupado", tr("admin.lockers.ocupados"), "cn_o"),
            ("total",   tr("admin.lockers.total"),    "cn_g"),
        ]:
            blk = QFrame(); blk.setObjectName("cnt")
            _shadow(blk, _dp(8), 12, _dp(1))
            bl = QHBoxLayout(blk)
            bl.setContentsMargins(_dp(12), _dp(8), _dp(12), _dp(8))
            bl.setSpacing(_dp(8))
            n = QLabel("0"); n.setObjectName(obj)
            n.setStyleSheet(f"font-size:{_dp(22)}px;")
            k = QLabel(label); k.setObjectName("ck")
            k.setStyleSheet(f"font-size:{_dp(9)}px;")
            bl.addWidget(n); bl.addWidget(k); bl.addStretch()
            cr.addWidget(blk, 1)
            self._cnt[key] = n
        root.addLayout(cr)

        div2 = QFrame(); div2.setObjectName("h_div"); root.addWidget(div2)

        # ── Grid de cards con scroll táctil ───────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.verticalScrollBar().setSingleStep(_dp(60))
        self.scroll.viewport().setAttribute(Qt.WA_AcceptTouchEvents, True)
        QScroller.grabGesture(self.scroll.viewport(), QScroller.LeftMouseButtonGesture)

        self.inner = QWidget()
        self.inner.setObjectName("inner")
        self.inner.setStyleSheet("background:transparent;")
        from PyQt5.QtWidgets import QGridLayout
        self.grid = QGridLayout(self.inner)
        self.grid.setContentsMargins(_dp(4), _dp(4), _dp(4), _dp(4))
        self.grid.setSpacing(_dp(16))
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll, 1)

        self.set_language(get_language())
        self.refresh()

    def set_language(self, _lang: str):
        self.title_lbl.setText(tr("admin.lockers.title"))
        self.subtitle_lbl.setText(tr("admin.lockers.subtitle"))
        self.btn_add.setText("＋  " + tr("admin.lockers.new"))
        self.btn_ref.setText("↻  " + tr("admin.lockers.refresh"))
        self.refresh()

    def paintEvent(self, _):
        p = QPainter(self)
        W, H = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0.0, QColor(232, 240, 251))
        g.setColorAt(1.0, QColor(214, 230, 248))
        p.fillRect(0, 0, W, H, QBrush(g))
        p.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_cols = self._calculate_cols()
        if new_cols != self._cols:
            self._cols = new_cols
            self._render_lockers()

    def _calculate_cols(self) -> int:
        avail   = self.scroll.viewport().width() - _dp(8)
        card_w  = LockerCard.CARD_W
        spacing = self.grid.spacing()
        cols    = max(1, (avail + spacing) // (card_w + spacing))
        return min(3, cols)

    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _render_lockers(self):
        self._clear_grid()
        if not self._cached_lockers:
            e = QLabel(tr("admin.lockers.empty"))
            e.setObjectName("empty"); e.setAlignment(Qt.AlignCenter)
            e.setStyleSheet(f"font-size:{_dp(10)}px;")
            e.setContentsMargins(0, _dp(20), 0, _dp(20))
            self.grid.addWidget(e, 0, 0); return
        cols = self._cols
        for i, lk in enumerate(self._cached_lockers):
            card = LockerCard(lk, i+1, self.admin_id, on_refresh=self.refresh)
            self.grid.addWidget(card, i // cols, i % cols)

    def _agregar(self):
        num = DlgInput.ask(
            tr("admin.lockers.dialog.msg"),
            title=tr("admin.lockers.dialog.title"),
            placeholder=tr("admin.lockers.dialog.placeholder"),
            parent=self,
        )
        if not num: return
        try:
            new_id = db_insert_locker(num, id_admin=self.admin_id)
            db_log_intento(id_locker=new_id, tipo="alta_locker_admin",
                           resultado="exitoso",
                           descripcion=f"Admin registró locker #{num}.",
                           id_usuario=self.admin_id)
            DlgInfo.show(tr("admin.lockers.dialog.created", n=num), parent=self)
            self.refresh()
        except Exception as ex:
            DlgError.show(str(ex), parent=self)

    def refresh(self):
        lockers = db_get_all_lockers()
        libres  = sum(1 for l in lockers if l.get("t_estado") == "libre")
        ocups   = sum(1 for l in lockers if l.get("t_estado") == "ocupado")
        self._cnt["libre"].setText(str(libres))
        self._cnt["ocupado"].setText(str(ocups))
        self._cnt["total"].setText(str(len(lockers)))
        _ord = {"ocupado": 0, "libre": 1, "mantenimiento": 2}
        self._cached_lockers = sorted(
            lockers, key=lambda l: _ord.get(l.get("t_estado", ""), 9)
        )
        self._cols = self._calculate_cols()
        self._render_lockers()