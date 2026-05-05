from db.connection import connectionDB
import datetime


def _decode_face_uid(raw_value):
    if isinstance(raw_value, bytes):
        return raw_value.decode("utf-8", errors="ignore").strip()
    if isinstance(raw_value, str):
        return raw_value.strip()
    return ""


def _delete_face_data(face_uid):
    if not face_uid:
        return
    try:
        from biometria.biometria import delete_face_data
        delete_face_data(face_uid)
    except Exception as ex:
        print(f"[Sesiones] No se pudo borrar biometria '{face_uid}': {ex}")


def _delete_session_face_data(id_sesion):
    with connectionDB() as con:
        row = con.execute(
            "SELECT b_vector_biometrico_temp FROM Sesiones WHERE ID_sesion=?",
            (id_sesion,)
        ).fetchone()
    face_uid = _decode_face_uid(row["b_vector_biometrico_temp"]) if row else ""
    if face_uid:
        _delete_face_data(face_uid)

    # Refuerzo por convencion: face_uid principal es "sesion_<ID_sesion>"
    fallback_uid = f"sesion_{id_sesion}"
    if face_uid != fallback_uid:
        _delete_face_data(fallback_uid)

# ──── SESIONES ───────────────────────────────────────────────────────────────

def db_create_sesion(id_locker, face_uid):
    """
    Crea una nueva sesion activa para un locker.
    Guarda el identificador de carpeta facial como blob de referencia.
    Retorna el ID_sesion generado.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ref_blob = face_uid.encode("utf-8")   # referencia al directorio de imagenes
    with connectionDB() as con:
        cur = con.execute(
            "INSERT INTO Sesiones "
            "(ID_locker, b_vector_biometrico_temp, d_fecha_hora_entrada, t_estado) "
            "VALUES (?,?,?,'activo')",
            (id_locker, ref_blob, now)
        )
        return cur.lastrowid


def db_close_sesion(id_sesion):
    """Marca una sesion como cerrada, registra la hora de salida y limpia sus imagenes."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _delete_session_face_data(id_sesion)
    with connectionDB() as con:
        con.execute(
            "UPDATE Sesiones SET t_estado='cerrado', d_fecha_hora_salida=?, b_vector_biometrico_temp=NULL "
            "WHERE ID_sesion=?",
            (now, id_sesion)
        )


def db_get_active_sesion_by_face(face_uid):
    """
    Busca la sesion activa cuyo blob de referencia coincide con face_uid.
    Retorna dict con ID_sesion e ID_locker, o None.
    """
    ref_blob = face_uid.encode("utf-8")
    with connectionDB() as con:
        row = con.execute(
            "SELECT ID_sesion, ID_locker FROM Sesiones "
            "WHERE b_vector_biometrico_temp=? AND t_estado='activo' "
            "ORDER BY d_fecha_hora_entrada DESC LIMIT 1",
            (ref_blob,)
        ).fetchone()
    return dict(row) if row else None


def db_get_all_sesiones_activas():
    """Devuelve todas las sesiones activas con info del locker."""
    with connectionDB() as con:
        rows = con.execute(
            "SELECT s.ID_sesion, s.ID_locker, s.b_vector_biometrico_temp, "
            "s.d_fecha_hora_entrada, l.t_numero_locker "
            "FROM Sesiones s JOIN Lockers l ON s.ID_locker=l.ID_locker "
            "WHERE s.t_estado='activo' ORDER BY s.d_fecha_hora_entrada DESC"
        ).fetchall()
    return [dict(r) for r in rows]