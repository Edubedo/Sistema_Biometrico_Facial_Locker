from db.connection import connectionDB
import datetime

# ──── INTENTOS DE ACCESO (log de auditoria) ──────────────────────────────────

def db_log_intento(id_locker, tipo, resultado, descripcion="",
                    id_sesion=None, id_usuario=None):
    """
    Registra un intento de acceso en la tabla de auditoria.

    tipo       : 'registro_biometrico' | 'retirar' | 'seguir_comprando' |
                 'liberacion_admin' | 'acceso_admin'
    resultado  : 'exitoso' | 'fallido' | 'cancelado'
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connectionDB() as con:
        con.execute(
            "INSERT INTO Intentos_acceso "
            "(ID_locker, ID_sesion, ID_usuario, t_tipo_intento, "
            "d_fecha_hora_acceso, t_resultado_acceso, t_descripcion_acceso) "
            "VALUES (?,?,?,?,?,?,?)",
            (id_locker, id_sesion, id_usuario, tipo, now, resultado, descripcion)
        )


def db_get_intentos_recientes(limit=50):
    with connectionDB() as con:
        rows = con.execute(
            "SELECT ia.*, l.t_numero_locker, u.t_usuario "
            "FROM Intentos_acceso ia "
            "LEFT JOIN Lockers l ON ia.ID_locker=l.ID_locker "
            "LEFT JOIN Usuarios u ON ia.ID_usuario=u.ID_admin "
            "ORDER BY ia.d_fecha_hora_acceso DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]