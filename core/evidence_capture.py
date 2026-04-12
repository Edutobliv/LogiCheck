"""
evidence_capture.py
====================
Módulo de captura automática de evidencia fotográfica para LogiCheck.

Cuando se detecta una DISCREPANCIA durante una auditoría, este módulo:
  1. Guarda el frame exacto del momento de la discrepancia como JPEG.
  2. Dibuja sobre el frame anotaciones informativas (bounding boxes, texto).
  3. Genera un thumbnail para previsualización en la UI.
  4. Retorna rutas relativas para almacenar en la BD (campo 'capturas').

Las capturas se guardan en: <proyecto>/captures/<YYYY-MM-DD>/<audit_id>_<timestamp>.jpg
"""

import os
import cv2
import json
import time
import datetime
import numpy as np
from typing import Optional, List, Dict, Tuple


# Directorio raíz del proyecto (un nivel arriba de este archivo)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAPTURES_DIR  = os.path.join(_PROJECT_ROOT, "captures")


# ─── Paleta de colores por categoría ───────────────────────────────────────
CATEGORY_COLORS: Dict[str, Tuple[int, int, int]] = {
    "Cemento":           (0,   200,  80),   # Verde
    "Tubería Presión":   (255, 165,   0),   # Naranja
    "Tubería Sanitaria": (30,  144, 255),   # Azul Dodger
}
DISCREPANCY_COLOR = (0, 0, 220)   # Rojo oscuro para discrepancias


class EvidenceCapture:
    """
    Captura y anota frames de video como evidencia de discrepancias.
    """

    def __init__(self, captures_dir: str = CAPTURES_DIR):
        self.captures_dir = captures_dir
        os.makedirs(captures_dir, exist_ok=True)

    # ──────────────────────────────────────────────────────────
    #  API principal
    # ──────────────────────────────────────────────────────────
    def capture_discrepancy(
        self,
        frame: np.ndarray,
        audit_id: int,
        factura_no: str,
        conteo_ia: Dict[str, int],
        conteo_factura: Dict[str, int],
        discrepancias: Dict[str, int],
        boxes: Optional[List[Tuple]] = None,
    ) -> str:
        """
        Guarda el frame como evidencia con anotaciones de discrepancia.

        Args:
            frame:          Frame BGR de OpenCV.
            audit_id:       ID de la auditoría a la que pertenece.
            factura_no:     Número de factura (para el nombre del archivo).
            conteo_ia:      Conteo detectado por IA.
            conteo_factura: Conteo según factura.
            discrepancias:  Dict {material: diferencia}.
            boxes:          Lista de bounding boxes [(x1,y1,x2,y2,track_id,ui_cat), ...].

        Returns:
            Ruta relativa al archivo guardado (para almacenar en BD).
        """
        annotated = self._annotate_frame(
            frame.copy(), conteo_ia, conteo_factura,
            discrepancias, factura_no, boxes
        )
        path = self._save_frame(annotated, audit_id, factura_no)
        return path

    def capture_frame(
        self,
        frame: np.ndarray,
        label: str = "captura",
        audit_id: int = 0,
    ) -> str:
        """
        Captura un frame simple sin anotaciones de discrepancia.
        Útil para evidencia de despacho conforme.
        """
        clean = frame.copy()
        self._draw_header(clean, label, "#GENERAL")
        return self._save_frame(clean, audit_id, label)

    def generate_thumbnail(self, image_path: str, size: Tuple[int, int] = (320, 180)) -> Optional[str]:
        """
        Genera un thumbnail de una captura existente.

        Returns:
            Ruta del thumbnail generado, o None si falla.
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            thumb = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
            thumb_path = image_path.replace(".jpg", "_thumb.jpg")
            cv2.imwrite(thumb_path, thumb, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return thumb_path
        except Exception as e:
            print(f"[EvidenceCapture] Error generando thumbnail: {e}")
            return None

    def load_captures_for_audit(self, audit_id: int) -> List[str]:
        """
        Lista todas las capturas guardadas para un audit_id.
        """
        results = []
        today = datetime.date.today().isoformat()
        day_dir = os.path.join(self.captures_dir, today)
        if not os.path.exists(day_dir):
            return results
        prefix = f"audit{audit_id}_"
        for f in sorted(os.listdir(day_dir)):
            if f.startswith(prefix) and f.endswith(".jpg") and "_thumb" not in f:
                results.append(os.path.join(day_dir, f))
        return results

    # ──────────────────────────────────────────────────────────
    #  Anotaciones sobre el frame
    # ──────────────────────────────────────────────────────────
    def _annotate_frame(
        self,
        frame: np.ndarray,
        conteo_ia: Dict[str, int],
        conteo_factura: Dict[str, int],
        discrepancias: Dict[str, int],
        factura_no: str,
        boxes: Optional[List[Tuple]],
    ) -> np.ndarray:
        h, w = frame.shape[:2]

        # 1. Dibujar bounding boxes con color por categoría
        if boxes:
            for box in boxes:
                if len(box) >= 6:
                    x1, y1, x2, y2, track_id, ui_cat = box[:6]
                    color = CATEGORY_COLORS.get(ui_cat, (200, 200, 200))
                    # Detectar si este material tiene discrepancia
                    if ui_cat in discrepancias:
                        color = DISCREPANCY_COLOR
                        # Borde doble para discrepancias
                        cv2.rectangle(frame, (x1-2, y1-2), (x2+2, y2+2), (255, 255, 255), 1)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    tid_str = f"ID:{track_id}" if track_id else ""
                    label   = f"{tid_str} {ui_cat}"
                    # Fondo del texto
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                    cv2.rectangle(frame, (x1, max(y1-20, 0)), (x1+tw+4, max(y1, 20)), color, -1)
                    cv2.putText(frame, label, (x1+2, max(y1-5, 15)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        # 2. Panel de información (esquina superior izquierda semitransparente)
        self._draw_info_panel(frame, conteo_ia, conteo_factura, discrepancias, factura_no)

        # 3. Sello de timestamp
        self._draw_header(frame, "DISCREPANCIA DETECTADA", factura_no)

        return frame

    def _draw_info_panel(
        self,
        frame: np.ndarray,
        conteo_ia: Dict[str, int],
        conteo_factura: Dict[str, int],
        discrepancias: Dict[str, int],
        factura_no: str,
    ):
        """Panel semitransparente con resumen de conteos y discrepancias."""
        h, w = frame.shape[:2]
        panel_w = min(340, w - 20)
        panel_h = 30 + (len(CATEGORY_COLORS) + len(discrepancias) + 2) * 22
        panel_h = min(panel_h, h - 60)

        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 40), (10 + panel_w, 40 + panel_h), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)
        cv2.rectangle(frame, (10, 40), (10 + panel_w, 40 + panel_h), (60, 60, 60), 1)

        y = 58
        font = cv2.FONT_HERSHEY_SIMPLEX

        cv2.putText(frame, f"FACTURA: {factura_no}", (18, y), font, 0.45, (200, 200, 200), 1)
        y += 20

        # Tabla IA vs Factura
        cv2.putText(frame, "MATERIAL            IA   FAC  DIFF", (18, y),
                    font, 0.38, (150, 150, 150), 1)
        y += 18

        all_mats = set(list(conteo_ia.keys()) + list(conteo_factura.keys()))
        for mat in sorted(all_mats):
            ia_v  = conteo_ia.get(mat, 0)
            fa_v  = conteo_factura.get(mat, 0)
            diff  = ia_v - fa_v
            color = (0, 200, 80) if diff == 0 else (0, 80, 220)
            short = mat[:16].ljust(16)
            line  = f"{short}  {str(ia_v).rjust(3)}  {str(fa_v).rjust(3)}  {('+' if diff>0 else '')+str(diff).rjust(4)}"
            cv2.putText(frame, line, (18, y), font, 0.38, color, 1)
            y += 18

    def _draw_header(self, frame: np.ndarray, label: str, factura_no: str):
        """Banda superior con timestamp y etiqueta de estado."""
        h, w = frame.shape[:2]
        ts  = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        banner_text = f"LogiCheck  |  {label}  |  Fact:{factura_no}  |  {ts}"

        cv2.rectangle(frame, (0, 0), (w, 32), (10, 10, 10), -1)
        cv2.putText(frame, banner_text, (8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

    # ──────────────────────────────────────────────────────────
    #  Guardado
    # ──────────────────────────────────────────────────────────
    def _save_frame(self, frame: np.ndarray, audit_id: int, label: str) -> str:
        """Guarda el frame en disco y retorna la ruta relativa al proyecto."""
        today   = datetime.date.today().isoformat()
        day_dir = os.path.join(self.captures_dir, today)
        os.makedirs(day_dir, exist_ok=True)

        ts        = datetime.datetime.now().strftime("%H%M%S_%f")
        safe_label = "".join(c if c.isalnum() or c in "._-" else "_" for c in str(label))
        filename  = f"audit{audit_id}_{safe_label}_{ts}.jpg"
        full_path = os.path.join(day_dir, filename)

        cv2.imwrite(full_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 92])

        # Ruta relativa desde la raíz del proyecto
        rel_path = os.path.relpath(full_path, _PROJECT_ROOT)
        print(f"[EvidenceCapture] Captura guardada: {rel_path}")
        return rel_path


# ──────────────────────────────────────────────────────────────────────────
#  Instancia global (singleton de conveniencia)
# ──────────────────────────────────────────────────────────────────────────
_default_capture = None


def get_evidence_capture() -> EvidenceCapture:
    """Retorna la instancia global reutilizable del capturador."""
    global _default_capture
    if _default_capture is None:
        _default_capture = EvidenceCapture()
    return _default_capture
