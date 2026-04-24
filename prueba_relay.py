# prueba_relay.py
# Ejecutar desde la carpeta raíz del proyecto:
#   python3 prueba_relay.py
from utils.gpio_locker import abrir_locker
import time

print("=== Prueba de cerraduras solenoides ===")

print("\nProbando Locker #1 (GPIO 17 / Pin 11)...")
abrir_locker("1")
time.sleep(5)
print("Locker #1 debería estar cerrado ya.")

print("\nProbando Locker #2 (GPIO 27 / Pin 13)...")
abrir_locker("2")
time.sleep(5)
print("Locker #2 debería estar cerrado ya.")

print("\n=== Prueba terminada ===")