"""
gpio_locker.py
==============
Control de cerraduras solenoides via GPIO (Raspberry Pi).

- Si RPi.GPIO no está disponible (ej. desarrollo en PC), funciona en modo
  simulación imprimiendo mensajes en consola sin lanzar errores.
- Cada locker tiene un pin GPIO asignado en LOCKER_PINS.
- abrir_locker() activa el relay en un hilo separado para no bloquear la UI.

CONEXIÓN FÍSICA:
  GPIO pin  →  IN del módulo relay
  GND       →  GND del relay
  3.3V/5V   →  VCC del relay
  Fuente 12V externa → COM del relay → + solenoide
  GND 12V            →                 - solenoide

NOTA: La mayoría de módulos relay son de lógica INVERTIDA:
  GPIO.LOW  → relay ACTIVADO (solenoide abre)
  GPIO.HIGH → relay DESACTIVADO (solenoide cierra)
  Si tu módulo es lógica directa, cambia _RELAY_ACTIVO a GPIO.HIGH.
"""

import threading
import time

try:
    import RPi.GPIO as GPIO
    _GPIO_DISPONIBLE = True
except ImportError:
    _GPIO_DISPONIBLE = False
    print("[GPIO] RPi.GPIO no encontrado — modo simulación activado.")

# ── Configuración ─────────────────────────────────────────────────────────────

# Mapa numero_locker (str) → pin BCM
# Agrega o modifica los pines según tu cableado real.
LOCKER_PINS = {
    "1": 17,
    "2": 27,

}

PULSO_SEGUNDOS = 3      # Tiempo que el solenoide permanece abierto
_RELAY_ACTIVO  = True  # False = LOW activa el relay (lógica invertida, más común)
                        # True  = HIGH activa el relay (lógica directa)

# ── Setup inicial ─────────────────────────────────────────────────────────────

def _setup():
    if not _GPIO_DISPONIBLE:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    estado_inicial = GPIO.LOW if _RELAY_ACTIVO else GPIO.HIGH
    for pin in LOCKER_PINS.values():
        GPIO.setup(pin, GPIO.OUT, initial=estado_inicial)

_setup()

# ── API pública ───────────────────────────────────────────────────────────────

def abrir_locker(numero_locker: str):
    """
    Activa el solenoide del locker indicado durante PULSO_SEGUNDOS.
    Se ejecuta en un hilo separado para no bloquear la interfaz gráfica.
    """
    t = threading.Thread(
        target=_pulso_relay,
        args=(str(numero_locker),),
        daemon=True
    )
    t.start()


def cleanup():
    """
    Libera los pines GPIO. Llamar al cerrar la aplicación (opcional).
    """
    if _GPIO_DISPONIBLE:
        GPIO.cleanup()


# ── Lógica interna ────────────────────────────────────────────────────────────

def _pulso_relay(numero_locker: str):
    pin = LOCKER_PINS.get(numero_locker)

    if pin is None:
        print(f"[GPIO] Locker #{numero_locker} no tiene pin asignado en LOCKER_PINS.")
        return

    if not _GPIO_DISPONIBLE:
        print(f"[GPIO] SIMULACIÓN — Locker #{numero_locker} abierto (pin {pin}) "
              f"por {PULSO_SEGUNDOS}s.")
        time.sleep(PULSO_SEGUNDOS)
        print(f"[GPIO] SIMULACIÓN — Locker #{numero_locker} cerrado.")
        return

    nivel_on  = GPIO.LOW  if not _RELAY_ACTIVO else GPIO.HIGH
    nivel_off = GPIO.HIGH if not _RELAY_ACTIVO else GPIO.LOW

    try:
        GPIO.output(pin, nivel_on)          # Activa solenoide
        print(f"[GPIO] Locker #{numero_locker} ABIERTO (pin {pin})")
        time.sleep(PULSO_SEGUNDOS)
        GPIO.output(pin, nivel_off)         # Desactiva solenoide
        print(f"[GPIO] Locker #{numero_locker} CERRADO (pin {pin})")
    except Exception as e:
        print(f"[GPIO] Error al controlar pin {pin}: {e}")