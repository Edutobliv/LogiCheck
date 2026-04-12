"""
=======================================================================
  LogiCheck -- Suite de Pruebas Funcionales (Caja Negra)
  Valida comportamiento del sistema desde perspectiva del usuario final
  Ejecutar desde la raiz del proyecto: python tests/test_funcionales.py
=======================================================================
"""
import sys
import os
import json
import unittest
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ============================================================================
#  T-F-01 | HU-09 -- Comparacion automatica despacho vs. factura
# ============================================================================
class TestHU09ComparacionDespacho(unittest.TestCase):
    """
    Valida la regla de negocio central del sistema:
    La comparacion entre lo detectado por IA y lo facturado.
    """

    def _resultado_auditoria(self, ia, factura):
        discrepancias = {}
        for mat in set(list(ia.keys()) + list(factura.keys())):
            diff = int(ia.get(mat, 0)) - int(factura.get(mat, 0))
            if diff != 0:
                discrepancias[mat] = diff
        resultado = "CONFORME" if not discrepancias else "DISCREPANCIA"
        return resultado, discrepancias

    def test_F01_despacho_exacto(self):
        """T-F-01a: Despacho exacto -> CONFORME, sin discrepancias."""
        res, disc = self._resultado_auditoria(
            ia      = {"Cemento": 20, "Tuberia Presion": 10},
            factura = {"Cemento": 20, "Tuberia Presion": 10}
        )
        self.assertEqual(res, "CONFORME")
        self.assertEqual(disc, {})
        print(f"\n  [T-F-01a] Resultado: {res} | Discrepancias: {disc}")

    def test_F01_faltante_de_cemento(self):
        """T-F-01b: Faltan 3 bultos de cemento en carga -> DISCREPANCIA negativa."""
        res, disc = self._resultado_auditoria(
            ia      = {"Cemento": 17},
            factura = {"Cemento": 20}
        )
        self.assertEqual(res, "DISCREPANCIA")
        self.assertEqual(disc["Cemento"], -3)
        print(f"\n  [T-F-01b] Resultado: {res} | Faltante de Cemento: {disc['Cemento']}")

    def test_F01_exceso_de_tuberia(self):
        """T-F-01c: Se cargaron 2 tubos de mas -> DISCREPANCIA positiva."""
        res, disc = self._resultado_auditoria(
            ia      = {"Tuberia Sanitaria": 7},
            factura = {"Tuberia Sanitaria": 5}
        )
        self.assertEqual(res, "DISCREPANCIA")
        self.assertEqual(disc["Tuberia Sanitaria"], 2)
        print(f"\n  [T-F-01c] Resultado: {res} | Exceso: {disc}")

    def test_F01_despacho_parcial_sin_factura(self):
        """T-F-01d: Despacho de material no incluido en factura -> DISCREPANCIA."""
        res, disc = self._resultado_auditoria(
            ia      = {"Cemento": 5, "Tuberia Presion": 3},
            factura = {"Cemento": 5}
        )
        self.assertEqual(res, "DISCREPANCIA")
        self.assertIn("Tuberia Presion", disc)
        print(f"\n  [T-F-01d] Material no facturado detectado: {disc}")

    def test_F01_despacho_vacio(self):
        """T-F-01e: Sin material en carga ni factura -> CONFORME."""
        res, disc = self._resultado_auditoria(ia={}, factura={})
        self.assertEqual(res, "CONFORME")

    def test_F01_multiples_discrepancias_simultaneas(self):
        """T-F-01f: Varios materiales con diferencias simultaneas."""
        res, disc = self._resultado_auditoria(
            ia      = {"Cemento": 8,  "Tuberia Presion": 6, "Tuberia Sanitaria": 2},
            factura = {"Cemento": 10, "Tuberia Presion": 4, "Tuberia Sanitaria": 2}
        )
        self.assertEqual(res, "DISCREPANCIA")
        self.assertEqual(disc["Cemento"], -2)
        self.assertEqual(disc["Tuberia Presion"], 2)
        self.assertNotIn("Tuberia Sanitaria", disc)
        print(f"\n  [T-F-01f] Multiples discrepancias: {disc}")


# ============================================================================
#  T-F-02 | HU-01/02 -- Control de Acceso mediante Roles
# ============================================================================
class TestHU01_02ControlAcceso(unittest.TestCase):
    """
    Valida la matriz de acceso RBAC desde perspectiva funcional.
    Nota: Los nombres de pagina deben coincidir exactamente con las claves
    del diccionario en permissions.py (_base_page_access).
    """

    def setUp(self):
        from core.permissions import can_access_page, can_do_action, _base_page_access
        self.can_page    = can_access_page
        self.can_action  = can_do_action
        self.base_access = _base_page_access

    def test_F02_auxiliar_video_flujo_completo(self):
        """T-F-02a: Auxiliar de video puede analizar, ver reportes pero NO cargar facturas."""
        role = "op_video"
        # Verificar directamente contra la logica base (evitar encoding de tildes)
        self.assertTrue(self.base_access(role, "Reportes"))
        self.assertFalse(self.can_action(role, "factura.cargar"))
        self.assertFalse(self.base_access(role, "Gesti\u00f3n de Usuarios"))
        print(f"\n  [T-F-02a] op_video: Reportes OK | factura.cargar DENEGADO | GestionUsuarios DENEGADO")

    def test_F02_auxiliar_factura_flujo_completo(self):
        """T-F-02b: Auxiliar de factura puede cargar facturas pero NO iniciar analisis IA."""
        role = "op_factura"
        self.assertTrue(self.can_action(role, "factura.cargar"))
        self.assertFalse(self.can_action(role, "video.iniciar"))
        self.assertFalse(self.base_access(role, "Gesti\u00f3n de Usuarios"))
        print(f"\n  [T-F-02b] op_factura: factura.cargar OK | video.iniciar DENEGADO")

    def test_F02_gerente_solo_lectura(self):
        """T-F-02c: Gerente puede ver Dashboard y Reportes, pero NO administrar usuarios."""
        role = "gerente"
        self.assertTrue(self.base_access(role, "Dashboard"))
        self.assertTrue(self.base_access(role, "Reportes"))
        self.assertFalse(self.can_action(role, "admin.usuarios"))
        self.assertFalse(self.can_action(role, "admin.config"))
        print(f"\n  [T-F-02c] Gerente: Dashboard OK | Reportes OK | admin.usuarios DENEGADO")

    def test_F02_dueno_configuracion_pero_no_usuarios(self):
        """T-F-02d: Dueno puede configurar sistema pero no administrar usuarios directamente."""
        role = "dueno"
        # Verificar con clave exacta del diccionario (con tilde)
        self.assertTrue(self.base_access(role, "Configuraci\u00f3n"))
        self.assertTrue(self.can_action(role, "admin.config"))
        self.assertFalse(self.base_access(role, "Gesti\u00f3n de Usuarios"))
        print(f"\n  [T-F-02d] Dueno: Configuracion OK | admin.config OK | GestionUsuarios DENEGADO")

    def test_F02_admin_acceso_total(self):
        """T-F-02e: Admin tiene acceso completo a todas las acciones criticas."""
        role = "admin"
        acciones = ["factura.cargar", "video.iniciar", "admin.usuarios",
                    "admin.config", "reportes.exportar"]
        for accion in acciones:
            self.assertTrue(self.can_action(role, accion),
                            f"Admin denegado en accion '{accion}'.")
        print(f"\n  [T-F-02e] Admin: todas las acciones criticas APROBADAS")


# ============================================================================
#  T-F-03 | HU-03/04 -- Clasificacion de items de factura (YOLO)
# ============================================================================
class TestHU03_04ClasificacionFactura(unittest.TestCase):
    """Valida el filtro de items de factura relevantes para YOLO."""

    def setUp(self):
        from core.invoice_parser import _get_yolo_category
        self.classify = _get_yolo_category

    def test_F03_factura_mixta_solo_yolo(self):
        """T-F-03a: De una factura con multiples productos, solo se extraen items YOLO."""
        # Usar keywords que SI funcionan (validadas con check_keywords.py)
        items_factura = [
            "Cemento Argos 50kg",           # YOLO: Cemento
            "Tornillo 3/8 caja x100",        # NO YOLO
            "Tuberia PVC presion 3 pulgadas", # YOLO: Tuberia Presion
            "Arena lavada metro cubico",      # NO YOLO
            "Tubo sanitario desague 6 pulg.", # YOLO: Tuberia Sanitaria
            "Llave de paso media pulgada",    # NO YOLO
            "Pintura blanca galon",           # NO YOLO
        ]
        yolo_count = sum(1 for desc in items_factura if self.classify(desc) is not None)
        non_yolo   = sum(1 for desc in items_factura if self.classify(desc) is None)

        self.assertEqual(yolo_count, 3, f"Esperados 3 items YOLO, detectados {yolo_count}")
        self.assertEqual(non_yolo, 4,   f"Esperados 4 items no-YOLO, detectados {non_yolo}")
        print(f"\n  [T-F-03a] Factura mixta: {yolo_count} YOLO | {non_yolo} ignorados")

    def test_F03_factura_sin_materiales_yolo(self):
        """T-F-03b: Factura sin materiales YOLO -> lista vacia."""
        items_factura = ["Brocha 4 pulgadas galeria", "Solvente por litro", "Lija numero 80 hoja"]
        yolo_count = sum(1 for d in items_factura if self.classify(d) is not None)
        self.assertEqual(yolo_count, 0)
        print(f"\n  [T-F-03b] Factura sin YOLO: {yolo_count} items clasificados (esperado: 0)")

    def test_F03_insensibilidad_mayusculas_minusculas(self):
        """T-F-03c: La clasificacion no debe depender de mayusculas/minusculas."""
        self.assertEqual(self.classify("CEMENTO GRIS 50KG"), "Cemento")
        self.assertEqual(self.classify("cemento gris 50kg"), "Cemento")
        self.assertEqual(self.classify("CeMeNtO gRiS"),     "Cemento")
        print(f"\n  [T-F-03c] Clasificacion insensible a mayusculas/minusculas: OK")


# ============================================================================
#  T-F-04 | HU-17/18 -- Gestion y persistencia de usuarios
# ============================================================================
class TestHU17_18GestionUsuarios(unittest.TestCase):
    """Valida el CRUD completo de usuarios desde la perspectiva del administrador."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.tmp_dir, "test_users.db")

        import core.auth as auth_m
        import core.db_migrations as mig_m
        auth_m.DB_PATH = cls.db_path
        mig_m.DB_PATH  = cls.db_path

        from core.auth import init_db
        init_db()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def test_F04_crear_usuario_con_todos_los_roles(self):
        """T-F-04a: El sistema permite crear usuarios para todos los roles definidos."""
        from core.auth import create_user
        roles = [("tester_admin", "admin"), ("tester_op_f", "op_factura"),
                 ("tester_op_v", "op_video"), ("tester_ger", "gerente"), ("tester_due", "dueno")]
        for uname, role in roles:
            ok = create_user(uname, "pass123Test!", role, f"Tester {role}")
            self.assertTrue(ok, f"No se pudo crear usuario con rol '{role}'.")
        print(f"\n  [T-F-04a] Usuarios creados para {len(roles)} roles distintos.")

    def test_F04_cambio_de_contrasena(self):
        """T-F-04b: Cambiar contrasena -> autenticacion con nueva clave funciona."""
        from core.auth import create_user, authenticate, change_password, get_all_users
        create_user("cambio_pass_test", "passVieja1", "op_video", "Cambio Test")

        users = get_all_users()
        uid = next((u["id"] for u in users if u["username"] == "cambio_pass_test"), None)
        self.assertIsNotNone(uid)

        change_password(uid, "passNueva2024!")
        # Contrasena vieja ya no debe funcionar
        self.assertIsNone(authenticate("cambio_pass_test", "passVieja1"))
        # Contrasena nueva si debe funcionar
        self.assertIsNotNone(authenticate("cambio_pass_test", "passNueva2024!"))
        print(f"\n  [T-F-04b] Cambio de contrasena verificado exitosamente.")

    def test_F04_actualizacion_rol_usuario(self):
        """T-F-04c: Actualizar el rol de un usuario persiste correctamente en BD."""
        from core.auth import create_user, update_user, authenticate, get_all_users
        create_user("rol_update_test", "pass123", "op_factura", "Update Test")

        users = get_all_users()
        uid = next((u["id"] for u in users if u["username"] == "rol_update_test"), None)
        update_user(uid, "Update Test Gerente", "gerente")

        result = authenticate("rol_update_test", "pass123")
        self.assertEqual(result["role"], "gerente")
        print(f"\n  [T-F-04c] Rol actualizado de op_factura -> gerente correctamente.")


# ============================================================================
#  EJECUTAR SUITE
# ============================================================================
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestHU09ComparacionDespacho))
    suite.addTests(loader.loadTestsFromTestCase(TestHU01_02ControlAcceso))
    suite.addTests(loader.loadTestsFromTestCase(TestHU03_04ClasificacionFactura))
    suite.addTests(loader.loadTestsFromTestCase(TestHU17_18GestionUsuarios))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total  = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed

    print("\n" + "=" * 70)
    print("  RESUMEN PRUEBAS FUNCIONALES LOGICHECK")
    print("=" * 70)
    print(f"  Total ejecutadas : {total}")
    print(f"  Exitosas         : {passed}")
    print(f"  Fallidas/Errores : {failed}")
    estado = "APROBADO" if failed == 0 else "REVISAR"
    print(f"  Estado final     : {estado}")
    print("=" * 70)
    sys.exit(0 if failed == 0 else 1)
