import os # Sistema operativo
import sys 

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(path=".env"):
        """Minimal .env loader fallback when python-dotenv is unavailable."""
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

from PyQt5.QtCore import QLibraryInfo

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QStackedWidget,
    QShortcut,
)
from PyQt5.QtGui import QKeySequence
from db.models.usuarios import db_count_active_admins, db_register_admin
from db.models.lockers import db_next_free_locker
from db.models.sesiones import db_get_all_sesiones_activas

# Views
from views.cliente.home import HomePage
from views.cliente.guardar import GuardarPage 
from views.cliente.retirar import RetirarPage
from views.cliente.resultado import ResultPage

from views.admin.adminPage import  AdminPage
from views.admin.loginPage import AdminLoginPage

from biometria.biometria import train_model
from utils.i18n import set_language, get_language, tr

load_dotenv()  

DB_PATH = os.getenv("DB_PATH")


def _fix_qt_plugin_path_for_linux():
    """Avoid Qt plugin conflicts caused by OpenCV's bundled Qt plugins."""
    current = os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", "")
    current_norm = current.replace("\\", "/")
    if "/site-packages/cv2/qt/plugins" in current_norm:
        pyqt_plugins = QLibraryInfo.location(QLibraryInfo.PluginsPath)
        if pyqt_plugins:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = pyqt_plugins


class MainWindow(QMainWindow):
    # Indices del QStackedWidget
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

        # ── Paginas ──────────────────────────────────────────────────────────
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

        # ── Conexiones de navegacion ─────────────────────────────────────────
        self.p_home.go_guardar.connect(self._try_go_guardar)
        self.p_home.go_retirar.connect(self._try_go_retirar)
        self.p_home.go_admin.connect(lambda: self._nav(self.ALOGIN))
        self.p_home.language_changed.connect(self._on_language_changed)

        self.p_guard.go_back.connect(lambda: self._nav(self.HOME))
        guard_done = getattr(self.p_guard, "done", None)
        if guard_done is not None:
            guard_done.connect(self._on_guardado)
        else:
            print("[WARN] GuardarPage no expone la senal 'done'.")

        guard_failed = getattr(self.p_guard, "failed", None)
        if guard_failed is not None:
            guard_failed.connect(
                lambda msg: self._show_result("err", tr("flow.no_space_title"), msg)
            )
        else:
            print("[WARN] GuardarPage no expone la senal 'failed'.")

        self.p_retir.go_back.connect(lambda: self._nav(self.HOME))
        self.p_retir.retirar_done.connect(self._on_retirado)
        self.p_retir.seguir_done.connect(self._on_seguir)

        self.p_result.go_home.connect(lambda: self._nav(self.HOME))

        self.p_alogin.go_back.connect(lambda: self._nav(self.HOME))
        self.p_alogin.login_ok.connect(self._on_login)

        self.p_admin.go_back.connect(lambda: self._nav(self.HOME))

        self._on_language_changed(get_language())
        self._nav(self.HOME)
        self._install_window_shortcuts()

    def _install_window_shortcuts(self):
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, activated=self.exit_fullscreen)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def exit_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()

    def _on_language_changed(self, lang):
        set_language(lang)
        for p in (self.p_home, self.p_guard, self.p_retir, self.p_alogin, self.p_admin):
            if hasattr(p, "set_language"):
                p.set_language(lang)

    def _try_go_guardar(self):
        """Navigate to GuardarPage only if there is at least one free locker."""
        try:
            if db_next_free_locker() is None:
                # No free lockers: keep the user on Home and leave the fixed no-space state visible
                try:
                    self.p_home.refresh()
                except Exception:
                    pass
                return
        except Exception as e:
            # If checking fails, stay on Home without interrupting the flow
            try:
                self.p_home.refresh()
            except Exception:
                pass
            return
        self._nav(self.GUARD)

    def _try_go_retirar(self):
        """Navigate to RetirarPage only if there is at least one active session."""
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

    # ── Navegacion ────────────────────────────────────────────────────────────

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
        """El cliente registro biometria y se le asigno un locker."""
        self.p_guard.reset()
        self._show_result(
            "ok_blue",
            tr("flow.assigned_title"),
            tr("flow.assigned_sub"),
            "LOCKER  #{}".format(num_locker)
        )

    def _on_retirado(self, face_uid, num_locker, id_sesion):
        """El cliente retiro sus cosas, sesion cerrada, locker liberado."""
        self.p_retir.reset()
        # Show result but do NOT auto-return to home (user should see result clearly)
        self.p_result.show_result(
            "ok_blue",
            tr("flow.bye_title"),
            tr("flow.bye_sub", n=num_locker),
            "LOCKER  #{}".format(num_locker),
            auto=False,
        )
        self._nav(self.RESULT)

    def _on_seguir(self, face_uid, num_locker, id_sesion):
        """El cliente sigue comprando, locker permanece activo."""
        self.p_retir.reset()
        detail = "LOCKER  #{}".format(num_locker) if num_locker else ""
        # Show result without auto-timer so the user sees the locker info
        self.p_result.show_result(
            "ok_blue",
            tr("flow.keep_title"),
            tr("flow.keep_sub"),
            detail,
            auto=False,
        )
        self._nav(self.RESULT)

    def _on_login(self, admin_data):
        """Admin autenticado correctamente."""
        self.p_admin.set_admin(admin_data)
        self._nav(self.ADMIN)

    def closeEvent(self, event):
        # Detiene hilos de captura/reconocimiento antes de cerrar Qt.
        try:
            self.p_guard.reset()
        except Exception:
            pass
        try:
            self.p_retir.reset()
        except Exception:
            pass
        super().closeEvent(event)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _fix_qt_plugin_path_for_linux()

    # Verificar que la base de datos existe
    if not os.path.exists(DB_PATH):
        print("[ERROR] No se encontro la base de datos en:")
        print("        {}".format(DB_PATH))
        print("[INFO]  Verifica la ruta en la variable DB_PATH al inicio del archivo.")
        sys.exit(1)

    # Crear admin por defecto si la tabla esta vacia
    try:
        if db_count_active_admins() == 0:
            db_register_admin(
                "Administrador", "Sistema", "Locker",
                "admin", "admin1234", rol="administrador"
            )
            print("[INFO] Admin por defecto creado.")
            print("[INFO] Usuario: admin | Contrasena: admin1234")
            print("[INFO] Cambialo desde el Panel de Administracion.")
    except Exception as e:
        print("[WARN] No se pudo verificar admins: {}".format(e))

    # Cargar modelo biometrico con imagenes existentes
    train_model()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    fullscreen_env = os.getenv("APP_FULLSCREEN", "1").strip().lower()
    fullscreen_enabled = fullscreen_env not in ("0", "false", "no", "off")
    if fullscreen_enabled:
        w.showFullScreen()
    else:
        w.show()
    exit_code = app.exec_()

    # Liberar pines GPIO al cerrar para evitar estado sucio en el próximo arranque
    try:
        from utils.gpio_locker import cleanup
        cleanup()
    except Exception as e:
        print(f"[WARN] No se pudo hacer cleanup de GPIO: {e}")

    sys.exit(exit_code)
