import sqlite3
import os
import sys
from datetime import datetime

DB = "inventario.db"
TXT_INV = "inventario.txt"
TXT_USR = "usuarios.txt"


def pedir_password(prompt="Password: "):
    sys.stdout.write(prompt)
    sys.stdout.flush()

    password = "*"

    if os.name == "nt":
        import msvcrt
        while True:
            ch = msvcrt.getch()
            if ch in (b"\r", b"\n"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                break
            elif ch == b"\x08":
                if password:
                    password = password[:-1]
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch == b"\x03":
                raise KeyboardInterrupt
            else:
                try:
                    char = ch.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                password += char
                sys.stdout.write("*")
                sys.stdout.flush()
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    break
                elif ch == "\x7f" or ch == "\x08":
                    if password:
                        password = password[:-1]
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif ch == "\x03":
                    raise KeyboardInterrupt
                else:
                    password += ch
                    sys.stdout.write("*")
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    return password


def conectar():
    return sqlite3.connect(DB)


def cargar_inventario_txt():
    if not os.path.exists(TXT_INV):
        print(f"No se encontro {TXT_INV}")
        return {}

    inventario = {}
    categoria_actual = None

    with open(TXT_INV, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue

            if "," not in linea:
                categoria_actual = linea
                inventario.setdefault(categoria_actual, {})
                continue

            if categoria_actual is None:
                continue

            partes = [p.strip() for p in linea.split(",")]
            nombre = partes[0]
            try:
                cantidad = int(partes[1]) if len(partes) > 1 and partes[1] else 0
            except ValueError:
                cantidad = 0
            unidad = partes[2] if len(partes) > 2 and partes[2] else None
            estado = partes[3] if len(partes) > 3 and partes[3] else None

            inventario[categoria_actual][nombre] = {
                "cantidad": cantidad,
                "unidad": unidad,
                "estado": estado,
            }

    return inventario


def guardar_inventario_txt(inventario):
    with open(TXT_INV, "w", encoding="utf-8") as f:
        for categoria, items in inventario.items():
            f.write(f"{categoria}\n")
            for nombre, info in items.items():
                cant = info.get("cantidad", 0)
                uni = info.get("unidad") or ""
                est = info.get("estado") or ""
                f.write(f"{nombre},{cant},{uni},{est}\n")
            f.write("\n")


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


class Usuario:
    def __init__(self, id, nombre):
        self.id = id
        self.nombre = nombre

    def ver_inventario(self):
        inventario = cargar_inventario_txt()
        if not inventario:
            print("No hay inventario registrado.")
            return

        print("\n=== INVENTARIO ===")
        for categoria, items in inventario.items():
            print(f"\n[{categoria}]")
            if not items:
                print("  (sin items)")
                continue
            for nombre, info in items.items():
                extra = f" {info['unidad']}" if info.get("unidad") else ""
                print(f"  - {nombre}: {info['cantidad']}{extra}")


class Estudiante(Usuario):
    def __init__(self, id, nombre, codigo):
        super().__init__(id, nombre)
        self.codigo = codigo

    def pedir(self, item, cantidad):
        if cantidad <= 0:
            print("Cantidad invalida")
            return

        inventario = cargar_inventario_txt()
        encontrado = False
        for categoria, items in inventario.items():
            if item in items:
                encontrado = True
                if items[item]["cantidad"] < cantidad:
                    print(f"No hay suficientes (disponibles: {items[item]['cantidad']})")
                    return
                items[item]["cantidad"] -= cantidad
                break

        if not encontrado:
            print("Item no existe")
            return

        guardar_inventario_txt(inventario)

        con = conectar()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO prestamos (item, cantidad, usuario_id, fecha) VALUES (?, ?, ?, ?)",
            (item, cantidad, self.id, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        con.commit()
        con.close()
        print("Prestado")

    def devolver(self, item, cantidad):
        if cantidad <= 0:
            print("Cantidad invalida")
            return

        con = conectar()
        cur = con.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(cantidad),0) FROM prestamos WHERE item = ? AND usuario_id = ?",
            (item, self.id),
        )
        prestado = cur.fetchone()[0]
        if prestado == 0:
            print("No tienes ese item en prestamo")
            con.close()
            return
        if cantidad > prestado:
            print(f"Solo tienes {prestado} en prestamo, se devolveran {prestado}")
            cantidad = prestado

        restante = cantidad
        cur.execute(
            "SELECT id, cantidad FROM prestamos WHERE item = ? AND usuario_id = ? ORDER BY fecha",
            (item, self.id),
        )
        for pid, pcant in cur.fetchall():
            if restante <= 0:
                break
            if pcant <= restante:
                restante -= pcant
                cur.execute("DELETE FROM prestamos WHERE id = ?", (pid,))
            else:
                cur.execute("UPDATE prestamos SET cantidad = cantidad - ? WHERE id = ?",
                            (restante, pid))
                restante = 0
        con.commit()
        con.close()

        inventario = cargar_inventario_txt()
        for categoria, items in inventario.items():
            if item in items:
                items[item]["cantidad"] += cantidad
                break
        guardar_inventario_txt(inventario)
        print("Devuelto")

    def mis_prestamos(self):
        con = conectar()
        cur = con.cursor()
        cur.execute(
            "SELECT item, cantidad, fecha FROM prestamos WHERE usuario_id = ? ORDER BY fecha DESC",
            (self.id,),
        )
        filas = cur.fetchall()
        con.close()

        if not filas:
            print("No tienes prestamos registrados.")
            return

        print("\n=== MIS PRESTAMOS ===")
        for nombre, cant, fecha in filas:
            print(f"  {cant} x {nombre}  ({fecha})")


class Admin(Usuario):
    def ver_prestamos(self):
        con = conectar()
        cur = con.cursor()
        cur.execute("""
            SELECT p.item, p.cantidad, u.nombre, u.identificador, p.fecha
            FROM prestamos p
            JOIN usuarios u ON u.id = p.usuario_id
            ORDER BY p.fecha DESC
        """)
        filas = cur.fetchall()
        con.close()

        if not filas:
            print("No hay prestamos registrados.")
            return

        print("\n=== PRESTAMOS ACTIVOS ===")
        for nombre, cant, usuario, ident, fecha in filas:
            print(f"  {cant} x {nombre} -> {usuario} ({ident})  [{fecha}]")

    def agregar_stock(self, item, cantidad):
        if cantidad <= 0:
            print("Cantidad invalida")
            return
        inventario = cargar_inventario_txt()
        for categoria, items in inventario.items():
            if item in items:
                items[item]["cantidad"] += cantidad
                guardar_inventario_txt(inventario)
                print("Stock actualizado")
                return
        print("Item no existe")

    def agregar_item(self, categoria, nombre, cantidad, unidad=None, estado=None):
        inventario = cargar_inventario_txt()
        inventario.setdefault(categoria, {})
        if nombre in inventario[categoria]:
            print("Ya existe ese item en esa categoria")
            return
        inventario[categoria][nombre] = {
            "cantidad": cantidad,
            "unidad": unidad,
            "estado": estado,
        }
        guardar_inventario_txt(inventario)
        print("Item agregado")

    def eliminar_item(self, nombre):
        con = conectar()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM prestamos WHERE item = ?", (nombre,))
        if cur.fetchone()[0] > 0:
            print("No se puede eliminar: hay prestamos activos de ese item")
            con.close()
            return
        con.close()

        inventario = cargar_inventario_txt()
        eliminado = False
        for categoria, items in inventario.items():
            if nombre in items:
                del items[nombre]
                eliminado = True
                break
        if not eliminado:
            print("Item no existe")
            return
        guardar_inventario_txt(inventario)
        print("Item eliminado")

    def agregar_usuario(self, nombre, rol, identificador, password):
        if rol not in ("estudiante", "admin"):
            print("Rol invalido (estudiante/admin)")
            return
        con = conectar()
        cur = con.cursor()
        try:
            cur.execute(
                "INSERT INTO usuarios (nombre, rol, identificador, password) VALUES (?, ?, ?, ?)",
                (nombre, rol, identificador, password),
            )
            con.commit()
            print("Usuario agregado")
        except sqlite3.IntegrityError:
            print("Ya existe un usuario con ese identificador")
        finally:
            con.close()

    def eliminar_usuario(self, identificador):
        con = conectar()
        cur = con.cursor()
        cur.execute("SELECT id FROM usuarios WHERE identificador = ?", (identificador,))
        fila = cur.fetchone()
        if not fila:
            print("Usuario no existe")
            con.close()
            return
        uid = fila[0]
        cur.execute("SELECT COUNT(*) FROM prestamos WHERE usuario_id = ?", (uid,))
        if cur.fetchone()[0] > 0:
            print("No se puede eliminar: el usuario tiene prestamos activos")
            con.close()
            return
        cur.execute("DELETE FROM usuarios WHERE id = ?", (uid,))
        con.commit()
        con.close()
        print("Usuario eliminado")

    def ver_usuarios(self):
        con = conectar()
        cur = con.cursor()
        cur.execute("SELECT nombre, rol, identificador FROM usuarios ORDER BY rol, nombre")
        filas = cur.fetchall()
        con.close()
        if not filas:
            print("No hay usuarios registrados.")
            return
        print("\n=== USUARIOS ===")
        for nombre, rol, ident in filas:
            print(f"  [{rol}] {nombre} - {ident}")


def login():
    print("\n=== SISTEMA DE INVENTARIO ===")
    print("1. Estudiante")
    print("2. Admin")
    print("0. Salir")
    op = input("Opcion: ").strip()

    if op == "0":
        return "salir"
    if op not in ("1", "2"):
        print("Opcion invalida")
        return None

    identificador = input("Codigo/Usuario: ").strip()
    password = pedir_password("Password: ")

    rol = "estudiante" if op == "1" else "admin"

    con = conectar()
    cur = con.cursor()
    cur.execute(
        "SELECT id, nombre FROM usuarios WHERE rol = ? AND identificador = ? AND password = ?",
        (rol, identificador, password),
    )
    fila = cur.fetchone()
    con.close()

    if not fila:
        print("Datos incorrectos")
        return None

    uid, nombre = fila
    if rol == "estudiante":
        return Estudiante(uid, nombre, identificador)
    return Admin(uid, nombre)


def menu_estudiante(e):
    while True:
        print("\n--- MENU ESTUDIANTE ---")
        print("1. Ver inventario")
        print("2. Pedir")
        print("3. Devolver")
        print("4. Mis prestamos")
        print("0. Salir")
        op = input("Opcion: ").strip()

        if op == "1":
            e.ver_inventario()
        elif op == "2":
            item = input("Item: ").strip()
            try:
                cant = int(input("Cantidad: "))
            except ValueError:
                print("Cantidad invalida")
                continue
            e.pedir(item, cant)
        elif op == "3":
            item = input("Item: ").strip()
            try:
                cant = int(input("Cantidad: "))
            except ValueError:
                print("Cantidad invalida")
                continue
            e.devolver(item, cant)
        elif op == "4":
            e.mis_prestamos()
        elif op == "0":
            break
        else:
            print("Opcion invalida")


def menu_admin(a):
    while True:
        print("\n--- MENU ADMIN ---")
        print("1. Ver inventario")
        print("2. Ver prestamos")
        print("3. Agregar stock")
        print("4. Agregar item")
        print("5. Eliminar item")
        print("6. Agregar usuario")
        print("7. Eliminar usuario")
        print("8. Ver usuarios")
        print("0. Salir")
        op = input("Opcion: ").strip()

        if op == "1":
            a.ver_inventario()
        elif op == "2":
            a.ver_prestamos()
        elif op == "3":
            item = input("Item: ").strip()
            try:
                cant = int(input("Cantidad: "))
            except ValueError:
                print("Cantidad invalida")
                continue
            a.agregar_stock(item, cant)
        elif op == "4":
            cat = input("Categoria (nueva o existente): ").strip()
            nom = input("Nombre del item: ").strip()
            try:
                cant = int(input("Cantidad inicial: "))
            except ValueError:
                print("Cantidad invalida")
                continue
            uni = input("Unidad (opcional): ").strip() or None
            est = input("Estado (opcional): ").strip() or None
            a.agregar_item(cat, nom, cant, uni, est)
        elif op == "5":
            nom = input("Nombre del item a eliminar: ").strip()
            a.eliminar_item(nom)
        elif op == "6":
            nombre = input("Nombre: ").strip()
            rol = input("Rol (estudiante/admin): ").strip().lower()
            ident = input("Codigo/Usuario: ").strip()
            pwd = pedir_password("Password: ")
            a.agregar_usuario(nombre, rol, ident, pwd)
        elif op == "7":
            ident = input("Codigo/Usuario a eliminar: ").strip()
            a.eliminar_usuario(ident)
        elif op == "8":
            a.ver_usuarios()
        elif op == "0":
            break
        else:
            print("Opcion invalida")


if __name__ == "__main__":
    inicializar_db()
    while True:
        usuario = login()
        if usuario == "salir":
            print("Hasta luego!")
            break
        if usuario is None:
            continue
        if isinstance(usuario, Estudiante):
            menu_estudiante(usuario)
        else:
            menu_admin(usuario)