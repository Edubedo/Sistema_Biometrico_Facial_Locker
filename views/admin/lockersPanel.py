from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy,
    QApplication, QDialog, QGridLayout,
    QLineEdit, QComboBox,
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QPen

from db.models.lockers import (
    db_get_all_lockers, db_insert_locker,
    db_set_locker_estado, db_update_locker,
)
from db.models.sesiones import db_close_sesion, db_get_all_sesiones_activas
from db.models.intentos_acceso import db_log_intento
from biometria.biometria import delete_face_data, train_model
from views.style.adminDialogs import DlgError, DlgInfo, DlgInput, DlgLiberar


def _dp(v):
    s = QApplication.primaryScreen()
    return max(1, round(v * (s.logicalDotsPerInch() if s else 96) / 96))


BLUE_DARK  = "#1d4ed8"
BLUE_MID   = "#3b82f6"
BLUE_LIGHT = "#60a5fa"
BLUE_PALE  = "#93c5fd"
BLUE_BG    = "#bfdbfe"
ORANGE     = "#f97316"
WHITE      = "#ffffff"
GRAY_BG    = "#f0f4ff"
GRAY_CHIP  = "#e8eef8"
GRAY_TEXT  = "#64748b"
RED_BG     = "#fee2e2"
RED_TEXT   = "#b91c1c"

_STATE = {
    "libre":         (WHITE,    BLUE_DARK, BLUE_DARK, "#e0f2fe", "open"),
    "ocupado":       (WHITE,    ORANGE,    "#fff3e8", "#c2410c", "closed"),
    "mantenimiento": (WHITE,    "#78909c", "#eceff1", "#546e7a", "closed"),
}

STYLE = """
QWidget#panel{background:transparent;}
QLabel#ttl{color:#1565c0;font-weight:900;font-family:'Segoe UI';letter-spacing:3px;}
QLabel#sub{color:#90a4ae;font-family:'Segoe UI';letter-spacing:2px;}
QFrame#h_div{background:#cfd8e3;border:none;min-height:1px;max-height:1px;}
QFrame#cnt{background:#fff;border:none;border-left:4px solid #1565c0;border-radius:8px;}
QLabel#cn_b{color:#1565c0;font-weight:800;font-family:'Segoe UI';}
QLabel#cn_o{color:#ef6c00;font-weight:800;font-family:'Segoe UI';}
QLabel#cn_g{color:#546e7a;font-weight:800;font-family:'Segoe UI';}
QLabel#ck{color:#90a4ae;font-family:'Segoe UI';letter-spacing:2px;}
QScrollArea{border:none;background:transparent;}
QScrollBar:vertical{background:#e8f0fb;width:4px;margin:0;}
QScrollBar::handle:vertical{background:#90c4f0;border-radius:2px;min-height:20px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
QDialog{background:#f0f6ff;}
QLineEdit,QComboBox{background:#fff;border:1px solid #cfd8e3;border-radius:5px;
    padding:5px 8px;color:#1565c0;font-family:'Segoe UI';}
QLineEdit:focus,QComboBox:focus{border-color:#1976d2;}
QLabel#flbl{color:#546e7a;font-family:'Segoe UI';font-weight:700;letter-spacing:1px;}
QPushButton#dok{background:#1976d2;color:#fff;border:none;border-radius:6px;
    padding:7px 20px;font-family:'Segoe UI';font-weight:700;}
QPushButton#dok:hover{background:#1565c0;}
QPushButton#dno{background:transparent;color:#90a4ae;border:1px solid #cfd8e3;
    border-radius:6px;padding:7px 16px;font-family:'Segoe UI';}
QLabel#empty{color:#b0bec5;font-family:'Segoe UI';letter-spacing:3px;}
QPushButton#btn_add{background:#1976d2;color:#fff;border:none;border-radius:7px;
    font-family:'Segoe UI';font-weight:700;letter-spacing:2px;}
QPushButton#btn_add:hover{background:#1565c0;}
QPushButton#btn_ref{background:transparent;color:#90a4ae;border:1px solid #cfd8e3;
    border-radius:6px;font-family:'Segoe UI';letter-spacing:2px;}
QPushButton#btn_ref:hover{color:#1565c0;border-color:#1976d2;background:#e3f0ff;}
"""


class LockerIcon(QWidget):
    def __init__(self, estado="ocupado", parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 48)
        self.estado = estado
        self._bg = QColor(WHITE)

    def set_estado(self, estado, bg=WHITE):
        self.estado = estado
        self._bg = QColor(bg)
        self.update()

    def _c(self, h):
        return QColor(h)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), self._bg)
        sx = self.width() / 54.0
        sy = self.height() / 64.0
        p.scale(sx, sy)
        if self.estado == "libre":
            self._draw_open(p)
        elif self.estado == "mantenimiento":
            self._draw_maint(p)
        else:
            self._draw_closed(p)
        p.end()

    def _draw_closed(self, p):
        c = self._c
        p.setPen(QPen(c(BLUE_DARK), 2))
        p.setBrush(QBrush(c(BLUE_LIGHT)))
        p.drawRoundedRect(4, 6, 46, 54, 5, 5)
        p.setBrush(QBrush(c(BLUE_MID)))
        p.drawRoundedRect(4, 6, 46, 10, 5, 5)
        p.setPen(QPen(c(BLUE_DARK), 1))
        p.setBrush(QBrush(c("#e0f2fe")))
        p.drawEllipse(20, 11, 14, 10)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c("#1e3a8a")))
        p.drawEllipse(24, 14, 7, 4)
        p.setBrush(QBrush(c(WHITE)))
        p.drawEllipse(25, 13, 2, 2)
        p.setBrush(QBrush(c(BLUE_DARK)))
        for y in [26, 30, 34]:
            p.drawRoundedRect(19, y, 16, 3, 1, 1)
        p.setPen(QPen(c("#94a3b8"), 1))
        p.setBrush(QBrush(c("#e2e8f0")))
        p.drawEllipse(38, 35, 7, 7)
        p.setPen(QPen(c("#94a3b8"), 2))
        p.drawLine(41, 42, 41, 52)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c("#94a3b8")))
        p.drawEllipse(38, 51, 6, 4)
        p.setBrush(QBrush(c(BLUE_DARK)))
        p.drawRoundedRect(2, 57, 8, 5, 2, 2)
        p.drawRoundedRect(44, 57, 8, 5, 2, 2)

    def _draw_open(self, p):
        c = self._c
        p.setPen(QPen(c(BLUE_DARK), 2))
        p.setBrush(QBrush(c(BLUE_PALE)))
        p.drawRoundedRect(4, 6, 46, 54, 5, 5)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c("#d1e8ff")))
        p.drawRoundedRect(10, 14, 34, 44, 3, 3)
        p.setPen(QPen(c("#d97706"), 1))
        p.setBrush(QBrush(c("#fbbf24")))
        p.drawRoundedRect(30, 36, 14, 20, 3, 3)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c("#d97706")))
        p.drawRoundedRect(33, 33, 8, 5, 2, 2)
        p.setBrush(QBrush(c(BLUE_PALE)))
        p.drawRoundedRect(28, 34, 16, 2, 1, 1)
        p.setPen(QPen(c(BLUE_DARK), 2))
        p.setBrush(QBrush(c(BLUE_MID)))
        p.drawRoundedRect(4, 6, 22, 54, 5, 5)
        p.setPen(QPen(c(BLUE_DARK), 1))
        p.setBrush(QBrush(c("#e0f2fe")))
        p.drawEllipse(9, 12, 12, 12)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c("#1e3a8a")))
        p.drawEllipse(12, 15, 6, 6)
        p.setBrush(QBrush(c(WHITE)))
        p.drawEllipse(13, 13, 2, 2)
        p.setBrush(QBrush(c(BLUE_DARK)))
        for y in [27, 31, 35]:
            p.drawRoundedRect(9, y, 12, 2, 1, 1)
        p.setPen(QPen(c(BLUE_DARK), 1))
        p.setBrush(QBrush(c(BLUE_PALE)))
        p.drawRoundedRect(23, 16, 4, 8, 2, 2)
        p.drawRoundedRect(23, 40, 4, 8, 2, 2)
        p.setPen(QPen(c("#94a3b8"), 1))
        p.setBrush(QBrush(c("#e2e8f0")))
        p.drawEllipse(38, 19, 5, 5)
        p.setPen(QPen(c("#94a3b8"), 2))
        p.drawLine(41, 24, 41, 33)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c("#94a3b8")))
        p.drawEllipse(38, 32, 6, 4)
        p.setBrush(QBrush(c(BLUE_DARK)))
        p.drawRoundedRect(2, 57, 8, 5, 2, 2)
        p.drawRoundedRect(44, 57, 8, 5, 2, 2)

    def _draw_maint(self, p):
        c = self._c
        GR = "#78909c"; GRL = "#b0bec5"; GRP = "#eceff1"
        p.setPen(QPen(c(GR), 2))
        p.setBrush(QBrush(c(GRL)))
        p.drawRoundedRect(4, 6, 46, 54, 5, 5)
        p.setBrush(QBrush(c(GR)))
        p.drawRoundedRect(4, 6, 46, 10, 5, 5)
        p.setPen(QPen(c(GR), 1))
        p.setBrush(QBrush(c(GRP)))
        p.drawEllipse(20, 11, 14, 10)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c("#546e7a")))
        p.drawEllipse(24, 14, 7, 4)
        p.setBrush(QBrush(c(WHITE)))
        p.drawEllipse(25, 13, 2, 2)
        p.setBrush(QBrush(c(GR)))
        for y in [26, 30, 34]:
            p.drawRoundedRect(19, y, 16, 3, 1, 1)
        p.setPen(QPen(c("#546e7a"), 3))
        p.drawLine(22, 42, 32, 52)
        p.drawLine(32, 42, 22, 52)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(c(GR)))
        p.drawRoundedRect(2, 57, 8, 5, 2, 2)
        p.drawRoundedRect(44, 57, 8, 5, 2, 2)


class LockerConfigDialog(QDialog):
    ESTADOS = ["libre", "ocupado", "mantenimiento"]
    TAMANOS = ["pequeño", "mediano", "grande", "extra-grande"]

    def __init__(self, locker, admin_id=None, parent=None):
        super().__init__(parent)
        self.locker = locker
        self.admin_id = admin_id
        self.data = None
        self.setWindowTitle(f"Configurar Locker #{locker['t_numero_locker']}")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(_dp(320))
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(_dp(20), _dp(16), _dp(20), _dp(16))
        root.setSpacing(_dp(12))

        ttl = QLabel(f"⚙  CONFIGURAR  #{locker['t_numero_locker']}")
        ttl.setStyleSheet(
            f"color:#1565c0;font-size:{_dp(11)}px;font-weight:900;"
            "font-family:'Segoe UI';letter-spacing:2px;"
        )
        root.addWidget(ttl)
        d = QFrame(); d.setObjectName("h_div"); root.addWidget(d)

        grid = QGridLayout()
        grid.setSpacing(_dp(8))
        grid.setColumnStretch(1, 1)
        fs = f"font-size:{_dp(9)}px;"

        def add_row(lbl_text, widget, r):
            lb = QLabel(lbl_text)
            lb.setObjectName("flbl")
            lb.setStyleSheet(fs)
            grid.addWidget(lb, r, 0, Qt.AlignRight | Qt.AlignVCenter)
            widget.setStyleSheet(fs)
            grid.addWidget(widget, r, 1)

        self.e_num  = QLineEdit(locker.get("t_numero_locker", ""))
        self.e_zona = QLineEdit(locker.get("t_zona") or "")
        self.e_zona.setPlaceholderText("ej. A, Planta Baja")
        self.c_tam  = QComboBox(); self.c_tam.addItems(self.TAMANOS)
        self.c_est  = QComboBox(); self.c_est.addItems(self.ESTADOS)
        if locker.get("t_tamano") in self.TAMANOS:
            self.c_tam.setCurrentText(locker["t_tamano"])
        if locker.get("t_estado") in self.ESTADOS:
            self.c_est.setCurrentText(locker["t_estado"])

        add_row("NÚMERO", self.e_num,  0)
        add_row("ZONA",   self.e_zona, 1)
        add_row("TAMAÑO", self.c_tam,  2)
        add_row("ESTADO", self.c_est,  3)
        root.addLayout(grid)

        br = QHBoxLayout(); br.addStretch()
        bn = QPushButton("CANCELAR"); bn.setObjectName("dno"); bn.setStyleSheet(fs)
        bn.setCursor(Qt.PointingHandCursor); bn.clicked.connect(self.reject)
        bo = QPushButton("GUARDAR");   bo.setObjectName("dok"); bo.setStyleSheet(fs)
        bo.setCursor(Qt.PointingHandCursor); bo.clicked.connect(self._save)
        br.addWidget(bn); br.addWidget(bo)
        root.addLayout(br)

    def _save(self):
        num = self.e_num.text().strip()
        if not num:
            DlgError.show("El número de locker no puede estar vacío.", parent=self)
            return
        self.data = {
            "numero": num,
            "zona":   self.e_zona.text().strip() or None,
            "tamano": self.c_tam.currentText(),
            "estado": self.c_est.currentText(),
        }
        self.accept()


class LockerCard(QFrame):
    CARD_W = 170
    CARD_H = 190

    def __init__(self, locker, index, admin_id=None, on_refresh=None, parent=None):
        super().__init__(parent)
        self.locker     = locker
        self.admin_id   = admin_id
        self.on_refresh = on_refresh

        estado = locker.get("t_estado", "libre").lower()
        if estado not in _STATE:
            estado = "libre"

        card_bg, bar_color, badge_bg, badge_fg, _ = _STATE[estado]
        self._bg     = QColor(card_bg)
        self._border = QColor(bar_color)
        self.setFixedSize(self.CARD_W, self.CARD_H)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(5)
        self.top_bar.setStyleSheet(
            f"background:{bar_color};"
            "border-top-left-radius:12px; border-top-right-radius:12px;"
        )
        outer.addWidget(self.top_bar)

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        outer.addWidget(content, 1)

        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(9, 8, 9, 8)
        vbox.setSpacing(0)

        icon_row = QHBoxLayout()
        icon_row.setSpacing(0)
        self.icon = LockerIcon(estado=estado)
        icon_row.addWidget(self.icon)
        icon_row.addStretch()
        badge_txt = {"libre": "LIBRE", "ocupado": "OCUPADO",
                     "mantenimiento": "MANT."}.get(estado, estado.upper())
        self.badge = QLabel(badge_txt)
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setStyleSheet(
            f"background:{badge_bg}; color:{badge_fg};"
            "font-size:9px; font-weight:800; font-family:'Segoe UI';"
            "padding:2px 5px; border-radius:5px;"
        )
        icon_row.addWidget(self.badge, alignment=Qt.AlignTop)
        vbox.addLayout(icon_row)

        vbox.addSpacing(6)

        num_lbl = QLabel(f"Locker #{locker['t_numero_locker']}")
        num_lbl.setWordWrap(True)
        num_lbl.setStyleSheet(
            f"font-size:11px; font-weight:900; color:{badge_fg}; font-family:'Segoe UI';"
        )
        vbox.addWidget(num_lbl)

        vbox.addSpacing(3)

        zona   = locker.get("t_zona")   or "—"
        tamano = locker.get("t_tamano") or "—"
        chips_row = QHBoxLayout()
        chips_row.setSpacing(3)
        for text in [f"Z:{zona}", tamano]:
            chip = QLabel(text)
            chip.setStyleSheet(
                f"background:{GRAY_CHIP}; color:{GRAY_TEXT};"
                "font-size:8px; padding:2px 6px; border-radius:6px; font-family:'Segoe UI';"
            )
            chips_row.addWidget(chip)
        chips_row.addStretch()
        vbox.addLayout(chips_row)

        vbox.addStretch()

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color:#e5e7eb;")
        vbox.addWidget(divider)
        vbox.addSpacing(5)

        fecha = str(locker.get("d_fecha_registro", "") or "")[:10]
        date_lbl = QLabel(fecha or "—")
        date_lbl.setStyleSheet("font-size:7px; color:#9ca3af; font-family:'Segoe UI';")
        vbox.addWidget(date_lbl)

        vbox.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(3)

        btn_config = QPushButton("⚙")
        btn_config.setFixedSize(34, 30)
        btn_config.setStyleSheet(
            f"background:{GRAY_CHIP}; color:{GRAY_TEXT};"
            "font-size:12px; border:none; border-radius:6px;"
        )
        btn_config.setToolTip("Configurar")
        btn_config.setCursor(Qt.PointingHandCursor)
        btn_config.clicked.connect(self._config)
        btn_row.addWidget(btn_config)

        if estado == "ocupado":
            self.btn_liberar = QPushButton("↩")
            self.btn_liberar.setFixedSize(34, 30)
            self.btn_liberar.setToolTip("Liberar")
            self.btn_liberar.setStyleSheet(
                f"background:{ORANGE}; color:white; font-size:13px;"
                "font-weight:800; border:none; border-radius:6px;"
            )
            self.btn_liberar.setCursor(Qt.PointingHandCursor)
            self.btn_liberar.clicked.connect(self._liberar)
            btn_row.addWidget(self.btn_liberar)

        btn_row.addStretch()

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(34, 30)
        btn_del.setStyleSheet(
            f"background:{RED_BG}; color:{RED_TEXT};"
            "font-size:12px; border:none; border-radius:6px;"
        )
        btn_del.setToolTip("Eliminar locker")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.clicked.connect(self._eliminar)
        btn_row.addWidget(btn_del)

        vbox.addLayout(btn_row)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(self._border, 2))
        p.setBrush(QBrush(self._bg))
        p.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 12, 12)
        p.end()

    def _log(self, tipo, resultado, desc, id_sesion=None):
        db_log_intento(
            id_locker   = self.locker["ID_locker"],
            tipo        = tipo,
            resultado   = resultado,
            descripcion = desc or "",
            id_sesion   = id_sesion,
            id_usuario  = self.admin_id,
        )

    def _close_active_session(self, extra_desc=""):
        for s in db_get_all_sesiones_activas():
            if s["ID_locker"] != self.locker["ID_locker"]:
                continue
            db_close_sesion(s["ID_sesion"])
            fuid = s.get("b_vector_biometrico_temp")
            if isinstance(fuid, bytes):
                fuid = fuid.decode()
            if fuid:
                delete_face_data(fuid)
            desc = (
                f"Sesión #{s['ID_sesion']} cerrada al liberar "
                f"locker #{self.locker['t_numero_locker']}."
            )
            if extra_desc:
                desc += f" Motivo: {extra_desc}"
            self._log("cierre_sesion_admin", "exitoso", desc, id_sesion=s["ID_sesion"])

    def _config(self):
        dlg = LockerConfigDialog(self.locker, self.admin_id, parent=self)
        if dlg.exec_() != QDialog.Accepted or not dlg.data:
            return
        d = dlg.data
        changes = []
        for nk, dk in [("numero", "t_numero_locker"), ("zona", "t_zona"),
                        ("tamano", "t_tamano"), ("estado", "t_estado")]:
            old = self.locker.get(dk)
            if str(old or "") != str(d[nk] or ""):
                changes.append(f"{dk}: '{old}'→'{d[nk]}'")
        try:
            db_update_locker(
                id_locker = self.locker["ID_locker"],
                numero    = d["numero"],
                zona      = d["zona"],
                tamano    = d["tamano"],
                estado    = d["estado"],
                id_admin  = self.admin_id,
            )
            self._log("configuracion_admin", "exitoso",
                      "Modificado: " + ("; ".join(changes) or "sin cambios"))
            if d["estado"] == "libre" and self.locker.get("t_estado") != "libre":
                self._close_active_session()
            DlgInfo.show(f"Locker #{d['numero']} actualizado.", parent=self)
            if self.on_refresh:
                self.on_refresh()
        except Exception as ex:
            DlgError.show(str(ex), parent=self)

    def _liberar(self):
        num = self.locker["t_numero_locker"]
        confirmed, reason = DlgLiberar.ask(num, parent=self)
        if not confirmed:
            return
        try:
            self._close_active_session(extra_desc=reason)
            db_set_locker_estado(self.locker["ID_locker"], "libre", self.admin_id)
            desc = f"Admin liberó locker #{num} manualmente."
            if reason:
                desc += f" Motivo: {reason}"
            self._log("liberacion_admin", "exitoso", desc)
            train_model()
            if self.on_refresh:
                self.on_refresh()
        except Exception as ex:
            DlgError.show(str(ex), parent=self)

    def _eliminar(self):
        num    = self.locker["t_numero_locker"]
        estado = self.locker.get("t_estado", "")
        if estado == "ocupado":
            DlgError.show(
                f"El locker #{num} está ocupado.\nLibéralo antes de eliminarlo.",
                title="No se puede eliminar", parent=self,
            )
            return
        from views.style.adminDialogs import DlgConfirm
        if not DlgConfirm.ask(
            f"¿Eliminar permanentemente el locker <b>#{num}</b>?\n"
            "Esta acción no se puede deshacer.",
            title=f"Eliminar Locker #{num}",
            confirm_label="ELIMINAR",
            danger=True,
            parent=self,
        ):
            return
        try:
            from db.models.lockers import db_delete_locker
            db_log_intento(
                id_locker   = self.locker["ID_locker"],
                tipo        = "eliminacion_admin",
                resultado   = "exitoso",
                descripcion = f"Admin eliminó locker #{num}.",
                id_usuario  = self.admin_id,
            )
            db_delete_locker(self.locker["ID_locker"])
            if self.on_refresh:
                self.on_refresh()
        except Exception as ex:
            DlgError.show(str(ex), parent=self)


class _AdminLockersPanel(QWidget):
    def __init__(self, admin_id=None):
        super().__init__()
        self.admin_id = admin_id
        self.setObjectName("panel")
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        m = _dp(14)
        root.setContentsMargins(m, _dp(10), m, _dp(10))
        root.setSpacing(_dp(8))

        hdr = QHBoxLayout()
        hdr.setSpacing(_dp(6))
        tc = QVBoxLayout()
        tc.setSpacing(_dp(2))
        t = QLabel("GESTIÓN DE LOCKERS")
        t.setObjectName("ttl")
        t.setStyleSheet(f"font-size:{_dp(12)}px;")
        s = QLabel("PANEL ADMIN · LOCKERS DE TIENDA")
        s.setObjectName("sub")
        s.setStyleSheet(f"font-size:{_dp(8)}px;")
        tc.addWidget(t)
        tc.addWidget(s)
        hdr.addLayout(tc)
        hdr.addStretch()

        for obj, icon, cb in [
            ("btn_add", "＋  NUEVO",      self._agregar),
            ("btn_ref", "↺  ACTUALIZAR", self.refresh),
        ]:
            b = QPushButton(icon)
            b.setObjectName(obj)
            b.setStyleSheet(f"font-size:{_dp(10)}px;padding:{_dp(7)}px {_dp(18)}px;")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(cb)
            hdr.addWidget(b)

        root.addLayout(hdr)
        root.addWidget(self._div())

        cr = QHBoxLayout()
        cr.setSpacing(_dp(10))
        self._cnt = {}
        for key, label, obj in [
            ("libre",   "LIBRES",   "cn_b"),
            ("ocupado", "OCUPADOS", "cn_o"),
            ("total",   "TOTAL",    "cn_g"),
        ]:
            blk = QFrame()
            blk.setObjectName("cnt")
            bl = QHBoxLayout(blk)
            bl.setContentsMargins(_dp(12), _dp(7), _dp(12), _dp(7))
            bl.setSpacing(_dp(8))
            n = QLabel("0")
            n.setObjectName(obj)
            n.setStyleSheet(f"font-size:{_dp(24)}px;")
            k = QLabel(label)
            k.setObjectName("ck")
            k.setStyleSheet(f"font-size:{_dp(7)}px;")
            bl.addWidget(n)
            bl.addWidget(k)
            bl.addStretch()
            cr.addWidget(blk, 1)
            self._cnt[key] = n

        root.addLayout(cr)
        root.addWidget(self._div())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.inner = QWidget()
        self.inner.setObjectName("inner")
        self.inner.setStyleSheet("background:transparent;")
        self.grid = QGridLayout(self.inner)
        self.grid.setContentsMargins(_dp(4), _dp(4), _dp(4), _dp(4))
        self.grid.setSpacing(_dp(10))
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(self.inner)
        root.addWidget(scroll, 1)

        self._cols = 3
        self.refresh()

    def _div(self):
        d = QFrame()
        d.setObjectName("h_div")
        return d

    def paintEvent(self, e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, QColor(232, 240, 251))
        g.setColorAt(1.0, QColor(214, 230, 248))
        p.fillRect(0, 0, self.width(), self.height(), QBrush(g))
        p.end()

    def _agregar(self):
        num = DlgInput.ask(
            "Ingresa el número del nuevo locker:",
            title="Nuevo Locker",
            placeholder="ej. 42",
            parent=self,
        )
        if not num:
            return
        try:
            new_id = db_insert_locker(num, id_admin=self.admin_id)
            db_log_intento(
                id_locker   = new_id,
                tipo        = "alta_locker_admin",
                resultado   = "exitoso",
                descripcion = f"Admin registró locker #{num}.",
                id_usuario  = self.admin_id,
            )
            DlgInfo.show(f"Locker #{num} creado correctamente.", parent=self)
            self.refresh()
        except Exception as ex:
            DlgError.show(str(ex), parent=self)

    def refresh(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        lockers = db_get_all_lockers()
        libres  = sum(1 for l in lockers if l.get("t_estado") == "libre")
        ocups   = sum(1 for l in lockers if l.get("t_estado") == "ocupado")
        self._cnt["libre"].setText(str(libres))
        self._cnt["ocupado"].setText(str(ocups))
        self._cnt["total"].setText(str(len(lockers)))

        if not lockers:
            e = QLabel("·  SIN LOCKERS REGISTRADOS  ·")
            e.setObjectName("empty")
            e.setAlignment(Qt.AlignCenter)
            e.setStyleSheet(f"font-size:{_dp(9)}px;")
            e.setContentsMargins(0, _dp(20), 0, _dp(20))
            self.grid.addWidget(e, 0, 0)
            return

        _ord = {"ocupado": 0, "libre": 1, "mantenimiento": 2}
        sorted_lockers = sorted(lockers, key=lambda l: _ord.get(l.get("t_estado", ""), 9))
        cols = self._cols
        for i, lk in enumerate(sorted_lockers):
            card = LockerCard(lk, i + 1, self.admin_id, on_refresh=self.refresh)
            self.grid.addWidget(card, i // cols, i % cols)