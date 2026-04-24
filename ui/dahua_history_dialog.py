"""
ui/dahua_history_dialog.py
--------------------------
Módulo de Historial de Grabaciones para cámaras Dahua.
Permite al usuario:
  1. Seleccionar fecha, hora inicio/fin y canal.
  2. Previsualizar el fragmento directamente del NVR (sin guardar en disco).
  3. Confirmar si desea Analizar con IA o Descargar el fragmento.
  4. Si cancela, el fragmento temporal se elimina automáticamente.

TOTALMENTE AISLADO: no modifica ninguna funcionalidad existente.
Solo se llama desde el botón "Ver Historial" de la página de Cámara en Vivo.
"""

import os
import sys
import time
import threading
import subprocess
import datetime

try:
    from static_ffmpeg import run as ffmpeg_run
    FFMPEG_STATS_AVAILABLE = True
except ImportError:
    FFMPEG_STATS_AVAILABLE = False

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QFrame, QSizePolicy, QProgressBar,
    QCalendarWidget, QSpinBox, QWidget, QMessageBox, QFileDialog,
    QGroupBox, QScrollArea, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QPoint
from PySide6.QtGui import QFont, QColor, QPixmap, QImage, QGuiApplication



# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_dahua_playback_url(host: str, port: int, user: str, password: str,
                              channel: int, start_dt: datetime.datetime,
                              end_dt: datetime.datetime) -> str:
    """
    Construye la URL RTSP de Playback de Dahua para el fragmento solicitado.
    Formato oficial Dahua:
      rtsp://user:pass@host:554/cam/playback?channel=<N>&starttime=<YYYYMMDDTHHmmss>&endtime=<YYYYMMDDTHHmmss>
    """
    start_str = start_dt.strftime("%Y_%m_%d_%H_%M_%S")
    end_str   = end_dt.strftime("%Y_%m_%d_%H_%M_%S")
    url = (
        f"rtsp://{user}:{password}@{host}:{port}"
        f"/cam/playback?channel={channel}&subtype=0"
        f"&starttime={start_str}&endtime={end_str}"
    )
    return url


def _get_ffmpeg_path() -> str:
    """Retorna la ruta al binario de FFmpeg, ya sea del sistema o de static-ffmpeg."""
    # 1. Intentar con el del sistema
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return "ffmpeg"
    except Exception:
        pass

    # 2. Intentar con static-ffmpeg
    if FFMPEG_STATS_AVAILABLE:
        try:
            # Esto descarga el binario si no existe (la primera vez)
            ffmpeg_path, _ = ffmpeg_run.get_or_fetch_platform_executables_else_raise()
            return ffmpeg_path
        except Exception:
            pass
            
    return ""


def _ffmpeg_available() -> bool:
    """Comprueba si ffmpeg está disponible."""
    return bool(_get_ffmpeg_path())


# ─────────────────────────────────────────────────────────────────────────────
# Worker: Previsualización del fragmento histórico
# ─────────────────────────────────────────────────────────────────────────────

class HistoryPreviewWorker(QThread):
    """
    Reproduce fotogramas del fragmento histórico Dahua via RTSP.
    Emite frame_ready con la imagen para mostrar en la UI.
    Emite connection_failed si la URL no responde.
    Emite finished cuando el fragmento termina o se detiene.
    """
    frame_ready       = Signal(QImage)
    connection_failed = Signal(str)
    finished          = Signal()
    progress_updated  = Signal(int)  # 0–100

    def __init__(self, url: str, start_frame: int = 0):
        super().__init__()
        self.url = url
        self._running = True
        self._frame_count = start_frame
        self.speed = 1.0  # Multiplicador de velocidad por defecto

    def set_speed(self, val: float):
        self.speed = val

    def stop(self):
        self._running = False

    def run(self):
        try:
            import cv2
            print(f"[HISTORIAL] Worker iniciado cargando archivo local: {self.url}")
        except ImportError:
            self.connection_failed.emit("OpenCV no está instalado.")
            self.finished.emit()
            return

        # Abrir archivo local (mucho más rápido y permite scroll/speed)
        cap = cv2.VideoCapture(self.url)
        
        if not cap.isOpened():
            print(f"[HISTORIAL] Error: No se pudo abrir el archivo temporal {self.url}")
            self.connection_failed.emit("Error al abrir el archivo de previsualización.")
            self.finished.emit()
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        
        # Saltar al frame guardado si es necesario
        if self._frame_count > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, self._frame_count)

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        base_delay = int(1000 / fps)

        while self._running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            self._frame_count += 1

            # Emitir fotograma
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self.frame_ready.emit(qimg.copy())

            # Progreso
            if total_frames > 0:
                pct = min(int((self._frame_count / total_frames) * 100), 99)
                self.progress_updated.emit(pct)

            # Ajuste de velocidad (msleep toma milisegundos)
            # Volver a calcular delay en cada iteración para captar cambios de velocidad
            delay = int(base_delay / max(0.1, self.speed))
            if delay < 1: delay = 1
            self.msleep(delay)

        cap.release()
        print("[HISTORIAL] Reproducción de archivo local finalizada.")
        self.progress_updated.emit(100)
        self.finished.emit()


# ─────────────────────────────────────────────────────────────────────────────
# Worker: Descarga PARALELA del fragmento histórico (Multi-Stream FFmpeg)
# ─────────────────────────────────────────────────────────────────────────────

def _build_dahua_segment_url(base_url_template: str, host: str, port: int,
                              user: str, password: str, channel: int,
                              seg_start: datetime.datetime,
                              seg_end: datetime.datetime) -> str:
    """Construye la URL de un segmento de tiempo específico para descarga paralela."""
    start_str = seg_start.strftime("%Y_%m_%d_%H_%M_%S")
    end_str   = seg_end.strftime("%Y_%m_%d_%H_%M_%S")
    return (
        f"rtsp://{user}:{password}@{host}:{port}"
        f"/cam/playback?channel={channel}&subtype=0"
        f"&starttime={start_str}&endtime={end_str}"
    )


class HistoryDownloadWorker(QThread):
    """
    Motor de descarga paralela para fragmentos históricos Dahua.

    Divide el rango de tiempo solicitado en N segmentos iguales y lanza N procesos
    FFmpeg simultáneos (uno por segmento). Cuando todos terminan, los concatena en
    un único archivo MP4 usando el demuxer 'concat' de FFmpeg.

    Esto maximiza el uso del ancho de banda disponible ya que el NVR atiende
    múltiples conexiones RTSP al mismo tiempo, una por segmento.
    """
    progress_updated = Signal(int)   # 0–100
    finished         = Signal(str)   # ruta del archivo final
    error_occurred   = Signal(str)
    status_updated   = Signal(str)   # mensaje descriptivo de estado

    # Número de conexiones paralelas — ajustable (máx 32 recomendado)
    # Número de conexiones paralelas — vuelto a 32 por petición del usuario
    NUM_WORKERS = 32

    def __init__(self, url: str, output_path: str, duration_secs: int,
                 # Datos para reconstruir las URLs de segmentos
                 host: str = "", port: int = 554,
                 user: str = "", password: str = "", channel: int = 1,
                 start_dt: datetime.datetime = None, end_dt: datetime.datetime = None):
        super().__init__()
        self.url           = url          # URL base (usada si no se proveen datos para segmentos)
        self.output_path   = output_path
        self.duration_secs = duration_secs
        self.host          = host
        self.port          = port
        self.user          = user
        self.password      = password
        self.channel       = channel
        self.start_dt      = start_dt
        self.end_dt        = end_dt
        self._running      = True
        self._procs        = []    # Lista de procesos FFmpeg activos

    def stop(self):
        self._running = False
        for proc in self._procs:
            try:
                proc.terminate()
            except Exception:
                pass

    def _spawn_ffmpeg(self, seg_url: str, seg_output: str, seg_secs: int):
        """Lanza un proceso FFmpeg para un único segmento."""
        ffmpeg_path = _get_ffmpeg_path()
        cmd = [
            ffmpeg_path, "-y",
            "-rtsp_transport", "tcp",
            "-timeout", "15000000",
            "-i", seg_url,
            "-t", str(seg_secs),
            "-c", "copy",
            seg_output
        ]
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags
        )

    def run(self):
        ffmpeg_path = _get_ffmpeg_path()
        if not ffmpeg_path:
            self.error_occurred.emit("FFmpeg no encontrado.")
            return

        # ── Determinar si podemos usar descarga paralela ────────────────────
        can_parallel = (
            self.host and self.user and self.start_dt and self.end_dt
            and self.duration_secs > 15  # Bajamos el umbral para ser más agresivos
        )

        if not can_parallel:
            # Fallback a descarga simple
            print("[HISTORIAL-DL] Modo simple (fragmento muy corto o sin metadatos).")
            self._download_simple()
            return

        # ── Descarga inteligente: Proporcional a la duración ──────────────────
        # Regla: Intentamos usar 1 hilo por cada 15 seg de video
        n = min(self.NUM_WORKERS, max(1, int(self.duration_secs // 15)))
        
        # Para videos largos (+10 min), forzamos al menos 8 hilos si ya no los tiene
        if self.duration_secs > 600:
            n = max(n, min(self.NUM_WORKERS, 8))

        seg_secs = self.duration_secs / n
        print(f"[HISTORIAL-DL] Motor de Descarga Inteligente: {n} hilos paralelos")
        print(f"[HISTORIAL-DL] {n} segmentos de ~{seg_secs:.1f}s | Total: {self.duration_secs}s")
        self.status_updated.emit(f"🚀 Usando {n} motores de descarga en paralelo...")
        self.progress_updated.emit(1)  # Mostrar que algo arrancó

        temp_dir = os.path.dirname(self.output_path)
        seg_paths = []
        seg_urls  = []

        for i in range(n):
            seg_start = self.start_dt + datetime.timedelta(seconds=i * seg_secs)
            seg_end   = self.start_dt + datetime.timedelta(seconds=(i + 1) * seg_secs)
            if seg_end > self.end_dt:
                seg_end = self.end_dt
            seg_url  = _build_dahua_segment_url(
                None, self.host, self.port, self.user, self.password,
                self.channel, seg_start, seg_end
            )
            seg_path = os.path.join(temp_dir, f"_seg_{i:03d}.mp4")
            seg_paths.append(seg_path)
            seg_urls.append((seg_url, seg_path, int((seg_end - seg_start).total_seconds())))

        # Tabla compartida de progreso por segmento (0.0–1.0)
        seg_progress = [0.0] * n
        seg_done     = [False] * n
        progress_lock = threading.Lock()
        import re as _re
        time_pattern  = _re.compile(rb'time=(\d+):(\d+):(\d+\.?\d*)')

        def _stderr_reader(proc, idx, duration):
            """Daemon: lee stderr de FFmpeg línea a línea y actualiza el progreso."""
            try:
                for raw in iter(proc.stderr.readline, b''):
                    if not self._running:
                        break
                    m = time_pattern.search(raw)
                    if m:
                        h  = int(m.group(1))
                        mi = int(m.group(2))
                        s  = float(m.group(3))
                        elapsed_in_seg = h * 3600 + mi * 60 + s
                        pct = min(elapsed_in_seg / max(1, duration), 1.0)
                        with progress_lock:
                            seg_progress[idx] = pct
            except Exception:
                pass
            finally:
                with progress_lock:
                    seg_done[idx]     = True
                    seg_progress[idx] = 1.0

        # Lanzar procesos y lectores de stderr
        self._procs = []
        start_time  = time.time()

        for i, (seg_url, seg_path, seg_dur) in enumerate(seg_urls):
            if not self._running:
                break
            try:
                proc = self._spawn_ffmpeg(seg_url, seg_path, seg_dur)
                self._procs.append(proc)
                t = threading.Thread(
                    target=_stderr_reader,
                    args=(proc, i, seg_dur),
                    daemon=True
                )
                t.start()
                print(f"[HISTORIAL-DL] ▶ Segmento {i+1}/{n} iniciado ({seg_dur}s) → {os.path.basename(seg_path)}")
                
                # Pequeña pausa para no saturar el NVR con peticiones instantáneas
                time.sleep(0.15)
            except Exception as e:
                print(f"[HISTORIAL-DL] ✗ Error al iniciar proceso: {e}")
                with progress_lock:
                    seg_done[i] = True

        # Monitorear progreso hasta que todos terminen
        while self._running:
            with progress_lock:
                local_prog = list(seg_progress)
                local_done = list(seg_done)

            alive        = [p for p in self._procs if p.poll() is None]
            active_count = len(alive)

            avg = sum(local_prog) / len(local_prog) if local_prog else 0.0
            pct = max(1, int(avg * 70))

            elapsed  = int(time.time() - start_time)
            mins, s2 = divmod(elapsed, 60)
            eta_str  = f"{mins}:{s2:02d}"

            self.progress_updated.emit(pct)
            self.status_updated.emit(
                f"⚡ {active_count}/{n} activos | {pct}% | ⏱ {eta_str}"
            )

            if all(local_done) or not alive:
                break
            time.sleep(0.5)

        if not self._running:
            self._cleanup_segments(seg_paths)
            return

        # Verificar que todos los segmentos existen y no están vacíos
        # Usamos 100 bytes como mínimo (el último seg puede ser pequeño por ser el remanente)
        valid_paths = [p for p in seg_paths if os.path.exists(p) and os.path.getsize(p) >= 100]
        failed = [p for p in seg_paths if p not in valid_paths]
        
        if failed:
            print(f"[HISTORIAL-DL] {len(failed)}/{n} segmentos fallaron o son muy pequeños.")
            
        # Solo fallar si la mayoría de los segmentos fallaron (> 40%)
        if len(valid_paths) < max(1, n * 0.6):
            print(f"[HISTORIAL-DL] Demasiados segmentos fallaron ({len(failed)}/{n}). Modo simple como fallback.")
            self.status_updated.emit("⚠️ Descarga parcial insuficiente. Reintentando en modo simple…")
            self._cleanup_segments(seg_paths)
            self._download_simple()
            return
        
        if failed:
            print(f"[HISTORIAL-DL] Continuando con {len(valid_paths)}/{n} segmentos válidos.")
            self.status_updated.emit(f"✅ {len(valid_paths)}/{n} segmentos OK. Uniendo…")

        # Concatenar con FFmpeg concat demuxer (solo los válidos)
        self.progress_updated.emit(75)
        self.status_updated.emit("🔗 Uniendo segmentos en un solo archivo…")
        print("[HISTORIAL-DL] Concatenando segmentos…")

        # Crear lista de concatenación (solo con segmentos válidos)
        concat_list = os.path.join(temp_dir, "_concat_list.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for seg_path in valid_paths:
                f.write(f"file '{seg_path}'\n")

        concat_cmd = [
            ffmpeg_path, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            "-movflags", "+faststart",
            self.output_path
        ]
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            concat_proc = subprocess.run(
                concat_cmd,
                capture_output=True,
                creationflags=creationflags,
                timeout=120
            )
            if concat_proc.returncode != 0:
                err = concat_proc.stderr.decode("utf-8", errors="ignore")
                print(f"[HISTORIAL-DL] Concat falló: {err[-300:]}")
                # Fallback: usar el primer segmento más grande que exista
                biggest = max(seg_paths, key=lambda p: os.path.getsize(p))
                import shutil
                shutil.copy(biggest, self.output_path)
                print(f"[HISTORIAL-DL] Usando segmento más grande como fallback: {biggest}")
        except Exception as e:
            print(f"[HISTORIAL-DL] Excepción en concat: {e}")
            self.error_occurred.emit(f"Error al unir segmentos: {e}")
            self._cleanup_segments(seg_paths, concat_list)
            return

        # Limpiar archivos temporales de segmentos
        self._cleanup_segments(seg_paths, concat_list)

        total_time = time.time() - start_time
        size_mb = os.path.getsize(self.output_path) / (1024 * 1024)
        print(f"[HISTORIAL-DL] ✅ Descarga paralela completada en {total_time:.1f}s → {size_mb:.1f} MB")
        self.progress_updated.emit(100)
        self.status_updated.emit(f"✅ Listo ({size_mb:.1f} MB en {total_time:.1f}s)")
        self.finished.emit(self.output_path)

    def _download_simple(self):
        """Descarga secuencial simple (fallback)."""
        ffmpeg_path = _get_ffmpeg_path()
        cmd = [
            ffmpeg_path, "-y",
            "-rtsp_transport", "tcp",
            "-i", self.url,
            "-t", str(self.duration_secs),
            "-c", "copy",
            "-movflags", "+faststart",
            self.output_path
        ]
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=creationflags
            )
            self._procs = [proc]
            start = time.time()
            while proc.poll() is None and self._running:
                elapsed = time.time() - start
                pct = min(int((elapsed / max(1, self.duration_secs)) * 95), 95)
                self.progress_updated.emit(pct)
                time.sleep(0.5)

            proc.wait()
            if proc.returncode == 0 and os.path.exists(self.output_path):
                self.progress_updated.emit(100)
                self.finished.emit(self.output_path)
            else:
                stderr = proc.stderr.read().decode("utf-8", errors="ignore")
                self.error_occurred.emit(f"FFmpeg falló:\n{stderr[-400:]}")
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _cleanup_segments(self, seg_paths: list, concat_list: str = None):
        """Elimina archivos temporales de segmentos."""
        for p in seg_paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        if concat_list and os.path.exists(concat_list):
            try:
                os.remove(concat_list)
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Diálogo Principal
# ─────────────────────────────────────────────────────────────────────────────

class DahuaHistoryDialog(QDialog):
    """
    Diálogo de Historial de Grabaciones Dahua.
    Recibe los parámetros de conexión ya configurados en la página de Cámara en Vivo.
    """

    # Señal emitida cuando el usuario confirma "Analizar con IA"
    # Emite la ruta al archivo temporal descargado
    analyze_requested = Signal(str)

    def __init__(self, host: str, port: int, user: str, password: str,
                 current_channel: int = 1, parent=None):
        super().__init__(parent)
        self.host           = host
        self.user           = user
        self.password       = password
        self.port           = port
        self.current_channel = current_channel

        self._playback_speed   = 1.0
        self._speed_presets    = [1.2, 1.5, 2.0, 3.0]
        self._preview_worker   = None
        self._download_worker  = None
        self._temp_file        = None   # Ruta del archivo temporal de descarga
        self._temp_settings    = {}     # Para saber si la descarga coincide con lo actual
        self._preview_active   = False
        self._is_paused        = False
        self._last_frame_pos   = 0
        self._confirmed        = False  # El usuario eligió Analizar o Descargar

        self.setWindowTitle("📼  Historial de Grabaciones — Dahua NVR")
        self.setMinimumSize(920, 680)
        self.setModal(True)
        self._apply_style()
        self._build_ui()

    @property
    def playback_speed(self):
        return self._playback_speed

    def _apply_style(self):
        """
        El diálogo tiene su propio stylesheet completo y autocontenido.
        Esto evita cualquier conflicto con el global QSS de la app.
        """
        self.setStyleSheet("""
            /* ── Diálogo base ── */
            QDialog {
                background-color: #0B0F19;
            }

            /* ── Fondo del contenedor izquierdo ── */
            #leftContainer {
                background-color: #0B0F19;
            }

            /* ── Grupos / Cards ── */
            QGroupBox {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 10px;
                margin-top: 16px;
                padding: 12px 10px 10px 10px;
                color: #3B82F6;
                font-weight: 700;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 2px 6px;
                background-color: #0F172A;
                border-radius: 4px;
            }

            /* ── Labels ── */
            QLabel {
                color: #F8FAFC;
                background: transparent;
            }
            #subtleLabel {
                color: #CBD5E1;
                font-size: 11px;
            }

            /* ── SpinBox ── */
            QSpinBox {
                background-color: #020617;
                border: 1px solid #1E293B;
                border-radius: 6px;
                padding: 4px 6px;
                color: #F8FAFC;
                font-weight: 700;
                font-size: 13px;
                min-width: 50px;
            }
            QSpinBox:hover { border-color: #3B82F6; }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 18px;
                background: #1E293B;
                border-radius: 3px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #334155;
            }

            /* ── ComboBox ── */
            QComboBox {
                background-color: #020617;
                border: 1px solid #1E293B;
                border-radius: 6px;
                padding: 6px 12px;
                color: #F8FAFC;
                font-weight: 600;
                min-height: 30px;
            }
            QComboBox:hover { border-color: #3B82F6; }
            QComboBox::drop-down { border: none; width: 28px; }
            QComboBox::down-arrow {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #CBD5E1;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #020617;
                border: 1px solid #1E293B;
                border-radius: 6px;
                color: #F8FAFC;
                outline: none;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 28px;
                padding-left: 8px;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #1E293B;
                color: #3B82F6;
            }

            /* ── Calendario ── */
            QCalendarWidget {
                background-color: #0F172A;
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: #0F172A;
                selection-background-color: #3B82F6;
                selection-color: #020617;
                color: #F8FAFC;
                alternate-background-color: #0B0F19;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #020617;
                padding: 4px;
            }
            QCalendarWidget QToolButton {
                color: #3B82F6;
                font-weight: 700;
                background: transparent;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QCalendarWidget QToolButton:hover { background-color: #1E293B; }
            QCalendarWidget QSpinBox {
                background-color: #020617;
                border: 1px solid #1E293B;
                color: #F8FAFC;
                padding: 2px 6px;
            }
            QCalendarWidget QHeaderView::section {
                background-color: #020617;
                color: #64748B;
                font-size: 11px;
                font-weight: 700;
                border: none;
                padding: 4px;
            }
            QCalendarWidget QTableView {
                gridline-color: #1E293B;
            }

            /* ── Barra de Progreso ── */
            QProgressBar {
                background-color: #1E293B;
                border-radius: 4px;
                height: 8px;
                text-align: center;
                color: #F8FAFC;
                font-size: 11px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #3B82F6, stop:0.5 #8B5CF6, stop:1 #10B981);
                border-radius: 4px;
            }

            /* ── Botones principales ── */
            QPushButton#primaryBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #3B82F6, stop:1 #0EA5E9);
                color: #020617;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 700;
                min-height: 38px;
            }
            QPushButton#primaryBtn:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #818CF8, stop:1 #89dceb);
            }
            QPushButton#primaryBtn:disabled {
                background: #1E293B;
                color: #64748B;
            }

            QPushButton#warningBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #F59E0B, stop:1 #f9e2af);
                color: #020617;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 700;
                min-height: 38px;
            }
            QPushButton#warningBtn:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #f9c890, stop:1 #fcd5a0);
            }
            QPushButton#warningBtn:disabled {
                background: #1E293B;
                color: #64748B;
            }

            QPushButton#successBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #10B981, stop:1 #14B8A6);
                color: #020617;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton#successBtn:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #c0f0bb, stop:1 #a6f0e0);
            }

            QPushButton#dangerBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #EF4444, stop:1 #eba0ac);
                color: #020617;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton#dangerBtn:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #f5a0b8, stop:1 #f0b8c0);
            }

            /* ── Botón de Velocidad ── */
            QPushButton#speedBtn {
                background-color: rgba(59, 130, 246, 0.12);
                color: #F8FAFC;
                border: 1px solid rgba(59, 130, 246, 0.28);
                border-radius: 8px;
                padding: 7px 10px;
                font-weight: 800;
            }
            QPushButton#speedBtn:hover {
                background-color: rgba(59, 130, 246, 0.22);
                border-color: #3B82F6;
            }

            /* ── Label de Velocidad ── */
            #speedLabel {
                font-size: 28px;
                font-weight: 900;
                color: #3B82F6;
                background: #020617;
                border-radius: 8px;
                padding: 12px;
                border: 1px solid #1E293B;
            }

            /* ── Área de Video ── */
            #videoPreviewFrame {
                background-color: #020617;
                border: 2px solid #1E293B;
                border-radius: 10px;
                color: #585b70;
                font-size: 15px;
            }

            /* ── Card de Acciones ── */
            #actionsCard {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 10px;
            }

            /* ── ScrollBar ── */
            QScrollBar:vertical {
                background: #020617;
                width: 6px;
                border-radius: 3px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #585b70; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)




    # ── Construcción de la UI ─────────────────────────────────────────────
    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ── Panel Izquierdo: Con SCROLL para evitar cortes ────────────────
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        
        left_container = QWidget()
        left_container.setObjectName("leftContainer")
        left_panel = QVBoxLayout(left_container)
        left_panel.setContentsMargins(0, 0, 8, 0)
        left_panel.setSpacing(8)

        # — Selector de Cámara —
        cam_group = QGroupBox("📷  Canal de Cámara")
        cam_layout = QHBoxLayout(cam_group)
        lbl_ch = QLabel("Cámara:")
        lbl_ch.setFixedWidth(56)
        cam_layout.addWidget(lbl_ch)
        self.cmb_channel = QComboBox()
        self.cmb_channel.addItems([f"Cámara {i}" for i in range(1, 17)])
        self.cmb_channel.setCurrentIndex(self.current_channel - 1)
        cam_layout.addWidget(self.cmb_channel)
        left_panel.addWidget(cam_group)

        # — Calendario —
        cal_group = QGroupBox("📅  Fecha")
        cal_layout = QVBoxLayout(cal_group)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setMaximumDate(datetime.date.today())
        self.calendar.setFixedHeight(210)
        cal_layout.addWidget(self.calendar)
        left_panel.addWidget(cal_group)

        # — Selector de Hora —
        time_group = QGroupBox("🕐  Rango de Hora")
        time_layout = QVBoxLayout(time_group)

        # Hora Inicio
        start_row = QHBoxLayout()
        lbl_start = QLabel("Inicio:")
        lbl_start.setFixedWidth(50)
        start_row.addWidget(lbl_start)
        self.spin_start_h = QSpinBox()
        self.spin_start_h.setRange(0, 23)
        self.spin_start_h.setValue(8)
        self.spin_start_h.setSuffix(" h")
        self.spin_start_h.setFixedWidth(75)
        self.spin_start_h.setFixedHeight(35)            
        start_row.addWidget(self.spin_start_h)
        self.spin_start_m = QSpinBox()
        self.spin_start_m.setRange(0, 59)
        self.spin_start_m.setValue(0)
        self.spin_start_m.setSuffix(" m")
        self.spin_start_m.setFixedWidth(75)
        self.spin_start_m.setFixedHeight(35)            
        start_row.addWidget(self.spin_start_m)
        start_row.addStretch()
        time_layout.addLayout(start_row)

        # Hora Fin
        end_row = QHBoxLayout()
        lbl_end = QLabel("Fin:")
        lbl_end.setFixedWidth(50)
        end_row.addWidget(lbl_end)
        self.spin_end_h = QSpinBox()
        self.spin_end_h.setRange(0, 23)
        self.spin_end_h.setValue(8)
        self.spin_end_h.setSuffix(" h")
        self.spin_end_h.setFixedWidth(75)
        self.spin_end_h.setFixedHeight(35)                
        end_row.addWidget(self.spin_end_h)
        self.spin_end_m = QSpinBox()
        self.spin_end_m.setRange(0, 59)
        self.spin_end_m.setValue(15)
        self.spin_end_m.setSuffix(" m")
        self.spin_end_m.setFixedWidth(75)
        self.spin_end_m.setFixedHeight(35)            
        end_row.addWidget(self.spin_end_m)
        end_row.addStretch()
        time_layout.addLayout(end_row)

        # Duración calculada
        self.lbl_duration = QLabel("Duración: 15 minutos")
        self.lbl_duration.setObjectName("subtleLabel")
        time_layout.addWidget(self.lbl_duration)

        # Conectar para actualizar duración
        for spinner in [self.spin_start_h, self.spin_start_m,
                        self.spin_end_h, self.spin_end_m]:
            spinner.valueChanged.connect(self._update_duration_label)

        left_panel.addWidget(time_group)

        # — Selector de Velocidad y Botones —
        speed_group = QGroupBox("⚡  Velocidad de Reproducción")
        speed_layout = QVBoxLayout(speed_group)
        self.lbl_speed_val = QLabel("1.0x")
        self.lbl_speed_val.setObjectName("speedLabel")
        self.lbl_speed_val.setAlignment(Qt.AlignCenter)
        speed_layout.addWidget(self.lbl_speed_val)

        self.btn_speed = QPushButton("Ajustar Velocidad")
        self.btn_speed.setObjectName("speedBtn")
        self.btn_speed.setCursor(Qt.PointingHandCursor)
        self.btn_speed.clicked.connect(self._open_speed_panel)
        speed_layout.addWidget(self.btn_speed)
        left_panel.addWidget(speed_group)

        self.btn_preview = QPushButton("▶  Reproducir")
        self.btn_preview.setObjectName("primaryBtn")
        self.btn_preview.setCursor(Qt.PointingHandCursor)
        self.btn_preview.clicked.connect(self._on_preview)
        left_panel.addWidget(self.btn_preview)

        self.btn_stop_preview = QPushButton("⏸  Pausar")
        self.btn_stop_preview.setObjectName("warningBtn")
        self.btn_stop_preview.setCursor(Qt.PointingHandCursor)
        self.btn_stop_preview.setEnabled(False)
        self.btn_stop_preview.clicked.connect(self._on_pause_toggle)
        left_panel.addWidget(self.btn_stop_preview)

        left_panel.addStretch()
        
        left_scroll.setWidget(left_container)
        main_layout.addWidget(left_scroll, 3)

        # ── Panel Derecho: Video + Acciones ──────────────────────────────
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)

        # Info del fragmento
        self.lbl_fragment_info = QLabel("Seleccione fecha, hora y cámara, luego pulse Reproducir.")
        self.lbl_fragment_info.setObjectName("subtleLabel")
        self.lbl_fragment_info.setWordWrap(True)
        right_panel.addWidget(self.lbl_fragment_info)

        # Área de video
        self.lbl_video = QLabel("📼\n\nSin grabación cargada")
        self.lbl_video.setObjectName("videoPreviewFrame")
        self.lbl_video.setAlignment(Qt.AlignCenter)
        self.lbl_video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lbl_video.setMinimumHeight(300)
        right_panel.addWidget(self.lbl_video)


        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("analysisProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setVisible(False)
        right_panel.addWidget(self.progress_bar)

        # Estado de la conexión
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("subtleLabel")
        right_panel.addWidget(self.lbl_status)

        # ── Botones de Acción (visibles después de previsualizar) ─────────
        self.actions_frame = QFrame()
        self.actions_frame.setObjectName("actionsCard")
        actions_layout = QVBoxLayout(self.actions_frame)
        actions_layout.setContentsMargins(14, 12, 14, 12)
        actions_layout.setSpacing(8)

        confirm_lbl = QLabel("¿Qué desea hacer con este fragmento?")
        confirm_lbl.setObjectName("cardTitle")
        actions_layout.addWidget(confirm_lbl)

        btns_row = QHBoxLayout()
        btns_row.setSpacing(8)

        self.btn_analyze = QPushButton("🤖  Analizar con IA")
        self.btn_analyze.setObjectName("successBtn")
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_analyze.clicked.connect(self._on_analyze)
        btns_row.addWidget(self.btn_analyze)

        self.btn_download = QPushButton("💾  Guardar Video Local")
        self.btn_download.setObjectName("warningBtn")
        self.btn_download.setToolTip("Guarda el video permanentemente en tu disco (sin descargar de nuevo)")
        self.btn_download.setCursor(Qt.PointingHandCursor)
        self.btn_download.clicked.connect(self._on_download)
        btns_row.addWidget(self.btn_download)

        self.btn_discard = QPushButton("🗑  Descartar")
        self.btn_discard.setObjectName("dangerBtn")
        self.btn_discard.setCursor(Qt.PointingHandCursor)
        self.btn_discard.clicked.connect(self._on_discard)
        btns_row.addWidget(self.btn_discard)

        actions_layout.addLayout(btns_row)

        # Progreso de descarga
        self.download_progress = QProgressBar()
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(0)
        self.download_progress.setTextVisible(True)
        self.download_progress.setFormat("Descargando... %p%")
        self.download_progress.setFixedHeight(22)
        self.download_progress.setVisible(False)
        actions_layout.addWidget(self.download_progress)

        self.actions_frame.setVisible(False)
        right_panel.addWidget(self.actions_frame)

        main_layout.addLayout(right_panel, 5)

    # ── Lógica ────────────────────────────────────────────────────────────

    def _update_duration_label(self):
        try:
            start_mins = self.spin_start_h.value() * 60 + self.spin_start_m.value()
            end_mins   = self.spin_end_h.value()   * 60 + self.spin_end_m.value()
            diff = end_mins - start_mins
            if diff <= 0:
                self.lbl_duration.setText("⚠️  La hora de fin debe ser posterior al inicio")
                self.lbl_duration.setStyleSheet("color: #EF4444; font-size: 11px;")
            else:
                h, m = divmod(diff, 60)
                if h > 0:
                    txt = f"Duración: {h}h {m}m ({diff} minutos)"
                else:
                    txt = f"Duración: {diff} minutos"
                self.lbl_duration.setText(txt)
                self.lbl_duration.setStyleSheet("color: #10B981; font-size: 11px;")
        except Exception:
            pass

    def _get_datetime_range(self):
        """Retorna (start_dt, end_dt, duration_secs) o None si hay error."""
        qdate = self.calendar.selectedDate()
        date  = datetime.date(qdate.year(), qdate.month(), qdate.day())

        start_h = self.spin_start_h.value()
        start_m = self.spin_start_m.value()
        end_h   = self.spin_end_h.value()
        end_m   = self.spin_end_m.value()

        start_dt = datetime.datetime.combine(date, datetime.time(start_h, start_m, 0))
        end_dt   = datetime.datetime.combine(date, datetime.time(end_h,   end_m,   0))

        if end_dt <= start_dt:
            return None

        # Nueva restricción: No permitir futuro
        now = datetime.datetime.now()
        if start_dt > now:
            return "FUTURE_START"
        if end_dt > now:
            return "FUTURE_END"

        duration_secs = int((end_dt - start_dt).total_seconds())
        return start_dt, end_dt, duration_secs

    def _get_playback_url(self):
        """Construye la URL de playback con los parámetros actuales."""
        result = self._get_datetime_range()
        if not result:
            return None, None, None
        start_dt, end_dt, duration_secs = result
        channel = self.cmb_channel.currentIndex() + 1
        url = _build_dahua_playback_url(
            host=self.host, port=self.port,
            user=self.user, password=self.password,
            channel=channel,
            start_dt=start_dt, end_dt=end_dt
        )
        return url, start_dt, duration_secs

    def _on_preview(self):
        """Descarga (si es necesario) y reproduce. Soporta reanudación local."""
        result = self._get_datetime_range()
        if result is None:
            QMessageBox.warning(self, "Rango inválido", "La hora de fin debe ser posterior a la de inicio.")
            return
        if result == "FUTURE_START" or result == "FUTURE_END":
            QMessageBox.warning(self, "Fecha/Hora Inválida", 
                                "No se puede previsualizar el futuro.\n"
                                "Por favor seleccione un rango que ya haya sucedido.")
            return

        start_dt, end_dt, duration_secs = result
        channel = self.cmb_channel.currentIndex() + 1
        
        # Validar si el archivo temporal ya existe y coincide con la selección actual
        current_req = {
            "ch": channel,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat()
        }

        # 1. Si existe y coincide, REANUDAR/REPRODUCIR LOCALMENTE (sin descargar)
        if self._temp_file and os.path.exists(self._temp_file) and self._temp_settings == current_req:
            print("[HISTORIAL] Reanudando reproducción local instantánea.")
            self.btn_preview.setEnabled(False)
            self.btn_stop_preview.setEnabled(True)
            self._start_local_preview(self._temp_file)
            return

        # 2. Si no coincide o no existe, DESCARGAR (Paso lento una sola vez)
        self._stop_preview_worker()
        self._last_frame_pos = 0 # Resetear posición si es descarga nueva
        
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.stop()

        url, _, _ = self._get_playback_url()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temp_dir = os.path.join(base_dir, "captures")
        os.makedirs(temp_dir, exist_ok=True)
        self._temp_file = os.path.join(temp_dir, "_temp_playback_preview.mp4")
        self._temp_settings = current_req

        self.btn_preview.setEnabled(False)
        self.btn_stop_preview.setEnabled(True)
        self.btn_stop_preview.setText("⏸  Pausar")
        self.lbl_status.setText("⏳ Descargando fragmento para reproducción fluida...")
        self.lbl_video.setText("⏳\n\nPreparando video local...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self._download_worker = HistoryDownloadWorker(
            url, self._temp_file, duration_secs,
            host=self.host, port=self.port,
            user=self.user, password=self.password,
            channel=channel, start_dt=start_dt, end_dt=end_dt
        )
        self._download_worker.progress_updated.connect(self.progress_bar.setValue)
        self._download_worker.status_updated.connect(self.lbl_status.setText)
        self._download_worker.finished.connect(self._on_initial_download_done)
        self._download_worker.error_occurred.connect(self._on_preview_failed)
        self._download_worker.start()

    def _on_initial_download_done(self, path: str):
        """Se llama solo tras la primera descarga. Muestra botones de guardado."""
        self.actions_frame.setVisible(True) # MOSTRAR BOTONES DE GUARDADO DE INMEDIATO
        self._start_local_preview(path)

    def _start_local_preview(self, video_path: str):
        """Inicia el reproductor sobre el archivo local desde la última posición."""
        self.lbl_status.setText("▶  Reproduciendo...")
        self._preview_worker = HistoryPreviewWorker(video_path, start_frame=self._last_frame_pos)
        self._preview_worker.set_speed(self._playback_speed) # ASEGURAR VELOCIDAD ANTES DE START
        self._preview_worker.frame_ready.connect(self._on_preview_frame)
        self._preview_worker.connection_failed.connect(self._on_preview_failed)
        self._preview_worker.progress_updated.connect(self.progress_bar.setValue)
        self._preview_worker.finished.connect(self._on_preview_finished)
        self._preview_worker.start()
        self._preview_active = True
        self._is_paused = False
        self.btn_stop_preview.setText("⏸  Pausar")

    def _on_pause_toggle(self):
        """Pausa y guarda la posición actual."""
        if self._preview_worker and self._preview_worker.isRunning():
            # Guardamos la posición del frame actual antes de cerrar
            self._last_frame_pos = self._preview_worker._frame_count
            self._stop_preview_worker()
            self._is_paused = True
            self.lbl_status.setText("⏸  Pausado.")
            self.btn_preview.setEnabled(True)
            self.btn_preview.setText("▶  Reanudar")
            self.btn_stop_preview.setText("⏹  Detener")
        else:
            # Si ya estaba "en pausa" y pulsan el botón de detener/pausa de nuevo
            self._last_frame_pos = 0
            self.btn_preview.setText("▶  Reproducir")
            self.btn_stop_preview.setEnabled(False)
            self.lbl_status.setText("⏹  Detenido.")

    def _on_speed_changed(self, v: float):
        self._playback_speed = float(v)
        self.btn_speed.setText(f"Ajustar ({self.playback_speed}x)")
        self.lbl_speed_val.setText(f"{self.playback_speed}x")
        self._apply_current_speed()

    def _apply_current_speed(self):
        """Actualiza la velocidad del worker instantáneamente."""
        if self._preview_worker:
            try:
                self._preview_worker.set_speed(self._playback_speed)
            except ValueError:
                pass

    def _open_speed_panel(self):
        """Panel dinámico para velocidad (slider + presets + +/-)."""
        if hasattr(self, "_speed_panel") and self._speed_panel and self._speed_panel.isVisible():
            self._speed_panel.close()
            return
            
        dlg = QDialog(self)
        dlg.setObjectName("speedPanel")
        dlg.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        dlg.setAttribute(Qt.WA_TranslucentBackground, True)

        card = QFrame(dlg)
        card.setObjectName("speedPanelCard")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 110))
        card.setGraphicsEffect(shadow)
        card.setMinimumWidth(320)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(16, 14, 16, 18)
        root.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        title = QLabel("Velocidad de reproducción")
        title.setObjectName("speedPanelTitle")
        lay.addWidget(title)

        self._speed_value_lbl = QLabel(f"{float(self._playback_speed):.1f}x")
        self._speed_value_lbl.setObjectName("speedPanelValue")
        self._speed_value_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._speed_value_lbl)

        row = QHBoxLayout()
        row.setSpacing(12)

        btn_minus = QPushButton("–")
        btn_minus.setObjectName("speedAdjustBtn")
        btn_minus.setFixedSize(36, 36)
        btn_plus = QPushButton("+")
        btn_plus.setObjectName("speedAdjustBtn")
        btn_plus.setFixedSize(36, 36)

        slider = QSlider(Qt.Horizontal)
        slider.setObjectName("speedPanelSlider")
        slider.setRange(5, 150)  # 0.5x..15.0x
        slider.setSingleStep(1)
        slider.setPageStep(5)
        slider.setValue(int(round(float(self._playback_speed) * 10)))

        def set_from_slider(v_int: int):
            v = max(0.5, min(15.0, round(v_int / 10.0, 1)))
            self._speed_value_lbl.setText(f"{v:.1f}x")
            self._on_speed_changed(v)
            refresh_chip_states(v)

        slider.valueChanged.connect(set_from_slider)
        btn_minus.clicked.connect(lambda: slider.setValue(max(slider.minimum(), slider.value() - 1)))
        btn_plus.clicked.connect(lambda: slider.setValue(min(slider.maximum(), slider.value() + 1)))

        row.addWidget(btn_minus)
        row.addWidget(slider, 1)
        row.addWidget(btn_plus)
        lay.addLayout(row)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        chip_buttons = []

        def make_chip(label: str, speed: float):
            b = QPushButton(label)
            b.setObjectName("speedChip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda: slider.setValue(int(round(speed * 10))))
            chip_buttons.append((b, speed))
            return b

        chips.addWidget(make_chip("Normal", 1.0))
        for v in self._speed_presets:
            if abs(v - 1.0) < 1e-9: continue
            chips.addWidget(make_chip(f"{v:.2g}", float(v)))

        chips.addStretch()
        lay.addLayout(chips)

        def refresh_chip_states(v: float):
            v = round(float(v), 1)
            for b, sv in chip_buttons:
                b.setChecked(round(float(sv), 1) == v)

        refresh_chip_states(float(self._playback_speed))

        anchor = self.btn_speed.mapToGlobal(QPoint(0, self.btn_speed.height()))
        dlg.adjustSize()

        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None

        x = anchor.x() - max(0, dlg.width() - self.btn_speed.width())
        y = anchor.y() + 10
        if avail is not None:
            x = max(avail.left() + 8, min(x, avail.right() - dlg.width() - 8))
            y = max(avail.top() + 8, min(y, avail.bottom() - dlg.height() - 8))
        dlg.move(x, y)

        self._speed_panel = dlg
        dlg.show()

    def _on_stop_preview(self):
        self._stop_preview_worker()
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.stop()
        self.lbl_status.setText("Previsualización detenida.")
        self.btn_preview.setEnabled(True)
        self.btn_stop_preview.setEnabled(False)

    def _stop_preview_worker(self):
        print(f"[HISTORIAL] Solicitando detención del preview_worker... Vivo: {bool(self._preview_worker)}")
        if self._preview_worker and self._preview_worker.isRunning():
            try:
                self._preview_worker.frame_ready.disconnect()
                self._preview_worker.connection_failed.disconnect()
                self._preview_worker.progress_updated.disconnect()
                self._preview_worker.finished.disconnect()
                print("[HISTORIAL] Señales de worker desconectadas correctamente.")
            except Exception as e:
                print(f"[HISTORIAL] Error desconectando señales (no es grave): {e}")
                pass
            
            # Frenar hilo lógicamente
            self._preview_worker.stop()
            print("[HISTORIAL] Se ordenó stop() del worker.")

            # Evitar recolección de basura destructiva antes de que el C++ QThread termine
            if not hasattr(self, '_dead_workers'):
                self._dead_workers = []
            
            self._dead_workers.append(self._preview_worker)
            w = self._preview_worker
            
            def _clean(worker=w):
                try:
                    if hasattr(self, '_dead_workers') and worker in self._dead_workers:
                        self._dead_workers.remove(worker)
                    print("[HISTORIAL] El worker de UI finalizó su ciclo vital completamente (safely collected).")
                except Exception as ex:
                    print(f"[HISTORIAL] Log de limpieza falló: {ex}")

            try:
                w.finished.connect(_clean)
            except Exception:
                pass
            
            self._preview_worker = None
        self._preview_active = False
        print("[HISTORIAL] _stop_preview_worker completado con exito.")

    def _on_preview_frame(self, qimg: QImage):
        """Muestra cada fotograma del fragmento histórico."""
        pixmap = QPixmap.fromImage(qimg)
        self.lbl_video.setPixmap(
            pixmap.scaled(self.lbl_video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        if self.lbl_status.text() != "▶  Reproduciendo…":
            self.lbl_status.setText("▶  Reproduciendo…")

    def _on_preview_failed(self, msg: str):
        """Maneja el error de conexión al NVR."""
        self.lbl_video.setText("❌\n\nError de conexión")
        self.lbl_video.setPixmap(QPixmap())
        self.lbl_status.setText("❌  Sin conexión")
        self.progress_bar.setVisible(False)
        self.btn_preview.setEnabled(True)
        self.btn_stop_preview.setEnabled(False)
        QMessageBox.critical(
            self, "Error de Conexión al NVR", msg
        )

    def _on_preview_finished(self):
        """Se llama cuando el fragmento termina de reproducirse."""
        self._last_frame_pos = 0 # Resetear al finalizar
        self.progress_bar.setValue(100)
        self.lbl_status.setText("✅  Reproducción completa.")
        self.btn_preview.setEnabled(True)
        self.btn_preview.setText("▶  Reproducir")
        self.btn_stop_preview.setEnabled(False)
        # Asegurarse de que las acciones se vean
        self.actions_frame.setVisible(True)

    def _on_analyze(self):
        """
        Descarga (o reutiliza) el fragmento temporal y emite la señal
        'analyze_requested' con la ruta para que MainWindow lo analice con YOLO.
        """
        url, start_dt, duration_secs = self._get_playback_url()
        if not url:
            return
            
        # 1. Si ya se previsualizó y el archivo temporal existe, no lo descargues de nuevo!
        if self._temp_file and os.path.exists(self._temp_file):
            print(f"[HISTORIAL] Reutilizando archivo temporal para análisis: {self._temp_file}")
            self._confirmed = True
            self.analyze_requested.emit(self._temp_file)
            self.accept()
            return

        if not _ffmpeg_available():
            QMessageBox.critical(
                self, "FFmpeg no encontrado",
                "Para descargar el fragmento y analizarlo con IA se necesita FFmpeg.\n\n"
                "Descárguelo de https://ffmpeg.org/download.html\n"
                "y asegúrese de que esté en el PATH del sistema.\n\n"
                "Alternativamente, puede previsualizar en tiempo real y usar la Cámara en Vivo."
            )
            return

        # 2. Si no ha sido previsualizado, proceder a descargar
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        captures_dir = os.path.join(base_dir, "captures")
        os.makedirs(captures_dir, exist_ok=True)
        ts = start_dt.strftime("%Y%m%d_%H%M%S")
        channel = self.cmb_channel.currentIndex() + 1
        tmp_path = os.path.join(captures_dir, f"_hist_cam{channel}_{ts}.mp4")
        self._temp_file = tmp_path

        # Deshabilitar botones durante descarga
        self.btn_analyze.setEnabled(False)
        self.btn_download.setEnabled(False)
        self.btn_discard.setEnabled(False)
        self.download_progress.setVisible(True)
        self.download_progress.setFormat("Preparando para IA... %p%")

        result2 = self._get_datetime_range()
        start_dt2, end_dt2, _ = result2
        self._download_worker = HistoryDownloadWorker(
            url, tmp_path, duration_secs,
            host=self.host, port=self.port,
            user=self.user, password=self.password,
            channel=self.cmb_channel.currentIndex() + 1,
            start_dt=start_dt2, end_dt=end_dt2
        )
        self._download_worker.progress_updated.connect(self.download_progress.setValue)
        self._download_worker.finished.connect(self._on_analysis_download_done)
        self._download_worker.error_occurred.connect(self._on_download_error)
        self._download_worker.start()

    def _on_analysis_download_done(self, path: str):
        """El fragmento se descargó para análisis IA. Emite la señal y cierra."""
        self.download_progress.setVisible(False)
        self._confirmed = True
        self.analyze_requested.emit(path)
        self.accept()

    def _on_download(self):
        """Guarda (o descarga) de manera permanente el fragmento en la PC."""
        url, start_dt, duration_secs = self._get_playback_url()
        if not url:
            return

        channel = self.cmb_channel.currentIndex() + 1
        ts = start_dt.strftime("%Y%m%d_%H%M")
        default_name = f"Cam{channel}_{ts}.mp4"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Grabación Permanentemente",
            os.path.expanduser(f"~\\Downloads\\{default_name}"),
            "Video MP4 (*.mp4);;Todos los archivos (*)"
        )
        if not save_path:
            return

        # 1. Si ya se previsualizó localmente, simplemente copiar el archivo (Instantáneo)
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                import shutil
                shutil.copy(self._temp_file, save_path)
                QMessageBox.information(
                    self, "Guardado exitoso",
                    f"✅ El video se guardó permanentemente en:\n{save_path}"
                )
                self._confirmed = True
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")
            return

        # 2. Si no, proceder a descargar desde cero desde el NVR
        if not _ffmpeg_available():
            QMessageBox.critical(
                self, "FFmpeg no encontrado",
                "La descarga requiere FFmpeg instalado en el sistema.\n"
                "Descárguelo de https://ffmpeg.org/download.html"
            )
            return

        # UI
        self.btn_analyze.setEnabled(False)
        self.btn_download.setEnabled(False)
        self.btn_discard.setEnabled(False)
        self.download_progress.setVisible(True)
        self.download_progress.setFormat("Descargando... %p%")

        result3 = self._get_datetime_range()
        start_dt3, end_dt3, _ = result3
        self._download_worker = HistoryDownloadWorker(
            url, save_path, duration_secs,
            host=self.host, port=self.port,
            user=self.user, password=self.password,
            channel=self.cmb_channel.currentIndex() + 1,
            start_dt=start_dt3, end_dt=end_dt3
        )
        self._download_worker.progress_updated.connect(self.download_progress.setValue)
        self._download_worker.finished.connect(self._on_user_download_done)
        self._download_worker.error_occurred.connect(self._on_download_error)
        self._download_worker.start()

    def _on_user_download_done(self, path: str):
        """La descarga del usuario se completó."""
        self.download_progress.setVisible(False)
        self._confirmed = True
        QMessageBox.information(
            self, "Descarga Completa",
            f"✅ Grabación guardada exitosamente en:\n{path}"
        )
        self.btn_analyze.setEnabled(True)
        self.btn_download.setEnabled(True)
        self.btn_discard.setEnabled(True)

    def _on_download_error(self, msg: str):
        """Maneja errores de descarga."""
        self.download_progress.setVisible(False)
        self.btn_analyze.setEnabled(True)
        self.btn_download.setEnabled(True)
        self.btn_discard.setEnabled(True)
        QMessageBox.critical(self, "Error de Descarga", msg)

    def _on_discard(self):
        """Descarta el fragmento sin guardar nada."""
        self._stop_preview_worker()
        self._cleanup_temp_file()
        self.reject()

    def _cleanup_temp_file(self):
        """Elimina el archivo temporal si existe y no fue confirmado para IA."""
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.remove(self._temp_file)
            except Exception:
                pass
        self._temp_file = None

    def closeEvent(self, event):
        """Asegura que todos los workers se detengan al cerrar el diálogo."""
        print("[HISTORIAL] closeEvent convocado. Dialogo pidiendo ser cerrado.")
        try:
            self._stop_preview_worker()
            
            if self._download_worker and self._download_worker.isRunning():
                print("[HISTORIAL] Deteniendo download_worker...")
                self._download_worker.stop()
                # Crucial: esperar a que el hilo termine realmente (max 2s) para evitar el crash de Qt
                self._download_worker.wait(2000) 
                
            # Si el usuario no confirmó usar el archivo, limpiarlo
            if not self._confirmed:
                print("[HISTORIAL] Limpiando archivo temporal (sin confirmar)...")
                self._cleanup_temp_file()
                
            print("[HISTORIAL] Limpieza de closeEvent exitosa.")
        except Exception as e:
            print(f"[HISTORIAL] EXCEPCIÓN en closeEvent: {e}")
            
        super().closeEvent(event)
        print("[HISTORIAL] Diálogo de historial cerrado.")
