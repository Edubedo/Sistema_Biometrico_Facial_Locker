# 🔒 Sistema de Lockers con Reconocimiento Facial

Sistema inteligente de gestión de lockers para supermercados y tiendas comerciales que utiliza **reconocimiento facial biométrico** para autenticación de usuarios. Implementado con Python, OpenCV, PyQt5 y SQLite.

## 📋 Características Principales

- ✅ **Autenticación biométrica** mediante reconocimiento facial (algoritmo LBPH)
- ✅ **Interfaz gráfica moderna** desarrollada con PyQt5
- ✅ **Gestión automática de lockers** (asignación, liberación, estado)
- ✅ **Panel de administración** completo con control de usuarios, lockers y sesiones
- ✅ **Sistema de auditoría** con registro detallado de todos los intentos de acceso
- ✅ **Base de datos SQLite** con integridad referencial
- ✅ **Flujo de usuario intuitivo** para guardar y retirar pertenencias

## 🏗️ Arquitectura del Proyecto

```
Sistema_Biometrico_Facial_Locker/
│
├── main.py                      # Aplicación principal (punto de entrada)
├── .env                         # Configuración de base de datos
├── LICENSE                      # Licencia del proyecto
├── README.md                    # Este archivo
│
├── biometria/                   # Módulo de reconocimiento facial
│   ├── biometria.py            # LBPH recognizer, entrenamiento y predicción
│   ├── haarcascade/            # Clasificadores Haar Cascade de OpenCV
│   │   ├── haarcascade_frontalface_default.xml
│   │   └── haarcascade_frontalface_alt.xml
│   └── locker_faces/           # Datos biométricos por sesión
│       └── sesion_<ID>/        # Imágenes de entrenamiento por usuario
│
├── db/                          # Capa de datos
│   ├── connection.py           # Conexión a SQLite
│   └── models/                 # Modelos de datos (ORM simplificado)
│       ├── usuarios.py         # CRUD de administradores
│       ├── lockers.py          # CRUD de lockers
│       ├── sesiones.py         # CRUD de sesiones activas
│       └── intentos_acceso.py  # Log de auditoría
│
├── views/                       # Interfaz gráfica (PyQt5)
│   ├── cliente/                # Vistas del flujo de cliente
│   │   ├── home.py            # Página principal
│   │   ├── guardar.py         # Registro biométrico y asignación
│   │   ├── retirar.py         # Reconocimiento y retiro
│   │   └── resultado.py       # Pantalla de confirmación
│   ├── admin/                  # Panel de administración
│   │   ├── loginPage.py       # Autenticación de administrador
│   │   ├── adminPage.py       # Vista principal del panel
│   │   ├── lockersPanel.py    # Gestión de lockers
│   │   ├── sesionesPanel.py   # Monitoreo de sesiones activas
│   │   ├── usuariosPanel.py   # Gestión de usuarios admin
│   │   └── logPanel.py        # Registro de auditoría
│   └── style/                  # Componentes de diseño
│       ├── style.py           # Estilos globales
│       ├── adminDialogs.py    # Diálogos del panel admin
│       └── widgets/
│           └── widgets.py     # Widgets reutilizables
│
└── utils/                       # Utilidades
    ├── camera.py               # Gestión de cámara y captura
    └── helpers.py              # Funciones auxiliares (hash, validación)
```

## 🔧 Requisitos del Sistema

### Software
- **Python 3.7+** (recomendado Python 3.8 o superior)
- **Cámara web** funcional
- **Sistema operativo**: Windows, Linux o macOS

### Dependencias Python
```
opencv-contrib-python >= 4.5.0
numpy >= 1.19.0
PyQt5 >= 5.15.0
python-dotenv >= 0.19.0
```

## 📥 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/Sistema_Biometrico_Facial_Locker.git
cd Sistema_Biometrico_Facial_Locker
```

### 2. Instalar dependencias
```bash
pip install opencv-contrib-python numpy PyQt5 python-dotenv
```

### 3. Configurar la base de datos

Crear un archivo `.env` en la raíz del proyecto:
```env
DB_PATH=C:/ruta/a/tu/base_de_datos/lockers.db
```

**Nota**: La base de datos SQLite debe existir previamente con el esquema correcto.

### 4. Ejecutar el sistema
```bash
python main.py
```

## 🚀 Uso del Sistema

### 👤 Flujo de Cliente

#### 1️⃣ **Guardar pertenencias**
1. Desde la pantalla principal, seleccionar **"Guardar mis cosas"**
2. Seguir las instrucciones en pantalla para el registro facial
3. El sistema captura múltiples imágenes del rostro
4. Se asigna automáticamente un locker disponible
5. **Importante**: Recordar el número de locker asignado

#### 2️⃣ **Retirar pertenencias**
1. Desde la pantalla principal, seleccionar **"Retirar mis cosas"**
2. Posicionarse frente a la cámara para reconocimiento facial
3. El sistema identifica al usuario y recupera su locker
4. Opciones:
   - **Retirar y cerrar**: Libera el locker
   - **Seguir comprando**: Mantiene el locker activo

### 🛡️ Panel de Administración

#### Acceso
- Desde la pantalla principal, clic en **"Admin"**
- Credenciales por defecto:
  - **Usuario**: `admin`
  - **Contraseña**: `admin1234`
  - ⚠️ **Cambiar inmediatamente después del primer acceso**

#### Funcionalidades

**📦 Gestión de Lockers**
- Ver estado de todos los lockers (libre/ocupado/mantenimiento)
- Agregar, editar o eliminar lockers
- Liberar lockers manualmente
- Configurar zona y tamaño

**👥 Gestión de Usuarios**
- Crear administradores y empleados
- Asignar roles (administrador/empleado)
- Dar de baja usuarios
- Gestionar permisos

**🔄 Sesiones Activas**
- Monitorear sesiones en curso
- Ver historial de entrada/salida
- Cerrar sesiones administrativamente

**📊 Auditoría**
- Registro completo de intentos de acceso
- Filtrado por tipo (registro, retiro, admin)
- Análisis de seguridad

## 🧬 Reconocimiento Facial

### Algoritmo: **LBPH (Local Binary Patterns Histograms)**

El sistema utiliza el reconocedor **LBPH** de OpenCV por las siguientes ventajas:

✅ **Robusto ante cambios de iluminación**  
✅ **Bajo costo computacional** (ideal para aplicaciones en tiempo real)  
✅ **No requiere GPU** (funciona en hardware modesto)  
✅ **Tolerante a variaciones faciales menores**

### Alternativas de Reconocimiento

OpenCV ofrece otros algoritmos que pueden ser probados modificando `biometria/biometria.py`:

```python
# LBPH (actual)
face_model = cv2.face.LBPHFaceRecognizer_create()

# Eigenfaces
face_model = cv2.face.EigenFaceRecognizer_create()

# Fisherfaces
face_model = cv2.face.FisherFaceRecognizer_create()
```

**Recomendación**: LBPH ofrece el mejor equilibrio entre precisión y rendimiento para este caso de uso.

## 💾 Estructura de la Base de Datos

### Tablas Principales

#### 🔐 **Usuarios**
Almacena administradores y empleados del sistema.
```sql
- ID_admin (PK)
- t_nombre, t_apellido_paterno, t_apellido_materno
- t_usuario (único)
- t_contrasena_hash (SHA-256)
- t_rol (administrador|empleado)
- t_estado (activo|inactivo)
- d_fecha_registro, d_fecha_modificacion
```

#### 📦 **Lockers**
Gestión de casilleros físicos.
```sql
- ID_locker (PK)
- t_numero_locker (identificador visible)
- t_zona (ubicación física)
- t_tamano (pequeño|mediano|grande)
- t_estado (libre|ocupado|mantenimiento)
- d_fecha_registro, d_fecha_modificacion
```

#### 🔄 **Sesiones**
Sesiones activas de uso de lockers.
```sql
- ID_sesion (PK)
- ID_locker (FK → Lockers)
- b_vector_biometrico_temp (referencia a carpeta de imágenes)
- d_fecha_hora_entrada
- d_fecha_hora_salida
- t_estado (activo|cerrado)
```

#### 📊 **Intentos_acceso**
Auditoría completa de eventos.
```sql
- ID_intento_acceso (PK)
- ID_locker (FK → Lockers)
- ID_sesion (FK → Sesiones)
- ID_usuario (FK → Usuarios)
- t_tipo_intento (registro_biometrico|retirar|seguir_comprando|...)
- d_fecha_hora_acceso
- t_resultado_acceso (exitoso|fallido|cancelado)
- t_descripcion_acceso
```

## ⚙️ Configuración Avanzada

### Parámetros del Reconocimiento Facial

Editar en `biometria/biometria.py`:

```python
IMG_W, IMG_H = 112, 92  # Resolución de imágenes de entrenamiento
```

### Umbral de Confianza

El sistema acepta reconocimientos con confianza menor a 100. Para ajustar:

```python
# En el método de predicción
label, confidence = face_model.predict(face_image)
if confidence < THRESHOLD:  # Ajustar THRESHOLD
    return face_labels[label]
```

### Captura de Imágenes

Número de capturas por registro (en `views/cliente/guardar.py` y `utils/camera.py`):

```python
CAPTURE_COUNT = 150  # Más imágenes = mejor precisión, pero más lento
```

## 🔒 Seguridad

- ✅ Contraseñas hasheadas con SHA-256
- ✅ Baja lógica de usuarios (no eliminación física)
- ✅ Auditoría completa de accesos
- ✅ Validación de integridad referencial en base de datos
- ⚠️ **Recomendación**: En producción, usar HTTPS y cifrado de base de datos

## 🐛 Solución de Problemas

### Error: "No se encontró la base de datos"
- Verificar que la ruta en `.env` sea correcta y absoluta
- Asegurarse de que el archivo `lockers.db` exista

### Error: "No se detecta la cámara"
- Verificar permisos de acceso a la cámara
- Probar con `camera_index = 1` en lugar de `0` en `utils/camera.py`

### Reconocimiento facial falla
- Asegurar buena iluminación durante captura y reconocimiento
- Capturar más imágenes de entrenamiento (aumentar CAPTURE_COUNT)
- Verificar que la cámara tenga resolución mínima de 640x480

### Interfaz se ve pixelada
- El sistema ajusta DPI automáticamente
- En Windows, verificar configuración de escala de pantalla (100% recomendado)

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrir un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

## 📧 Contacto

Para preguntas, sugerencias o reporte de bugs, por favor abrir un issue en GitHub.

---

**Desarrollado con**: Python 🐍 | OpenCV 👁️ | PyQt5 🖥️ | SQLite 💾
