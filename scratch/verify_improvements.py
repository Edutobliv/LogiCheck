import sys
import os
import datetime
import numpy as np

# Aadir root al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_imports():
    print("--- [TEST 1] Verificando Importaciones ---")
    try:
        from core.inference_optimizer import InferenceOptimizer
        from core.evidence_capture import EvidenceCapture
        from ui.dashboard_chart import TrendChartWidget
        print("[OK] Mdulos nuevos importados correctamente.")
    except Exception as e:
        print(f"[FALLO] Error de importacin: {e}")
        return False
    return True

def test_fuzzy_parser_logic():
    print("\n--- [TEST 2] Verificando Lgica Fuzzy en Parser ---")
    from core.invoice_parser import _get_yolo_category
    
    cases = [
        ("Cernento Argos", "Cemento"),
        ("tubo snitario 4p", "Tubería Sanitaria"),
        ("hidraulico pvc", "Tubería Presión"),
        ("Tornillo madera", None)
    ]
    
    all_ok = True
    for desc, expected in cases:
        got = _get_yolo_category(desc)
        status = "OK" if got == expected else "FALLO"
        print(f"  [{status}] '{desc}' -> Got: {got} | Exp: {expected}")
        if got != expected: all_ok = False
    return all_ok

def test_evidence_paths():
    print("\n--- [TEST 3] Verificando Rutas de Evidencia ---")
    from core.evidence_capture import get_evidence_capture
    
    ec = get_evidence_capture()
    # Crear un frame negro dummy
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    try:
        rel_path = ec.capture_discrepancy(
            frame=dummy_frame,
            audit_id=999,
            factura_no="TEST-001",
            conteo_ia={"Cemento": 1},
            conteo_factura={"Cemento": 2},
            discrepancias={"Cemento": -1}
        )
        full_path = os.path.join(os.getcwd(), rel_path)
        exists = os.path.exists(full_path)
        print(f"  Capture Rel Path: {rel_path}")
        print(f"  File exists: {exists}")
        
        # Limpiar
        if exists: os.remove(full_path)
        
        if not exists: return False
    except Exception as e:
        print(f"  [FALLO] Error en captura: {e}")
        return False
    return True

def test_optimizer_metadata():
    print("\n--- [TEST 4] Verificando Metadatos del Optimizer ---")
    from core.inference_optimizer import InferenceOptimizer
    
    # No cargamos el modelo (pesado), solo probamos la deteccin de backend
    opt = InferenceOptimizer("models/yolo26n.pt")
    backend, device = opt._detect_best_backend()
    print(f"  Mejor backend detectado: {backend} ({device})")
    
    if backend not in ["cuda", "openvino", "cpu"]:
        return False
    return True

if __name__ == "__main__":
    results = [
        test_imports(),
        test_fuzzy_parser_logic(),
        test_evidence_paths(),
        test_optimizer_metadata()
    ]
    
    print("\n" + "="*40)
    if all(results):
        print("  VERIFICACIN COMPLETA: TODO OK  ")
    else:
        print("  VERIFICACIN FALLIDA: REVISAR LOGS  ")
    print("="*40)
    sys.exit(0 if all(results) else 1)
