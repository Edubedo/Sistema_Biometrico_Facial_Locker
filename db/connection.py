import os
from dotenv import load_dotenv
import sqlite3
load_dotenv()  

DB_PATH = os.getenv("DB_PATH")

def connectionDB():
    """Devuelve una conexion SQLite con row_factory activado."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con
