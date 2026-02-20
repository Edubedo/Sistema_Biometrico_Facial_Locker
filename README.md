# Sistema de Lockers con Reconocimiento Facial

Este proyecto implementa un sistema de apertura y registro de lockers para tiendas comerciales utilizando reconocimiento facial con Python, OpenCV y una interfaz gráfica sencilla con Tkinter.

## Estructura del Proyecto

```
capture.py                  # Script para capturar imágenes de entrenamiento de rostros
reconocimiento.py           # Script para reconocimiento facial en consola
locker_gui.py               # Interfaz gráfica para el sistema de lockers
listaPermitidos.py          # Clase para gestionar lista de personas permitidas (opcional)
haarcascade_frontalface_default.xml  # Clasificador de rostros de OpenCV
haarcascade_frontalface_alt.xml      # Clasificador alternativo
README.md                   # Este archivo
att_faces/orl_faces/        # Carpeta de imágenes de entrenamiento (para scripts base)
lockers_faces/              # Carpeta donde se guardan los rostros de cada locker (para GUI)
```

## Requisitos

- Python 3.7+
- OpenCV (opencv-contrib-python)
- Numpy
- Tkinter (incluido en la mayoría de instalaciones de Python)

Instalación de dependencias:
```bash
pip install opencv-contrib-python numpy
```

## Scripts y Funcionalidad

### 1. capture.py
Permite capturar imágenes del rostro de una persona y guardarlas en una carpeta específica para entrenamiento.

Uso:
```bash
python capture.py nombrePersona
```
Esto creará una carpeta `att_faces/orl_faces/nombrePersona` y guardará 100 imágenes del rostro detectado.

### 2. reconocimiento.py
Realiza el reconocimiento facial usando las imágenes de entrenamiento. Muestra en pantalla el nombre de la persona reconocida y, si está en la lista de permitidos, imprime un mensaje de bienvenida.

Uso:
```bash
python reconocimiento.py
```

### 3. locker_gui.py
Interfaz gráfica con dos botones:
- **Nuevo locker**: Solicita el nombre, captura el rostro y registra un nuevo locker.
- **Abrir mi locker**: Solicita reconocimiento facial y abre el locker solo si el rostro coincide con uno registrado.

Uso:
```bash
python locker_gui.py
```

Las imágenes de cada usuario se guardan en la carpeta `lockers_faces/NombreUsuario/`.

### 4. listaPermitidos.py (opcional)
Clase para gestionar una lista de personas permitidas. Se usa en reconocimiento.py para mostrar mensajes personalizados.

## Archivos importantes
- **haarcascade_frontalface_default.xml**: Clasificador de OpenCV necesario para la detección de rostros.
- **lockers_faces/**: Carpeta donde se almacenan las imágenes de cada usuario registrado desde la GUI.
- **att_faces/orl_faces/**: Carpeta de imágenes de entrenamiento para los scripts base.

## Notas de uso
- Para registrar un nuevo locker, asegúrate de que la cámara esté conectada y funcione correctamente.
- Para abrir un locker, la persona debe acercar su rostro a la cámara y debe coincidir con el registrado.
- El sistema puede ampliarse para agregar más seguridad, logs, o integración con hardware real de apertura de lockers.

## Créditos
Desarrollado con Python, OpenCV y Tkinter.


~~~
- Puedes cambiar el metodo de reconocimiento por caulquiera de los 3 mencionados al inicio, prueba los 3 y checa cual te da mejores resultados.

<img src="https://github.com/futurelabmx/FaceRecognition2/blob/master/reconocido.png" width="600">
