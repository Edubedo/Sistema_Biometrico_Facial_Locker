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

