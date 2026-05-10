# -*- coding: utf-8 -*-
"""
=======================================================================
  LogiCheck -- Suite de Pruebas Unitarias
  MÃ³dulos: auth.py, permissions.py, invoice_parser.py, audit_store.py
  Ejecutar desde la raÃ­z del proyecto: python tests/test_unitarias.py
=======================================================================
"""
import sys
import os
import json
import hashlib
import secrets
import unittest
import tempfile
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  T-U-01 | MÃ³dulo: auth.py â€” Hashing y VerificaciÃ³n de ContraseÃ±as
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class TestHashingSeguro(unittest.TestCase):
    """Pruebas del sistema de hash SHA-256 + salt único por usuario."""

    def setUp(self):
        from core.auth import _generate_salt, _hash_password, _verify_password
        self._gen_salt    = _generate_salt
        self._hash_pw     = _hash_password
        self._verify_pw   = _verify_password

    def test_salt_longitud_correcta(self):
        """T-U-01a: El salt debe tener 64 caracteres hexadecimales (32 bytes)."""
        salt = self._gen_salt()
        self.assertEqual(len(salt), 64, f"Salt generado tiene longitud {len(salt)}, se esperaban 64.")

    def test_salt_es_unico(self):
        """T-U-01b: Dos salts generados consecutivamente deben ser distintos."""
        s1, s2 = self._gen_salt(), self._gen_salt()
        self.assertNotEqual(s1, s2, "Dos salts consecutivos resultaron idÃ©nticos â€” posible fallo en PRNG.")

    def test_hash_determinista_con_mismo_salt(self):
        """T-U-01c: El mismo par (password, salt) siempre produce el mismo hash."""
        salt = self._gen_salt()
        h1 = self._hash_pw("miContraseÃ±a123", salt)
        h2 = self._hash_pw("miContraseÃ±a123", salt)
        self.assertEqual(h1, h2)

    def test_hash_diferente_con_distinto_salt(self):
        """T-U-01d: La misma contraseña con salts distintos produce hashes distintos."""
        s1, s2 = self._gen_salt(), self._gen_salt()
        h1 = self._hash_pw("mismaPass", s1)
        h2 = self._hash_pw("mismaPass", s2)
        self.assertNotEqual(h1, h2, "Hashes iguales a pesar de salts distintos â€” colisiÃ³n crÃ­tica.")

    def test_verificacion_correcta(self):
        """T-U-01e: La verificación retorna True para credenciales válidas."""
        salt = self._gen_salt()
        pw   = "ContraseÃ±aSegura!2024"
        h    = self._hash_pw(pw, salt)
        self.assertTrue(self._verify_pw(pw, h, salt))

    def test_verificacion_incorrecta(self):
        """T-U-01f: La verificación retorna False para contraseña incorrecta."""
        salt = self._gen_salt()
        h    = self._hash_pw("contraseñaReal", salt)
        self.assertFalse(self._verify_pw("contraseñaMAL", h, salt))

    def test_hash_formato_pbkdf2(self):
        """T-U-01g: El hash resultante debe declarar algoritmo PBKDF2."""
        h = self._hash_pw("test", self._gen_salt())
        self.assertTrue(h.startswith("pbkdf2_sha256$"))
        self.assertEqual(len(h.split("$")), 4)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  T-U-02 | MÃ³dulo: permissions.py â€” Control de Acceso por Rol (RBAC)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class TestPermisosRBAC(unittest.TestCase):
    """Pruebas del sistema de roles y accesos del sistema LogiCheck."""

    def setUp(self):
        from core.permissions import can_access_page, can_do_action, get_role_permissions
        self.can_page   = can_access_page
        self.can_action = can_do_action
        self.get_perms  = get_role_permissions

    def test_admin_accede_todas_las_paginas(self):
        """T-U-02a: El rol 'admin' debe tener acceso a todas las páginas crÃ­ticas."""
        paginas = ["Dashboard", "Factura PDF", "Análisis de Video",
                   "Gestión de Usuarios", "Configuración"]
        for pag in paginas:
            self.assertTrue(self.can_page("admin", pag),
                            f"Admin NO puede acceder a '{pag}' â€” fallo de permisos.")

    def test_op_video_no_accede_gestion_usuarios(self):
        """T-U-02b: El rol 'op_video' NO debe poder acceder a Gestión de Usuarios."""
        self.assertFalse(self.can_page("op_video", "Gestión de Usuarios"))

    def test_op_video_no_accede_configuracion(self):
        """T-U-02c: El rol 'op_video' NO debe poder acceder a Configuración."""
        self.assertFalse(self.can_page("op_video", "Configuración"))

    def test_op_factura_no_puede_iniciar_video(self):
        """T-U-02d: El operador de factura no puede iniciar anÃ¡lisis de IA."""
        self.assertFalse(self.can_action("op_factura", "video.iniciar"))

    def test_op_video_no_puede_cargar_factura(self):
        """T-U-02e: El operador de video no puede cargar facturas PDF."""
        self.assertFalse(self.can_action("op_video", "factura.cargar"))

    def test_gerente_no_puede_gestionar_usuarios(self):
        """T-U-02f: El gerente no puede administrar cuentas de usuario."""
        self.assertFalse(self.can_action("gerente", "admin.usuarios"))

    def test_dueno_puede_acceder_configuracion(self):
        """T-U-02g: El dueño debe poder acceder a Configuración del sistema."""
        self.assertTrue(self.can_page("dueno", "Configuración"))

    def test_rol_inexistente_deniega_acceso(self):
        """T-U-02h: Un rol desconocido no debe obtener acceso a ninguna pÃ¡gina."""
        self.assertFalse(self.can_page("hacker_externo", "Gestión de Usuarios"))
        self.assertFalse(self.can_action("hacker_externo", "admin.config"))

    def test_get_role_permissions_retorna_estructura_valida(self):
        """T-U-02i: get_role_permissions debe retornar dict con claves 'páginas' y 'acciones'."""
        perms = self.get_perms("admin")
        self.assertIn("páginas", perms)
        self.assertIn("acciones", perms)
        self.assertIsInstance(perms["páginas"], list)
        self.assertIsInstance(perms["acciones"], list)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  T-U-03 | MÃ³dulo: invoice_parser.py â€” ClasificaciÃ³n por Palabras Clave
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class TestClasificacionFactura(unittest.TestCase):
    """Pruebas de la lÃ³gica de categorizaciÃ³n YOLO del parser de facturas."""

    def setUp(self):
        from core.invoice_parser import _get_yolo_category, InvoiceData, YoloItem
        self.classify  = _get_yolo_category
        self.InvData   = InvoiceData
        self.YoloItem  = YoloItem

    def test_clasifica_cemento_correctamente(self):
        """T-U-03a: Descripciones con 'cemento' deben clasificarse en 'Cemento'."""
        casos = ["Bulto de cemento Gris 50kg", "Cemento Argos Portland",
                 "CEMENTO BLANCO x50kg", "2 sacos de mortero seco"]
        for desc in casos:
            cat = self.classify(desc)
            self.assertEqual(cat, "Cemento", f"'{desc}' â†’ categoría incorrecta: {cat}")

    def test_clasifica_tuberia_presion_correctamente(self):
        """T-U-03b: Descripciones de tuberia de presion deben clasificarse correctamente."""
        casos = ["Tuberia PVC presion 110mm", "Tubo PVC presion 4 pulgadas",
                 "pvc presion RDE 26 hidraulico"]
        for desc in casos:
            cat = self.classify(desc)
            self.assertIsNotNone(cat, f"'{desc}' no fue clasificado (retorno None)")

    def test_clasifica_tuberia_sanitaria_correctamente(self):
        """T-U-03c: Descripciones de tuberías sanitarias deben clasificarse correctamente."""
        casos = ["Tubo Sanitario 6\" x 3m", "Tubería PVC Sanitaria desagÃ¼e",
                 "tubo saneamiento alcantarillado"]
        for desc in casos:
            cat = self.classify(desc)
            self.assertEqual(cat, "Tubería Sanitaria", f"'{desc}' â†’ categoría incorrecta: {cat}")

    def test_item_no_yolo_retorna_none(self):
        """T-U-03d: Productos sin categoria YOLO deben retornar None."""
        casos = ["Tornillo galvanizado 3/8", "Pintura exterior blanco mate",
                 "Malla electrosoldada 1.5m x 6m", "Varilla corrugada 3/8"]
        for desc in casos:
            cat = self.classify(desc)
            self.assertIsNone(cat, f"'{desc}' clasificado como '{cat}' incorrectamente")

    def test_get_category_qty_suma_correctamente(self):
        """T-U-03e: InvoiceData.get_category_qty suma cantidades por categoría."""
        data  = self.InvData()
        item1 = self.YoloItem("Cemento", "Bulto cemento", "10", "CEM001", "$50,000")
        item2 = self.YoloItem("Cemento", "Cemento Argos", "5",  "CEM002", "$27,500")
        item3 = self.YoloItem("Tubería PresiÃ³n", "Tubo PVC", "3", "TUB001", "$15,000")
        data.yolo_items = [item1, item2, item3]
        self.assertEqual(data.get_category_qty("Cemento"), 15)
        self.assertEqual(data.get_category_qty("Tubería PresiÃ³n"), 3)
        self.assertEqual(data.get_category_qty("Tubería Sanitaria"), 0)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def test_get_category_qty_tolera_formatos_decimales(self):
        """T-U-03f: Las cantidades toleran separadores comunes de facturas."""
        data = self.InvData()
        data.yolo_items = [
            self.YoloItem("Cemento", "Cemento", "1,0", "C1", "$1"),
            self.YoloItem("Cemento", "Cemento", "2.000", "C2", "$1"),
        ]
        self.assertEqual(data.get_category_qty("Cemento"), 2001)
#  T-U-04 | MÃ³dulo: audit_store.py â€” CÃ¡lculo de Discrepancias
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
class TestCalculoDiscrepancias(unittest.TestCase):
    """Pruebas del cÃ¡lculo automÃ¡tico de discrepancias entre IA y factura."""

    def _calcular_discrepancias(self, conteo_ia: dict, conteo_factura: dict) -> dict:
        """Replica la lÃ³gica de discrepancias de audit_store.save_audit."""
        discrepancias = {}
        for mat in set(list(conteo_ia.keys()) + list(conteo_factura.keys())):
            ia_val  = int(conteo_ia.get(mat, 0))
            fac_val = int(conteo_factura.get(mat, 0))
            diff = ia_val - fac_val
            if diff != 0:
                discrepancias[mat] = diff
        return discrepancias

    def _resultado(self, discrepancias: dict) -> str:
        return "CONFORME" if not discrepancias else "DISCREPANCIA"

    def test_despacho_conforme(self):
        """T-U-04a: Conteos iguales â†’ resultado CONFORME, sin discrepancias."""
        d = self._calcular_discrepancias(
            {"Cemento": 10, "Tubería PresiÃ³n": 5},
            {"Cemento": 10, "Tubería PresiÃ³n": 5}
        )
        self.assertEqual(d, {})
        self.assertEqual(self._resultado(d), "CONFORME")

    def test_faltante_detectado(self):
        """T-U-04b: IA detecta menos unidades que las facturadas â†’ discrepancia negativa."""
        d = self._calcular_discrepancias(
            {"Cemento": 8},
            {"Cemento": 10}
        )
        self.assertEqual(d["Cemento"], -2)
        self.assertEqual(self._resultado(d), "DISCREPANCIA")

    def test_exceso_detectado(self):
        """T-U-04c: IA detecta más unidades que las facturadas â†’ discrepancia positiva."""
        d = self._calcular_discrepancias(
            {"Cemento": 12},
            {"Cemento": 10}
        )
        self.assertEqual(d["Cemento"], 2)
        self.assertEqual(self._resultado(d), "DISCREPANCIA")

    def test_material_en_factura_no_detectado_por_ia(self):
        """T-U-04d: Material en factura no detectado por IA â†’ discrepancia = conteo_ia - conteo_factura."""
        d = self._calcular_discrepancias(
            {},
            {"Tubería Sanitaria": 4}
        )
        self.assertEqual(d["Tubería Sanitaria"], -4)

    def test_material_detectado_no_facturado(self):
        """T-U-04e: IA detecta material no contemplado en factura â†’ exceso positivo."""
        d = self._calcular_discrepancias(
            {"Cemento": 3},
            {}
        )
        self.assertEqual(d["Cemento"], 3)

    def test_multiples_discrepancias(self):
        """T-U-04f: Múltiples materiales pueden tener discrepancias simultÃ¡neas."""
        d = self._calcular_discrepancias(
            {"Cemento": 8, "Tubería PresiÃ³n": 6, "Tubería Sanitaria": 3},
            {"Cemento": 10, "Tubería PresiÃ³n": 6, "Tubería Sanitaria": 5}
        )
        self.assertIn("Cemento", d)
        self.assertNotIn("Tubería PresiÃ³n", d)  # Coincide, no debe aparecer
        self.assertIn("Tubería Sanitaria", d)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  EJECUTAR SUITE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
if __name__ == "__main__":
    loader  = unittest.TestLoader()
    suite   = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestHashingSeguro))
    suite.addTests(loader.loadTestsFromTestCase(TestPermisosRBAC))
    suite.addTests(loader.loadTestsFromTestCase(TestClasificacionFactura))
    suite.addTests(loader.loadTestsFromTestCase(TestCalculoDiscrepancias))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total  = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed

    print("\n" + "=" * 70)
    print("  RESUMEN PRUEBAS UNITARIAS LOGICHECK")
    print("=" * 70)
    print(f"  Total ejecutadas : {total}")
    print(f"  Exitosas         : {passed}")
    print(f"  Fallidas/Errores : {failed}")
    estado = 'APROBADO' if failed == 0 else 'REVISAR'
    print(f"  Estado final     : {estado}")
    print("=" * 70)
    sys.exit(0 if failed == 0 else 1)
