import tkinter as tk
from tkinter import messagebox
import cv2
import numpy as np
import os

# Ruta donde se guardarán los datos de los lockers
LOCKERS_DIR = 'lockers_faces'
if not os.path.exists(LOCKERS_DIR):
    os.makedirs(LOCKERS_DIR)

# Parámetros de la imagen
IMG_WIDTH, IMG_HEIGHT = 112, 92

# Inicializar el reconocedor de caras
model = cv2.face.LBPHFaceRecognizer_create()

# Cargar datos de entrenamiento si existen
locker_owners = {}
def train_model():
    images, labels, names, idx = [], [], {}, 0
    for subdir in os.listdir(LOCKERS_DIR):
        subpath = os.path.join(LOCKERS_DIR, subdir)
        if os.path.isdir(subpath):
            names[idx] = subdir
            for fname in os.listdir(subpath):
                img_path = os.path.join(subpath, fname)
                img = cv2.imread(img_path, 0)
                if img is not None:
                    img_resized = cv2.resize(img, (IMG_WIDTH, IMG_HEIGHT))
                    images.append(img_resized)
                    labels.append(idx)
            idx += 1
    if len(images) > 1:
        model.train(np.array(images), np.array(labels))
    return names

def capture_face(person_name):
    save_dir = os.path.join(LOCKERS_DIR, person_name)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    cap = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    count = 0
    while count < 20:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face, (IMG_WIDTH, IMG_HEIGHT))
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.imwrite(f'{save_dir}/{count}.png', face_resized)
            count += 1
            if count >= 20:
                break
        cv2.imshow('Captura de rostro', frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break
    cap.release()
    cv2.destroyAllWindows()

def recognize_face(names):
    cap = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    recognized = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face, (IMG_WIDTH, IMG_HEIGHT))
            label, confidence = model.predict(face_resized)
            if confidence < 100:
                recognized = names[label]
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f'{recognized}', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
                break
        cv2.imshow('Reconocimiento de rostro', frame)
        if recognized or (cv2.waitKey(1) & 0xFF == 27):
            break
    cap.release()
    cv2.destroyAllWindows()
    return recognized

def nuevo_locker():
    capture_face("Locker 1")
    global locker_owners
    locker_owners = train_model()
    messagebox.showinfo('Locker', f'Locker creado para Locker 1.')
    # Asegurarse de que la ventana principal siga activa
    root.deiconify()

def abrir_locker():
    global locker_owners
    if not locker_owners:
        locker_owners = train_model()
    if not locker_owners:
        messagebox.showerror('Error', 'No hay lockers registrados.')
        return
    messagebox.showinfo('Locker', 'Por favor, acerque su rostro a la cámara.')
    nombre = recognize_face(locker_owners)
    if nombre:
        messagebox.showinfo('Locker', f'Locker abierto para {nombre}!')
    else:
        messagebox.showerror('Error', 'No se reconoció el rostro.')
    # Asegurarse de que la ventana principal siga activa
    root.deiconify()

def simple_input(prompt):
    input_win = tk.Toplevel(root)
    input_win.title('Entrada')
    tk.Label(input_win, text=prompt).pack(padx=10, pady=5)
    entry = tk.Entry(input_win)
    entry.pack(padx=10, pady=5)
    entry.focus_set()
    result = {'value': None}
    def submit():
        result['value'] = entry.get()
        input_win.destroy()
    tk.Button(input_win, text='OK', command=submit).pack(pady=5)
    input_win.wait_window()
    return result['value']

root = tk.Tk()
root.title('Sistema de Lockers')
root.geometry('300x200')

btn_nuevo = tk.Button(root, text='Nuevo locker', font=('Arial', 14), command=nuevo_locker)
btn_nuevo.pack(pady=20)

btn_abrir = tk.Button(root, text='Abrir mi locker', font=('Arial', 14), command=abrir_locker)
btn_abrir.pack(pady=20)

root.mainloop()
