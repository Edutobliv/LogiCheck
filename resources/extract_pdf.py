import fitz
import sys

doc = fitz.open(r'c:\Users\samuv\Desktop\Programas_mios\LogiCheck\resources\proyecto de grado ferreteria.pdf')

# Write all text to a file
with open(r'c:\Users\samuv\Desktop\Programas_mios\LogiCheck\resources\pdf_text.txt', 'w', encoding='utf-8') as f:
    for i, page in enumerate(doc):
        text = page.get_text()
        f.write(f"\n=== PAGE {i+1} ===\n")
        f.write(text)

print(f"Extracted {len(doc)} pages to pdf_text.txt")
