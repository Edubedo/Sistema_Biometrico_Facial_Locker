from db.connection import connectionDB
import datetime
from utils.helpers import hash_password
# ──── USUARIOS (administradores) ─────────────────────────────────────────────

def db_get_admin_by_username(username):
    with connectionDB() as con:
        row = con.execute(
            "SELECT * FROM Usuarios WHERE t_usuario=? AND t_estado='activo'",
            (username,)
        ).fetchone()
    return dict(row) if row else None


def db_admin_exists(username):
    return db_get_admin_by_username(username) is not None


def db_admin_valid(username, password):
    admin = db_get_admin_by_username(username)
    if not admin:
        return False
    return admin["t_contrasena_hash"] == hash_password(password)


def db_register_admin(nombre, ap_paterno, ap_materno, username, password,
                       rol="empleado", id_registrador=None):
    """
    Inserta un nuevo administrador/empleado.
    Retorna el ID generado o None si el usuario ya existe.
    """
    if db_admin_exists(username):
        return None
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connectionDB() as con:
        cur = con.execute(
            "INSERT INTO Usuarios "
            "(t_nombre, t_apellido_paterno, t_apellido_materno, t_usuario, "
            "t_contrasena_hash, t_rol, t_estado, d_fecha_registro, ID_usuario_registro) "
            "VALUES (?,?,?,?,?,?,'activo',?,?)",
            (nombre, ap_paterno, ap_materno, username,
             hash_password(password), rol, now, id_registrador)
        )
        return cur.lastrowid


def db_delete_admin(username, id_admin_actual):
    """Desactiva (baja logica) un admin. No elimina fisicamente."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connectionDB() as con:
        con.execute(
            "UPDATE Usuarios SET t_estado='inactivo', d_fecha_modificacion=?, "
            "ID_usuario_modificacion=? WHERE t_usuario=?",
            (now, id_admin_actual, username)
        )


def db_get_all_admins():
    with connectionDB() as con:
        rows = con.execute(
            "SELECT ID_admin, t_nombre, t_apellido_paterno, t_apellido_materno, "
            "t_usuario, t_rol, t_estado, d_fecha_registro "
            "FROM Usuarios ORDER BY d_fecha_registro DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def db_count_active_admins():
    with connectionDB() as con:
        row = con.execute(
            "SELECT COUNT(*) as n FROM Usuarios WHERE t_estado='activo'"
        ).fetchone()
    return row["n"] if row else 0

