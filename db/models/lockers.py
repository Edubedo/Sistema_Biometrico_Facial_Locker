from db.connection import connectionDB
import datetime


def db_get_all_lockers():
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
    with connectionDB() as con:
        row = con.execute(
            "SELECT ID_locker, t_numero_locker FROM Lockers "
            "WHERE t_estado='libre' ORDER BY CAST(t_numero_locker AS INTEGER) LIMIT 1"
        ).fetchone()
    return (row["ID_locker"], row["t_numero_locker"]) if row else None


def db_set_locker_estado(id_locker, estado, id_admin=None):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connectionDB() as con:
        con.execute(
            "UPDATE Lockers SET t_estado=?, d_fecha_modificacion=?, "
            "ID_usuario_modificacion=? WHERE ID_locker=?",
            (estado, now, id_admin, id_locker)
        )


def db_insert_locker(numero, zona="", tamano="mediano", id_admin=None):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connectionDB() as con:
        cur = con.execute(
            "INSERT INTO Lockers (t_numero_locker, t_zona, t_tamano, t_estado, "
            "d_fecha_registro, ID_usuario_registro) VALUES (?,?,?,'libre',?,?)",
            (numero, zona, tamano, now, id_admin)
        )
        return cur.lastrowid


def db_update_locker(id_locker, numero=None, zona=None, tamano=None,
                     estado=None, id_admin=None):
    """Actualiza los campos enviados (solo los que no son None)."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fields, params = [], []
    if numero  is not None: fields.append("t_numero_locker=?");    params.append(numero)
    if zona    is not None: fields.append("t_zona=?");             params.append(zona)
    if tamano  is not None: fields.append("t_tamano=?");           params.append(tamano)
    if estado  is not None: fields.append("t_estado=?");           params.append(estado)
    fields.append("d_fecha_modificacion=?");      params.append(now)
    fields.append("ID_usuario_modificacion=?");   params.append(id_admin)
    params.append(id_locker)
    with connectionDB() as con:
        con.execute(
            f"UPDATE Lockers SET {', '.join(fields)} WHERE ID_locker=?", params
        )


def db_delete_locker(id_locker):
    with connectionDB() as con:
        con.execute("DELETE FROM Lockers WHERE ID_locker=?", (id_locker,))