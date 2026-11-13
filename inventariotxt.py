import os

TXT_INV = "inventario.txt"


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
