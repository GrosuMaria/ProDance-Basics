import sqlite3
import hashlib

def conectare():
    conn = sqlite3.connect("dance_app.db")
    conn.row_factory = sqlite3.Row
    return conn

def hash_parola(parola):
    return hashlib.sha256(parola.encode()).hexdigest()

def initializare():
    conn = conectare()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS utilizatori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            parola TEXT NOT NULL,
            caracter TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            dans TEXT NOT NULL,
            miscare_id INTEGER NOT NULL,
            finalizat INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sesiuni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            data_login TEXT NOT NULL,
            dans_practicat TEXT
        )
    """)

    conn.commit()
    conn.close()

def inregistrare(username, parola, caracter):
    conn = conectare()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM utilizatori WHERE username = ?",
            (username,)
        )
        if cursor.fetchone():
            return False, "Acest nume este deja folosit!"
        cursor.execute(
            "INSERT INTO utilizatori (username, parola, caracter) VALUES (?, ?, ?)",
            (username, hash_parola(parola), caracter)
        )
        conn.commit()
        return True, "Cont creat cu succes!"
    finally:
        conn.close()

def login(username, parola):
    conn = conectare()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT username, caracter FROM utilizatori WHERE username = ? AND parola = ?",
            (username, hash_parola(parola))
        )
        utilizator = cursor.fetchone()
        if utilizator:
            return True, dict(utilizator)
        return False, "Username sau parola incorecta!"
    finally:
        conn.close()

def salveaza_sesiune(username, dans=None):
    conn = conectare()
    cursor = conn.cursor()
    from datetime import datetime
    data = datetime.now().strftime("%d/%m/%Y %H:%M")
    cursor.execute(
        "INSERT INTO sesiuni (username, data_login, dans_practicat) VALUES (?, ?, ?)",
        (username, data, dans)
    )
    conn.commit()
    conn.close()

def get_istoric(username):
    conn = conectare()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT data_login, dans_practicat FROM sesiuni WHERE username = ? ORDER BY id DESC LIMIT 10",
        (username,)
    )
    rezultat = cursor.fetchall()
    conn.close()
    return rezultat

def get_progres(username, dans):
    conn = conectare()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT miscare_id, finalizat FROM progres WHERE username=? AND dans=?",
        (username, dans)
    )
    rezultat = {row["miscare_id"]: row["finalizat"] for row in cursor.fetchall()}
    conn.close()
    return rezultat

def salveaza_progres(username, dans, miscare_id, finalizat):
    conn = conectare()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO progres (username, dans, miscare_id, finalizat)
        VALUES (?, ?, ?, ?)
        ON CONFLICT DO NOTHING
    """, (username, dans, miscare_id, finalizat))
    conn.commit()
    conn.close()