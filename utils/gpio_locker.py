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

LED_PIN    = 22        # Pin físico 15 — LED indicador
PULSE_DURATION = 2.0   # Segundos que el solenoide permanece abierto

# ── Setup inicial ──────────────────────────────────────────────────────────────
if GPIO:
    for pin in LOCKER_PINS.values():
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.output(pin, GPIO.HIGH)
    GPIO.setup(LED_PIN,    GPIO.OUT, initial=GPIO.LOW)
    GPIO.output(LED_PIN,    GPIO.LOW)
    GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    print("[GPIO] Setup inicial completo — todos los pines en estado seguro")

# ── Lock global para el buzzer (evita colisión de PWM) ────────────────────────
_buzzer_lock = threading.Lock()

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

# ── Cerraduras ─────────────────────────────────────────────────────────────────
def abrir_locker(num_locker):
    """
    Abre la cerradura del locker indicado, suena buzzer y enciende LED 15s.
    Lógica invertida: LOW activa relay, HIGH lo desactiva.
    NO es daemon — el hilo vive hasta completarse aunque el UI cambie de página.
    """
    print(f"[GPIO] abrir_locker('{num_locker}') — tipo={type(num_locker).__name__}")

    pin = LOCKER_PINS.get(str(num_locker))
    if pin is None:
        raise ValueError(
            f"El locker #{num_locker} no tiene un pin GPIO asignado.\n"
            f"Agrega '\"{ num_locker }\": <pin>' en LOCKER_PINS dentro de utils/gpio_locker.py"
        )

    if not GPIO:
        print(f"[SIMULADO] Locker {num_locker} abierto (sin hardware)")
        return

    def _worker():
        print(f"[GPIO] _worker iniciado — locker={num_locker} pin={pin}")
        try:
            # Esperar a que cualquier beep anterior termine
            with _buzzer_lock:
                pass  # solo adquirir y soltar para esperar turno

            # Buzzer: dos pitidos
            _sonar_sync(1000, 0.15)
            time.sleep(0.05)
            _sonar_sync(1000, 0.15)

            # Abrir cerradura
            GPIO.output(pin, GPIO.LOW)
            print(f"[GPIO] Relay ON — locker {num_locker} ABIERTO")

            time.sleep(PULSE_DURATION)

            GPIO.output(pin, GPIO.HIGH)
            print(f"[GPIO] Relay OFF — locker {num_locker} CERRADO")

            # LED 15 segundos
            GPIO.output(LED_PIN, GPIO.HIGH)
            print(f"[GPIO] LED ON")
            time.sleep(15)
            GPIO.output(LED_PIN, GPIO.LOW)
            print(f"[GPIO] LED OFF")

        except Exception as e:
            import traceback
            print(f"[GPIO] EXCEPCION en _worker: {e}")
            traceback.print_exc()

    # daemon=False: el hilo vive hasta terminar aunque el UI navegue
    t = threading.Thread(target=_worker, daemon=False, name=f"locker-{num_locker}")
    t.start()
    print(f"[GPIO] Hilo '{t.name}' lanzado — alive={t.is_alive()}")


def cleanup():
    """Liberar pines al cerrar la app."""
    if GPIO:
        try:
            GPIO.cleanup()
            print("[GPIO] Pines liberados.")
        except Exception as e:
            print(f"[GPIO] Error en cleanup: {e}")