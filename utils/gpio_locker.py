import RPi.GPIO as GPIO
import time

BUZZER_PIN = 24

LOCKER_PINS = {
    "1": 17,
    "2": 27,
}

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# --- CAMBIO 1: ESTADO INICIAL ---
for pin in LOCKER_PINS.values():
    # Usamos LOW para que el relay se ACTIVE al arrancar.
    # Al activarse, cierra el contacto NO y la cerradura recibe energía (SE CIERRA).
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW) 

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

    print(f"Abriendo locker {num_locker}...")
    _sonar(440, 0.3)
    
    # --- CAMBIO 2: LÓGICA DE APERTURA ---
    # Ponemos HIGH para APAGAR el relay.
    # Al apagarse, el contacto NO se abre -> se corta la luz -> LA PUERTA SE ABRE.
    GPIO.output(pin, GPIO.HIGH)  
    
    time.sleep(3) 
    
    # --- CAMBIO 3: LÓGICA DE CIERRE ---
    # Volvemos a LOW para ENCENDER el relay.
    # El contacto NO se vuelve a cerrar -> pasa luz -> LA PUERTA SE CIERRA.
    GPIO.output(pin, GPIO.LOW) 
    
    _sonar(880, 0.2)