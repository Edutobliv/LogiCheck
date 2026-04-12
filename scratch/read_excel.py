import pandas as pd
import os

def extract_to_text():
    file_path = r'C:\Users\samuv\Desktop\Programas_mios\LogiCheck\requerimientos\Apartado 11 Requerimientos\Requerimientos loginCheck.xlsx'
    output_path = r'c:\Users\samuv\Desktop\Programas_mios\LogiCheck\scratch\excel_content.txt'
    
    xl = pd.ExcelFile(file_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        for sheet in xl.sheet_names:
            f.write(f"\n{'='*20} SHEET: {sheet} {'='*20}\n")
            df = pd.read_excel(file_path, sheet_name=sheet)
            f.write(df.to_string())
            f.write("\n\n")
    print(f"Content saved to {output_path}")

if __name__ == "__main__":
    extract_to_text()
