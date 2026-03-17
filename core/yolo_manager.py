import cv2
import time
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


class YoloAnalyzerWorker(QThread):
    progress_updated = Signal(int)
    # Emits: final_counts, count_history {frame_idx: counts}, tracking_data {frame_idx: [boxes]}, fps
    finished_analysis = Signal(object, object, object, float)
    error_occurred = Signal(str)

    def __init__(self, video_path, model_path, line_pos=0.60):
        super().__init__()
        self.video_path = video_path
        self.model_path = model_path
        self.line_pos   = line_pos  # fraction of height for counting line
        self._is_running = True
        self.tracking_data = {}   # {frame_idx: [(x1,y1,x2,y2,track_id,label), ...]}
        # Removed cumulative_counts from Analyzer, moving logic to Player

        try:
            from ultralytics import YOLO
            import torch
            self.model = YOLO(model_path)
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
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

                    # Mapeo flexible
                    ui_cat = None
                    if cls_name.lower() in ["bulto", "cemento", "bag"]:
                        ui_cat = "Cemento"
                    elif "tuberia" in cls_name.lower() and "presion" in cls_name.lower():
                        ui_cat = "Tubería Presión"
                    elif "tuberia" in cls_name.lower() and "sanitaria" in cls_name.lower():
                        ui_cat = "Tubería Sanitaria"
                    
                    if ui_cat:
                        frame_boxes.append((int(x1), int(y1), int(x2), int(y2), track_id, ui_cat))

            self.tracking_data[frame_idx] = frame_boxes

            if frame_idx % 60 == 0:
                print(f"[Analyzer] Frame {frame_idx}: {len(frame_boxes)} bultos filtrados")
                if total_frames > 0:
                    progress = min(int((frame_idx / total_frames) * 100), 100)
                    self.progress_updated.emit(progress)

        cap.release()

        if self._is_running:
            final_data = dict(self.tracking_data)
            print(f"[Analyzer] Finalizado. Frames procesados: {len(final_data)}. Emitiendo...")
            self.progress_updated.emit(100)
            self.finished_analysis.emit({}, {}, final_data, fps)

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
        self.cumulative_counts = {"Cemento": 0, "Tubería Presión": 0, "Tubería Sanitaria": 0}
        self.crossed_ids = set()
        self.prev_positions = {}

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
                self.cumulative_counts = {"Cemento": 0, "Tubería Presión": 0, "Tubería Sanitaria": 0}
                self.crossed_ids.clear()
                self.prev_positions.clear()

            if self._seek_offset_msec is not None:
                offset = self._seek_offset_msec
                self._seek_offset_msec = None
                current_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                new_msec = max(0.0, current_msec + offset)
                cap.set(cv2.CAP_PROP_POS_MSEC, new_msec)
                self._frame_idx = max(0, int(round((new_msec / 1000.0) * fps)))
                # Reset counting state
                self.cumulative_counts = {"Cemento": 0, "Tubería Presión": 0, "Tubería Sanitaria": 0}
                self.crossed_ids.clear()
                self.prev_positions.clear()

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
                new_prev_positions = {}
                
                for x1, y1, x2, y2, track_id, ui_cat in current_frame_boxes:
                    center_y = (y1 + y2) / 2.0
                    center_x = (x1 + x2) / 2.0
                    
                    # 1. Usar track_id real si existe
                    if track_id is not None:
                        if track_id in self.prev_positions:
                            prev_y = self.prev_positions[track_id]
                            crossed = (prev_y < line_y <= center_y) or (prev_y > line_y >= center_y)
                            if crossed and track_id not in self.crossed_ids:
                                if ui_cat in self.cumulative_counts:
                                    self.cumulative_counts[ui_cat] += 1
                                    # Emitir evento de detección
                                    timestamp = time.strftime("%H:%M:%S")
                                    self.detection_event.emit(timestamp, f"{ui_cat} detectado (ID:{track_id})")
                                self.crossed_ids.add(track_id)
                        new_prev_positions[track_id] = center_y
                    else:
                        # 2. Fallback: Proximidad simple para objetos sin ID
                        # (Buscamos el objeto más cercano en el frame anterior que no tenga ID real)
                        best_match = None
                        min_dist = 50 # pixeles de tolerancia
                        for old_id, old_y in self.prev_positions.items():
                            if isinstance(old_id, str) and old_id.startswith("proxy_"):
                                dist = abs(center_y - old_y)
                                if dist < min_dist:
                                    min_dist = dist
                                    best_match = old_id
                        
                        if best_match:
                            prev_y = self.prev_positions[best_match]
                            crossed = (prev_y < line_y <= center_y) or (prev_y > line_y >= center_y)
                            if crossed and best_match not in self.crossed_ids:
                                if ui_cat in self.cumulative_counts:
                                    self.cumulative_counts[ui_cat] += 1
                                    # Emitir evento de detección para proxy
                                    timestamp = time.strftime("%H:%M:%S")
                                    self.detection_event.emit(timestamp, f"{ui_cat} detectado (ID:Proxy)")
                                self.crossed_ids.add(best_match)
                            new_prev_positions[best_match] = center_y
                        else:
                            # Nuevo objeto "proxy"
                            proxy_id = f"proxy_{len(new_prev_positions)}_{int(center_x)}"
                            new_prev_positions[proxy_id] = center_y
                
                self.prev_positions = new_prev_positions

            self.counts_updated.emit(self.cumulative_counts)

            # --- Draw overlays ---
            cv2.line(frame, (0, line_y), (w, line_y), (0, 0, 255), 3)
            cv2.putText(frame, "LINEA DE CONTEO", (10, line_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            if lookup in self.tracking_data:
                for x1, y1, x2, y2, track_id, ui_cat in self.tracking_data[lookup]:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    tid_str = f"ID:{track_id}" if track_id is not None else "ID:--"
                    cv2.putText(frame, f"{tid_str} {ui_cat}", (x1, max(y1 - 5, 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

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
