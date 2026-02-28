import sqlite3
DB_PATH   = r"C:\Users\ezesc\Desktop\rasp\lockers.db"


def connectionDB():
    """Devuelve una conexion SQLite con row_factory activado."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con
