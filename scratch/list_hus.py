import pandas as pd
import os

def list_hus():
    file_path = r'C:\Users\samuv\Desktop\Programas_mios\LogiCheck\requerimientos\Apartado 11 Requerimientos\Requerimientos loginCheck.xlsx'
    df = pd.read_excel(file_path, sheet_name='Req. Funcionales')
    
    # The Excel format seems to have headers multiple times or a custom layout
    # Let's try to find rows that look like HUs
    
    hus = []
    current_hu = {}
    
    for _, row in df.iterrows():
        val0 = str(row[0]).strip()
        val1 = str(row[1]).strip()
        
        if val0 == "ID":
            current_hu['ID'] = val1
        elif val0 == "Nombre":
            current_hu['Nombre'] = val1
        elif val0 == "Prioridad":
            current_hu['Prioridad'] = val1
            if 'ID' in current_hu and 'Nombre' in current_hu:
                hus.append(current_hu.copy())
                current_hu = {}
    
    print("--- Historias de Usuario detectadas en el Excel ---")
    for hu in hus:
        print(f"[{hu['ID']}] {hu['Nombre']} (Prioridad: {hu['Prioridad']})")

if __name__ == "__main__":
    list_hus()
