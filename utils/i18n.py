LANG_ES = "es"
LANG_EN = "en"

_current_lang = LANG_ES

_TRANSLATIONS = {
    "es": {
        "home.lang": "Idioma",
        "home.admin": "ADMIN",
        "home.store": "Guardar",
        "home.pickup": "Recoger",
        "home.online": "EN LINEA",
        "home.free_lockers": "  {n} lockers libres ",

        "guard.back": "< Volver",
        "guard.title": "GUARDAR PERTENENCIAS",
        "guard.subtitle": "ASIGNACION AUTOMATICA DE LOCKER",
        "guard.how": "COMO FUNCIONA",
        "guard.scan_title": "ESCANER BIOMETRICO",
        "guard.start": "  INICIAR ESCANEO",
        "guard.no_lockers_now": "No hay lockers disponibles en este momento.",
        "guard.no_lockers": "Sin lockers disponibles.",
        "guard.cam_open_error": "No se pudo abrir la camara. Verifica que no este en uso.",
        "guard.capture_error": "Error al capturar. Intenta de nuevo.",
        "guard.face_ok": "Rostro detectado correctamente.",
        "guard.step1": "Mira directo a la camara",
        "guard.step2": "Tu biometria facial es capturada",
        "guard.step3": "Se te asigna el siguiente locker libre",
        "guard.step4": "Guarda tus cosas y disfruta comprando",
        "guard.step5": "Tus imagenes se borran al terminar",

        "ret.back": "< Volver",
        "ret.title": "RETIRAR / CONTINUAR",
        "ret.subtitle": "VERIFICACION BIOMETRICA",
        "ret.how": "COMO FUNCIONA",
        "ret.scan_title": "ESCANER BIOMETRICO",
        "ret.start": "  INICIAR ESCANEO",
        "ret.no_biometrics": "No hay biometrias registradas.",
        "ret.cam_open_error": "No se pudo abrir la camara. Verifica que no este en uso.",
        "ret.not_recognized": "No se reconocio el rostro. Intenta de nuevo.",
        "ret.no_active_session": "No tienes una sesion activa.",
        "ret.verified": "Identidad verificada",
        "ret.your_locker": "Tu locker: #{n}",
        "ret.choice_prompt": "Elige una opcion para continuar ({n}s)",
        "ret.detect_title": "Deteccion exitosa",
        "ret.detect_text": "Rostro detectado correctamente",
        "ret.btn_take": "RETIRAR Y SALIR",
        "ret.btn_continue": "SEGUIR COMPRANDO",
        "ret.step1": "Mira directo a la camara",
        "ret.step2": "Tu biometria facial es verificada",
        "ret.step3": "Se te muestra el locker asignado",
        "ret.step4": "Elige: retirar tus cosas o seguir comprando",
        "ret.step5": "Tus imagenes se borran al terminar",

        "login.back": "← VOLVER",
        "login.user": "USUARIO",
        "login.pass": "CONTRASENA",
        "login.user_ph": "Nombre de usuario",
        "login.pass_ph": "••••••••",
        "login.enter": "INGRESAR",
        "login.fill_fields": "Llena todos los campos.",
        "login.bad_access": "Acceso incorrecto.",
        "login.kbd.space": "ESPACIO",
        "login.kbd.clear": "LIMPIAR",
        "login.kbd.shift": "MAYUS",

        "admin.logout": "‹  CERRAR SESION",
        "admin.panel": "PANEL DE ADMINISTRACION",
        "admin.tab.lockers": "LOCKERS",
        "admin.tab.sessions": "SESIONES",
        "admin.tab.log": "REGISTRO",
        "admin.tab.admins": "ADMINS",
        "admin.read_only": "Solo lectura",
        "admin.manage_admins": "Gestionar administradores",

        "result.ok": "EXITO",
        "result.warn": "ATENCION",
        "result.err": "ERROR",
        "result.home": "VOLVER AL INICIO",

        "flow.assigned_title": "Locker Asignado",
        "flow.assigned_sub": "Tus pertenencias quedaran seguras. Recuerda tu numero de locker.",
        "flow.bye_title": "Hasta Pronto",
        "flow.bye_sub": "El locker #{n} ha sido liberado. Recoge tus cosas.",
        "flow.keep_title": "Que sigas comprando",
        "flow.keep_sub": "Tus cosas permanecen seguras. Tu locker sigue activo.",
        "flow.no_space_title": "Sin espacio",
    },
    "en": {
        "home.lang": "Language",
        "home.admin": "ADMIN",
        "home.store": "Store",
        "home.pickup": "Retrieve",
        "home.online": "ONLINE",
        "home.free_lockers": "  {n} free lockers ",

        "guard.back": "< Back",
        "guard.title": "STORE YOUR ITEMS",
        "guard.subtitle": "AUTOMATIC LOCKER ASSIGNMENT",
        "guard.how": "HOW IT WORKS",
        "guard.scan_title": "BIOMETRIC SCANNER",
        "guard.start": "  START SCAN",
        "guard.no_lockers_now": "No lockers are available right now.",
        "guard.no_lockers": "No lockers available.",
        "guard.cam_open_error": "Could not open the camera. Verify it is not in use.",
        "guard.capture_error": "Capture failed. Please try again.",
        "guard.face_ok": "Face detected successfully.",
        "guard.step1": "Look directly at the camera",
        "guard.step2": "Your facial biometrics are captured",
        "guard.step3": "The next free locker is assigned to you",
        "guard.step4": "Store your items and enjoy shopping",
        "guard.step5": "Your images are deleted when finished",

        "ret.back": "< Back",
        "ret.title": "RETRIEVE / CONTINUE",
        "ret.subtitle": "BIOMETRIC VERIFICATION",
        "ret.how": "HOW IT WORKS",
        "ret.scan_title": "BIOMETRIC SCANNER",
        "ret.start": "  START SCAN",
        "ret.no_biometrics": "No biometrics registered.",
        "ret.cam_open_error": "Could not open the camera. Verify it is not in use.",
        "ret.not_recognized": "Face not recognized. Try again.",
        "ret.no_active_session": "You do not have an active session.",
        "ret.verified": "Identity verified",
        "ret.your_locker": "Your locker: #{n}",
        "ret.choice_prompt": "Choose an option to continue ({n}s)",
        "ret.detect_title": "Detection successful",
        "ret.detect_text": "Face detected successfully",
        "ret.btn_take": "TAKE ITEMS AND EXIT",
        "ret.btn_continue": "KEEP SHOPPING",
        "ret.step1": "Look directly at the camera",
        "ret.step2": "Your facial biometrics are verified",
        "ret.step3": "Your assigned locker is shown",
        "ret.step4": "Choose: take your items or keep shopping",
        "ret.step5": "Your images are deleted when finished",

        "login.back": "← BACK",
        "login.user": "USERNAME",
        "login.pass": "PASSWORD",
        "login.user_ph": "Username",
        "login.pass_ph": "••••••••",
        "login.enter": "SIGN IN",
        "login.fill_fields": "Fill all fields.",
        "login.bad_access": "Invalid credentials.",
        "login.kbd.space": "SPACE",
        "login.kbd.clear": "CLEAR",
        "login.kbd.shift": "SHIFT",

        "admin.logout": "‹  LOG OUT",
        "admin.panel": "ADMIN PANEL",
        "admin.tab.lockers": "LOCKERS",
        "admin.tab.sessions": "SESSIONS",
        "admin.tab.log": "LOG",
        "admin.tab.admins": "ADMINS",
        "admin.read_only": "Read-only",
        "admin.manage_admins": "Manage administrators",

        "result.ok": "SUCCESS",
        "result.warn": "WARNING",
        "result.err": "ERROR",
        "result.home": "BACK TO HOME",

        "flow.assigned_title": "Locker Assigned",
        "flow.assigned_sub": "Your belongings will remain safe. Remember your locker number.",
        "flow.bye_title": "See You Soon",
        "flow.bye_sub": "Locker #{n} has been released. Take your belongings.",
        "flow.keep_title": "Keep Shopping",
        "flow.keep_sub": "Your belongings remain safe. Your locker is still active.",
        "flow.no_space_title": "No Space",
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
