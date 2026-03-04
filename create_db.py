import pandas as pd
import os

def create_excel_db():
    print("Creando BaseDatos_Ferreteria.xlsx...")
    
    # Datos de Materiales
    materiales_data = {
        'ID_Producto': ['001', '002', '003'],
        'Nombre_Material': ['Cemento Argos Gris', 'Tubo Presion PVC 1/2" 6m', 'Tubo Sanitario PVC 4" 6m'],
        'Categoria': ['Cemento', 'Tuberia_Presion', 'Tuberia_Sanitaria'],
        'Peso_Unitario (Kg)': [50.0, 0.8, 4.5],
        'Volumen_Unitario (m3)': [0.035, 0.005, 0.025]
    }
    df_materiales = pd.DataFrame(materiales_data)

    # Datos de Vehiculos
    vehiculos_data = {
        'ID_Vehiculo': ['V01', 'V02'],
        'Tipo_Vehiculo': ['Motocarro', 'Camion Turbo'],
        'Placa': ['ABC-123', 'DEF-456'],
        'Capacidad_Max_Peso (Kg)': [500.0, 4500.0],
        'Capacidad_Max_Volumen (m3)': [2.5, 18.0]
    }
    df_vehiculos = pd.DataFrame(vehiculos_data)

    # Exportar a Excel
    excel_path = os.path.join(os.path.dirname(__file__), 'BaseDatos_Ferreteria.xlsx')
    with pd.ExcelWriter(excel_path) as writer:
        df_materiales.to_excel(writer, sheet_name='Materiales', index=False)
        df_vehiculos.to_excel(writer, sheet_name='Vehiculos', index=False)
        
    print(f"Archivo Excel creado con éxito en: {excel_path}")

if __name__ == "__main__":
    create_excel_db()
