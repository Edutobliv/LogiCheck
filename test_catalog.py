import sys
sys.path.insert(0, ".")
from core.catalog_store import get_all_materiales, get_all_vehiculos, import_from_excel, get_vehiculos_opciones
import os

excel = os.path.join(".", "BaseDatos_Ferreteria.xlsx")
counts = import_from_excel(excel)
print("Importacion:", counts)

mats = get_all_materiales()
print("== Materiales ==")
for m in mats:
    print(" ", m["codigo"], m["nombre"], m["categoria"], m["peso_unitario_kg"], "kg")

vehs = get_all_vehiculos()
print("== Vehiculos ==")
for v in vehs:
    print(" ", v["codigo"], v["tipo"], v["placa"], "max", v["capacidad_max_peso_kg"], "kg")

print("Opciones UI vehiculos:", get_vehiculos_opciones())
