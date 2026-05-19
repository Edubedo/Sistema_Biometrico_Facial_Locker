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

# ── Pines ─────────────────────────────────────────────────────────────────────
BUZZER_PIN = 24        # Pin físico 18 — buzzer pasivo

LOCKER_PINS = {
    "1": 17,           # Pin físico 11 — relay cerradura 1
    "2": 27,           # Pin físico 13 — relay cerradura 2
}

LED_PIN = 22           # Pin físico 15 — LED indicador (paralelo al solenoide, opcional por código)

PULSE_DURATION = 0.5   # Segundos que el solenoide permanece abierto

# ── Setup inicial ─────────────────────────────────────────────────────────────
if GPIO:
    for pin in LOCKER_PINS.values():
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.output(pin, GPIO.HIGH)   # Forzar relay desactivado (cerradura cerrada)
    GPIO.setup(LED_PIN,    GPIO.OUT, initial=GPIO.LOW)
    GPIO.output(LED_PIN, GPIO.LOW)    # Forzar LED apagado al inicio
    GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.output(BUZZER_PIN, GPIO.LOW) # Forzar buzzer apagado al inicio


# ── Buzzer pasivo — funciones internas síncronas ──────────────────────────────
# Todas crean su propio objeto PWM y lo destruyen al terminar.
# NUNCA se llaman desde hilos distintos al mismo tiempo.

def _sonar_sync(frecuencia, duracion):
    """Tono síncrono: bloquea el hilo actual durante 'duracion' segundos."""
    if not GPIO:
        print(f"[BUZZER SIMULADO] {frecuencia}Hz por {duracion}s")
        time.sleep(duracion)
        return
    pwm = GPIO.PWM(BUZZER_PIN, frecuencia)
    pwm.start(50)
    time.sleep(duracion)
    pwm.stop()


# ── Beeps para el reconocimiento facial (hilos propios, no colisionan) ────────

def beep_start_scan():
    """Un tono corto al iniciar el escaneo facial."""
    def _w():
        _sonar_sync(880, 0.15)
    threading.Thread(target=_w, daemon=True).start()


def beep_success():
    """Dos tonos ascendentes al reconocer cara exitosamente."""
    def _w():
        _sonar_sync(880, 0.2)
        time.sleep(0.08)
        _sonar_sync(1200, 0.25)
    threading.Thread(target=_w, daemon=True).start()


def beep_error():
    """Tono descendente al fallar el reconocimiento."""
    def _w():
        _sonar_sync(440, 0.12)
        time.sleep(0.06)
        _sonar_sync(220, 0.25)
    threading.Thread(target=_w, daemon=True).start()


# ── Cerraduras ────────────────────────────────────────────────────────────────

def abrir_locker(num_locker):
    """
    Abre la cerradura, suena el buzzer y enciende el LED (si está conectado
    por GPIO). Todo en un único hilo para evitar conflictos de PWM.

    Lógica invertida: LOW activa el relay, HIGH lo desactiva.
    """
    pin = LOCKER_PINS.get(str(num_locker))
    if pin is None:
        print(f"[GPIO] Locker '{num_locker}' no tiene pin asignado.")
        return

    def _worker():
        if not GPIO:
            print(f"[SIMULADO] Locker {num_locker}: buzzer → abriendo → cerrando")
            time.sleep(PULSE_DURATION)
            return

        # 1. Buzzer — dos pitidos
        _sonar_sync(1000, 0.1)
        time.sleep(0.05)
        _sonar_sync(1000, 0.1)

        # 2. Relay activo → cerradura abierta
        GPIO.output(pin, GPIO.LOW)
        print(f"[GPIO] Locker {num_locker} ABIERTO (pin {pin})")

        time.sleep(PULSE_DURATION)

        # 3. Relay desactivado → cerradura cerrada
        GPIO.output(pin, GPIO.HIGH)
        print(f"[GPIO] Locker {num_locker} CERRADO (pin {pin})")

        # 4. LED encendido 15 segundos, independiente del relay
        GPIO.output(LED_PIN, GPIO.HIGH)
        print(f"[GPIO] LED encendido por 15 segundos")
        time.sleep(15)
        GPIO.output(LED_PIN, GPIO.LOW)
        print(f"[GPIO] LED apagado")

    threading.Thread(target=_worker, daemon=True).start()


def cleanup():
    """Libera todos los pines GPIO. Llamar al cerrar la aplicación."""
    if GPIO:
        try:
            GPIO.cleanup()
            print("[GPIO] Pines liberados correctamente.")
        except Exception as e:
            print(f"[GPIO] Error en cleanup: {e}")