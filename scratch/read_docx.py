from docx import Document
import os

doc = Document(r'C:\Users\samuv\Desktop\Programas_mios\LogiCheck\TESIS\Manual de Usuario\Manual_Usuario_LogiCheck_v1.docx')

print('=== ESTRUCTURA DEL DOCUMENTO ===')
print(f'Total de parrafos: {len(doc.paragraphs)}')
print(f'Total de tablas: {len(doc.tables)}')

# Count images
img_count = 0
for rel in doc.part.rels.values():
    if 'image' in rel.reltype:
        img_count += 1
print(f'Total de imagenes embebidas: {img_count}')
print()

print('=== CONTENIDO COMPLETO ===')
for i, p in enumerate(doc.paragraphs):
    style = p.style.name if p.style else 'None'
    text = p.text.strip()
    if text or 'Heading' in style:
        print(f'[{i}] ({style}) {text[:250]}')

    # Check for images in runs
    for run in p.runs:
        drawings = run._element.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing')
        if drawings:
            print(f'  >>> IMAGEN encontrada en parrafo {i}')
        # Also check inline
        ns_wp = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'
        inlines = run._element.findall(f'.//{ns_wp}inline')
        if inlines:
            print(f'  >>> INLINE SHAPE en parrafo {i}')

# Also check tables for images
print()
print('=== TABLAS ===')
for ti, table in enumerate(doc.tables):
    print(f'Tabla {ti}: {len(table.rows)} filas x {len(table.columns)} columnas')
    for ri, row in enumerate(table.rows):
        for ci, cell in enumerate(row.cells):
            txt = cell.text.strip()
            if txt:
                print(f'  [{ri},{ci}] {txt[:120]}')
