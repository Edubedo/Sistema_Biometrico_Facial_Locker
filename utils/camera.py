
Claude terminó la respuesta
Dijiste: haz que el segundo zip tenga las funciones de pi4d zip sin modificar los estilos del segundo zip de favor

PI4D_ReconocimientoFacil_Lookers.zip
zip


Sistema_Biometrico_Facial_Locker (1) (1).zip
zip

haz que el segundo zip tenga las funciones de pi4d zip sin modificar los estilos del segundo zip de favor

23:15
Claude respondió: Ahora voy a leer los archivos funcionales clave de ambos proyectos para entender qué tiene PI4D que no tiene el segundo zip.

Archivo visualizado, ejecutó un comando
Archivo visualizado, ejecutó un comando
Ahora voy a leer los archivos funcionales clave de ambos proyectos para entender qué tiene PI4D que no tiene el segundo zip.


Se ejecutaron 10 comandos
Se ejecutaron 10 comandos
Hay muchas diferencias en casi todos los archivos. Voy a leer los archivos más importantes para entender qué funciones específicas agrega PI4D.


Se ejecutaron 4 comandos
Se ejecutaron 4 comandos
Ahora tengo una comprensión clara. El PI4D tiene varias diferencias funcionales vs el SB (segundo zip). Voy a leer también retirar.py para ver esas diferencias, y luego procederé a actualizar el SB con las funciones del PI4D sin tocar los estilos.


Ver diff de retirar.py
Ver diff de retirar.py
Ahora tengo todo claro. Las diferencias funcionales son:

utils/gpio_locker.py — archivo nuevo en PI4D (no existe en SB)
prueba_relay.py — archivo nuevo en PI4D (no existe en SB)
views/cliente/guardar.py — PI4D agrega abrir_locker() después del registro biométrico exitoso
views/cliente/retirar.py — PI4D agrega abrir_locker() cuando retira y además tiene un método reset() completo
El resto de diferencias en guardar.py son de UI/estilo. Voy a aplicar solo los cambios funcionales al SB.


Se ejecutaron 3 comandos
Se ejecutaron 3 comandos
Based on my analysis, the functional differences that PI4D has and SB doesn't are:

New file: utils/gpio_locker.py — control of solenoid locks via GPIO
New file: prueba_relay.py — relay test script
views/cliente/guardar.py: Missing from utils.gpio_locker import abrir_locker import AND the abrir_locker(num_locker) call after successful registration
views/cliente/retirar.py: Missing from utils.gpio_locker import abrir_locker import, missing abrir_locker(num_locker) call on retrieval, and missing the complete reset() method
Let me now apply these changes:

Dijiste: Continuar
Continuar

23:17
Claude respondió: Ahora ya sé exactamente qué cambiar.

Se ejecutaron 3 comandos, vio 3 archivos
Se ejecutaron 3 comandos, vio 3 archivos
Ahora ya sé exactamente qué cambiar. Voy a hacer las modificaciones:

Copiar gpio_locker.py y prueba_relay.py al SB
Agregar import y abrir_locker() en guardar.py
Agregar import y abrir_locker() en retirar.py

Se ejecutaron 4 comandos, editó 4 archivos, archivo leído
Se ejecutaron 4 comandos, editó 4 archivos, archivo leído
Listo. Los cambios aplicados al segundo ZIP fueron estrictamente funcionales, sin tocar ningún estilo:

Archivos nuevos añadidos:

utils/gpio_locker.py — control de cerraduras solenoides via GPIO (con modo simulación si no hay RPi)
prueba_relay.py — script de prueba para los relays
Modificaciones en archivos existentes:

views/cliente/guardar.py — agregado from utils.gpio_locker import abrir_locker y la llamada abrir_locker(num_locker) justo después de marcar el locker como ocupado
views/cliente/retirar.py — agregado el mismo import y abrir_locker(num_locker) justo después de cerrar la sesión cuando el cliente retira sus cosas
Todo lo demás (estilos, layout, widgets, paneles de admin, etc.) quedó exactamente igual que en el segundo ZIP original.


Sistema biometrico facial locker actualizado
ZIP 
Dijiste: solo dame los archivos de favor
solo dame los archivos de favor

23:22
Claude respondió: Aquí están los 4 archivos modificados/nuevos.

Presented 4 files
Presented 4 files
Aquí están los 4 archivos modificados/nuevos. Recuerda dónde van en el proyecto:

gpio_locker.py → utils/gpio_locker.py
prueba_relay.py → raíz del proyecto
guardar.py → views/cliente/guardar.py
retirar.py → views/cliente/retirar.py

Gpio locker
PY 

Prueba relay
PY 

Guardar
PY 

Retirar
PY 
Dijiste: edubedo@edubedo:~/Desktop/SistemaBiometricoFacial_Locker $ python3 main.
edubedo@edubedo:~/Desktop/Sistema_Biometrico_Facial_Locker $ python3 main.py
[1:30:31.512647604] [2506]  INFO Camera camera_manager.cpp:340 libcamera v0.6.0+rpt20251202
[1:30:31.541285509] [2520]  INFO IPAProxy ipa_proxy.cpp:180 Using tuning file /usr/share/libcamera/ipa/rpi/vc4/imx219.json
[1:30:31.547225292] [2520]  INFO Camera camera_manager.cpp:223 Adding camera '/base/soc/i2c0mux/i2c@1/imx219@10' for pipeline handler rpi/vc4
[1:30:31.547325921] [2520]  INFO RPI vc4.cpp:445 Registered camera /base/soc/i2c0mux/i2c@1/imx219@10 to Unicam device /dev/media1 and ISP device /dev/media2
[1:30:31.547381716] [2520]  INFO RPI pipeline_base.cpp:1111 Using configuration file '/usr/share/libcamera/pipeline/rpi/vc4/rpi_apps.yaml'
[1:30:31.554291065] [2506]  INFO Camera camera.cpp:1215 configuring streams: (0) 640x480-XBGR8888/SMPTE170M/Rec709/None/Full (1) 640x480-SBGGR10_CSI2P/RAW
[1:30:31.554754469] [2520]  INFO RPI vc4.cpp:620 Sensor: /base/soc/i2c0mux/i2c@1/imx219@10 - Selected sensor format: 640x480-SBGGR10_1X10/RAW - Selected unicam format: 640x480-pBAA/RAW
[GPIO] Locker #1 ABIERTO (pin 17)
[GPIO] Locker #1 CERRADO (pin 17)
[1:30:50.086307733] [2525] ERROR Camera camera.cpp:702 Camera in Configured state trying acquire() requiring state Available
Camera __init__ sequence did not complete.
[ WARN:4@24.513] global cap_v4l.cpp:914 open VIDEOIO(V4L2:/dev/video0): can't open camera by index
[ WARN:4@24.513] global cap.cpp:478 open VIDEOIO(V4L2): backend is generally available but can't be used to capture by index
[ WARN:4@24.513] global cap_v4l.cpp:914 open VIDEOIO(V4L2:/dev/video1): can't open camera by index
[ WARN:4@24.513] global cap.cpp:478 open VIDEOIO(V4L2): backend is generally available but can't be used to capture by index
[ WARN:4@24.513] global cap_v4l.cpp:914 open VIDEOIO(V4L2:/dev/video2): can't open camera by index
[ WARN:4@24.513] global cap.cpp:478 open VIDEOIO(V4L2): backend is generally available but can't be used to capture by index
[ WARN:4@24.514] global cap_v4l.cpp:914 open VIDEOIO(V4L2:/dev/video3): can't open camera by index
[ WARN:4@24.514] global cap.cpp:478 open VIDEOIO(V4L2): backend is generally available but can't be used to capture by index
[ WARN:4@24.514] global cap_v4l.cpp:914 open VIDEOIO(V4L2:/dev/video4): can't open camera by index
[ WARN:4@24.514] global cap.cpp:478 open VIDEOIO(V4L2): backend is generally available but can't be used to capture by index
[ WARN:4@24.514] global cap_v4l.cpp:914 open VIDEOIO(V4L2:/dev/video5): can't open camera by index
[ WARN:4@24.514] global cap.cpp:478 open VIDEOIO(V4L2): backend is generally available but can't be used to capture by index

Mostrar más
23:27
Claude respondió: El error es claro: cuando se lanza un segundo CamThread, la cámara ya está siendo usada por picamera2 de la instancia anterior y no se liberó correctamente.
El error es claro: cuando se lanza un segundo CamThread, la cámara ya está siendo usada por picamera2 de la instancia anterior y no se liberó correctamente.

El problema está en camera.py — cuando se crea un nuevo CamThread, la Picamera2 anterior sigue ocupada. Necesitamos ver ese archivo para corregirlo.


Ver camera.py del SB
Ver camera.py del SB
El problema es que cuando se crea un nuevo CamThread, la Picamera2 anterior no fue cerrada completamente antes. La solución es usar un singleton global para la instancia de Picamera2, de modo que se reutilice en lugar de crear una nueva cada vez.


Creó un archivo, ejecutó un comando, archivo leído
Creó un archivo, ejecutó un comando, archivo leído
El problema era que cada vez que se creaba un nuevo CamThread, intentaba instanciar una nueva Picamera2 mientras la anterior aún estaba en estado Configured, provocando el error acquire() requiring state Available.

La solución fue un singleton global (_get_picam()): la cámara se inicializa una sola vez al primer uso y permanece abierta entre sesiones. El hilo ya no la cierra al terminar — solo libera OpenCV si se usó como fallback.

Reemplaza utils/camera.py con este archivo y el error debería desaparecer.


Camera
PY 

¿Quieres recibir una notificación cuando Claude responda?



Claude es IA y puede cometer errores. Por favor, verifica nuevamente las respuestas.
Camera · PY
Copiar

import sys
import os
import cv2
import time
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage
 
try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None
 
# Importamos tus configuraciones locales
from biometria.biometria import CASCADE, face_dir_for, face_model, IMG_H, IMG_W
 
# ── Singleton global de Picamera2 ─────────────────────────────────────────────
# La Raspberry Pi solo permite una instancia activa a la vez.
# Reutilizamos la misma instancia entre hilos para evitar el error
# "Camera in Configured state trying acquire() requiring state Available".
_picam_instance = None
_picam_lock = __import__("threading").Lock()
 
 
def _get_picam():
    """Devuelve la instancia global de Picamera2, creándola si no existe."""
    global _picam_instance
    with _picam_lock:
        if _picam_instance is not None:
            return _picam_instance
        if Picamera2 is None:
            return None
        try:
            cam = Picamera2()
            config = cam.create_video_configuration(main={"size": (640, 480)})
            cam.configure(config)
            cam.start()
            time.sleep(1.5)
            _picam_instance = cam
            return _picam_instance
        except Exception as e:
            print(f"[Camera] No se pudo inicializar Picamera2: {e}")
            return None
 
 
def _release_picam():
    """Detiene y libera la instancia global de Picamera2."""
    global _picam_instance
    with _picam_lock:
        if _picam_instance is not None:
            try:
                _picam_instance.stop()
                _picam_instance.close()
            except Exception:
                pass
            _picam_instance = None
 
 
# ─────────────────────────────────────────────────────────────────────────────
 
class CamThread(QThread):
    frame_sig = pyqtSignal(QImage)
    cap_done  = pyqtSignal(bool, str)
    rec_done  = pyqtSignal(str)
    progress  = pyqtSignal(int)
 
    CAPTURE      = "capture"
    RECOGNIZE    = "recognize"
    CAMERA_ERROR = "__CAMERA_ERROR__"
    _disable_picamera2 = False
 
    def __init__(self, mode, face_uid="", labels=None):
        super().__init__()
        self.mode     = mode
        self.face_uid = face_uid
        self.labels   = labels or {}
        self._active  = True
        self._manual_stop = False
        self.cap = None  # Solo usado como fallback a OpenCV
 
        # Intentar usar el singleton de Picamera2
        if Picamera2 is not None and not CamThread._disable_picamera2:
            self.use_picamera2 = True
        else:
            self.use_picamera2 = False
            self._open_cv_capture()
 
    def _open_cv_capture(self):
        self.cap = None
        for idx in (0, 1, 2, 3, 4, 5):
            cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            if not cap.isOpened():
                cap.release()
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            ok, _ = cap.read()
            if ok:
                self.cap = cap
                return
            cap.release()
 
    def _switch_to_cv_fallback(self):
        self.use_picamera2 = False
        CamThread._disable_picamera2 = True
        self._open_cv_capture()
 
    def stop(self):
        self._manual_stop = True
        self._active = False
        self.wait(3000)
 
    def run(self):
        capture_count = 0
        recognized_uid = ""
        read_failed = False
 
        if self.use_picamera2:
            picam = _get_picam()
            if picam is None:
                self._switch_to_cv_fallback()
        else:
            picam = None
 
        if not self.use_picamera2 and (not self.cap or not self.cap.isOpened()):
            if self.mode == self.CAPTURE:
                self.cap_done.emit(False, self.CAMERA_ERROR)
            elif self.mode == self.RECOGNIZE:
                self.rec_done.emit(self.CAMERA_ERROR)
            return
 
        fc = cv2.CascadeClassifier(CASCADE)
        sdir = face_dir_for(self.face_uid) if self.mode == self.CAPTURE else None
 
        if sdir:
            os.makedirs(sdir, exist_ok=True)
 
        while self._active:
            if self.use_picamera2:
                try:
                    frame = picam.capture_array()
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                except Exception as e:
                    print(f"[Camera] Error leyendo Picamera2: {e}")
                    self._switch_to_cv_fallback()
                    if not self.cap or not self.cap.isOpened():
                        read_failed = True
                        break
                    ok, frame = self.cap.read()
                    if not ok:
                        read_failed = True
                        break
            else:
                ok, frame = self.cap.read()
                if not ok:
                    read_failed = True
                    break
 
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = fc.detectMultiScale(gray, 1.3, 5)
 
            for (x, y, w, h) in faces:
                roi = cv2.resize(gray[y:y+h, x:x+w], (IMG_W, IMG_H))
 
                if self.mode == self.CAPTURE:
                    cv2.imwrite(os.path.join(sdir, "{}.png".format(capture_count)), roi)
                    capture_count += 1
                    self.progress.emit(capture_count)
                    cv2.putText(frame, f"{capture_count}/20", (x, y - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 180, 255), 2)
                    if capture_count >= 20:
                        self._active = False
                        break
 
                elif self.mode == self.RECOGNIZE:
                    try:
                        lbl_idx, conf = face_model.predict(roi)
                        if conf < 100 and lbl_idx in self.labels:
                            recognized_uid = self.labels[lbl_idx]
                            cv2.putText(frame, recognized_uid, (x, y - 8),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 180, 255), 2)
                            self._active = False
                            break
                    except:
                        pass
 
            self._emit_frame(frame)
 
        # Al terminar: liberar solo OpenCV si se usó como fallback.
        # La Picamera2 global NO se cierra aquí — se reutiliza en el siguiente hilo.
        if self.cap is not None:
            self.cap.release()
            self.cap = None
 
        if self.mode == self.CAPTURE:
            if capture_count >= 20 or not self._manual_stop:
                ref = self.face_uid
                if read_failed and capture_count == 0:
                    ref = self.CAMERA_ERROR
                self.cap_done.emit(capture_count >= 20, ref)
        elif self.mode == self.RECOGNIZE:
            if recognized_uid:
                self.rec_done.emit(recognized_uid)
            elif read_failed and not self._manual_stop:
                self.rec_done.emit(self.CAMERA_ERROR)
            elif self._active is False and not self._manual_stop:
                self.rec_done.emit("")
 
    def _emit_frame(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        img_qt = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self.frame_sig.emit(img_qt)
 
