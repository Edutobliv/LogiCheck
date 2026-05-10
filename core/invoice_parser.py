"""
invoice_parser.py
-----------------
Módulo para leer facturas electrónicas PDF de Ferretería Durán (Siigo Nube)
y extraer ÚNICAMENTE los productos que serán detectados por YOLO:

  - Cemento (ej: "Bulto de cemento Gris", "Cemento Argos")
  - Tubería de Presión (ej: "Tubo Presión", "Tubería PVC Presión")
  - Tubería Sanitaria (ej: "Tubo Sanitario", "Tubería PVC Sanitaria")

Mejora v2: Clasificador híbrido con Fuzzy Matching.
Si la búsqueda exacta de substring no encuentra coincidencia, se aplica
similitud difusa (difflib.SequenceMatcher) para tolerar:
  - Errores de OCR ("cernento" vs "cemento")
  - Ausencia de tildes ("tuberia presion" vs "tubería presión")
  - Abreviaturas del proveedor ("TB PVC PRES" vs "tubo pvc presion")
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Optional
from decimal import Decimal, InvalidOperation

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


# ─────────────────────────────────────────────────────────────
# Utilidades de normalización para fuzzy matching
# ─────────────────────────────────────────────────────────────
def _normalize(text: str) -> str:
    """
    Normaliza texto para comparación fuzzy:
    - Convierte a minúsculas
    - Elimina diacríticos (tildes, ñ → n, etc.)
    - Colapsa espacios múltiples
    """
    nfkd = unicodedata.normalize('NFKD', text.lower())
    without_diacritics = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', without_diacritics).strip()


# Keywords normalizadas para fuzzy matching (pre-computadas al importar)
_NORMALIZED_KEYWORDS: dict[str, list[str]] = {
    cat: [_normalize(kw) for kw in kws]
    for cat, kws in YOLO_CATEGORIES.items()
}

# Umbral de similitud fuzzy — calibrado para facturas Siigo Nube
# 0.72 = tolera ~3 caracteres erróneos en palabras de 10 letras
FUZZY_THRESHOLD = 0.72


def _parse_quantity(value: str) -> int:
    """
    Convierte cantidades de factura a entero tolerando formatos comunes:
    10, 10.0, 10,0, 1.000 y 1,000.
    """
    text = str(value).strip().replace(" ", "")
    if not text:
        return 0

    if "," in text and "." in text:
        # El ultimo separador suele ser el decimal.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        left, right = text.rsplit(",", 1)
        text = left + "." + right if len(right) <= 2 else text.replace(",", "")
    elif "." in text:
        left, right = text.rsplit(".", 1)
        if len(right) == 3 and left.isdigit():
            text = text.replace(".", "")

    try:
        qty = Decimal(text)
    except InvalidOperation:
        return 0
    return int(qty.to_integral_value())


def _get_yolo_category(descripcion: str) -> Optional[str]:
    """
    Retorna la categoría YOLO del ítem si coincide, o None si no aplica.

    Estrategia híbrida:
      1. Coincidencia exacta de substring (rápido, sin falsos positivos).
      2. Fuzzy matching por ventana deslizante sobre la descripción
         normalizada (tolerante a OCR y variaciones tipográficas).

    Args:
        descripcion: Texto de la descripción del producto en la factura.

    Returns:
        Nombre de la categoría YOLO, o None si no aplica.
    """
    desc_lower = descripcion.lower()
    desc_norm  = _normalize(descripcion)

    # ── Fase 1: Coincidencia exacta de substring ─────────────
    for category, keywords in YOLO_CATEGORIES.items():
        for kw in keywords:
            if kw in desc_lower:
                return category

    # ── Fase 2: Fuzzy matching con keywords normalizadas ─────
    # Para cada keyword, extraemos una ventana del mismo tamaño sobre
    # la descripción normalizada y calculamos similitud.
    words = desc_norm.split()
    for category, norm_keywords in _NORMALIZED_KEYWORDS.items():
        for kw_norm in norm_keywords:
            kw_words = kw_norm.split()
            kw_len   = len(kw_words)

            # Ventana deslizante sobre las palabras de la descripción
            for i in range(len(words) - kw_len + 1):
                window = ' '.join(words[i:i + kw_len])
                ratio  = SequenceMatcher(None, window, kw_norm).ratio()
                if ratio >= FUZZY_THRESHOLD:
                    return category

            # También comparar la descripción completa vs keyword
            # (útil cuando la keyword es más corta que la descripción)
            if len(kw_norm) >= 4:  # Solo para keywords significativas
                ratio = SequenceMatcher(None, desc_norm, kw_norm).ratio()
                if ratio >= FUZZY_THRESHOLD + 0.05:  # umbral más alto para desc completa
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
                    total += _parse_quantity(it.cantidad)
                except Exception:
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
