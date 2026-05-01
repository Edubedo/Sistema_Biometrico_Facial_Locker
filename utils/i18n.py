LANG_ES = "es"
LANG_EN = "en"

_current_lang = LANG_ES

_TRANSLATIONS = {
    "es": {
        # ── Inicio ─────────────────────────────────────────────────────────────
        "home.lang":          "Idioma",
        "home.admin":         "ADMIN",
        "home.store":         "Guardar",
        "home.pickup":        "Recoger",
        "home.online":        "EN LÍNEA",
        "home.free_lockers":  "  {n} disponibles ",

        # ── Guardar pertenencias ────────────────────────────────────────────────
        "guard.back":           "< Volver",
        "guard.title":          "GUARDAR PERTENENCIAS",
        "guard.subtitle":       "ASIGNACIÓN AUTOMÁTICA DE LOCKER",
        "guard.how":            "CÓMO FUNCIONA",
        "guard.scan_title":     "ESCÁNER BIOMÉTRICO",
        "guard.start":          "  INICIAR ESCANEO",
        "guard.no_lockers_now": "No hay lockers disponibles en este momento.",
        "guard.no_lockers":     "Sin lockers disponibles.",
        "guard.cam_open_error": "No se pudo acceder a la cámara. Verifique que no esté en uso.",
        "guard.capture_error":  "Error al capturar imagen. Inténtelo de nuevo.",
        "guard.face_ok":        "Rostro detectado correctamente.",
        "guard.step1":          "Mire directamente a la cámara",
        "guard.step2":          "Sus datos biométricos faciales son capturados",
        "guard.step3":          "Se le asigna el siguiente locker disponible",
        "guard.step4":          "Guarde sus pertenencias y disfrute sus compras",
        "guard.step5":          "Sus imágenes se eliminan al finalizar",

        # ── Retirar / continuar ────────────────────────────────────────────────
        "ret.back":             "< Volver",
        "ret.title":            "RETIRAR / CONTINUAR",
        "ret.subtitle":         "VERIFICACIÓN BIOMÉTRICA",
        "ret.how":              "CÓMO FUNCIONA",
        "ret.scan_title":       "ESCÁNER BIOMÉTRICO",
        "ret.start":            "  INICIAR ESCANEO",
        "ret.no_biometrics":    "No hay registros biométricos activos.",
        "ret.cam_open_error":   "No se pudo acceder a la cámara. Verifique que no esté en uso.",
        "ret.not_recognized":   "No se pudo reconocer el rostro. Inténtelo de nuevo.",
        "ret.no_active_session":"No tiene una sesión activa en el sistema.",
        "ret.verified":         "Identidad verificada",
        "ret.your_locker":      "Su locker: #{n}",
        "ret.choice_prompt":    "Seleccione una opción para continuar ({n}s)",
        "ret.detect_title":     "Detección exitosa",
        "ret.detect_text":      "Rostro detectado correctamente",
        "ret.btn_take":         "RETIRAR Y SALIR",
        "ret.btn_continue":     "SEGUIR COMPRANDO",
        "ret.step1":            "Mire directamente a la cámara",
        "ret.step2":            "Sus datos biométricos faciales son verificados",
        "ret.step3":            "Se muestra el locker que tiene asignado",
        "ret.step4":            "Elija: retirar sus pertenencias o seguir comprando",
        "ret.step5":            "Sus imágenes se eliminan al finalizar",

        # ── Login ───────────────────────────────────────────────────────────────
        "login.back":       "← VOLVER",
        "login.user":       "USUARIO",
        "login.pass":       "CONTRASEÑA",
        "login.user_ph":    "Nombre de usuario",
        "login.pass_ph":    "••••••••",
        "login.enter":      "INGRESAR",
        "login.fill_fields":"Complete todos los campos.",
        "login.bad_access": "Usuario o contraseña incorrectos.",
        "login.kbd.space":  "ESPACIO",
        "login.kbd.clear":  "LIMPIAR",
        "login.kbd.shift":  "MAYÚS",

        # ── Panel de administración ─────────────────────────────────────────────
        "admin.logout":        "‹  CERRAR SESIÓN",
        "admin.panel":         "PANEL DE ADMINISTRACIÓN",
        "admin.tab.lockers":   "LOCKERS",
        "admin.tab.sessions":  "SESIONES",
        "admin.tab.log":       "REGISTRO",
        "admin.tab.admins":    "ADMINS",
        "admin.read_only":     "Solo lectura",
        "admin.manage_admins": "Gestionar administradores",

        # ── Resultados genéricos ────────────────────────────────────────────────
        "result.ok":   "ÉXITO",
        "result.warn": "ATENCIÓN",
        "result.err":  "ERROR",
        "result.home": "VOLVER AL INICIO",

        # ── Flujos de resultado ─────────────────────────────────────────────────
        "flow.assigned_title": "Locker Asignado",
        "flow.assigned_sub":   "Sus pertenencias quedarán seguras. Recuerde su número de locker.",
        "flow.bye_title":      "¡Hasta pronto!",
        "flow.bye_sub":        "El locker #{n} ha sido liberado. Recoja sus pertenencias.",
        "flow.keep_title":     "¡Que siga comprando!",
        "flow.keep_sub":       "Sus pertenencias permanecen seguras. Su locker sigue activo.",
        "flow.no_space_title": "Sin Lockers Disponibles",
        "flow.no_space_sub":   "No hay lockers libres en este momento. Inténtelo más tarde.",
    },

    "en": {
        # ── Home ────────────────────────────────────────────────────────────────
        "home.lang":          "Language",
        "home.admin":         "ADMIN",
        "home.store":         "Deposit",
        "home.pickup":        "Claim",
        "home.online":        "ONLINE",
        "home.free_lockers":  "  {n} available ",

        # ── Store items ─────────────────────────────────────────────────────────
        "guard.back":           "< Back",
        "guard.title":          "STORE YOUR ITEMS",
        "guard.subtitle":       "AUTOMATIC LOCKER ASSIGNMENT",
        "guard.how":            "HOW IT WORKS",
        "guard.scan_title":     "BIOMETRIC SCANNER",
        "guard.start":          "  START SCAN",
        "guard.no_lockers_now": "No lockers are currently available.",
        "guard.no_lockers":     "No lockers available.",
        "guard.cam_open_error": "Unable to access the camera. Make sure it is not in use.",
        "guard.capture_error":  "Image capture failed. Please try again.",
        "guard.face_ok":        "Face detected successfully.",
        "guard.step1":          "Look directly at the camera",
        "guard.step2":          "Your facial biometrics are captured",
        "guard.step3":          "The next available locker is assigned to you",
        "guard.step4":          "Store your items and enjoy your shopping",
        "guard.step5":          "Your images are permanently deleted when done",

        # ── Retrieve / continue ─────────────────────────────────────────────────
        "ret.back":             "< Back",
        "ret.title":            "CLAIM / CONTINUE",
        "ret.subtitle":         "BIOMETRIC VERIFICATION",
        "ret.how":              "HOW IT WORKS",
        "ret.scan_title":       "BIOMETRIC SCANNER",
        "ret.start":            "  START SCAN",
        "ret.no_biometrics":    "No active biometric records found.",
        "ret.cam_open_error":   "Unable to access the camera. Make sure it is not in use.",
        "ret.not_recognized":   "Face not recognized. Please try again.",
        "ret.no_active_session":"No active session found for your account.",
        "ret.verified":         "Identity verified",
        "ret.your_locker":      "Your locker: #{n}",
        "ret.choice_prompt":    "Choose an option to continue ({n}s)",
        "ret.detect_title":     "Detection successful",
        "ret.detect_text":      "Face detected successfully",
        "ret.btn_take":         "CLAIM ITEMS & EXIT",
        "ret.btn_continue":     "KEEP SHOPPING",
        "ret.step1":            "Look directly at the camera",
        "ret.step2":            "Your facial biometrics are verified",
        "ret.step3":            "Your assigned locker number is displayed",
        "ret.step4":            "Choose: claim your items or keep shopping",
        "ret.step5":            "Your images are permanently deleted when done",

        # ── Login ───────────────────────────────────────────────────────────────
        "login.back":       "← BACK",
        "login.user":       "USERNAME",
        "login.pass":       "PASSWORD",
        "login.user_ph":    "Username",
        "login.pass_ph":    "••••••••",
        "login.enter":      "SIGN IN",
        "login.fill_fields":"Please fill in all fields.",
        "login.bad_access": "Invalid username or password.",
        "login.kbd.space":  "SPACE",
        "login.kbd.clear":  "CLEAR",
        "login.kbd.shift":  "SHIFT",

        # ── Admin panel ─────────────────────────────────────────────────────────
        "admin.logout":        "‹  LOG OUT",
        "admin.panel":         "ADMIN PANEL",
        "admin.tab.lockers":   "LOCKERS",
        "admin.tab.sessions":  "SESSIONS",
        "admin.tab.log":       "LOG",
        "admin.tab.admins":    "ADMINS",
        "admin.read_only":     "Read-only",
        "admin.manage_admins": "Manage administrators",

        # ── Generic results ─────────────────────────────────────────────────────
        "result.ok":   "SUCCESS",
        "result.warn": "WARNING",
        "result.err":  "ERROR",
        "result.home": "BACK TO HOME",

        # ── Result flows ────────────────────────────────────────────────────────
        "flow.assigned_title": "Locker Assigned",
        "flow.assigned_sub":   "Your belongings are safe. Remember your locker number.",
        "flow.bye_title":      "See You Soon!",
        "flow.bye_sub":        "Locker #{n} has been released. Please collect your belongings.",
        "flow.keep_title":     "Happy Shopping!",
        "flow.keep_sub":       "Your belongings are safe. Your locker remains active.",
        "flow.no_space_title": "No Lockers Available",
        "flow.no_space_sub":   "All lockers are currently in use. Please try again later.",
    },
}


def set_language(lang: str) -> str:
    global _current_lang
    _current_lang = LANG_EN if lang == LANG_EN else LANG_ES
    return _current_lang


def get_language() -> str:
    return _current_lang


def tr(key: str, **kwargs) -> str:
    bundle = _TRANSLATIONS.get(_current_lang, _TRANSLATIONS[LANG_ES])
    template = bundle.get(key) or _TRANSLATIONS[LANG_ES].get(key) or key
    try:
        return template.format(**kwargs)
    except Exception:
        return template