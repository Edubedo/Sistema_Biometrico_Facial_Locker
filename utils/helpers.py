
import hashlib
from db.models.lockers import db_get_locker_by_id

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def db_get_locker_num_by_id(id_locker):
    """Retorna t_numero_locker de un locker dado su ID."""
    row = db_get_locker_by_id(id_locker)
    return row["t_numero_locker"] if row else "?"