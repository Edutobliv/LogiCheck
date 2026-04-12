import docx
import os

def read_docx(file_path):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return
    
    doc = docx.Document(file_path)
    for para in doc.paragraphs:
        print(para.text)

if __name__ == "__main__":
    read_docx(r'C:\Users\samuv\Desktop\Programas_mios\LogiCheck\requerimientos\Pruebas\Indicaciones.docx')
