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

# Global PWM object to avoid "PWM object already exists" errors
_pwm = None

if GPIO:
    for pin in LOCKER_PINS.values():
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)

def _sonar(frecuencia, duracion):
    global _pwm
    if not GPIO:
        print(f"[BUZZER SIMULADO] {frecuencia}Hz por {duracion}s")
        return
    
    # Create PWM object once and reuse it, changing frequency as needed
    if _pwm is None:
        _pwm = GPIO.PWM(BUZZER_PIN, frecuencia)
    else:
        # Change frequency if PWM already exists
        _pwm.ChangeFrequency(frecuencia)
    
    _pwm.start(50)
    time.sleep(duracion)
    _pwm.stop()

def beep_start_scan():
    """Beep to signal scanning has started (short high tone)."""
    def _worker():
        _sonar(880, 0.15)
    t = threading.Thread(target=_worker, daemon=True)
    t.start()

def beep_success():
    """Beep to signal successful capture (two ascending tones)."""
    def _worker():
        _sonar(880, 0.2)
        time.sleep(0.1)
        _sonar(1200, 0.2)
    t = threading.Thread(target=_worker, daemon=True)
    t.start()

def beep_error():
    """Beep to signal error (low descending tone)."""
    def _worker():
        _sonar(440, 0.1)
        time.sleep(0.05)
        _sonar(220, 0.2)
    t = threading.Thread(target=_worker, daemon=True)
    t.start()

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