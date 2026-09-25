
import json
import os
from datetime import datetime

INV = "inventario.json"
USR = "usuarios.json"


def cargar(archivo):
    if not os.path.exists(archivo):
        print("No se encontro el archivo:", archivo)
        return None
    with open(archivo, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar(archivo, datos):
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)


class Usuario:
    def __init__(self, nombre):
        self.nombre = nombre

    def ver_inventario(self):
        datos = cargar(INV)
        if datos is None:
            return
        print("\nINVENTARIO")
        for categoria, items in datos.items():
            if categoria == "prestamos":
                continue
            print("\n" + categoria)
            for nombre, info in items.items():
                print(" ", nombre, "-", info["cantidad"])


class Estudiante(Usuario):
    def __init__(self, nombre, codigo):
        super().__init__(nombre)
        self.codigo = codigo

    def pedir(self, item, cantidad):
        datos = cargar(INV)
        if datos is None:
            return
        for categoria, items in datos.items():
            if categoria == "prestamos":
                continue
            if item in items:
                if items[item]["cantidad"] < cantidad:
                    print("No hay suficientes")
                    return
                items[item]["cantidad"] -= cantidad
                datos["prestamos"].append({
                    "item": item,
                    "cantidad": cantidad,
                    "estudiante": self.nombre,
                    "codigo": self.codigo,
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                guardar(INV, datos)
                print("Prestado")
                return
        print("Item no existe")

    def devolver(self, item, cantidad):
        datos = cargar(INV)
        if datos is None:
            return
        restante = cantidad
        for p in list(datos["prestamos"]):
            if p["codigo"] == self.codigo and p["item"] == item:
                if p["cantidad"] <= restante:
                    restante -= p["cantidad"]
                    datos["prestamos"].remove(p)
                else:
                    p["cantidad"] -= restante
                    restante = 0
        for categoria, items in datos.items():
            if categoria == "prestamos":
                continue
            if item in items:
                items[item]["cantidad"] += cantidad
                break
        guardar(INV, datos)
        print("Devuelto")

    def mis_prestamos(self):
        datos = cargar(INV)
        if datos is None:
            return
        for p in datos["prestamos"]:
            if p["codigo"] == self.codigo:
                print(p["cantidad"], "x", p["item"], "-", p["fecha"])


class Admin(Usuario):
    def ver_prestamos(self):
        datos = cargar(INV)
        if datos is None:
            return
        for p in datos["prestamos"]:
            print(p["cantidad"], "x", p["item"], "->", p["estudiante"], p["codigo"])

    def agregar_stock(self, item, cantidad):
        datos = cargar(INV)
        if datos is None:
            return
        for categoria, items in datos.items():
            if categoria == "prestamos":
                continue
            if item in items:
                items[item]["cantidad"] += cantidad
                guardar(INV, datos)
                print("Stock actualizado")
                return
        print("Item no existe")


def login():
    usuarios = cargar(USR)
    if usuarios is None:
        return None

    if "estudiantes" not in usuarios or "admins" not in usuarios:
        print("usuarios.json esta mal formado")
        return None

    print("1. Estudiante")
    print("2. Admin")
    op = input("Opcion: ").strip()

    if op == "1":
        print(usuarios["estudiantes"])
        codigo = input("Codigo: ").strip()
        password = input("Password: ").strip()

        for e in usuarios["estudiantes"]:
            if str(e["codigo"]) == codigo and str(e["password"]) == password:
                return Estudiante(e["nombre"], str(e["codigo"]))

        print("Datos incorrectos")
        return None

    elif op == "2":
        usuario = input("Usuario: ").strip()
        password = input("Password: ").strip()

        for a in usuarios["admins"]:
            if str(a["usuario"]) == usuario and str(a["password"]) == password:
                return Admin(a["nombre"])

        print("Datos incorrectos")
        return None

    else:
        print("Opcion invalida")
        return None


def menu_estudiante(e):
    while True:
        print("\n1. Ver inventario")
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
        print("\n1. Ver inventario")
        print("2. Ver prestamos")
        print("3. Agregar stock")
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
        elif op == "0":
            break
        else:
            print("Opcion invalida")


if __name__ == "__main__":
    while True:
        usuario = login()
        if usuario is None:
            continue
        if isinstance(usuario, Estudiante):
            menu_estudiante(usuario)
        else:
            menu_admin(usuario)