from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Iterable, Optional

from core.config_manager import config


@dataclass(frozen=True)
class ModelResolution:
    path: str
    source: str
    exists: bool


def get_project_base_dir() -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
        internal = os.path.join(base_dir, "_internal")
        if os.path.exists(internal):
            return internal
        return base_dir
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _candidate_paths(base_dir: str) -> Iterable[tuple[str, str]]:
    configured = config.get("ai.model_path", "") or os.environ.get("LOGICHECK_MODEL_PATH", "")
    if configured:
        path = configured if os.path.isabs(configured) else os.path.join(base_dir, configured)
        yield os.path.abspath(path), "config"

    defaults = [
        ("models/estacion_bultos_v1.pt", "default"),
        ("training/runs/bultos_cemento/weights/best.pt", "training"),
        ("models/yolo26n.pt", "fallback"),
    ]
    for rel_path, source in defaults:
        yield os.path.abspath(os.path.join(base_dir, rel_path)), source


def resolve_model_path(required: bool = False) -> ModelResolution:
    base_dir = get_project_base_dir()
    first: Optional[ModelResolution] = None
    for path, source in _candidate_paths(base_dir):
        resolution = ModelResolution(path=path, source=source, exists=os.path.exists(path))
        if first is None:
            first = resolution
        if resolution.exists:
            return resolution

    fallback = first or ModelResolution("", "none", False)
    if required:
        raise FileNotFoundError(
            "No se encontro el modelo YOLO. Configure ai.model_path o agregue "
            "models/estacion_bultos_v1.pt."
        )
    return fallback
