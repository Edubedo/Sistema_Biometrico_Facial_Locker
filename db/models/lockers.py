from db.connection import connectionDB
import datetime

def db_get_all_lockers():
    """Devuelve lista de todos los lockers como dicts."""
    with connectionDB() as con:
        rows = con.execute(
            "SELECT * FROM Lockers ORDER BY CAST(t_numero_locker AS INTEGER)"
        ).fetchall()
    return [dict(r) for r in rows]


def db_get_locker_by_id(id_locker):
    with connectionDB() as con:
        row = con.execute(
            "SELECT * FROM Lockers WHERE ID_locker=?", (id_locker,)
        ).fetchone()
    return dict(row) if row else None


def db_next_free_locker():
    """Devuelve (ID_locker, t_numero_locker) del primer locker libre, o None."""
    with connectionDB() as con:
        row = con.execute(
            "SELECT ID_locker, t_numero_locker FROM Lockers "
            "WHERE t_estado='libre' ORDER BY CAST(t_numero_locker AS INTEGER) LIMIT 1"
        ).fetchone()
    return (row["ID_locker"], row["t_numero_locker"]) if row else None


def db_set_locker_estado(id_locker, estado, id_admin=None):
    """Actualiza el estado de un locker y registra quien lo modifico."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connectionDB() as con:
        con.execute(
            "UPDATE Lockers SET t_estado=?, d_fecha_modificacion=?, "
            "ID_usuario_modificacion=? WHERE ID_locker=?",
            (estado, now, id_admin, id_locker)
        )


def db_insert_locker(numero, zona="", tamano="mediano", id_admin=None):
    """Inserta un nuevo locker. Retorna el ID generado."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connectionDB() as con:
        cur = con.execute(
            "INSERT INTO Lockers (t_numero_locker, t_zona, t_tamano, t_estado, "
            "d_fecha_registro, ID_usuario_registro) VALUES (?,?,?,'libre',?,?)",
            (numero, zona, tamano, now, id_admin)
        )
        return cur.lastrowid


def db_delete_locker(id_locker):
    with connectionDB() as con:
        con.execute("DELETE FROM Lockers WHERE ID_locker=?", (id_locker,))
