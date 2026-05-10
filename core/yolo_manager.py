import cv2
import time
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
import os
import sys

from core.counting_engine import CountingEngine, DetectionBox, map_model_class_to_category


def _redact_rtsp_url(url: str) -> str:
    if not url or "://" not in url:
        return url
    try:
        from urllib.parse import urlsplit, urlunsplit
        parsed = urlsplit(url)
        netloc = parsed.netloc
        if "@" in netloc:
            credentials, host = netloc.rsplit("@", 1)
            user = credentials.split(":", 1)[0]
            netloc = f"{user}:***@{host}" if user else f"***@{host}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    except Exception:
        return url.replace(url.split("@", 1)[0], "rtsp://***") if "@" in url else url

# Nota: La integración P2P directa fue removida ya que OpenCV requiere RTSP.
# El SDK de Dahua no entrega RTSP nativamente sobre P2P sin transcodificación.


class YoloAnalyzerWorker(QThread):
    progress_updated = Signal(int)
    thumbnail_ready  = Signal(int, QImage)
    # Emits: final_counts, count_history {frame_idx: counts}, tracking_data {frame_idx: [boxes]}, fps, crossing_frames [idx]
    finished_analysis = Signal(object, object, object, float, object)
    error_occurred = Signal(str)

    def __init__(self, video_path, model_path, line_pos=0.60,
                 preloaded_model=None, preloaded_device=None):
        super().__init__()
        self.video_path = video_path
        self.model_path = model_path
        self.line_pos   = line_pos  # fraction of height for counting line
        self._is_running = True
        self.tracking_data = {}   # {frame_idx: [(x1,y1,x2,y2,track_id,label), ...]}

        # ── Usar modelo precargado si está disponible ──────────
        if preloaded_model is not None:
            self.model  = preloaded_model
            self.device = preloaded_device or "cpu"
            print(f"[YOLO] Reutilizando modelo precargado en {self.device}. Clases: {self.model.names}")
            self.model_loaded = True
        else:
            # Carga normal (fallback si el splash no precargó el modelo)
            try:
                from ultralytics import YOLO
                import torch
                self.model  = YOLO(model_path)
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                self.model.to(self.device)
                print(f"[YOLO] Modelo cargado en {self.device}. Clases: {self.model.names}")
                self.model_loaded = True
            except Exception as e:
                self.model_loaded = False
                self.error_msg = str(e)


    def run(self):
        if not self.model_loaded:
            self.error_occurred.emit(f"Error cargando modelo: {self.error_msg}")
            return

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.error_occurred.emit("No se pudo abrir el video.")
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        frame_idx = 0
        self.tracking_data.clear()
        
        # Crossing detection state
        self.crossing_frames = []
        counting_engine = CountingEngine()
        count_history = {}
        self.cumulative_counts = dict(counting_engine.counts)

        while self._is_running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1

            results = self.model.track(frame, persist=True, device=self.device, verbose=False, conf=0.15, iou=0.5)
            result = results[0]
            
            frame_boxes = []

            if result.boxes is not None and len(result.boxes) > 0:
                boxes_xyxy = result.boxes.xyxy.cpu().numpy()
                clss       = result.boxes.cls.int().cpu().tolist()
                track_ids  = result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None] * len(boxes_xyxy)
                names      = self.model.names

                for box, track_id, cls_id in zip(boxes_xyxy, track_ids, clss):
                    x1, y1, x2, y2 = box
                    cls_name = names[cls_id]

                    ui_cat = map_model_class_to_category(cls_name)
                    
                    if ui_cat:
                        frame_boxes.append((int(x1), int(y1), int(x2), int(y2), track_id, ui_cat))

            line_y = int(height * self.line_pos)
            events = counting_engine.process(
                [
                    DetectionBox(x1, y1, x2, y2, track_id, ui_cat)
                    for x1, y1, x2, y2, track_id, ui_cat in frame_boxes
                ],
                frame_idx,
                line_y,
            )
            if events:
                self.crossing_frames.extend(event.frame_idx for event in events)
            self.cumulative_counts = dict(counting_engine.counts)
            count_history[frame_idx] = dict(self.cumulative_counts)

            self.tracking_data[frame_idx] = frame_boxes

            if frame_idx % 60 == 0:
                print(f"[Analyzer] Frame {frame_idx}: {len(frame_boxes)} bultos filtrados")
                if total_frames > 0:
                    progress = min(int((frame_idx / total_frames) * 100), 100)
                    self.progress_updated.emit(progress)
            
            # --- Emit thumbnail every 1% ---
            if total_frames > 0 and (frame_idx % max(1, total_frames // 100) == 0):
                # Resize for thumbnail
                small_frame = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
                rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                h2, w2, ch = rgb.shape
                q_img = QImage(rgb.data, w2, h2, ch * w2, QImage.Format_RGB888)
                self.thumbnail_ready.emit(frame_idx, q_img.copy())

        cap.release()

        if self._is_running:
            final_data = dict(self.tracking_data)
            print(f"[Analyzer] Finalizado. Frames procesados: {len(final_data)}. Emitiendo...")
            self.progress_updated.emit(100)
            self.finished_analysis.emit(self.cumulative_counts, count_history, final_data, fps, self.crossing_frames)

    def stop(self):
        self._is_running = False


class VideoPlayerWorker(QThread):
    frame_ready    = Signal(QImage)
    progress_updated = Signal(int)
    position_updated = Signal(int, int)  # (current_msec, total_msec)
    counts_updated = Signal(dict)
    detection_event = Signal(str, str) # (timestamp_str, message)
    finished       = Signal()

    def __init__(self, video_path, count_history, tracking_data, fps, line_pos=0.60):
        super().__init__()
        self.video_path    = video_path
        self.tracking_data = tracking_data   # {frame_idx: [boxes]}
        self.fps           = fps
        self.line_pos      = line_pos
        self._is_running   = True
        self.speed         = 1.0
        self._seek_msec    = None
        self._seek_offset_msec = None
        self._is_paused    = False
        self._step_dir     = 0 # -1 or 1 for manual stepping

        # Internal frame counter
        self._frame_idx    = 0
        
        # Incremental Counting per playback session
        self.counting_engine = CountingEngine()
        self.cumulative_counts = dict(self.counting_engine.counts)

    def set_speed(self, speed):
        self.speed = speed

    def set_paused(self, paused):
        self._is_paused = paused

    def stop(self):
        self._is_running = False

    def seek_to_start(self):
        self._seek_msec = 0

    def seek_to_msec(self, msec: float):
        try:
            self._seek_msec = max(0.0, float(msec))
        except Exception:
            self._seek_msec = 0.0

    def seek_backward_10s(self):
        self._seek_offset_msec = -10000

    def seek_forward_10s(self):
        self._seek_offset_msec = 10000

    def step_forward(self):
        if self._is_paused:
            self._step_dir = 1

    def step_backward(self):
        if self._is_paused:
            self._step_dir = -1

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.finished.emit()
            return

        fps           = self.fps or cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        base_delay_ms = 1000.0 / fps
        total_msec = int(round((total_frames / fps) * 1000.0)) if total_frames > 0 else 0

        self._frame_idx = 0  # Reset to beginning

        # --- Diagnostic: confirm data received ---
        frames_with_boxes = sum(1 for v in self.tracking_data.values() if v)
        print(f"[Player] tracking_data frames: {len(self.tracking_data)} | frames with boxes: {frames_with_boxes}")

        while self._is_running and cap.isOpened():
            if self._is_paused and self._step_dir == 0:
                self.msleep(30)
                continue

            start_time = time.time()

            # --- Handle seeking ---
            if self._seek_msec is not None:
                target_msec = self._seek_msec
                self._seek_msec = None
                cap.set(cv2.CAP_PROP_POS_MSEC, target_msec)
                self._frame_idx = max(0, int(round((target_msec / 1000.0) * fps)))
                # Reset counting state
                self.counting_engine.reset()
                self.cumulative_counts = dict(self.counting_engine.counts)

            if self._seek_offset_msec is not None:
                offset = self._seek_offset_msec
                self._seek_offset_msec = None
                current_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                new_msec = max(0.0, current_msec + offset)
                cap.set(cv2.CAP_PROP_POS_MSEC, new_msec)
                self._frame_idx = max(0, int(round((new_msec / 1000.0) * fps)))
                # Reset counting state
                self.counting_engine.reset()
                self.cumulative_counts = dict(self.counting_engine.counts)

            if self._step_dir != 0:
                offset_ms = self._step_dir * base_delay_ms
                self._step_dir = 0
                current_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                new_msec = max(0.0, current_msec + offset_ms)
                cap.set(cv2.CAP_PROP_POS_MSEC, new_msec)
                self._frame_idx = max(0, int(round((new_msec / 1000.0) * fps)))

            ret, frame = cap.read()
            if not ret:
                break

            self._frame_idx += 1
            lookup = self._frame_idx

            # Fallback to nearest exact frame to prevent desync
            if lookup not in self.tracking_data:
                for shift in range(1, 6):
                    if (lookup - shift) in self.tracking_data:
                        lookup = lookup - shift
                        break
                    if (lookup + shift) in self.tracking_data:
                        lookup = lookup + shift
                        break

            h, w = frame.shape[:2]
            line_y = int(h * self.line_pos)

            if lookup in self.tracking_data:
                current_frame_boxes = self.tracking_data[lookup]
                events = self.counting_engine.process(
                    [
                        DetectionBox(x1, y1, x2, y2, track_id, ui_cat)
                        for x1, y1, x2, y2, track_id, ui_cat in current_frame_boxes
                    ],
                    lookup,
                    line_y,
                )
                for event in events:
                    timestamp = time.strftime("%H:%M:%S")
                    id_label = event.track_id if not str(event.track_id).startswith("proxy_") else "Proxy"
                    self.detection_event.emit(
                        timestamp,
                        f"{event.category} {event.direction} (ID:{id_label})",
                    )
                self.cumulative_counts = dict(self.counting_engine.counts)


            self.counts_updated.emit(self.cumulative_counts)

            # --- Draw overlays ---
            cv2.line(frame, (0, line_y), (w, line_y), (0, 0, 255), 3)
            cv2.putText(frame, "LINEA DE CONTEO", (10, line_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            if lookup in self.tracking_data:
                _cat_colors = {
                    "Cemento":           ( 50, 200,  80),
                    "Tubería Presión":   (255, 160,   0),
                    "Tubería Sanitaria": ( 30, 144, 255),
                }
                for x1, y1, x2, y2, track_id, ui_cat in self.tracking_data[lookup]:
                    color = _cat_colors.get(ui_cat, (0, 255, 0))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    tid_str = f"ID:{track_id}" if track_id is not None else "ID:--"
                    label   = f"{tid_str} {ui_cat}"
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                    cv2.rectangle(frame, (x1, max(y1-18, 0)), (x1+tw+4, max(y1, 18)), color, -1)
                    cv2.putText(frame, label, (x1+2, max(y1-4, 14)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

            # --- Emit frame ---
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h2, w2, ch = rgb.shape
            q_img = QImage(rgb.data, w2, h2, ch * w2, QImage.Format_RGB888)
            self.frame_ready.emit(q_img.copy())

            # --- Accurate time position ---
            try:
                cur_msec = int(round(cap.get(cv2.CAP_PROP_POS_MSEC)))
            except Exception:
                cur_msec = int(round((self._frame_idx / fps) * 1000.0))
            self.position_updated.emit(max(0, cur_msec), max(0, total_msec))

            # --- Timing ---
            elapsed_ms = (time.time() - start_time) * 1000.0
            target_ms  = base_delay_ms / self.speed
            sleep_ms   = target_ms - elapsed_ms
            if sleep_ms > 0:
                self.msleep(int(sleep_ms))

            # --- Progress ---
            if total_frames > 0 and self._frame_idx % 5 == 0:
                progress = min(int((self._frame_idx / total_frames) * 100), 100)
                self.progress_updated.emit(progress)

        cap.release()
        self.finished.emit()


class RtspCameraWorker(QThread):
    """Worker para captura y detección YOLO en tiempo real desde una cámara IP (RTSP/HTTP).
    Cuenta objetos que intersectan una zona rectangular configurable (una vez por ID único).
    """
    frame_ready       = Signal(QImage)   # Frame procesado con overlays
    counts_updated    = Signal(dict)     # {categoria: count}
    detection_event   = Signal(str, str) # (timestamp, mensaje)
    connection_status = Signal(str)      # "connecting", "ok", "lost", "error"
    error_occurred    = Signal(str)
    finished          = Signal()

    def __init__(self, camera_url: str, model_path: str,
                 zone_x1: float = 0.20, zone_y1: float = 0.40,
                 zone_x2: float = 0.80, zone_y2: float = 0.70,
                 preloaded_model=None, preloaded_device=None,
                 p2p_sn: str = None):
        super().__init__()
        self.camera_url  = camera_url
        self.model_path  = model_path
        # Zona de conteo normalizada (0.0 – 1.0)
        self.zone_x1 = zone_x1
        self.zone_y1 = zone_y1
        self.zone_x2 = zone_x2
        self.zone_y2 = zone_y2
        self._is_running = True
        self._is_paused  = False

        # Conteo acumulado de la sesión en vivo
        self.cumulative_counts = {"Cemento": 0, "Tubería Presión": 0, "Tubería Sanitaria": 0}
        self.counted_ids = set()   # IDs que están actualmente "afuera"
        self.prev_positions = {}
        self.track_persistence = {} # {track_id: num_frames_visto}

        # Cargar/reutilizar modelo
        if preloaded_model is not None:
            self.model = preloaded_model
            self.device = preloaded_device or "cpu"
            self.model_loaded = True
            print(f"[RTSP] Modelo precargado en {self.device}")
        else:
            try:
                from ultralytics import YOLO
                import torch
                self.model  = YOLO(model_path)
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                self.model.to(self.device)
                self.model_loaded = True
                print(f"[RTSP] Modelo cargado en {self.device}")
            except Exception as e:
                self.model_loaded = False
                self.error_msg = str(e)
        
        # Silenciar logs molestos de Ultralytics (not enough matching points)
        import logging
        logging.getLogger("ultralytics").setLevel(logging.ERROR)

    def set_paused(self, paused: bool):
        self._is_paused = paused

    def stop(self):
        self._is_running = False

    def reset_counts(self):
        """Reinicia el conteo de la sesión en vivo."""
        self.cumulative_counts = {"Cemento": 0, "Tubería Presión": 0, "Tubería Sanitaria": 0}
        self.counted_ids.clear()
        self.prev_positions.clear()
        self.track_persistence.clear()

    def _boxes_overlap(self, bx1, by1, bx2, by2, zx1, zy1, zx2, zy2) -> bool:
        """Retorna True si el bounding box del objeto se solapa con la zona de conteo."""
        return not (bx2 < zx1 or bx1 > zx2 or by2 < zy1 or by1 > zy2)

    def run(self):
        if not self.model_loaded:
            self.error_occurred.emit(
                f"Error cargando modelo: {getattr(self, 'error_msg', 'desconocido')}"
            )
            self.finished.emit()
            return

        self.connection_status.emit("connecting")
        safe_camera_url = _redact_rtsp_url(self.camera_url)
        print(f"[RTSP] Conectando a: {safe_camera_url}")

        RECONNECT_DELAY_MS = 3000
        MAX_RECONNECT      = 5
        FRAME_SKIP         = 2
        reconnect_count    = 0

        # Forzar TCP construyendo una URL con parámetros FFMPEG embebidos.
        # Esta técnica es la más confiable cuando se trabaja con túneles (Bore, Ngrok, etc.)
        # OpenCV soporta pasar opciones de ffmpeg como: {"rtsp_transport": "tcp"}
        import os as _os
        _os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        
        # Conexión RTSP estándar
        self.connection_status.emit("connecting")
        
        while self._is_running:
            # Re-verificar si el thread sigue activo antes de intentar abrir
            if not self._is_running: break

            cap = cv2.VideoCapture(self.camera_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cap.isOpened():
                reconnect_count += 1
                print(f"[RTSP] Fallo de conexión (intento {reconnect_count}/{MAX_RECONNECT}) -> {safe_camera_url}")
                self.connection_status.emit("lost")
                if reconnect_count >= MAX_RECONNECT:
                    self.error_occurred.emit(
                        f"No se pudo conectar a la cámara después de {MAX_RECONNECT} intentos.\n"
                        f"Verifique que el Host, las credenciales y el puerto RTSP sean correctos.\n"
                        f"URL actual: {safe_camera_url}"
                    )
                    break
                self.msleep(RECONNECT_DELAY_MS)
                continue

            # Conexión exitosa
            reconnect_count = 0
            fps    = cap.get(cv2.CAP_PROP_FPS) or 25.0
            self.connection_status.emit("ok")
            print(f"[RTSP] Conectado OK — FPS declarados: {fps:.1f}")

            frame_local = 0

            while self._is_running and cap.isOpened():
                if self._is_paused:
                    self.msleep(30)
                    continue

                ret, frame = cap.read()
                if not ret:
                    print("[RTSP] Pérdida de señal, reconectando…")
                    self.connection_status.emit("lost")
                    break

                frame_local += 1
                h, w = frame.shape[:2]

                # Píxeles de la zona de conteo
                zx1 = int(self.zone_x1 * w)
                zy1 = int(self.zone_y1 * h)
                zx2 = int(self.zone_x2 * w)
                zy2 = int(self.zone_y2 * h)

                # ── Frames sin inferencia → solo dibujar zona ──────────
                if frame_local % FRAME_SKIP != 0:
                    self._draw_zone(frame, zx1, zy1, zx2, zy2, active=False)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    hh, ww, ch = rgb.shape
                    qimg = QImage(rgb.data, ww, hh, ch * ww, QImage.Format_RGB888)
                    self.frame_ready.emit(qimg.copy())
                    continue

                start_t = time.time()

                results = self.model.track(
                    frame, persist=True, device=self.device,
                    verbose=False, conf=0.20, iou=0.5
                )
                result = results[0]

                frame_boxes = []
                zone_active = False  # Se pondrá True si algún objeto toca la zona

                if result.boxes is not None and len(result.boxes) > 0:
                    boxes_xyxy = result.boxes.xyxy.cpu().numpy()
                    clss       = result.boxes.cls.int().cpu().tolist()
                    track_ids  = (result.boxes.id.int().cpu().tolist()
                                  if result.boxes.id is not None
                                  else [None] * len(boxes_xyxy))
                    names = self.model.names

                    self.prev_positions = {k: v for k, v in self.prev_positions.items() if frame_local - v[1] < 15}
                    line_y = (zy1 + zy2) / 2.0  # Mitad de la zona para el conteo bidireccional

                    for box, track_id, cls_id in zip(boxes_xyxy, track_ids, clss):
                        x1, y1, x2, y2 = box
                        cls_name = names[cls_id]

                        ui_cat = map_model_class_to_category(cls_name)

                        if ui_cat is None:
                            continue

                        ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
                        in_zone = self._boxes_overlap(ix1, iy1, ix2, iy2, zx1, zy1, zx2, zy2)

                        frame_boxes.append((ix1, iy1, ix2, iy2, track_id, ui_cat, in_zone))

                        if in_zone:
                            zone_active = True

                        # ── Conteo Bidireccional Integrado ──────────────────
                        cy = (iy1 + iy2) / 2.0
                        center_x = (x1 + x2) / 2.0
                        if track_id is not None:
                            if track_id in self.prev_positions:
                                prev_y, _ = self.prev_positions[track_id]
                                is_exiting = (prev_y < line_y and cy >= line_y)
                                is_entering = (prev_y >= line_y and cy < line_y)

                                if is_exiting and track_id not in self.counted_ids:
                                    # --- Filtro de Persistencia: Deshabilitado (0 frames) ---
                                    if self.track_persistence.get(track_id, 0) >= 0:
                                        self.cumulative_counts[ui_cat] += 1
                                        self.counted_ids.add(track_id)
                                        ts = time.strftime("%H:%M:%S")
                                        self.detection_event.emit(ts, f"{ui_cat} despachado (ID:{track_id})")
                                elif is_entering and track_id in self.counted_ids:
                                    # --- También para el retorno (deshabilitado) ---
                                    if self.track_persistence.get(track_id, 0) >= 0:
                                        self.cumulative_counts[ui_cat] = max(0, self.cumulative_counts[ui_cat] - 1)
                                        self.counted_ids.remove(track_id)
                                        ts = time.strftime("%H:%M:%S")
                                        self.detection_event.emit(ts, f"{ui_cat} retornado (ID:{track_id})")

                            self.prev_positions[track_id] = (cy, frame_local)
                            self.track_persistence[track_id] = self.track_persistence.get(track_id, 0) + 1
                        else:
                            # 2. Fallback: Proximidad simple para objetos sin ID
                            # (Buscamos el objeto más cercano en el frame anterior que no tenga ID real)
                            best_match = None
                            min_dist = 50 # pixeles de tolerancia
                            for old_id, old_y in self.prev_positions.items():
                                if isinstance(old_id, str) and old_id.startswith("proxy_"):
                                    old_center_y = old_y[0] if isinstance(old_y, tuple) else old_y
                                    dist = abs(cy - old_center_y)
                                    if dist < min_dist:
                                        min_dist = dist
                                        best_match = old_id
                            
                            if best_match:
                                prev_y = self.prev_positions[best_match][0]
                                is_exiting = (prev_y < line_y <= cy)
                                is_entering = (prev_y > line_y >= cy)
                                if is_exiting and best_match not in self.counted_ids:
                                    if self.track_persistence.get(best_match, 0) >= 0:
                                        self.cumulative_counts[ui_cat] += 1
                                        ts = time.strftime("%H:%M:%S")
                                        self.detection_event.emit(ts, f"{ui_cat} despachado (ID:Proxy)")
                                    self.counted_ids.add(best_match)
                                elif is_entering and best_match in self.counted_ids:
                                    if self.track_persistence.get(best_match, 0) >= 0:
                                        self.cumulative_counts[ui_cat] = max(0, self.cumulative_counts[ui_cat] - 1)
                                        ts = time.strftime("%H:%M:%S")
                                        self.detection_event.emit(ts, f"{ui_cat} retornado (ID:Proxy)")
                                    self.counted_ids.remove(best_match)
                                self.prev_positions[best_match] = (cy, frame_local)
                                self.track_persistence[best_match] = self.track_persistence.get(best_match, 0) + 1
                            else:
                                # Nuevo objeto "proxy"
                                proxy_id = f"proxy_{frame_local}_{int(center_x)}"
                                self.prev_positions[proxy_id] = (cy, frame_local)
                                self.track_persistence[proxy_id] = 1

    

                # ── Dibujar zona y bounding boxes ─────────────────────
                self._draw_zone(frame, zx1, zy1, zx2, zy2, active=zone_active)

                for ix1, iy1, ix2, iy2, track_id, ui_cat, in_zone in frame_boxes:
                    # Verde si está en zona, blanco si no
                    color = (0, 255, 80) if in_zone else (200, 200, 200)
                    thickness = 3 if in_zone else 1
                    cv2.rectangle(frame, (ix1, iy1), (ix2, iy2), color, thickness)
                    tid_str = f"ID:{track_id}" if track_id is not None else ""
                    label = f"{tid_str} {ui_cat}"
                    cv2.putText(frame, label, (ix1, max(iy1 - 5, 12)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

                # ── FPS ───────────────────────────────────────────────
                elapsed_ms = (time.time() - start_t) * 1000.0
                infer_fps  = 1000.0 / max(elapsed_ms, 1.0)
                cv2.putText(frame, f"IA:{infer_fps:.1f}fps", (w - 110, 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 255, 180), 2)

                # ── Emitir frame y conteos ─────────────────────────────
                self.counts_updated.emit(dict(self.cumulative_counts))
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                hh, ww, ch = rgb.shape
                qimg = QImage(rgb.data, ww, hh, ch * ww, QImage.Format_RGB888)
                self.frame_ready.emit(qimg.copy())

                # ── Timing ────────────────────────────────────────────
                target_ms = (1000.0 / fps) * FRAME_SKIP
                sleep_ms  = target_ms - elapsed_ms
                if sleep_ms > 0:
                    self.msleep(int(sleep_ms))

            cap.release()
            print("[RTSP] Cámara liberada.")

            if self._is_running:
                self.msleep(RECONNECT_DELAY_MS)

        self.finished.emit()

    def _draw_zone(self, frame, zx1: int, zy1: int, zx2: int, zy2: int, active: bool):
        """Dibuja la zona de conteo sobre el frame con un efecto semitransparente."""
        overlay = frame.copy()
        # Color: amarillo dorado cuando está inactivo, verde brillante cuando hay detección
        color = (0, 220, 60) if active else (0, 200, 255)
        alpha = 0.18 if active else 0.10
        cv2.rectangle(overlay, (zx1, zy1), (zx2, zy2), color, -1)  # Relleno
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        # Borde sólido
        border_color = (0, 255, 80) if active else (0, 200, 255)
        cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), border_color, 2)
        # Etiqueta
        label = "ZONA DE CONTEO ●" if active else "ZONA DE CONTEO"
        label_color = (0, 255, 80) if active else (0, 200, 255)
        cv2.putText(frame, label, (zx1 + 6, zy1 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, label_color, 2)
