"""
inference_optimizer.py
======================
Optimización automática de inferencia para el modelo YOLO26 de LogiCheck.

Estrategia de selección de backend (prioridad descendente):
  1. CUDA  — GPU NVIDIA con CUDA disponible  (más rápido)
  2. OpenVINO — Intel CPU optimizado         (aceleración hardware Intel)
  3. CPU   — Fallback universal              (siempre disponible)

Uso:
    from core.inference_optimizer import InferenceOptimizer
    optimizer = InferenceOptimizer("yolo26n.pt")
    model, device, info = optimizer.load_optimized()
"""

import os
import time
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)
logging.getLogger("ultralytics").setLevel(logging.WARNING)


class InferenceOptimizer:
    """
    Gestor de carga y warmup del modelo YOLO26 con selección automática
    del backend más rápido disponible en el sistema.
    """

    # Resolución de benchmark (menor que producción para medir rápido)
    BENCHMARK_SIZE = (320, 320)
    WARMUP_FRAMES  = 3

    def __init__(self, model_path: str):
        self.model_path   = model_path
        self.model        = None
        self.device       = "cpu"
        self.backend_info = {}

    # ──────────────────────────────────────────────────────────
    #  API pública
    # ──────────────────────────────────────────────────────────
    def load_optimized(self) -> Tuple[object, str, dict]:
        """
        Carga el modelo aplicando el mejor backend disponible.

        Returns:
            (model, device_str, info_dict)
            info_dict incluye: backend, fps_benchmark, warmup_ms, export_path
        """
        backend, device = self._detect_best_backend()
        logger.info(f"[InferenceOptimizer] Backend seleccionado: {backend} | Device: {device}")

        model, extra_info = self._load_with_backend(backend, device)

        # Warmup: ejecutar N inferencias vacías para JIT compilation
        warmup_ms = self._warmup(model, device)

        # Benchmark rápido de FPS
        fps = self._benchmark_fps(model, device)

        info = {
            "backend":      backend,
            "device":       device,
            "fps_benchmark": round(fps, 1),
            "warmup_ms":    round(warmup_ms, 1),
            **extra_info,
        }

        self.model        = model
        self.device       = device
        self.backend_info = info

        logger.info(f"[InferenceOptimizer] Listo — {fps:.1f} FPS estimados, warmup {warmup_ms:.0f}ms")
        return model, device, info

    def get_info_string(self) -> str:
        """Retorna un resumen legible del backend activo."""
        if not self.backend_info:
            return "Modelo no cargado"
        b = self.backend_info
        return (
            f"Backend: {b.get('backend','?')} | "
            f"Device: {b.get('device','?')} | "
            f"{b.get('fps_benchmark',0):.1f} FPS"
        )

    # ──────────────────────────────────────────────────────────
    #  Detección de backend
    # ──────────────────────────────────────────────────────────
    def _detect_best_backend(self) -> Tuple[str, str]:
        """
        Prueba los backends en orden de preferencia y retorna
        (backend_name, device_string).
        """
        # 1. CUDA
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"[InferenceOptimizer] CUDA disponible: {gpu_name}")
                return "cuda", "cuda"
        except ImportError:
            pass

        # 2. OpenVINO (Intel)
        try:
            import openvino  # noqa: F401
            logger.info("[InferenceOptimizer] OpenVINO disponible (Intel CPU optimizado)")
            return "openvino", "cpu"
        except ImportError:
            pass

        # 3. Fallback CPU estándar
        logger.info("[InferenceOptimizer] Usando CPU estándar")
        return "cpu", "cpu"

    # ──────────────────────────────────────────────────────────
    #  Carga por backend
    # ──────────────────────────────────────────────────────────
    def _load_with_backend(self, backend: str, device: str):
        """Carga el modelo con el backend indicado."""
        from ultralytics import YOLO

        extra = {}

        if backend == "cuda":
            model = YOLO(self.model_path)
            model.to("cuda")
            extra["note"] = "GPU NVIDIA — inferencia en VRAM"

        elif backend == "openvino":
            # Intentar exportar/cargar versión OpenVINO
            ov_path = self._get_openvino_model_path()
            if ov_path and os.path.exists(ov_path):
                logger.info(f"[InferenceOptimizer] Cargando modelo OpenVINO desde: {ov_path}")
                model = YOLO(ov_path, task="detect")
                extra["export_path"] = ov_path
                extra["note"] = "OpenVINO INT8 — CPU Intel optimizado"
            else:
                # Exportar y guardar para próximas ejecuciones
                logger.info("[InferenceOptimizer] Exportando modelo a OpenVINO (primera vez)...")
                base_model = YOLO(self.model_path)
                try:
                    ov_path = base_model.export(format="openvino", int8=True)
                    model = YOLO(ov_path, task="detect")
                    extra["export_path"] = str(ov_path)
                    extra["note"] = "OpenVINO INT8 — exportado y cargado"
                    logger.info(f"[InferenceOptimizer] OpenVINO exportado a: {ov_path}")
                except Exception as e:
                    logger.warning(f"[InferenceOptimizer] Fallo exportación OpenVINO: {e}. Fallback a CPU.")
                    model = base_model
                    model.to("cpu")
                    extra["note"] = f"CPU fallback (OpenVINO falló: {e})"

        else:  # cpu
            model = YOLO(self.model_path)
            model.to("cpu")
            extra["note"] = "CPU estándar — compatible universal"

        return model, extra

    def _get_openvino_model_path(self) -> Optional[str]:
        """Busca el directorio OpenVINO exportado previamente junto al .pt."""
        base_dir  = os.path.dirname(self.model_path)
        base_name = os.path.splitext(os.path.basename(self.model_path))[0]
        # Ultralytics exporta en <nombre>_openvino_model/
        ov_dir  = os.path.join(base_dir, f"{base_name}_openvino_model")
        ov_xml  = os.path.join(ov_dir, f"{base_name}.xml")
        return ov_xml if os.path.exists(ov_xml) else None

    # ──────────────────────────────────────────────────────────
    #  Warmup y benchmark
    # ──────────────────────────────────────────────────────────
    def _warmup(self, model, device: str) -> float:
        """
        Ejecuta N inferencias con un frame negro para compilar el grafo JIT.
        Retorna el tiempo total de warmup en ms.
        """
        import numpy as np
        dummy = np.zeros((*self.BENCHMARK_SIZE, 3), dtype=np.uint8)
        t0 = time.perf_counter()
        for _ in range(self.WARMUP_FRAMES):
            try:
                model.predict(dummy, device=device, verbose=False, conf=0.5)
            except Exception:
                break
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(f"[InferenceOptimizer] Warmup: {self.WARMUP_FRAMES} frames en {elapsed:.0f}ms")
        return elapsed

    def _benchmark_fps(self, model, device: str, n_frames: int = 10) -> float:
        """
        Mide los FPS reales del modelo con frames dummy.
        Retorna FPS promedio.
        """
        import numpy as np
        dummy = np.zeros((*self.BENCHMARK_SIZE, 3), dtype=np.uint8)
        timings = []
        for _ in range(n_frames):
            t0 = time.perf_counter()
            try:
                model.predict(dummy, device=device, verbose=False, conf=0.5)
            except Exception:
                break
            timings.append(time.perf_counter() - t0)

        if not timings:
            return 0.0
        avg_s = sum(timings) / len(timings)
        return 1.0 / avg_s if avg_s > 0 else 0.0


# ──────────────────────────────────────────────────────────────
#  Función de conveniencia para carga rápida (uso en splash screen)
# ──────────────────────────────────────────────────────────────
def load_best_model(model_path: str) -> Tuple[object, str, dict]:
    """
    Atajo para cargar el modelo con la mejor optimización disponible.

    Returns:
        (model, device_str, info_dict)
    """
    optimizer = InferenceOptimizer(model_path)
    return optimizer.load_optimized()
