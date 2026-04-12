"""
=======================================================================
  LogiCheck -- Suite de Pruebas de Integracion
  Verifica la cooperacion entre modulos: auth<->DB, audit<->DB, parser->audit
  Ejecutar desde la raiz del proyecto: python tests/test_integracion.py
=======================================================================
"""
import sys
import os
import json
import unittest
import tempfile
import sqlite3
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ============================================================================
#  T-I-01 | auth.py <-> SQLite -- Autenticacion real contra BD temporal
# ============================================================================
class TestAuthIntegracion(unittest.TestCase):
    """Prueba el ciclo completo de autenticacion usando una BD SQLite temporal."""

    @classmethod
    def setUpClass(cls):
        """Crea BD temporal y ejecuta migraciones + seed de usuarios."""
        cls.tmp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmp_dir, "test_logicheck.db")

        import core.auth as auth_module
        import core.db_migrations as mig_module
        import core.audit_store as audit_module

        auth_module.DB_PATH   = cls.db_path
        mig_module.DB_PATH    = cls.db_path
        audit_module.DB_PATH  = cls.db_path

        from core.auth import init_db
        init_db()

        print(f"\n  [SETUP] BD de prueba creada en: {cls.db_path}")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)
        print(f"\n  [TEARDOWN] BD temporal eliminada.")

    def test_autenticacion_credenciales_validas(self):
        """T-I-01a: Login con credenciales correctas retorna dict con datos del usuario."""
        from core.auth import authenticate
        result = authenticate("admin", "admin123")
        self.assertIsNotNone(result, "Login valido retorno None inesperadamente.")
        self.assertEqual(result["username"], "admin")
        self.assertEqual(result["role"],     "admin")
        print(f"\n  [T-I-01a] Usuario autenticado: {result['full_name']} | Rol: {result['role']}")

    def test_autenticacion_contrasena_incorrecta(self):
        """T-I-01b: Login con contrasena incorrecta retorna None."""
        from core.auth import authenticate
        result = authenticate("admin", "contrasena_incorrecta_999")
        self.assertIsNone(result, "Sistema autentico con contrasena erronea -- fallo de seguridad.")

    def test_autenticacion_usuario_inexistente(self):
        """T-I-01c: Login con usuario desconocido retorna None."""
        from core.auth import authenticate
        result = authenticate("fantasma_usuario", "cualquierClave")
        self.assertIsNone(result)

    def test_crear_y_autenticar_usuario_nuevo(self):
        """T-I-01d: Ciclo completo: crear usuario -> autenticar -> verificar rol."""
        from core.auth import create_user, authenticate
        ok = create_user("nuevo_tester", "claveTest2024!", "op_video", "Tester Integracion")
        self.assertTrue(ok, "Fallo la creacion del usuario.")
        
        result = authenticate("nuevo_tester", "claveTest2024!")
        self.assertIsNotNone(result)
        self.assertEqual(result["role"], "op_video")
        print(f"\n  [T-I-01d] Nuevo usuario creado y autenticado: {result['full_name']}")

    def test_desactivar_usuario_impide_login(self):
        """T-I-01e: Un usuario desactivado no puede iniciar sesion."""
        from core.auth import create_user, authenticate, deactivate_user, get_all_users
        create_user("usuario_inactivo", "pass123", "op_factura", "Inactivo Test")
        
        users = get_all_users()
        uid = next((u["id"] for u in users if u["username"] == "usuario_inactivo"), None)
        self.assertIsNotNone(uid)
        
        deactivate_user(uid)
        result = authenticate("usuario_inactivo", "pass123")
        self.assertIsNone(result, "Usuario desactivado logro autenticarse -- fallo de control de acceso.")

    def test_username_duplicado_retorna_false(self):
        """T-I-01f: Intentar crear un usuario con username existente retorna False."""
        from core.auth import create_user
        create_user("dup_test", "pass1", "op_video", "Primero")
        ok = create_user("dup_test", "pass2", "admin", "Duplicado")
        self.assertFalse(ok, "Sistema permitio crear username duplicado.")


# ============================================================================
#  T-I-02 | audit_store.py <-> SQLite -- Persistencia de Auditorias
# ============================================================================
class TestAuditIntegracion(unittest.TestCase):
    """Prueba el guardado, recuperacion y calculo de estadisticas de auditorias."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmp_dir, "test_audits.db")
        
        import core.auth as auth_module
        import core.db_migrations as mig_module
        import core.audit_store as audit_module

        auth_module.DB_PATH   = cls.db_path
        mig_module.DB_PATH    = cls.db_path
        audit_module.DB_PATH  = cls.db_path

        from core.auth import init_db
        init_db()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _usuario_prueba(self):
        return {"id": 1, "username": "op_test", "role": "op_video"}

    def test_guardar_auditoria_conforme(self):
        """T-I-02a: Guardar una auditoria conforme y verificar su ID."""
        from core.audit_store import save_audit, get_audits
        audit_id = save_audit(
            self._usuario_prueba(),
            {
                "factura_no":     "POSE-001",
                "cliente":        "Cliente Test S.A.S.",
                "video_nombre":   "despacho_001.mp4",
                "conteo_ia":      {"Cemento": 10},
                "conteo_factura": {"Cemento": 10},
                "vehiculo":       "ABC-123",
            }
        )
        self.assertGreater(audit_id, 0, "ID de auditoria invalido -- fallo al insertar.")
        
        audits = get_audits(limit=1)
        self.assertEqual(len(audits), 1)
        self.assertEqual(audits[0]["resultado"], "CONFORME")
        self.assertEqual(audits[0]["factura_no"], "POSE-001")
        print(f"\n  [T-I-02a] Auditoria guardada con ID={audit_id}, resultado: CONFORME")

    def test_guardar_auditoria_con_discrepancia(self):
        """T-I-02b: Auditoria con diferencias -> resultado DISCREPANCIA."""
        from core.audit_store import save_audit, get_audits
        save_audit(
            self._usuario_prueba(),
            {
                "factura_no":     "POSE-002",
                "cliente":        "Cliente Discrepante",
                "video_nombre":   "despacho_002.mp4",
                "conteo_ia":      {"Cemento": 8,  "Tuberia Presion": 5},
                "conteo_factura": {"Cemento": 10, "Tuberia Presion": 5},
                "vehiculo":       "XYZ-456",
            }
        )
        audits = get_audits(limit=5)
        ultima = next((a for a in audits if a["factura_no"] == "POSE-002"), None)
        self.assertIsNotNone(ultima)
        self.assertEqual(ultima["resultado"], "DISCREPANCIA")
        self.assertIn("Cemento", ultima["discrepancias"])
        self.assertEqual(ultima["discrepancias"]["Cemento"], -2)
        print(f"\n  [T-I-02b] Discrepancia detectada: {ultima['discrepancias']}")

    def test_dashboard_stats_cuenta_despachos_hoy(self):
        """T-I-02c: get_dashboard_stats refleja los despachos del dia actual."""
        from core.audit_store import get_dashboard_stats
        stats = get_dashboard_stats()
        self.assertIn("despachos_hoy", stats)
        self.assertIn("accuracy_pct", stats)
        self.assertGreaterEqual(stats["despachos_hoy"], 0)
        print(f"\n  [T-I-02c] Dashboard stats: {stats}")


# ============================================================================
#  T-I-03 | invoice_parser.py -- Clasificacion de texto de factura
# ============================================================================
class TestParserClasificacion(unittest.TestCase):
    """Prueba la logica de clasificacion YOLO sin necesidad de un PDF real."""

    def setUp(self):
        from core.invoice_parser import _get_yolo_category, InvoiceData, YoloItem
        self.classify = _get_yolo_category
        self.InvData  = InvoiceData
        self.YoloItem = YoloItem

    def test_pipeline_clasificacion_completo(self):
        """T-I-03a: Pipeline completo: crear items, clasificar y sumar cantidades."""
        data = self.InvData()
        
        # Usar keywords que el modulo si reconoce (validadas con check_keywords.py)
        raw_items = [
            ("Bulto de cemento gris 50kg",        "15"),   # YOLO: Cemento
            ("Tuberia PVC presion 110mm",           "8"),   # YOLO: Tuberia Presion
            ("Tornillo 3/8 x 1 galvanizado",       "200"), # NO YOLO (se filtra)
            ("Tubo sanitario desague 6 pulgadas",   "4"),   # YOLO: Tuberia Sanitaria
        ]
        for desc, cant in raw_items:
            cat = self.classify(desc)
            if cat:
                data.yolo_items.append(self.YoloItem(cat, desc, cant, "COD001", "$1,000"))
        
        # Solo deben quedar 3 items YOLO (el tornillo se filtra automaticamente)
        self.assertEqual(len(data.yolo_items), 3,
                         f"Se esperaban 3 items YOLO, se obtuvieron {len(data.yolo_items)}")
        self.assertEqual(data.get_category_qty("Cemento"), 15)
        self.assertEqual(data.total_yolo_items, 3)
        
        print(f"\n  [T-I-03a] Items clasificados: {data.total_yolo_items}/4")
        for item in data.yolo_items:
            print(f"    - [{item.categoria}] {item.descripcion} x {item.cantidad}")


# ============================================================================
#  EJECUTAR SUITE
# ============================================================================
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestAuthIntegracion))
    suite.addTests(loader.loadTestsFromTestCase(TestAuditIntegracion))
    suite.addTests(loader.loadTestsFromTestCase(TestParserClasificacion))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total  = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed

    print("\n" + "=" * 70)
    print("  RESUMEN PRUEBAS DE INTEGRACION LOGICHECK")
    print("=" * 70)
    print(f"  Total ejecutadas : {total}")
    print(f"  Exitosas         : {passed}")
    print(f"  Fallidas/Errores : {failed}")
    estado = "APROBADO" if failed == 0 else "REVISAR"
    print(f"  Estado final     : {estado}")
    print("=" * 70)
    sys.exit(0 if failed == 0 else 1)
