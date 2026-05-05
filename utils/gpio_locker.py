import time

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
    pin = LOCKER_PINS.get(str(num_locker))
    if not pin:
        print(f"Locker {num_locker} no tiene pin asignado")
        return

    if not GPIO:
        print(f"[LOCKER SIMULADO] Abriendo locker {num_locker}...")
        time.sleep(3)
        print(f"[LOCKER SIMULADO] Cerrando locker {num_locker}")
        return

    _sonar(440, 0.3)
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(3)
    GPIO.output(pin, GPIO.LOW)
    _sonar(880, 0.2)