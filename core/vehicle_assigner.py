# core/vehicle_assigner.py
# ============================================================
#  LogiCheck — Motor de Asignación Vehicular Inteligente
#
#  1. Detecta tipo y medida de tubería desde la descripción
#     de la factura (sanitaria/presión + diámetro en pulgadas).
#  2. Calcula peso y volumen total del despacho.
#  3. Recomienda el vehículo óptimo de la flota.
#  4. Evalúa si dividir en múltiples viajes es más eficiente.
# ============================================================

import re
import math
from dataclasses import dataclass, field
from typing import Optional


# ════════════════════════════════════════════════════════════
#  CATÁLOGO DE MATERIALES — Datos técnicos estándar Colombia
#  Fuentes: Pavco Wavin, Gerfor, proveedores ferreteros
# ════════════════════════════════════════════════════════════

# Peso de un bulto de cemento estándar en Colombia
PESO_BULTO_CEMENTO_KG = 50.0
VOLUMEN_BULTO_CEMENTO_M3 = 0.035  # ~35 litros ≈ 0.035 m³

# ── Tubería Sanitaria PVC (tramo estándar 6 metros) ──────
#    diámetro_pulgadas → {peso_kg_6m, diámetro_ext_mm, espesor_mm}
TUBERIA_SANITARIA = {
    "1 1/2": {"peso_kg_6m": 1.80, "diam_ext_mm": 48.0,  "espesor_mm": 1.8, "nombre": 'Tubo Sanitario PVC 1 1/2"'},
    "2":     {"peso_kg_6m": 2.80, "diam_ext_mm": 60.0,  "espesor_mm": 1.8, "nombre": 'Tubo Sanitario PVC 2"'},
    "3":     {"peso_kg_6m": 5.20, "diam_ext_mm": 88.0,  "espesor_mm": 2.0, "nombre": 'Tubo Sanitario PVC 3"'},
    "4":     {"peso_kg_6m": 11.7, "diam_ext_mm": 114.0, "espesor_mm": 2.4, "nombre": 'Tubo Sanitario PVC 4"'},
}

# ── Tubería Presión PVC (tramo estándar 6 metros) ────────
#    diámetro_pulgadas → {peso_kg_6m, diámetro_ext_mm, espesor_mm}
TUBERIA_PRESION = {
    "1/2":   {"peso_kg_6m": 0.95, "diam_ext_mm": 21.0,  "espesor_mm": 1.5, "nombre": 'Tubo Presión PVC 1/2"'},
    "3/4":   {"peso_kg_6m": 1.35, "diam_ext_mm": 26.7,  "espesor_mm": 1.6, "nombre": 'Tubo Presión PVC 3/4"'},
    "1":     {"peso_kg_6m": 2.10, "diam_ext_mm": 33.4,  "espesor_mm": 1.8, "nombre": 'Tubo Presión PVC 1"'},
    "1 1/4": {"peso_kg_6m": 3.00, "diam_ext_mm": 42.2,  "espesor_mm": 2.0, "nombre": 'Tubo Presión PVC 1 1/4"'},
    "1 1/2": {"peso_kg_6m": 3.80, "diam_ext_mm": 48.3,  "espesor_mm": 2.2, "nombre": 'Tubo Presión PVC 1 1/2"'},
}


def _calc_pipe_volume_m3(diam_ext_mm: float, length_m: float) -> float:
    """
    Calcula el volumen cilíndrico que ocupa un tubo en el espacio de carga.
    Usa el diámetro exterior como radio del cilindro envolvente.
    V = π * r² * L
    """
    r_m = (diam_ext_mm / 2.0) / 1000.0  # mm a metros
    return math.pi * r_m ** 2 * length_m


# ════════════════════════════════════════════════════════════
#  CATÁLOGO DE VEHÍCULOS — Flota estándar ferreterías Colombia
# ════════════════════════════════════════════════════════════

VEHICULOS_DEFAULT = [
    {
        "codigo": "V01", "tipo": "Motocarro",
        "placa": "---", "capacidad_max_peso_kg": 480.0,
        "capacidad_max_vol_m3": 2.0, "costo_viaje": 1.0,
        "descripcion": "Reparto urbano, zonas estrechas",
    },
    {
        "codigo": "V02", "tipo": "Camioneta / NHR",
        "placa": "---", "capacidad_max_peso_kg": 2500.0,
        "capacidad_max_vol_m3": 10.0, "costo_viaje": 2.5,
        "descripcion": "Entregas urbanas rápidas",
    },
    {
        "codigo": "V03", "tipo": "Camión Turbo (NPR)",
        "placa": "---", "capacidad_max_peso_kg": 4500.0,
        "capacidad_max_vol_m3": 18.0, "costo_viaje": 4.0,
        "descripcion": "Distribución zonal, ferreterías",
    },
    {
        "codigo": "V04", "tipo": "Camión Sencillo (C2)",
        "placa": "---", "capacidad_max_peso_kg": 8500.0,
        "capacidad_max_vol_m3": 35.0, "costo_viaje": 7.0,
        "descripcion": "Transporte media distancia",
    },
    {
        "codigo": "V05", "tipo": "Dobletroque (C3)",
        "placa": "---", "capacidad_max_peso_kg": 17000.0,
        "capacidad_max_vol_m3": 48.0, "costo_viaje": 12.0,
        "descripcion": "Cargas pesadas, inter-municipal",
    },
]


# ════════════════════════════════════════════════════════════
#  DETECTOR DE TAMAÑO DE TUBERÍA EN DESCRIPCIONES
# ════════════════════════════════════════════════════════════

# Patrones ordenados de mayor a menor para evitar que "1/2" matchee antes de "1 1/2"
_PIPE_SIZES_ORDERED = [
    "1 1/2", "1 1/4",
    "3/4", "1/2",
    "4", "3", "2", "1",
]

# Regex para detectar el largo del tubo si se especifica (ej. "3mt", "3 mts", "x 3m", "de 3 metros")
_LENGTH_PATTERN = re.compile(
    r'(?:x\s*|de\s+)?'                # optional "x " or "de "
    r'(\d+(?:[.,]\d+)?)\s*'           # number (integer or decimal)
    r'(?:mt(?:s|r(?:os?)?)?|m(?:etros?)?)\b',  # unit: mt, mts, mtr, mtrs, m, metro, metros
    re.IGNORECASE
)

# Regex para detectar cantidad antes de "tubo(s)" (ej. "3 tubos de...", "5 tuberías...")
_QTY_INLINE_PATTERN = re.compile(
    r'(\d+)\s*(?:tubos?|tuberías?|unid(?:ades?)?)\b',
    re.IGNORECASE
)


def _normalize_desc(text: str) -> str:
    """Normaliza la descripción para facilitar la detección."""
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', text.lower())
    clean = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Normalizar comillas y caracteres especiales
    clean = clean.replace('"', '"').replace('"', '"').replace("''", '"')
    clean = clean.replace('″', '"').replace('´´', '"').replace("``", '"')
    return clean


def detect_pipe_size(descripcion: str) -> Optional[str]:
    """
    Detecta el diámetro de la tubería en una descripción de factura.
    
    Reconoce formatos como:
    - 'Tubo Sanitario 4"'
    - 'Tubo Presión 1 1/2 X 6MT'
    - 'TB PVC PRES 3/4'
    - 'TUBO SANITARIO DE 2'
    - 'Tubería PVC 1.5"' → se mapea a "1 1/2"
    
    Returns:
        El tamaño detectado como string (ej. "4", "1 1/2", "3/4") o None.
    """
    desc = _normalize_desc(descripcion)
    
    # Mapeo de decimales → fracciones
    decimal_map = {
        "0.5": "1/2", "0,5": "1/2",
        "1.5": "1 1/2", "1,5": "1 1/2",
        "1.25": "1 1/4", "1,25": "1 1/4",
        "0.75": "3/4", "0,75": "3/4",
    }
    
    # Primero intentar detectar formatos decimales (ej. 1.5")
    for dec_str, frac_str in decimal_map.items():
        if dec_str in desc:
            return frac_str
    
    # Buscar por tamaños conocidos (del mayor al menor para priorizar correctamente)
    for size in _PIPE_SIZES_ORDERED:
        # Pattern: el tamaño puede estar seguido de ", espacio, x, etc.
        # Pero no debe ser parte de otro número
        escaped = re.escape(size)
        pattern = rf'(?<!\d)(?<!\d\s){escaped}(?:\s*"|\s*pulg|\s*x|\s*$|\s+(?:mt|m|de|pvc|livian|pesad)|\s*,)'
        if re.search(pattern, desc):
            return size
    
    # Último intento: buscar solo el número en contexto de tubo
    if any(kw in desc for kw in ["tubo", "tuberia", "pvc", "sanitari", "presion", "hidraulic"]):
        for size in _PIPE_SIZES_ORDERED:
            if size in desc:
                return size
    
    return None


def detect_pipe_length(descripcion: str) -> float:
    """
    Detecta el largo del tubo en metros desde la descripción.
    Si no se menciona, retorna 6.0 (estándar Colombia).
    
    Reconoce: "3mt", "3 mts", "x 3m", "de 3 metros", "3MTS"
    """
    desc = _normalize_desc(descripcion)
    m = _LENGTH_PATTERN.search(desc)
    if m:
        val = m.group(1).replace(",", ".")
        try:
            length = float(val)
            if 0.5 <= length <= 12.0:  # Rango razonable
                return length
        except ValueError:
            pass
    return 6.0  # Estándar


@dataclass
class DespachoItem:
    """Representa un ítem del despacho con sus propiedades físicas calculadas."""
    categoria: str          # "Cemento", "Tubería Presión", "Tubería Sanitaria"
    descripcion: str        # Descripción original de la factura
    cantidad: int           # Unidades del ítem
    medida: Optional[str]   # Diámetro en pulgadas (ej. "4", "1/2") o None
    largo_m: float          # Largo del tubo en metros
    peso_unitario_kg: float # Peso por unidad
    vol_unitario_m3: float  # Volumen por unidad
    peso_total_kg: float    # peso_unitario * cantidad
    vol_total_m3: float     # vol_unitario * cantidad
    confianza: str          # "alta", "media", "baja" — indica si la medida fue detectada
    medida_sugerida: Optional[str] = None  # Si confianza es baja, sugerencia


@dataclass
class OpcionVehiculo:
    """Opción de vehículo o combinación de viajes para un despacho."""
    vehiculo_tipo: str
    vehiculo_placa: str
    vehiculo_codigo: str
    capacidad_peso_kg: float
    capacidad_vol_m3: float
    num_viajes: int
    uso_peso_pct: float     # % de uso de la capacidad de peso
    uso_vol_pct: float      # % de uso de la capacidad de volumen
    uso_max_pct: float      # max(uso_peso, uso_vol) 
    costo_relativo: float   # costo_viaje * num_viajes (para comparar)
    viable: bool            # True si la carga cabe en N viajes
    descripcion: str        # Texto descriptivo (ej. "2 viajes de Motocarro")
    recomendado: bool = False


@dataclass
class ResultadoAsignacion:
    """Resultado completo del análisis de asignación vehicular."""
    items: list[DespachoItem] = field(default_factory=list)
    peso_total_kg: float = 0.0
    vol_total_m3: float = 0.0
    opciones: list[OpcionVehiculo] = field(default_factory=list)
    mejor_opcion: Optional[OpcionVehiculo] = None
    items_ambiguos: list[DespachoItem] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)


# ════════════════════════════════════════════════════════════
#  MOTOR PRINCIPAL
# ════════════════════════════════════════════════════════════

class VehicleAssigner:
    """
    Motor de asignación vehicular inteligente.
    
    Flujo:
    1. Recibe los YoloItems de la factura.
    2. Para cada uno, detecta medida y largo.
    3. Calcula peso y volumen totales.
    4. Evalúa la flota disponible y genera opciones.
    5. Recomienda la opción óptima (costo-eficiente).
    """
    
    def __init__(self, vehiculos: list[dict] = None):
        """
        Args:
            vehiculos: Lista de dicts con datos de vehículos desde la BD.
                       Si None, usa los defaults.
        """
        self._vehiculos = vehiculos or VEHICULOS_DEFAULT
    
    def analizar_despacho(self, yolo_items: list) -> ResultadoAsignacion:
        """
        Analiza los ítems YOLO de la factura y genera un resultado
        completo de asignación vehicular.
        
        Args:
            yolo_items: Lista de YoloItem del invoice_parser.
            
        Returns:
            ResultadoAsignacion con todos los datos calculados.
        """
        resultado = ResultadoAsignacion()
        
        for item in yolo_items:
            despacho_item = self._procesar_item(item)
            resultado.items.append(despacho_item)
            resultado.peso_total_kg += despacho_item.peso_total_kg
            resultado.vol_total_m3 += despacho_item.vol_total_m3
            
            if despacho_item.confianza == "baja":
                resultado.items_ambiguos.append(despacho_item)
        
        # Generar alertas
        if resultado.items_ambiguos:
            n = len(resultado.items_ambiguos)
            resultado.alertas.append(
                f"⚠️ {n} ítem(s) con medida no identificada. "
                "Por favor verifique manualmente."
            )
        
        # Evaluar opciones de vehículo
        resultado.opciones = self._evaluar_opciones(
            resultado.peso_total_kg, resultado.vol_total_m3
        )
        
        # Seleccionar la mejor opción
        resultado.mejor_opcion = self._seleccionar_mejor(resultado.opciones)
        
        return resultado
    
    def recalcular_con_correcciones(
        self, resultado: ResultadoAsignacion,
        correcciones: dict[int, str]
    ) -> ResultadoAsignacion:
        """
        Recalcula el despacho después de que el usuario corrige
        medidas ambiguas.
        
        Args:
            resultado: El resultado anterior.
            correcciones: dict {indice_item: nueva_medida}
        """
        nuevo = ResultadoAsignacion()
        
        for i, item in enumerate(resultado.items):
            if i in correcciones:
                nueva_medida = correcciones[i]
                # Recalcular este ítem con la medida corregida
                nuevo_item = self._calcular_item_con_medida(
                    item.categoria, item.descripcion, item.cantidad,
                    nueva_medida, item.largo_m
                )
                nuevo_item.confianza = "alta"
                nuevo.items.append(nuevo_item)
            else:
                nuevo.items.append(item)
            
            nuevo.peso_total_kg += nuevo.items[-1].peso_total_kg
            nuevo.vol_total_m3 += nuevo.items[-1].vol_total_m3
        
        # Re-evaluar opciones
        nuevo.opciones = self._evaluar_opciones(
            nuevo.peso_total_kg, nuevo.vol_total_m3
        )
        nuevo.mejor_opcion = self._seleccionar_mejor(nuevo.opciones)
        
        return nuevo
    
    def _procesar_item(self, yolo_item) -> DespachoItem:
        """Procesa un YoloItem y retorna un DespachoItem con cálculos."""
        categoria = yolo_item.categoria
        descripcion = yolo_item.descripcion
        try:
            cantidad = int(yolo_item.cantidad)
        except (ValueError, AttributeError):
            cantidad = 1
        
        if categoria == "Cemento":
            return DespachoItem(
                categoria=categoria,
                descripcion=descripcion,
                cantidad=cantidad,
                medida=None,
                largo_m=0,
                peso_unitario_kg=PESO_BULTO_CEMENTO_KG,
                vol_unitario_m3=VOLUMEN_BULTO_CEMENTO_M3,
                peso_total_kg=PESO_BULTO_CEMENTO_KG * cantidad,
                vol_total_m3=VOLUMEN_BULTO_CEMENTO_M3 * cantidad,
                confianza="alta",
            )
        
        # ── Tubería ──
        medida = detect_pipe_size(descripcion)
        largo = detect_pipe_length(descripcion)
        confianza = "alta"
        medida_sugerida = None
        
        catalogo = (TUBERIA_SANITARIA if categoria == "Tubería Sanitaria"
                    else TUBERIA_PRESION)
        
        if medida and medida in catalogo:
            # Medida detectada y válida
            datos = catalogo[medida]
            peso_6m = datos["peso_kg_6m"]
            diam_ext = datos["diam_ext_mm"]
            
            # Ajustar peso proporcionalmente si el largo ≠ 6m
            peso_unit = peso_6m * (largo / 6.0)
            vol_unit = _calc_pipe_volume_m3(diam_ext, largo)
            confianza = "alta"
            
        elif medida and medida not in catalogo:
            # Medida detectada pero no está en el catálogo de esta categoría
            # Intentar en la otra categoría
            otro_catalogo = (TUBERIA_PRESION if categoria == "Tubería Sanitaria"
                            else TUBERIA_SANITARIA)
            if medida in otro_catalogo:
                datos = otro_catalogo[medida]
                peso_unit = datos["peso_kg_6m"] * (largo / 6.0)
                vol_unit = _calc_pipe_volume_m3(datos["diam_ext_mm"], largo)
                confianza = "media"
                medida_sugerida = medida
            else:
                # Medida detectada pero no reconocida
                peso_unit = 2.0 * (largo / 6.0)  # Estimación conservadora
                vol_unit = _calc_pipe_volume_m3(50.0, largo)  # ~2" promedio
                confianza = "baja"
                medida_sugerida = "2"  # Sugerir la más común
        else:
            # No se detectó medida — ambiguo
            peso_unit = 3.0 * (largo / 6.0)  # Estimación media
            vol_unit = _calc_pipe_volume_m3(60.0, largo)
            confianza = "baja"
            medida_sugerida = "2" if categoria == "Tubería Sanitaria" else "1/2"
        
        return DespachoItem(
            categoria=categoria,
            descripcion=descripcion,
            cantidad=cantidad,
            medida=medida,
            largo_m=largo,
            peso_unitario_kg=round(peso_unit, 3),
            vol_unitario_m3=round(vol_unit, 6),
            peso_total_kg=round(peso_unit * cantidad, 2),
            vol_total_m3=round(vol_unit * cantidad, 6),
            confianza=confianza,
            medida_sugerida=medida_sugerida,
        )
    
    def _calcular_item_con_medida(
        self, categoria: str, descripcion: str,
        cantidad: int, medida: str, largo_m: float
    ) -> DespachoItem:
        """Calcula un DespachoItem con una medida específica (corrección manual)."""
        catalogo = (TUBERIA_SANITARIA if categoria == "Tubería Sanitaria"
                    else TUBERIA_PRESION)
        
        if medida in catalogo:
            datos = catalogo[medida]
            peso_unit = datos["peso_kg_6m"] * (largo_m / 6.0)
            vol_unit = _calc_pipe_volume_m3(datos["diam_ext_mm"], largo_m)
        else:
            peso_unit = 2.0 * (largo_m / 6.0)
            vol_unit = _calc_pipe_volume_m3(50.0, largo_m)
        
        return DespachoItem(
            categoria=categoria, descripcion=descripcion,
            cantidad=cantidad, medida=medida, largo_m=largo_m,
            peso_unitario_kg=round(peso_unit, 3),
            vol_unitario_m3=round(vol_unit, 6),
            peso_total_kg=round(peso_unit * cantidad, 2),
            vol_total_m3=round(vol_unit * cantidad, 6),
            confianza="alta",
        )
    
    def _evaluar_opciones(
        self, peso_total: float, vol_total: float
    ) -> list[OpcionVehiculo]:
        """
        Evalúa cada vehículo de la flota y genera opciones,
        incluyendo múltiples viajes si es necesario.
        """
        opciones = []
        
        for v in self._vehiculos:
            cap_peso = v.get("capacidad_max_peso_kg", 0)
            cap_vol = v.get("capacidad_max_vol_m3", 0)
            costo = v.get("costo_viaje", 1.0)
            
            if cap_peso <= 0 or cap_vol <= 0:
                continue
            
            # ── Viaje único ──
            uso_peso = (peso_total / cap_peso) * 100 if cap_peso > 0 else 999
            uso_vol = (vol_total / cap_vol) * 100 if cap_vol > 0 else 999
            uso_max = max(uso_peso, uso_vol)
            
            if uso_max <= 100:
                opciones.append(OpcionVehiculo(
                    vehiculo_tipo=v["tipo"],
                    vehiculo_placa=v.get("placa", "---"),
                    vehiculo_codigo=v.get("codigo", ""),
                    capacidad_peso_kg=cap_peso,
                    capacidad_vol_m3=cap_vol,
                    num_viajes=1,
                    uso_peso_pct=round(uso_peso, 1),
                    uso_vol_pct=round(uso_vol, 1),
                    uso_max_pct=round(uso_max, 1),
                    costo_relativo=costo,
                    viable=True,
                    descripcion=f"1 viaje de {v['tipo']}",
                ))
            
            # ── Múltiples viajes (hasta 5) ──
            for n_viajes in range(2, 6):
                peso_por_viaje = peso_total / n_viajes
                vol_por_viaje = vol_total / n_viajes
                
                uso_peso_v = (peso_por_viaje / cap_peso) * 100
                uso_vol_v = (vol_por_viaje / cap_vol) * 100
                uso_max_v = max(uso_peso_v, uso_vol_v)
                
                if uso_max_v <= 100:
                    opciones.append(OpcionVehiculo(
                        vehiculo_tipo=v["tipo"],
                        vehiculo_placa=v.get("placa", "---"),
                        vehiculo_codigo=v.get("codigo", ""),
                        capacidad_peso_kg=cap_peso,
                        capacidad_vol_m3=cap_vol,
                        num_viajes=n_viajes,
                        uso_peso_pct=round(uso_peso_v, 1),
                        uso_vol_pct=round(uso_vol_v, 1),
                        uso_max_pct=round(uso_max_v, 1),
                        costo_relativo=round(costo * n_viajes, 2),
                        viable=True,
                        descripcion=f"{n_viajes} viajes de {v['tipo']}",
                    ))
                    break  # Solo la primera opción multi-viaje viable
        
        # Ordenar por costo relativo, luego por uso para desempatar
        opciones.sort(key=lambda o: (o.costo_relativo, -o.uso_max_pct))
        
        return opciones
    
    def _seleccionar_mejor(self, opciones: list[OpcionVehiculo]) -> Optional[OpcionVehiculo]:
        """
        Selecciona la opción más eficiente:
        - Prefiere viaje único sobre múltiples.
        - Entre costo igual, prefiere mayor uso de capacidad (menos desperdicio).
        - Marca la mejor como recomendada.
        """
        viables = [o for o in opciones if o.viable]
        if not viables:
            return None
        
        # Agrupar: viaje único vs multi-viaje
        unicos = [o for o in viables if o.num_viajes == 1]
        multiples = [o for o in viables if o.num_viajes > 1]
        
        mejor = None
        
        if unicos:
            # El de menor costo con mayor aprovechamiento
            mejor = min(unicos, key=lambda o: (o.costo_relativo, -o.uso_max_pct))
        
        # Verificar si algún multi-viaje es más barato
        if multiples:
            mejor_multi = min(multiples, key=lambda o: o.costo_relativo)
            if mejor is None or mejor_multi.costo_relativo < mejor.costo_relativo:
                mejor = mejor_multi
        
        if mejor:
            mejor.recomendado = True
        
        return mejor


def get_medidas_disponibles(categoria: str) -> list[str]:
    """
    Retorna las medidas disponibles para una categoría.
    Útil para el dropdown de corrección manual en la UI.
    """
    if categoria == "Tubería Sanitaria":
        return list(TUBERIA_SANITARIA.keys())
    elif categoria == "Tubería Presión":
        return list(TUBERIA_PRESION.keys())
    return []


def get_info_material(categoria: str, medida: str) -> dict:
    """Retorna la info técnica de un material específico."""
    if categoria == "Tubería Sanitaria" and medida in TUBERIA_SANITARIA:
        return TUBERIA_SANITARIA[medida]
    elif categoria == "Tubería Presión" and medida in TUBERIA_PRESION:
        return TUBERIA_PRESION[medida]
    elif categoria == "Cemento":
        return {
            "peso_kg_6m": PESO_BULTO_CEMENTO_KG,
            "nombre": "Bulto de Cemento 50Kg",
        }
    return {}
