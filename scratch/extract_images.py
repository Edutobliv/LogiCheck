"""Extrae todas las imagenes del docx actual y las guarda en una carpeta temporal."""
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import os

doc = Document(r'C:\Users\samuv\Desktop\Programas_mios\LogiCheck\TESIS\Manual de Usuario\Manual_Usuario_LogiCheck_v1.docx')

out_dir = r'C:\Users\samuv\Desktop\Programas_mios\LogiCheck\TESIS\Manual de Usuario\_imgs'
os.makedirs(out_dir, exist_ok=True)

img_idx = 0
for rel in doc.part.rels.values():
    if 'image' in rel.reltype:
        img_idx += 1
        ext = os.path.splitext(rel.target_ref)[1]  # .png, .jpeg, etc.
        fname = f'img_{img_idx:02d}{ext}'
        with open(os.path.join(out_dir, fname), 'wb') as f:
            f.write(rel.target_part.blob)
        print(f'Saved: {fname} ({len(rel.target_part.blob)} bytes)')

print(f'\nTotal: {img_idx} images extracted to {out_dir}')
