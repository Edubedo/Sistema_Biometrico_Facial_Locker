import time
import threading

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
    print("[GPIO] Modo simulado — RPi.GPIO no está disponible")
else:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

# ── Pines ──────────────────────────────────────────────────────────────────────
BUZZER_PIN = 24        # Pin físico 18 — buzzer pasivo

LOCKER_PINS = {
    "1": 17,           # Pin físico 11 — relay cerradura 1
    "2": 27,           # Pin físico 13 — relay cerradura 2
}

# Switches para detectar si el locker está abierto o cerrado
SWITCH_PINS = {
    "1": 23,           # Pin físico 16 — switch locker 1
    "2": 25,           # Pin físico 22 — switch locker 2
}

LED_PIN        = 22    # Pin físico 15 — LED indicador
PULSE_DURATION = 2.0   # Segundos que el solenoide permanece abierto
ALERTA_SEGUNDOS = 0    # Empieza a alertar de inmediato

# ── Setup inicial ──────────────────────────────────────────────────────────────
if GPIO:
    for pin in LOCKER_PINS.values():
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.output(pin, GPIO.HIGH)
    for pin in SWITCH_PINS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # pull-up interno
    GPIO.setup(LED_PIN,    GPIO.OUT, initial=GPIO.HIGH)
    GPIO.output(LED_PIN,    GPIO.HIGH)
    GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    print("[GPIO] Setup inicial completo — todos los pines en estado seguro")

# ── Lock global para el buzzer (evita colisión de PWM) ────────────────────────
_buzzer_lock = threading.Lock()

# ── Hilos de alerta activos por locker ────────────────────────────────────────
_alertas_activas = {}   # num_locker -> threading.Event (para detener alerta)
_switch_closed_level = {}  # num_locker -> GPIO level observado como cerrado


def _read_switch_level(pin, samples=3, delay=0.01):
    if not GPIO:
        return None
    counts = {GPIO.LOW: 0, GPIO.HIGH: 0}
    for _ in range(samples):
        val = GPIO.input(pin)
        counts[val] = counts.get(val, 0) + 1
        time.sleep(delay)
    return GPIO.HIGH if counts[GPIO.HIGH] >= counts[GPIO.LOW] else GPIO.LOW

def _sonar_sync(frecuencia, duracion):
    """Tono síncrono con lock para evitar colisión de PWM."""
    if not GPIO:
        time.sleep(duracion)
        return
    with _buzzer_lock:
        try:
            pwm = GPIO.PWM(BUZZER_PIN, frecuencia)
            pwm.start(50)
            time.sleep(duracion)
            pwm.stop()
        except Exception as e:
            print(f"[BUZZER] Error: {e}")

# ── Beeps ──────────────────────────────────────────────────────────────────────
def beep_start_scan():
    threading.Thread(target=lambda: _sonar_sync(880, 0.15), daemon=True).start()

def beep_success():
    def _w():
        _sonar_sync(880, 0.2)
        time.sleep(0.08)
        _sonar_sync(1200, 0.25)
    threading.Thread(target=_w, daemon=True).start()

def beep_error():
    def _w():
        _sonar_sync(440, 0.12)
        time.sleep(0.06)
        _sonar_sync(220, 0.25)
    threading.Thread(target=_w, daemon=True).start()

def _beep_alerta():
    """Alarma continua y agresiva — locker abierto."""
    for _ in range(6):
        _sonar_sync(2000, 0.2)
        time.sleep(0.05)
    time.sleep(0.3)
    for _ in range(3):
        _sonar_sync(1000, 0.4)
        time.sleep(0.1)

# ── Detección de estado del locker ────────────────────────────────────────────
def locker_esta_abierto(num_locker):
    """
    Retorna True si el switch detecta que el locker está abierto.
    Switch en NO + pull-up: LOW = cerrado, HIGH = abierto.
    """
    pin = SWITCH_PINS.get(str(num_locker))
    if pin is None or not GPIO:
        return False
    level = _read_switch_level(pin)
    if level is None:
        return False
    key = str(num_locker)
    if key not in _switch_closed_level:
        # Asumimos que el locker esta cerrado al iniciar el sistema.
        _switch_closed_level[key] = level
    return level != _switch_closed_level[key]

# ── Alerta de locker olvidado abierto ─────────────────────────────────────────
def _monitor_locker_abierto(num_locker, stop_event):
    """
    Espera ALERTA_SEGUNDOS y si el locker sigue abierto,
    suena el buzzer en loop hasta que se cierre.
    """
    print(f"[SWITCH] Monitor iniciado — locker {num_locker}")
    time.sleep(ALERTA_SEGUNDOS)

    while not stop_event.is_set():
        if not locker_esta_abierto(num_locker):
            print(f"[SWITCH] Locker {num_locker} cerrado — alerta detenida")
            break
        print(f"[SWITCH] Locker {num_locker} lleva más de {ALERTA_SEGUNDOS}s abierto — alertando")
        _beep_alerta()
        time.sleep(5)  # espera 5 segundos antes de volver a alertar

def iniciar_monitor(num_locker):
    """Inicia el monitor de locker abierto para el locker indicado."""
    # Cancelar monitor anterior si existe
    detener_monitor(num_locker)
    stop_event = threading.Event()
    _alertas_activas[str(num_locker)] = stop_event
    t = threading.Thread(
        target=_monitor_locker_abierto,
        args=(num_locker, stop_event),
        daemon=True,
        name=f"monitor-{num_locker}"
    )
    t.start()

def detener_monitor(num_locker):
    """Detiene el monitor de alerta del locker indicado."""
    ev = _alertas_activas.pop(str(num_locker), None)
    if ev:
        ev.set()

# ── Cerraduras ─────────────────────────────────────────────────────────────────
def abrir_locker(num_locker):
    """
    Abre la cerradura del locker indicado.
    - Bloquea si el switch detecta que ya está abierto.
    - Enciende LED mientras está abierto.
    - Inicia monitor de alerta si se deja abierto más de 10 segundos.
    """
    print(f"[GPIO] abrir_locker('{num_locker}')")

    pin = LOCKER_PINS.get(str(num_locker))
    if pin is None:
        raise ValueError(
            f"El locker #{num_locker} no tiene un pin GPIO asignado.\n"
            f"Agrega '\"{ num_locker }\": <pin>' en LOCKER_PINS dentro de utils/gpio_locker.py"
        )

    if locker_esta_abierto(num_locker):
        raise ValueError(
            f"El locker #{num_locker} ya está abierto físicamente.\n"
            "Ciérralo antes de intentar abrirlo desde el sistema."
        )

    if not GPIO:
        print(f"[SIMULADO] Locker {num_locker} abierto (sin hardware)")
        return

    def _worker():
        print(f"[GPIO] _worker iniciado — locker={num_locker} pin={pin}")
        try:
            with _buzzer_lock:
                pass

            # Buzzer: dos pitidos
            _sonar_sync(1000, 0.15)
            time.sleep(0.05)
            _sonar_sync(1000, 0.15)

            # Abrir cerradura + encender LED
            GPIO.output(LED_PIN, GPIO.LOW)
            GPIO.output(pin, GPIO.LOW)
            print(f"[GPIO] Relay ON — locker {num_locker} ABIERTO")

            time.sleep(PULSE_DURATION)

            GPIO.output(pin, GPIO.HIGH)
            GPIO.output(LED_PIN, GPIO.HIGH)
            print(f"[GPIO] Relay OFF — locker {num_locker} CERRADO")

            # Iniciar monitor por si el usuario deja el locker abierto
            iniciar_monitor(num_locker)

        except Exception as e:
            import traceback
            print(f"[GPIO] EXCEPCION en _worker: {e}")
            traceback.print_exc()

    t = threading.Thread(target=_worker, daemon=False, name=f"locker-{num_locker}")
    t.start()
    print(f"[GPIO] Hilo '{t.name}' lanzado — alive={t.is_alive()}")


def cleanup():
    """Liberar pines al cerrar la app."""
    for num in list(_alertas_activas.keys()):
        detener_monitor(num)
    if GPIO:
        try:
            GPIO.cleanup()
            print("[GPIO] Pines liberados.")
        except Exception as e:
            print(f"[GPIO] Error en cleanup: {e}")