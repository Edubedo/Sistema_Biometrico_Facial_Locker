import RPi.GPIO as GPIO
import time

BUZZER_PIN = 24

# Mapa: número de locker → GPIO pin del relé
LOCKER_PINS = {
    "1": 17,
    "2": 27,  # ajusta según tus pines reales
}

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in LOCKER_PINS.values():
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)  # NC = cerrado en reposo

GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)

def _sonar(frecuencia, duracion):
    pwm = GPIO.PWM(BUZZER_PIN, frecuencia)
    pwm.start(50)
    time.sleep(duracion)
    pwm.stop()

def abrir_locker(num_locker):
    pin = LOCKER_PINS.get(str(num_locker))
    if not pin:
        print(f"Locker {num_locker} no tiene pin asignado")
        return
    _sonar(440, 0.3)
    GPIO.output(pin, GPIO.LOW)   # Activa relé → abre cerradura
    time.sleep(3)                # Abierta 3 segundos
    GPIO.output(pin, GPIO.HIGH)  # Desactiva relé → cierra
    _sonar(880, 0.2)