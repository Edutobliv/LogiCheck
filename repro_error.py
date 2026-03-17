
class Item:
    def __init__(self, cat, qty):
        self.categoria = cat
        self.cantidad = qty

yolo_items = [Item("Cemento", "5"), Item("Cemento", "10")]
factura_map = {}
for item in yolo_items:
    cat = item.categoria
    try:
        # This is what's happening in line 1523
        factura_map[cat] = factura_map.get(cat, 0) + item.cantidad
    except TypeError as e:
        print(f"Error caught: {e}")

# Correct way
factura_map = {}
for item in yolo_items:
    cat = item.categoria
    factura_map[cat] = factura_map.get(cat, 0) + int(item.cantidad)
print(f"Correct map: {factura_map}")
