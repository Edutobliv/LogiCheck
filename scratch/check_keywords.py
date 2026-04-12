import sys
sys.path.insert(0, ".")
from core.invoice_parser import _get_yolo_category

casos = [
    "Tubo presion hidraulica RDE 26",
    "Tuberia PVC presion 110mm",
    "Tubo PVC presion 4 pulgadas",
    "hidraulico 3 pulgadas",
    "tubo presion",
    "pvc presion",
    "Cemento gris 50kg",
    "Tuberia sanitaria 6 pulgadas",
    "tubo sanitario desague",
    "saneamiento",
]
for d in casos:
    print(f"{d!r:50s} -> {_get_yolo_category(d)}")
