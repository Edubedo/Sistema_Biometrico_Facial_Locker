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

BUZZER_PIN = 24
LOCKER_PINS = {
    "1": 17,
    "2": 27,
}

if GPIO:
    for pin in LOCKER_PINS.values():
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)

def _sonar(frecuencia, duracion):
    if not GPIO:
        print(f"[BUZZER SIMULADO] {frecuencia}Hz por {duracion}s")
        return
    pwm = GPIO.PWM(BUZZER_PIN, frecuencia)
    pwm.start(50)
    time.sleep(duracion)
    pwm.stop()

def abrir_locker(num_locker):
    """Open the locker without blocking the caller: perform GPIO sequence in a background thread.

    This avoids freezing the UI while the solenoid is energized for a few seconds.
    """
    pin = LOCKER_PINS.get(str(num_locker))
    if not pin:
        print(f"Locker {num_locker} no tiene pin asignado")
        return

    def _worker(p):
        if not GPIO:
            print(f"[LOCKER SIMULADO] Abriendo locker {num_locker}...")
            time.sleep(3)
            print(f"[LOCKER SIMULADO] Cerrando locker {num_locker}")
            return

        _sonar(440, 0.3)
        GPIO.output(p, GPIO.HIGH)
        time.sleep(3)
        GPIO.output(p, GPIO.LOW)
        _sonar(880, 0.2)

    t = threading.Thread(target=_worker, args=(pin,), daemon=True)
    t.start()