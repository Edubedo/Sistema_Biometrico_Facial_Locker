from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy,
    QApplication, QDialog, QGridLayout,
    QLineEdit, QComboBox,
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient

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


_C = {
    "libre":          ("#ffffff", "#1976d2", "#e3f0ff", "#1565c0", "#90c4f0"),
    "ocupado":        ("#fff8f0", "#ef6c00", "#fff3e0", "#e65100", "#ffcc80"),
    "mantenimiento":  ("#fafafa", "#78909c", "#eceff1", "#546e7a", "#b0bec5"),
}

STYLE = """
QWidget#panel,QWidget#inner{background:transparent;}
QLabel#ttl{color:#1565c0;font-weight:900;font-family:'Segoe UI';letter-spacing:3px;}
QLabel#sub{color:#90a4ae;font-family:'Segoe UI';letter-spacing:2px;}
QFrame#h_div{background:#cfd8e3;border:none;min-height:1px;max-height:1px;}
QFrame#cnt{background:#fff;border:none;border-left:4px solid #1565c0;border-radius:8px;}
QLabel#cn_b{color:#1565c0;font-weight:800;font-family:'Segoe UI';}
QLabel#cn_o{color:#ef6c00;font-weight:800;font-family:'Segoe UI';}
QLabel#cn_g{color:#546e7a;font-weight:800;font-family:'Segoe UI';}
QLabel#ck  {color:#90a4ae;font-family:'Segoe UI';letter-spacing:2px;}
QFrame#card_libre        {background:#fff;   border:none;border-left:4px solid #1976d2;border-radius:8px;}
QFrame#card_ocupado      {background:#fff8f0;border:none;border-left:4px solid #ef6c00;border-radius:8px;}
QFrame#card_mantenimiento{background:#fafafa;border:none;border-left:4px solid #78909c;border-radius:8px;}
QLabel#meta{color:#78909c;font-family:'Segoe UI';letter-spacing:1px;}
QPushButton#btn_add{background:#1976d2;color:#fff;border:none;border-radius:7px;
    font-family:'Segoe UI';font-weight:700;letter-spacing:2px;}
QPushButton#btn_add:hover{background:#1565c0;}
QPushButton#btn_ref{background:transparent;color:#90a4ae;border:1px solid #cfd8e3;
    border-radius:6px;font-family:'Segoe UI';letter-spacing:2px;}
QPushButton#btn_ref:hover{color:#1565c0;border-color:#1976d2;background:#e3f0ff;}
QPushButton#btn_cfg{background:transparent;color:#b0bec5;border:1px solid #e0e8f4;
    border-radius:5px;font-family:'Segoe UI';}
QPushButton#btn_cfg:hover{color:#1565c0;border-color:#1976d2;background:#e3f0ff;}
QPushButton#btn_lib{background:transparent;color:#e65100;border:1px solid #ffcc80;
    border-radius:5px;font-family:'Segoe UI';font-weight:700;}
QPushButton#btn_lib:hover{background:#fff3e0;}
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
"""


class LockerConfigDialog(QDialog):
    ESTADOS = ["libre", "ocupado", "mantenimiento"]
    TAMANOS = ["pequeño", "mediano", "grande", "extra-grande"]

    def __init__(self, locker, admin_id=None, parent=None):
        super().__init__(parent)
        self.locker = locker; self.admin_id = admin_id; self.data = None
        self.setWindowTitle(f"Configurar Locker #{locker['t_numero_locker']}")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(_dp(320)); self.setStyleSheet(STYLE)

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

        grid = QGridLayout(); grid.setSpacing(_dp(8)); grid.setColumnStretch(1, 1)
        fs = f"font-size:{_dp(9)}px;"

        def add_row(lbl_text, widget, r):
            lb = QLabel(lbl_text); lb.setObjectName("flbl"); lb.setStyleSheet(fs)
            grid.addWidget(lb, r, 0, Qt.AlignRight | Qt.AlignVCenter)
            widget.setStyleSheet(fs); grid.addWidget(widget, r, 1)

        self.e_num  = QLineEdit(locker.get("t_numero_locker", ""))
        self.e_zona = QLineEdit(locker.get("t_zona") or "")
        self.e_zona.setPlaceholderText("ej. A, Planta Baja")
        self.c_tam  = QComboBox(); self.c_tam.addItems(self.TAMANOS)
        self.c_est  = QComboBox(); self.c_est.addItems(self.ESTADOS)
        if locker.get("t_tamano") in self.TAMANOS: self.c_tam.setCurrentText(locker["t_tamano"])
        if locker.get("t_estado") in self.ESTADOS: self.c_est.setCurrentText(locker["t_estado"])

        add_row("NÚMERO", self.e_num,  0); add_row("ZONA",   self.e_zona, 1)
        add_row("TAMAÑO", self.c_tam,  2); add_row("ESTADO", self.c_est,  3)
        root.addLayout(grid)

        br = QHBoxLayout(); br.addStretch()
        bn = QPushButton("CANCELAR"); bn.setObjectName("dno"); bn.setStyleSheet(fs)
        bn.setCursor(Qt.PointingHandCursor); bn.clicked.connect(self.reject)
        bo = QPushButton("GUARDAR");   bo.setObjectName("dok"); bo.setStyleSheet(fs)
        bo.setCursor(Qt.PointingHandCursor); bo.clicked.connect(self._save)
        br.addWidget(bn); br.addWidget(bo); root.addLayout(br)

    def _save(self):
        num = self.e_num.text().strip()
        if not num:
            DlgError.show("El número de locker no puede estar vacío.", parent=self)
            return
        self.data = {
            "numero": num, "zona": self.e_zona.text().strip() or None,
            "tamano": self.c_tam.currentText(), "estado": self.c_est.currentText(),
        }
        self.accept()


class LockerCard(QFrame):
    def __init__(self, locker, index, admin_id=None, on_refresh=None, parent=None):
        super().__init__(parent)
        self.locker = locker; self.admin_id = admin_id; self.on_refresh = on_refresh

        estado = locker.get("t_estado", "libre").lower()
        if estado not in _C: estado = "libre"
        _, _, badge_bg, badge_fg, badge_border = _C[estado]

        self.setObjectName(f"card_{estado}")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(_dp(12), _dp(8), _dp(12), _dp(8))
        lay.setSpacing(_dp(10))

        idx = QLabel(f"{index:02d}")
        idx.setStyleSheet(
            f"color:#bbdefb;font-size:{_dp(13)}px;font-weight:900;"
            f"font-family:'Segoe UI';min-width:{_dp(22)}px;"
        )
        idx.setAlignment(Qt.AlignCenter); lay.addWidget(idx)

        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(
            f"background:#e3f0ff;border:none;"
            f"min-width:{_dp(1)}px;max-width:{_dp(1)}px;"
        )
        lay.addWidget(sep)

        col = QVBoxLayout(); col.setSpacing(_dp(2))
        num_lbl = QLabel(f"LOCKER  #{locker['t_numero_locker']}")
        num_lbl.setStyleSheet(
            f"color:{badge_fg};font-size:{_dp(11)}px;font-weight:900;font-family:'Segoe UI';"
        )
        col.addWidget(num_lbl)
        meta = QLabel(
            f"ZONA  {locker.get('t_zona') or '—'}   ·   TAMAÑO  {locker.get('t_tamano') or '—'}"
        )
        meta.setObjectName("meta"); meta.setStyleSheet(f"font-size:{_dp(7)}px;")
        col.addWidget(meta); lay.addLayout(col); lay.addStretch()

        fecha = str(locker.get("d_fecha_registro", "") or "")[:10]
        if fecha:
            fl = QLabel(fecha)
            fl.setStyleSheet(f"color:#b0bec5;font-size:{_dp(7)}px;font-family:'Segoe UI';")
            fl.setAlignment(Qt.AlignRight | Qt.AlignVCenter); lay.addWidget(fl)

        badge_txt = {"libre":"LIBRE","ocupado":"OCUPADO","mantenimiento":"MANTENIM."}.get(estado, estado.upper())
        badge = QLabel(badge_txt)
        badge.setStyleSheet(
            f"background:{badge_bg};color:{badge_fg};border:1px solid {badge_border};"
            f"border-radius:8px;font-size:{_dp(7)}px;font-weight:700;"
            f"font-family:'Segoe UI';letter-spacing:2px;padding:{_dp(2)}px {_dp(8)}px;"
        )
        lay.addWidget(badge)

        bc = QPushButton("⚙"); bc.setObjectName("btn_cfg")
        bc.setToolTip("Configurar"); bc.setFixedSize(_dp(26), _dp(26))
        bc.setCursor(Qt.PointingHandCursor); bc.clicked.connect(self._config)
        lay.addWidget(bc)

        if estado == "ocupado":
            bl = QPushButton("↩ LIBERAR"); bl.setObjectName("btn_lib")
            bl.setStyleSheet(f"font-size:{_dp(7)}px;padding:{_dp(3)}px {_dp(8)}px;")
            bl.setCursor(Qt.PointingHandCursor); bl.clicked.connect(self._liberar)
            lay.addWidget(bl)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _log(self, tipo, resultado, desc, id_sesion=None):
        """Single point for db_log_intento — column names match Intentos_acceso exactly."""
        db_log_intento(
            id_locker   = self.locker["ID_locker"],
            tipo        = tipo,
            resultado   = resultado,
            descripcion = desc or "",
            id_sesion   = id_sesion,
            id_usuario  = self.admin_id,
        )

    def _close_active_session(self, extra_desc: str = ""):
        for s in db_get_all_sesiones_activas():
            if s["ID_locker"] != self.locker["ID_locker"]: continue
            db_close_sesion(s["ID_sesion"])
            fuid = s.get("b_vector_biometrico_temp")
            if isinstance(fuid, bytes): fuid = fuid.decode()
            if fuid: delete_face_data(fuid)
            desc = f"Sesión #{s['ID_sesion']} cerrada al liberar locker #{self.locker['t_numero_locker']}."
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
            db_update_locker(
                id_locker=self.locker["ID_locker"], numero=d["numero"],
                zona=d["zona"], tamano=d["tamano"], estado=d["estado"],
                id_admin=self.admin_id,
            )
            self._log("configuracion_admin", "exitoso",
                      "Modificado: " + ("; ".join(changes) or "sin cambios"))
            if d["estado"] == "libre" and self.locker.get("t_estado") != "libre":
                self._close_active_session()
            DlgInfo.show(f"Locker #{d['numero']} actualizado.", parent=self)
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


class _AdminLockersPanel(QWidget):
    def __init__(self, admin_id=None):
        super().__init__()
        self.admin_id = admin_id
        self.setObjectName("panel"); self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)
        m = _dp(14)
        root.setContentsMargins(m, _dp(10), m, _dp(10)); root.setSpacing(_dp(8))

        hdr = QHBoxLayout(); hdr.setSpacing(_dp(6))
        tc  = QVBoxLayout(); tc.setSpacing(_dp(2))
        t = QLabel("GESTIÓN DE LOCKERS"); t.setObjectName("ttl"); t.setStyleSheet(f"font-size:{_dp(12)}px;")
        s = QLabel("PANEL ADMIN · LOCKERS DE TIENDA"); s.setObjectName("sub"); s.setStyleSheet(f"font-size:{_dp(8)}px;")
        tc.addWidget(t); tc.addWidget(s); hdr.addLayout(tc); hdr.addStretch()

        for obj, icon, cb in [("btn_add","＋  NUEVO",self._agregar),("btn_ref","↺  ACTUALIZAR",self.refresh)]:
            b = QPushButton(icon); b.setObjectName(obj)
            b.setStyleSheet(f"font-size:{_dp(8)}px;padding:{_dp(5)}px {_dp(14)}px;")
            b.setCursor(Qt.PointingHandCursor); b.clicked.connect(cb); hdr.addWidget(b)
        root.addLayout(hdr); root.addWidget(self._div())

        cr = QHBoxLayout(); cr.setSpacing(_dp(10)); self._cnt = {}
        for key, label, obj in [("libre","LIBRES","cn_b"),("ocupado","OCUPADOS","cn_o"),("total","TOTAL","cn_g")]:
            blk = QFrame(); blk.setObjectName("cnt")
            bl  = QHBoxLayout(blk); bl.setContentsMargins(_dp(12),_dp(7),_dp(12),_dp(7)); bl.setSpacing(_dp(8))
            n = QLabel("0"); n.setObjectName(obj); n.setStyleSheet(f"font-size:{_dp(24)}px;")
            k = QLabel(label); k.setObjectName("ck"); k.setStyleSheet(f"font-size:{_dp(7)}px;")
            bl.addWidget(n); bl.addWidget(k); bl.addStretch(); cr.addWidget(blk, 1); self._cnt[key] = n
        root.addLayout(cr); root.addWidget(self._div())

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.inner = QWidget(); self.inner.setObjectName("inner")
        self.il = QVBoxLayout(self.inner)
        self.il.setContentsMargins(0,_dp(4),_dp(4),0); self.il.setSpacing(_dp(5))
        self.il.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.inner); root.addWidget(scroll, 1)
        self.refresh()

    def _div(self):
        d = QFrame(); d.setObjectName("h_div"); return d

    def paintEvent(self, e):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0.0, QColor(232, 240, 251)); g.setColorAt(1.0, QColor(214, 230, 248))
        p.fillRect(0, 0, self.width(), self.height(), QBrush(g)); p.end()

    def _agregar(self):
        num = DlgInput.ask("Ingresa el número del nuevo locker:", title="Nuevo Locker",
                           placeholder="ej. 42", parent=self)
        if not num: return
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
        for i in reversed(range(self.il.count())):
            w = self.il.itemAt(i)
            if w and w.widget(): w.widget().deleteLater()

        lockers = db_get_all_lockers()
        libres  = sum(1 for l in lockers if l.get("t_estado") == "libre")
        ocups   = sum(1 for l in lockers if l.get("t_estado") == "ocupado")
        self._cnt["libre"].setText(str(libres))
        self._cnt["ocupado"].setText(str(ocups))
        self._cnt["total"].setText(str(len(lockers)))

        if not lockers:
            e = QLabel("·  SIN LOCKERS REGISTRADOS  ·")
            e.setObjectName("empty"); e.setAlignment(Qt.AlignCenter)
            e.setStyleSheet(f"font-size:{_dp(9)}px;")
            e.setContentsMargins(0,_dp(20),0,_dp(20)); self.il.addWidget(e); return

        _ord = {"ocupado":0,"libre":1,"mantenimiento":2}
        for i, lk in enumerate(
            sorted(lockers, key=lambda l: _ord.get(l.get("t_estado",""),9)), 1
        ):
            self.il.addWidget(LockerCard(lk, i, self.admin_id, on_refresh=self.refresh))