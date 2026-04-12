import os

path = 'core/yolo_manager.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# El diccionario insertado anteriormente no tena acentos. 
# Lo corregimos para que coincida con ui_cat ("Tubera Presin" y "Tubera Sanitaria")
replacements = {
    '"Tuberia Presion":   (255, 160,   0)': '"Tubería Presión":   (255, 160,   0)',
    '"Tuberia Sanitaria": ( 30, 144, 255)': '"Tubería Sanitaria": ( 30, 144, 255)'
}

for old, new in replacements.items():
    if old in content:
        content = content.replace(old, new)
        print(f"Sustituido: {old} -> {new}")
    else:
        print(f"No encontrado (quizás ya corregido): {old}")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Proceso finalizado.")
