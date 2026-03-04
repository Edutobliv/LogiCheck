"""
invoice_parser.py
-----------------
Módulo para leer facturas electrónicas PDF de Ferretería Durán (Siigo Nube)
y extraer ÚNICAMENTE los productos que serán detectados por YOLO:

  - Cemento (ej: "Bulto de cemento Gris", "Cemento Argos")
  - Tubería de Presión (ej: "Tubo Presión", "Tubería PVC Presión")
  - Tubería Sanitaria (ej: "Tubo Sanitario", "Tubería PVC Sanitaria")
"""

import re
from typing import Optional

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


# ─────────────────────────────────────────────────────────────
# Categorías YOLO — palabras clave por tipo de producto
# ─────────────────────────────────────────────────────────────
YOLO_CATEGORIES = {
    "Cemento": [
        "cemento", "bulto de cemento", "cemento gris", "cemento blanco",
        "cemento argos", "cemento súper", "mortero", "cemento portland",
    ],
    "Tubería Presión": [
        "tubo presión", "tubería presión", "tubo pvc presión",
        "tubería pvc presión", "presión hidráulica", "tubo hidráulico",
        "hidráulico", "tubopresión", "pvc presion",
    ],
    "Tubería Sanitaria": [
        "tubo sanitario", "tubería sanitaria", "tubo pvc sanitario",
        "tubería pvc sanitaria", "alcantarillado", "desagüe",
        "sanitaria", "saneamiento", "drenaje",
    ],
}


def _get_yolo_category(descripcion: str) -> Optional[str]:
    """
    Retorna la categoría YOLO del ítem si coincide, o None si no aplica.
    """
    desc_lower = descripcion.lower()
    for category, keywords in YOLO_CATEGORIES.items():
        for kw in keywords:
            if kw in desc_lower:
                return category
    return None


# ─────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────
class YoloItem:
    """
    Representa un ítem de la factura relevante para la detección YOLO.
    Solo guarda los datos necesarios para comparar con el conteo del modelo.
    """
    def __init__(self, categoria: str, descripcion: str,
                 cantidad: str, codigo: str, valor_bruto: str):
        self.categoria     = categoria    # "Cemento" | "Tubería Presión" | "Tubería Sanitaria"
        self.descripcion   = descripcion
        self.cantidad      = cantidad
        self.codigo        = codigo
        self.valor_bruto   = valor_bruto
        self.conteo_yolo   = 0           # Se llenará con el resultado de YOLO
        self.discrepancia  = None        # Se calculará al comparar

    def to_table_row(self):
        """Retorna los datos como lista para insertar en la tabla de la UI."""
        return [
            self.categoria,
            self.descripcion,
            self.cantidad,
            self.valor_bruto,
        ]


class InvoiceData:
    """Datos extraídos de una factura, solo con ítems YOLO."""
    def __init__(self):
        self.raw_text         = ""
        self.numero_factura   = "—"
        self.fecha_expedicion = "—"
        self.cliente          = "—"
        self.nit_cliente      = "—"
        self.total_pagar      = "—"
        self.yolo_items: list[YoloItem] = []
        self.total_items_factura = 0   # Total de ítems en la factura original
        self.pdf_path         = ""
        self.parse_error      = None

    @property
    def total_yolo_items(self) -> int:
        return len(self.yolo_items)

    def get_category_qty(self, categoria: str) -> int:
        """Suma las cantidades de todos los ítems de una categoría."""
        total = 0
        for it in self.yolo_items:
            if it.categoria == categoria:
                try:
                    total += int(it.cantidad)
                except ValueError:
                    pass
        return total


# ─────────────────────────────────────────────────────────────
# Parser principal
# ─────────────────────────────────────────────────────────────
class InvoiceParser:
    """
    Lee una factura PDF de Ferretería Durán y extrae solo los 3 tipos
    de productos relevantes para la detección YOLO.
    """

    def __init__(self):
        if not PYMUPDF_AVAILABLE:
            raise ImportError(
                "PyMuPDF no está instalado.\n"
                "Ejecuta:  pip install PyMuPDF"
            )

    # ── Public API ────────────────────────────────────────────
    def parse(self, pdf_path: str) -> InvoiceData:
        """Lee el PDF y retorna un InvoiceData con los ítems YOLO extraídos."""
        data = InvoiceData()
        data.pdf_path = pdf_path

        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            for page in doc:
                full_text += page.get_text("text") + "\n"
            doc.close()

            data.raw_text = full_text
            self._extract_header(data)
            self._extract_client(data)
            self._extract_dates(data)
            self._extract_yolo_items(data)
            self._extract_totals(data)

        except Exception as e:
            data.parse_error = str(e)

        return data

    # ── Header ────────────────────────────────────────────────
    def _extract_header(self, data: InvoiceData):
        text = data.raw_text
        patterns = [
            r"No\.\s+(POSE\s*\d+)",
            r"No\.\s+([A-Z]+-\d+)",
            r"Factura[^\n]*No\.?\s*([A-Z0-9\s\-]+?)\n",
            r"Nro\.?\s*([A-Z0-9\-]+)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                data.numero_factura = m.group(1).strip()
                break

    # ── Client ────────────────────────────────────────────────
    def _extract_client(self, data: InvoiceData):
        text = data.raw_text

        m = re.search(r"Se[ñn]ores?\s+([A-ZÁÉÍÓÚÑ][^\n]{3,60})", text, re.IGNORECASE)
        if m:
            data.cliente = m.group(1).strip()

        nit_matches = re.findall(r"NIT\s+([\d\-\.]+)", text, re.IGNORECASE)
        if len(nit_matches) >= 2:
            data.nit_cliente = nit_matches[1]
        elif nit_matches:
            data.nit_cliente = nit_matches[0]

    # ── Dates ─────────────────────────────────────────────────
    def _extract_dates(self, data: InvoiceData):
        text = data.raw_text
        m = re.search(r"Expedici[oó]n\s+(\d{4}-\d{2}-\d{2}(?:,?\s*\d{2}:\d{2})?)", text, re.IGNORECASE)
        if m:
            data.fecha_expedicion = m.group(1).strip()
        else:
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", text)
            if dates:
                data.fecha_expedicion = dates[0]

    # ── YOLO Items ────────────────────────────────────────────
    def _extract_yolo_items(self, data: InvoiceData):
        """
        Extrae SOLO los ítems de cemento, tubería presión y tubería sanitaria.
        """
        text = data.raw_text
        all_items = self._parse_all_items(text)
        data.total_items_factura = len(all_items)

        yolo_items = []
        for raw in all_items:
            cat = _get_yolo_category(raw.get("descripcion", ""))
            if cat:
                yolo_items.append(YoloItem(
                    categoria   = cat,
                    descripcion = raw["descripcion"],
                    cantidad    = raw["cantidad"],
                    codigo      = raw["codigo"],
                    valor_bruto = raw["valor_bruto"],
                ))

        data.yolo_items = yolo_items

    def _parse_all_items(self, text: str) -> list[dict]:
        """
        Intenta dos estrategias para extraer todas las filas de la tabla.
        """
        items = []

        # ── Estrategia 1: Buscar el bloque de tabla ───────────
        table_start = re.search(
            r"Item\s+Cantidad\s+Unidad(?:\s+de\s+medida)?\s+C[oó]digo\s+Descripci[oó]n",
            text, re.IGNORECASE
        )
        table_end = re.search(r"Total\s+[Íiíi]tems?:", text, re.IGNORECASE)

        block = text
        if table_start:
            block = text[table_start.end():]
        if table_end:
            block = block[:text[table_start.end() if table_start else 0:].find(table_end.group())]

        # Patrón estricto de línea de ítem Siigo Nube:
        # "1   2   94   332254   Lona de Arena Amarilla   6,722.69   13,445.38"
        strict = re.compile(
            r"^(\d{1,2})\s+"                         # ítem
            r"(\d+(?:[,\.]\d+)?)\s+"                 # cantidad
            r"(\d+|UND|UNI|KG|MTS?|GL|GAL)\s+"      # unidad
            r"([A-Z0-9][A-Z0-9\-]*)\s+"              # código
            r"(.+?)\s+"                              # descripción
            r"([\d\.,]+)\s+"                         # valor unitario
            r"([\d\.,]+)\s*$",                       # valor bruto
            re.IGNORECASE | re.MULTILINE
        )
        for m in strict.finditer(block):
            items.append({
                "item":         m.group(1),
                "cantidad":     m.group(2),
                "unidad":       m.group(3),
                "codigo":       m.group(4),
                "descripcion":  m.group(5).strip(),
                "valor_unit":   m.group(6),
                "valor_bruto":  f"${m.group(7)}",
            })

        # ── Estrategia 2 (flexible): si el strict no capturó nada ──
        if not items:
            for line in block.splitlines():
                line = line.strip()
                m = re.match(
                    r"^(\d{1,2})\s+(\d+(?:[,\.]\d+)?)\s+(\S+)\s+([A-Z0-9][A-Z0-9\-]*)\s+(.+)",
                    line, re.IGNORECASE
                )
                if m:
                    rest  = m.group(5).strip()
                    money = re.findall(r"[\d,\.]+", rest)
                    if len(money) >= 2:
                        valor_bruto = f"${money[-1]}"
                        desc = re.sub(r"\s+[\d,\.]+\s+[\d,\.]+\s*$", "", rest).strip()
                    else:
                        valor_bruto = "—"
                        desc = rest
                    items.append({
                        "item":        m.group(1),
                        "cantidad":    m.group(2),
                        "unidad":      m.group(3),
                        "codigo":      m.group(4),
                        "descripcion": desc,
                        "valor_unit":  "—",
                        "valor_bruto": valor_bruto,
                    })

        return items

    # ── Totals ────────────────────────────────────────────────
    def _extract_totals(self, data: InvoiceData):
        text = data.raw_text
        m = re.search(r"Total\s+a\s+Pagar\s+([\d,\.\s]+)", text, re.IGNORECASE)
        if m:
            data.total_pagar = f"${m.group(1).strip()}"
