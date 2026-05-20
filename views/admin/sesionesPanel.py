from PyQt5.QtCore import Qt, QTimer, QAbstractTableModel, QModelIndex, QVariant
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QApplication, QGraphicsDropShadowEffect,
    QTableView, QAbstractItemView, QHeaderView, QScroller,
)
from PyQt5.QtGui import QPainter, QColor, QBrush, QLinearGradient, QFont

from db.models.sesiones import db_get_all_sesiones_activas
from utils.i18n import tr, get_language


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers  (idénticos al resto del proyecto)
# ─────────────────────────────────────────────────────────────────────────────
def _dp(value: float) -> int:
    screen = QApplication.primaryScreen()
    dpi    = screen.logicalDotsPerInch() if screen else 96
    scale  = min(dpi / 96, 1.25)
    return max(1, round(value * scale))


_TOUCH_H = 52   # altura mínima de objetivo táctil en px


def _shadow(widget, blur=12, alpha=18, dy=2):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setColor(QColor(21, 101, 192, alpha))
    s.setOffset(0, dy)
    widget.setGraphicsEffect(s)


# ─────────────────────────────────────────────────────────────────────────────
#  Modelo de tabla  (QAbstractTableModel)
# ─────────────────────────────────────────────────────────────────────────────
_COLS = ["Sesión", "Locker", "Fecha / Hora", "Estado"]
_KEYS = ["ID_sesion", "t_numero_locker", "d_fecha_hora_entrada", "_estado"]


def _fmt_ts(ts: str) -> str:
    if ts and len(ts) >= 16:
        return f"{ts[8:10]}/{ts[5:7]}/{ts[0:4]}  {ts[11:16]}"
    return str(ts).replace("T", "  ")


class SesionesTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[dict] = []

    def load(self, rows: list[dict]):
        self.beginResetModel()
        self._data = rows
        self.endResetModel()

    def rowCount(self,    parent=QModelIndex()): return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(_COLS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return _COLS[section]
        return QVariant()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()

        row = self._data[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:   # Sesión
                return f"SESIÓN  #{row.get('ID_sesion', '—')}"
            if col == 1:   # Locker
                v = row.get("t_numero_locker", "")
                return str(v) if v else "—"
            if col == 2:   # Fecha/Hora
                return _fmt_ts(str(row.get("d_fecha_hora_entrada", "") or ""))
            if col == 3:   # Estado — siempre activa en este panel
                return tr("admin.sessions.active")
            return ""

        if role == Qt.ForegroundRole and col == 3:
            return QBrush(QColor("#1565c0"))

        if role == Qt.BackgroundRole:
            if col == 3:
                return QBrush(QColor("#e3f0ff"))
            if index.row() % 2 == 1:
                return QBrush(QColor("#f4f8ff"))

        if role == Qt.TextAlignmentRole:
            if col in (0, 1, 3): return Qt.AlignCenter
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        if role == Qt.FontRole:
            f = QFont("Segoe UI", _dp(11))
            if col == 3: f.setBold(True)
            return f

        return QVariant()


# ─────────────────────────────────────────────────────────────────────────────
#  Dot de estado animado
# ─────────────────────────────────────────────────────────────────────────────
class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        sz = _dp(12); self.setFixedSize(sz, sz)
        self._alpha  = 255
        self._growing = False
        t = QTimer(self); t.timeout.connect(self._tick); t.start(40)

    def _tick(self):
        self._alpha += -5 if not self._growing else 5
        if self._alpha <= 80:  self._growing = True
        if self._alpha >= 255: self._growing = False
        self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = QColor(25, 118, 210); c.setAlpha(self._alpha)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(c))
        m = _dp(1)
        p.drawEllipse(m, m, self.width()-m*2, self.height()-m*2)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  Botón toggle táctil  (mismo que adminLogPanel)
# ─────────────────────────────────────────────────────────────────────────────
class ToggleBtn(QPushButton):
    _ON  = "QPushButton{{background:{bg};color:{fg};border:2px solid {bg};border-radius:{r}px;font-family:'Segoe UI',sans-serif;font-weight:800;font-size:{fs}px;letter-spacing:1px;padding:0 {pad}px;}}"
    _OFF = "QPushButton{{background:#f4f8ff;color:{border};border:2px solid {border};border-radius:{r}px;font-family:'Segoe UI',sans-serif;font-weight:700;font-size:{fs}px;letter-spacing:1px;padding:0 {pad}px;}}QPushButton:pressed{{background:#e3f0ff;}}"

    def __init__(self, text, bg="#1565c0", fg="#ffffff", border="#1565c0", parent=None):
        super().__init__(text, parent)
        self._bg = bg; self._fg = fg; self._border = border
        self._active = False
        self.setFixedHeight(_dp(_TOUCH_H))
        self.setMinimumWidth(_dp(80))
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self._apply()

    def set_active(self, val: bool):
        self._active = val; self._apply()

    def _apply(self):
        kw = dict(r=_dp(10), fs=_dp(11), pad=_dp(18))
        if self._active:
            self.setStyleSheet(self._ON.format(bg=self._bg, fg=self._fg, **kw))
        else:
            self.setStyleSheet(self._OFF.format(border=self._border, **kw))


# ─────────────────────────────────────────────────────────────────────────────
#  Estilos globales
# ─────────────────────────────────────────────────────────────────────────────
def _build_style():
    TH  = _dp(_TOUCH_H)
    r10 = _dp(10)
    r6  = _dp(6)
    return f"""
QWidget#admin_sessions_panel {{ background: transparent; }}

QLabel#section_title {{
    color: #1565c0; font-weight: 900;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 3px; font-size: {_dp(13)}px;
}}
QLabel#section_sub {{
    color: #37474f; font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px; font-size: {_dp(11)}px;
}}

QFrame#counter_block {{
    background: #ffffff; border: none;
    border-left: 4px solid #1565c0; border-radius: {r10}px;
}}
QLabel#counter_num {{
    color: #1565c0; font-weight: 800;
    font-family: 'Segoe UI', sans-serif; font-size: {_dp(26)}px;
}}
QLabel#counter_key {{
    color: #37474f; font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px; font-size: {_dp(10)}px;
}}
QLabel#status_text {{
    color: #37474f; font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px; font-weight: 600; font-size: {_dp(10)}px;
}}

QFrame#filter_bar {{
    background: #ffffff; border: 1px solid #cfd8e3;
    border-radius: {r10}px;
}}
QLabel#filter_lbl {{
    color: #546e7a; font-family: 'Segoe UI', sans-serif;
    font-size: {_dp(10)}px; letter-spacing: 1px;
}}

QPushButton#btn_refresh {{
    background: #1565c0; color: #ffffff;
    border: none; border-radius: {r10}px;
    font-family: 'Segoe UI', sans-serif;
    font-weight: 800; letter-spacing: 2px;
    font-size: {_dp(11)}px;
    min-height: {TH}px; min-width: {_dp(140)}px;
    padding: 0 {_dp(20)}px;
}}
QPushButton#btn_refresh:hover   {{ background: #1976d2; }}
QPushButton#btn_refresh:pressed {{ background: #0d47a1; }}

QTableView#admin_sessions_tbl {{
    background: #ffffff;
    alternate-background-color: #f4f8ff;
    border: 1px solid #cfd8e3;
    border-radius: {r10}px;
    gridline-color: #e8f0fb;
    selection-background-color: #bbdefb;
    font-family: 'Segoe UI', sans-serif;
    font-size: {_dp(11)}px;
    color: #000000;
}}
QTableView#admin_sessions_tbl::item {{
    padding: {_dp(10)}px {_dp(12)}px;
    border-bottom: 1px solid #f0f4fa;
}}
QTableView#admin_sessions_tbl::item:selected {{
    background: #bbdefb; color: #0d47a1;
}}
QHeaderView::section {{
    background: #1565c0; color: #ffffff;
    font-weight: 900; font-family: 'Segoe UI', sans-serif;
    letter-spacing: 1px; font-size: {_dp(10)}px;
    padding: {_dp(10)}px {_dp(12)}px;
    border: none;
    border-right: 1px solid rgba(255,255,255,0.18);
    min-height: {_dp(40)}px;
}}
QHeaderView::section:last  {{ border-right: none; }}
QHeaderView::section:hover {{ background: #1976d2; }}

QScrollBar:vertical {{
    background: #e8f0fb; width: {_dp(6)}px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #90c4f0; border-radius: {_dp(3)}px; min-height: {_dp(28)}px;
}}
QScrollBar::add-line:vertical,  QScrollBar::sub-line:vertical  {{ height: 0; }}
QScrollBar:horizontal {{
    background: #e8f0fb; height: {_dp(6)}px; margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: #90c4f0; border-radius: {_dp(3)}px; min-width: {_dp(28)}px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QFrame#page_bar {{
    background: #ffffff; border: 1px solid #cfd8e3;
    border-radius: {r10}px;
}}
QPushButton#btn_page {{
    background: #e3f0ff; color: #1565c0;
    border: 2px solid #90c4f0; border-radius: {r6}px;
    font-family: 'Segoe UI', sans-serif;
    font-size: {_dp(16)}px; font-weight: 900;
    min-width: {_dp(56)}px; min-height: {TH}px;
    padding: 0 {_dp(6)}px;
}}
QPushButton#btn_page:hover   {{ background: #bbdefb; border-color: #1565c0; }}
QPushButton#btn_page:pressed {{ background: #90c4f0; }}
QPushButton#btn_page:disabled {{
    background: #f4f8ff; color: #b0bec5; border-color: #e0e8f0;
}}
QLabel#page_lbl {{
    color: #1565c0; font-family: 'Segoe UI', sans-serif;
    font-size: {_dp(12)}px; font-weight: 800;
    min-width: {_dp(100)}px;
}}
QLabel#count_lbl {{
    color: #546e7a; font-family: 'Segoe UI', sans-serif;
    font-size: {_dp(10)}px;
}}

QFrame#h_divider {{
    background: #cfd8e3; border: none;
    min-height: 1px; max-height: 1px;
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Panel principal
# ─────────────────────────────────────────────────────────────────────────────
class _AdminSesionesPanel(QWidget):

    _PAGE_STEPS = [25, 50, 100, 200]
    _PAGE_SIZE  = 50

    def __init__(self):
        super().__init__()
        self.setObjectName("admin_sessions_panel")
        self.setStyleSheet(_build_style())

        self._all_rows:  list[dict] = []
        self._page      = 0
        self._page_size = self._PAGE_SIZE

        root = QVBoxLayout(self)
        m = _dp(12)
        root.setContentsMargins(m, _dp(8), m, _dp(8))
        root.setSpacing(_dp(7))

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(_dp(10))

        col = QVBoxLayout(); col.setSpacing(_dp(2))
        self.title_lbl = QLabel(tr("admin.sessions.title"))
        self.title_lbl.setObjectName("section_title")
        self.sub_lbl = QLabel(tr("admin.sessions.subtitle"))
        self.sub_lbl.setObjectName("section_sub")
        col.addWidget(self.title_lbl)
        col.addWidget(self.sub_lbl)
        hdr.addLayout(col)
        hdr.addStretch()

        self.btn_ref = QPushButton("↻  " + tr("admin.sessions.refresh"))
        self.btn_ref.setObjectName("btn_refresh")
        self.btn_ref.setCursor(Qt.PointingHandCursor)
        self.btn_ref.setFocusPolicy(Qt.NoFocus)
        self.btn_ref.clicked.connect(self.refresh)
        hdr.addWidget(self.btn_ref)
        root.addLayout(hdr)

        div = QFrame(); div.setObjectName("h_divider")
        root.addWidget(div)

        # ── Counter ───────────────────────────────────────────────────────────
        cb = QFrame(); cb.setObjectName("counter_block")
        _shadow(cb, _dp(10), 14, _dp(2))
        cb_lay = QHBoxLayout(cb)
        cb_lay.setContentsMargins(_dp(14), _dp(8), _dp(14), _dp(8))
        cb_lay.setSpacing(_dp(8))
        self.counter_lbl = QLabel("0")
        self.counter_lbl.setObjectName("counter_num")
        self.key_lbl = QLabel(tr("admin.sessions.count"))
        self.key_lbl.setObjectName("counter_key")
        cb_lay.addWidget(self.counter_lbl)
        cb_lay.addWidget(self.key_lbl)
        cb_lay.addStretch()
        cb_lay.addWidget(StatusDot())
        self.status_lbl = QLabel(tr("admin.sessions.status"))
        self.status_lbl.setObjectName("status_text")
        cb_lay.addWidget(self.status_lbl)
        root.addWidget(cb)

        # ── Barra de filtros táctil ───────────────────────────────────────────
        # Sesiones solo tienen un estado (activa), así que el filtro útil
        # es ordenar por locker o por fecha — se expone como toggle de orden.
        fb = QFrame(); fb.setObjectName("filter_bar")
        _shadow(fb, _dp(8), 10, _dp(1))
        fb_lay = QHBoxLayout(fb)
        fb_lay.setContentsMargins(_dp(12), _dp(8), _dp(12), _dp(8))
        fb_lay.setSpacing(_dp(8))

        lbl_f = QLabel("Ordenar:"); lbl_f.setObjectName("filter_lbl")
        fb_lay.addWidget(lbl_f)

        # Toggle de orden: más reciente primero / más antiguo primero
        self._tbtn_desc = ToggleBtn("↓  Más reciente", bg="#1565c0")
        self._tbtn_asc  = ToggleBtn("↑  Más antiguo",  bg="#546e7a", border="#546e7a")
        self._tbtn_desc.set_active(True)

        self._sort_desc = True
        self._tbtn_desc.clicked.connect(lambda: self._apply_sort(desc=True))
        self._tbtn_asc.clicked.connect(lambda:  self._apply_sort(desc=False))

        fb_lay.addWidget(self._tbtn_desc)
        fb_lay.addWidget(self._tbtn_asc)
        fb_lay.addStretch()

        root.addWidget(fb)

        # ── Tabla ─────────────────────────────────────────────────────────────
        self._model = SesionesTableModel()

        self.table = QTableView()
        self.table.setObjectName("admin_sessions_tbl")
        self.table.setModel(self._model)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalScrollBar().setSingleStep(_dp(48))
        QScroller.grabGesture(self.table.viewport(), QScroller.LeftMouseButtonGesture)
        self.table.viewport().setAttribute(Qt.WA_AcceptTouchEvents, True)

        hh = self.table.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setMinimumSectionSize(_dp(70))
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setStretchLastSection(False)
        self.table.verticalHeader().setDefaultSectionSize(_dp(52))
        self.table.setSortingEnabled(False)   # el orden lo manejamos nosotros

        root.addWidget(self.table, 1)

        # ── Barra de paginación táctil ────────────────────────────────────────
        pg_bar = QFrame(); pg_bar.setObjectName("page_bar")
        _shadow(pg_bar, _dp(8), 10, _dp(1))
        pg_lay = QHBoxLayout(pg_bar)
        pg_lay.setContentsMargins(_dp(12), _dp(6), _dp(12), _dp(6))
        pg_lay.setSpacing(_dp(8))

        self.count_lbl = QLabel("")
        self.count_lbl.setObjectName("count_lbl")
        pg_lay.addWidget(self.count_lbl, 1)

        self.btn_first = QPushButton("«")
        self.btn_prev  = QPushButton("‹  Ant")
        self.page_lbl  = QLabel("1 / 1")
        self.btn_next  = QPushButton("Sig  ›")
        self.btn_last  = QPushButton("»")

        for b, w in (
            (self.btn_first, _dp(52)),
            (self.btn_prev,  _dp(110)),
            (self.btn_next,  _dp(110)),
            (self.btn_last,  _dp(52)),
        ):
            b.setObjectName("btn_page")
            b.setFixedSize(w, _dp(_TOUCH_H))
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            pg_lay.addWidget(b)
            if b is self.btn_prev:
                self.page_lbl.setObjectName("page_lbl")
                self.page_lbl.setAlignment(Qt.AlignCenter)
                pg_lay.addWidget(self.page_lbl)

        self.btn_first.clicked.connect(lambda: self._go_page(0))
        self.btn_prev.clicked.connect(lambda:  self._go_page(self._page - 1))
        self.btn_next.clicked.connect(lambda:  self._go_page(self._page + 1))
        self.btn_last.clicked.connect(lambda:  self._go_page(self._total_pages() - 1))

        root.addWidget(pg_bar)

        self.set_language(get_language())
        self.refresh()

    # ── Fondo ─────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        W, H = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0.0, QColor(232, 240, 251))
        g.setColorAt(1.0, QColor(214, 230, 248))
        p.fillRect(0, 0, W, H, QBrush(g))
        p.end()

    # ── Orden ─────────────────────────────────────────────────────────────────
    def _apply_sort(self, desc: bool):
        self._sort_desc = desc
        self._tbtn_desc.set_active(desc)
        self._tbtn_asc.set_active(not desc)
        self._all_rows.sort(
            key=lambda r: (r.get("d_fecha_hora_entrada", "") or ""),
            reverse=desc,
        )
        self._page = 0
        self._render_page()

    # ── Tamaño de página ──────────────────────────────────────────────────────
    def _inc_page_size(self):
        steps = self._PAGE_STEPS
        nxt = next((s for s in steps if s > self._page_size), steps[-1])
        self._page_size = nxt
        self._pg_size_lbl.setText(str(nxt))
        self._page = 0; self._render_page()

    def _dec_page_size(self):
        steps = self._PAGE_STEPS
        prv = next((s for s in reversed(steps) if s < self._page_size), steps[0])
        self._page_size = prv
        self._pg_size_lbl.setText(str(prv))
        self._page = 0; self._render_page()

    # ── Paginación ────────────────────────────────────────────────────────────
    def _total_pages(self) -> int:
        total = len(self._all_rows)
        return max(1, (total + self._page_size - 1) // self._page_size)

    def _go_page(self, page: int):
        self._page = max(0, min(page, self._total_pages() - 1))
        self._render_page()

    def _render_page(self):
        start = self._page * self._page_size
        end   = start + self._page_size
        self._model.load(self._all_rows[start:end])

        pages = self._total_pages()
        total = len(self._all_rows)
        s0    = start + 1 if total else 0
        s1    = min(end, total)

        self.count_lbl.setText(f"{s0}–{s1}  de  {total}")
        self.page_lbl.setText(f"{self._page + 1} / {pages}")
        self.btn_first.setEnabled(self._page > 0)
        self.btn_prev.setEnabled(self._page  > 0)
        self.btn_next.setEnabled(self._page  < pages - 1)
        self.btn_last.setEnabled(self._page  < pages - 1)

    # ── Datos ─────────────────────────────────────────────────────────────────
    def refresh(self):
        sesiones = db_get_all_sesiones_activas()
        self._all_rows = sorted(
            sesiones,
            key=lambda r: (r.get("d_fecha_hora_entrada", "") or ""),
            reverse=self._sort_desc,
        )
        self.counter_lbl.setText(str(len(self._all_rows)))
        self._page = 0
        self._render_page()

    # ── Idioma ────────────────────────────────────────────────────────────────
    def set_language(self, _lang: str):
        self.title_lbl.setText(tr("admin.sessions.title"))
        self.sub_lbl.setText(tr("admin.sessions.subtitle"))
        self.btn_ref.setText("↻  " + tr("admin.sessions.refresh"))
        self.key_lbl.setText(tr("admin.sessions.count"))
        self.status_lbl.setText(tr("admin.sessions.status"))