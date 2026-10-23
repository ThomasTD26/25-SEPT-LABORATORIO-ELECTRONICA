import sqlite3
import os

DB = "inventario.db"
TXT_USR = "usuarios.txt"


def conectar():
    return sqlite3.connect(DB)


def inicializar_db():
    con = conectar()
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('estudiante','admin')),
            identificador TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS prestamos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );
    """)

    cur.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        cargar_usuarios_txt(cur)

    con.commit()
    con.close()


def cargar_usuarios_txt(cur):
    if not os.path.exists(TXT_USR):
        print(f"No se encontro {TXT_USR}")
        return

    with open(TXT_USR, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            partes = [p.strip() for p in linea.split(",")]
            if len(partes) < 4:
                continue
            rol, ident, nombre, pwd = partes[0].lower(), partes[1], partes[2], partes[3]
            if rol not in ("estudiante", "admin"):
                continue
            cur.execute(
                "INSERT OR IGNORE INTO usuarios (nombre, rol, identificador, password) "
                "VALUES (?, ?, ?, ?)",
                (nombre, rol, ident, pwd),
            )
    print("Usuarios cargados desde", TXT_USR)
