import sys
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(path=".env"):
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        return True

from PyQt5.QtCore import QLibraryInfo, QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QStackedWidget, QShortcut, QLabel,
)
from PyQt5.QtGui import QKeySequence

from db.models.usuarios import db_count_active_admins, db_register_admin
from db.models.lockers import db_next_free_locker
from db.models.sesiones import db_get_all_sesiones_activas

from views.cliente.home import HomePage
from views.cliente.guardar import GuardarPage
from views.cliente.retirar import RetirarPage
from views.cliente.resultado import ResultPage

from views.admin.adminPage import AdminPage
from views.admin.loginPage import AdminLoginPage

from biometria.biometria import train_model
from utils.i18n import set_language, get_language, tr

load_dotenv()

DB_PATH = os.getenv("DB_PATH")


def _fix_qt_plugin_path_for_linux():
    current = os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", "")
    if "/site-packages/cv2/qt/plugins" in current.replace("\\", "/"):
        pyqt_plugins = QLibraryInfo.location(QLibraryInfo.PluginsPath)
        if pyqt_plugins:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = pyqt_plugins


class MainWindow(QMainWindow):
    HOME   = 0
    GUARD  = 1
    RETIR  = 2
    RESULT = 3
    ALOGIN = 4
    ADMIN  = 5

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app.title"))
        self.setMinimumSize(800, 480)

        cw = QWidget()
        self.setCentralWidget(cw)
        ml = QVBoxLayout(cw); ml.setContentsMargins(0, 0, 0, 0); ml.setSpacing(0)

        self.stack    = QStackedWidget()
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

        # ── Navegación ────────────────────────────────────────────────────────
        self.p_home.go_guardar.connect(self._try_go_guardar)
        self.p_home.go_retirar.connect(self._try_go_retirar)
        self.p_home.go_admin.connect(lambda: self._nav(self.ALOGIN))
        self.p_home.language_changed.connect(self._on_language_changed)

        self.p_guard.go_back.connect(lambda: self._nav(self.HOME))
        guard_done = getattr(self.p_guard, "done", None)
        if guard_done is not None:
            guard_done.connect(self._on_guardado)

        guard_failed = getattr(self.p_guard, "failed", None)
        if guard_failed is not None:
            guard_failed.connect(
                lambda msg: self._show_result("err", tr("flow.no_space_title"), msg)
            )

        # ── NUEVO: sesión ya activa detectada al guardar ──────────────────────
        # Muestra ResultPage con aviso y redirige al inicio automáticamente.
        guard_session = getattr(self.p_guard, "already_has_session", None)
        if guard_session is not None:
            guard_session.connect(self._on_session_active)

        self.p_retir.go_back.connect(lambda: self._nav(self.HOME))
        self.p_retir.retirar_done.connect(self._on_retirado)
        self.p_retir.seguir_done.connect(self._on_seguir)
        self.p_retir.no_session.connect(self._on_retir_no_session)

        self.p_result.go_home.connect(lambda: self._nav(self.HOME))

        self.p_alogin.go_back.connect(lambda: self._nav(self.HOME))
        self.p_alogin.login_ok.connect(self._on_login)

        self.p_admin.go_back.connect(lambda: self._nav(self.HOME))

        self._on_language_changed(get_language())
        self._nav(self.HOME)
        self._install_window_shortcuts()

        self._alerta_visible = False
        self._alerta_banner  = self._crear_banner_alerta()
        self._lockers_alertando = set()
        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._check_lockers_abiertos)
        self._monitor_timer.start(2000)

    def _install_window_shortcuts(self):
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, activated=self.exit_fullscreen)

    def toggle_fullscreen(self):
        if self.isFullScreen(): self.showNormal()
        else: self.showFullScreen()

    def exit_fullscreen(self):
        if self.isFullScreen(): self.showNormal()

    def _on_language_changed(self, lang):
        set_language(lang)
        for p in (self.p_home, self.p_guard, self.p_retir, self.p_alogin, self.p_admin):
            if hasattr(p, "set_language"):
                p.set_language(lang)

    def _try_go_guardar(self):
        try:
            if db_next_free_locker() is None:
                try: self.p_home.refresh()
                except Exception: pass
                return
        except Exception:
            try: self.p_home.refresh()
            except Exception: pass
            return
        self._nav(self.GUARD)

    def _try_go_retirar(self):
        try:
            if not db_get_all_sesiones_activas():
                self._show_result(
                    "err",
                    tr("admin.sessions.no_data"),
                    tr("ret.no_active_session"),
                )
                return
        except Exception:
            self._show_result(
                "err",
                tr("admin.sessions.no_data"),
                tr("ret.no_active_session"),
            )
            return
        self._nav(self.RETIR)

    # ── Navegación ────────────────────────────────────────────────────────────

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

    # ── Callbacks de flujo ────────────────────────────────────────────────────

    def _on_guardado(self, face_uid, num_locker, id_sesion):
        self.p_guard.reset()
        self._show_result(
            "ok_blue",
            tr("flow.assigned_title"),
            tr("flow.assigned_sub"),
            "LOCKER  #{}".format(num_locker)
        )

    def _on_session_active(self, num_locker: str):
        """
        El precheck biométrico detectó que la persona ya tiene locker activo.
        Muestra aviso visual con countdown de 5 s y regresa al inicio.
        """
        self.p_guard.reset()
        self.stack.setCurrentIndex(self.RESULT)
        self.p_result.show_already_has_locker(
            num_locker=num_locker,
            on_timeout=lambda: self._nav(self.HOME),
        )

    def _on_retirado(self, face_uid, num_locker, id_sesion):
        self.p_retir.reset()
        self.p_result.show_result(
            "ok_blue",
            tr("flow.bye_title"),
            tr("flow.bye_sub", n=num_locker),
            "LOCKER  #{}".format(num_locker),
        )
        self._nav(self.RESULT)

    def _on_seguir(self, face_uid, num_locker, id_sesion):
        self.p_retir.reset()
        detail = "LOCKER  #{}".format(num_locker) if num_locker else ""
        self.p_result.show_result(
            "ok_blue",
            tr("flow.keep_title"),
            tr("flow.keep_sub"),
            detail,
        )
        self._nav(self.RESULT)

    def _on_retir_no_session(self):
        """
        Se reconoció a alguien en retirar pero NO tiene sesión activa.
        Muestra ResultPage con aviso de error y redirige al inicio en 5 s.
        """
        self.p_retir.reset()
        self.p_result.show_result(
            "err",
            tr("ret.no_session_title"),
            tr("ret.no_session_sub"),
            auto=True,
        )
        self._nav(self.RESULT)

    def _on_login(self, admin_data):
        self.p_admin.set_admin(admin_data)
        self._nav(self.ADMIN)

    # ── Banner alerta locker abierto ─────────────────────────────────────────

    def _crear_banner_alerta(self):
        banner = QLabel(self)
        banner.setAlignment(Qt.AlignCenter)
        banner.setWordWrap(True)
        banner.setStyleSheet("""
            background-color: #D32F2F; color: white;
            font-size: 22px; font-weight: bold;
            padding: 18px; border-radius: 0px;
        """)
        banner.hide()
        return banner

    def _check_lockers_abiertos(self):
        try:
            from utils.gpio_locker import locker_esta_abierto, SWITCH_PINS, iniciar_monitor, detener_monitor
        except ImportError:
            return
        abiertos = []
        for num in SWITCH_PINS.keys():
            if locker_esta_abierto(num):
                abiertos.append(num)
                if num not in self._lockers_alertando:
                    self._lockers_alertando.add(num)
                    iniciar_monitor(num)
            else:
                if num in self._lockers_alertando:
                    self._lockers_alertando.discard(num)
                    detener_monitor(num)
        if abiertos:
            nums = ", ".join(f"#{n}" for n in abiertos)
            self._alerta_banner.setText(f"⚠  LOCKER {nums} ABIERTO — POR FAVOR CIÉRRALO  ⚠")
            self._alerta_banner.setGeometry(0, 0, self.width(), 70)
            self._alerta_banner.raise_()
            self._alerta_banner.show()
        else:
            self._alerta_banner.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._alerta_banner and not self._alerta_banner.isHidden():
            self._alerta_banner.setGeometry(0, 0, self.width(), 70)

    def closeEvent(self, event):
        try: self.p_guard.reset()
        except Exception: pass
        try: self.p_retir.reset()
        except Exception: pass
        super().closeEvent(event)


# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _fix_qt_plugin_path_for_linux()

    if not os.path.exists(DB_PATH):
        print("[ERROR] No se encontro la base de datos en: {}".format(DB_PATH))
        sys.exit(1)

    try:
        if db_count_active_admins() == 0:
            db_register_admin(
                "Administrador", "Sistema", "Locker",
                "admin", "admin1234", rol="administrador"
            )
            print("[INFO] Admin por defecto creado: admin / admin1234")
    except Exception as e:
        print("[WARN] No se pudo verificar admins: {}".format(e))

    train_model()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    fullscreen_env = os.getenv("APP_FULLSCREEN", "1").strip().lower()
    if fullscreen_env not in ("0", "false", "no", "off"):
        w.showFullScreen()
    else:
        w.show()
    exit_code = app.exec_()

    try:
        from utils.gpio_locker import cleanup
        cleanup()
    except Exception as e:
        print(f"[WARN] No se pudo hacer cleanup de GPIO: {e}")

    sys.exit(exit_code)