
import sys
import os
import cv2
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QProgressBar, 
                               QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
                               QFrame, QComboBox)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QImage, QPixmap, QFont, QColor

# Ensure core is in path
_base_path = os.path.dirname(os.path.abspath(__file__))
if _base_path not in sys.path:
    sys.path.insert(0, _base_path)

from core.yolo_manager import YoloAnalyzerWorker, VideoPlayerWorker

class DebugWindow(QMainWindow):
    def __init__(self, video_path=None):
        super().__init__()
        self.setWindowTitle("LogiCheck Debugger — Análisis Directo")
        self.setMinimumSize(1280, 850)
        
        # Default settings
        self.model_path = os.path.join(_base_path, "training", "runs", "bultos_cemento2", "weights", "best.pt")
        self.default_video = video_path or os.path.join(_base_path, "resources", "Videos", "bulto.mp4")
        self.line_pos = 0.19  # 19% from top
        
        # Central Widget Styling
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")
        
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(15)
        
        # Header Section
        header = QHBoxLayout()
        self.status_label = QLabel(f"📹 Video: {os.path.basename(self.default_video)}")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #89b4fa;")
        header.addWidget(self.status_label)
        header.addStretch()
        
        # Load Video Button in Header
        self.btn_load_new = QPushButton("📂 Cargar Video")
        self.btn_load_new.setFixedHeight(35)
        self.btn_load_new.setFixedWidth(150)
        self.btn_load_new.setStyleSheet("""
            QPushButton { background-color: #45475a; border-radius: 5px; padding: 5px; font-weight: bold;}
            QPushButton:hover { background-color: #585b70; }
        """)
        self.btn_load_new.clicked.connect(self.change_video)
        header.addWidget(self.btn_load_new)
        root_layout.addLayout(header)
        
        # Main Work Area
        work_area = QHBoxLayout()
        root_layout.addLayout(work_area)
        
        # Video Section (Left)
        video_container = QVBoxLayout()
        self.video_frame = QLabel("Cargue un video para iniciar")
        self.video_frame.setAlignment(Qt.AlignCenter)
        self.video_frame.setStyleSheet("""
            background-color: #11111b; 
            border: 2px solid #313244; 
            border-radius: 10px;
            font-size: 16px; 
            color: #6c7086;
        """)
        self.video_frame.setMinimumSize(850, 480)
        video_container.addWidget(self.video_frame)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #313244; border-radius: 5px; border: none;}
            QProgressBar::chunk { background-color: #89b4fa; border-radius: 5px; }
        """)
        video_container.addWidget(self.progress_bar)
        
        # Playback Controls (Immediately under video)
        playback_controls = QHBoxLayout()
        playback_controls.setSpacing(10)
        
        btn_style = """
            QPushButton { background-color: #313244; border-radius: 5px; padding: 8px; font-weight: bold; min-width: 80px;}
            QPushButton:hover { background-color: #45475a; }
            QPushButton:pressed { background-color: #585b70; }
        """
        
        self.btn_rewind = QPushButton("⏪ -10s")
        self.btn_rewind.setStyleSheet(btn_style)
        self.btn_rewind.clicked.connect(self.rewind_10s)
        playback_controls.addWidget(self.btn_rewind)
        
        self.btn_restart = QPushButton("🔄 Reiniciar")
        self.btn_restart.setStyleSheet(btn_style)
        self.btn_restart.clicked.connect(self.restart_video)
        playback_controls.addWidget(self.btn_restart)
        
        self.btn_forward = QPushButton("+10s ⏩")
        self.btn_forward.setStyleSheet(btn_style)
        self.btn_forward.clicked.connect(self.forward_10s)
        playback_controls.addWidget(self.btn_forward)
        
        playback_controls.addStretch()
        
        # Speed Combo
        speed_layout = QHBoxLayout()
        speed_label = QLabel("🚀 Velocidad:")
        speed_label.setStyleSheet("font-weight: bold; color: #a6e3a1;")
        speed_layout.addWidget(speed_label)
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["1.0x", "2.0x", "3.0x", "5.0x", "10.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setFixedWidth(80)
        self.speed_combo.setStyleSheet("""
            QComboBox { background-color: #313244; border-radius: 5px; padding: 5px; border: 1px solid #45475a; }
            QComboBox::drop-down { border: none; }
        """)
        self.speed_combo.currentIndexChanged.connect(self.update_speed)
        speed_layout.addWidget(self.speed_combo)
        playback_controls.addLayout(speed_layout)
        
        video_container.addLayout(playback_controls)
        work_area.addLayout(video_container, 3)
        
        # Side Panel (Right)
        side_panel = QVBoxLayout()
        side_panel.setSpacing(15)
        
        # Stats Table
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #181825; border-radius: 10px;")
        stats_vbox = QVBoxLayout(stats_frame)
        
        stats_title = QLabel("📊 Conteo IA")
        stats_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f9e2af; padding-bottom: 5px;")
        stats_vbox.addWidget(stats_title)
        
        self.table_counts = QTableWidget(3, 2)
        self.table_counts.setHorizontalHeaderLabels(["Material", "Unidades"])
        self.table_counts.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_counts.verticalHeader().setVisible(False)
        self.table_counts.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_counts.setStyleSheet("""
            QTableWidget { background-color: transparent; border: none; gridline-color: #313244; }
            QHeaderView::section { background-color: #313244; color: #cdd6f4; border: none; padding: 5px; }
            QTableWidget::item { padding: 5px; font-size: 14px; }
        """)
        
        items = [("Cemento", "0"), ("Tub. Presión", "0"), ("Tub. Sanitaria", "0")]
        for row, (mat, count) in enumerate(items):
            self.table_counts.setItem(row, 0, QTableWidgetItem(mat))
            self.table_counts.setItem(row, 1, QTableWidgetItem(count))
            self.table_counts.item(row, 1).setTextAlignment(Qt.AlignCenter)
        
        stats_vbox.addWidget(self.table_counts)
        side_panel.addWidget(stats_frame, 1)
        
        # Debug Logs Frame
        log_frame = QFrame()
        log_frame.setStyleSheet("background-color: #181825; border-radius: 10px;")
        log_vbox = QVBoxLayout(log_frame)
        log_title = QLabel("📝 Registros")
        log_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #fab387;")
        log_vbox.addWidget(log_title)
        
        self.log_area = QLabel("Esperando inicio...")
        self.log_area.setWordWrap(True)
        self.log_area.setAlignment(Qt.AlignTop)
        self.log_area.setStyleSheet("color: #bac2de; font-family: 'Consolas'; font-size: 12px;")
        log_vbox.addWidget(self.log_area)
        log_vbox.addStretch()
        
        side_panel.addWidget(log_frame, 2)
        
        # Bottom Big Button
        self.btn_start = QPushButton("🚀 INICIAR ANÁLISIS DE VIDEO")
        self.btn_start.setFixedHeight(60)
        self.btn_start.setStyleSheet("""
            QPushButton { 
                background-color: #a6e3a1; 
                color: #11111b; 
                border-radius: 10px; 
                font-weight: 900; 
                font-size: 18px;
            }
            QPushButton:hover { background-color: #94e2d5; }
            QPushButton:disabled { background-color: #45475a; color: #6c7086; }
        """)
        self.btn_start.clicked.connect(self.start_debug)
        side_panel.addWidget(self.btn_start)
        
        work_area.addLayout(side_panel, 1)
        
        # State
        self.analyzer = None
        self.player = None
        self.tracking_data = None
        self.fps = 25.0
        
        # Auto-start after a short delay
        QTimer.singleShot(1500, self.start_debug)

    def update_speed(self):
        if self.player:
            speed = float(self.speed_combo.currentText().replace("x", ""))
            self.player.set_speed(speed)
            self.log_area.setText(f"Velocidad cambiada a {speed}x")

    def change_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Video", "", "Videos (*.mp4 *.avi *.dav *.mkv)")
        if path:
            if self.analyzer and self.analyzer.isRunning():
                self.analyzer.stop()
                self.analyzer.wait()
            if self.player and self.player.isRunning():
                self.player.stop()
                self.player.wait()
            
            self.default_video = path
            self.status_label.setText(f"📹 Video: {os.path.basename(path)}")
            self.btn_start.setEnabled(True)
            self.log_area.setText(f"Video cargado.\nReady.")
            self.update_counts({"Cemento": 0, "Tubería Presión": 0, "Tubería Sanitaria": 0})
            self.progress_bar.setValue(0)
            self.video_frame.setPixmap(QPixmap())
            self.video_frame.setText("Nuevo video cargado.\nClick en INICIAR.")
            
    def start_debug(self):
        if not os.path.exists(self.default_video):
            self.log_area.setText("Error: Video no encontrado.")
            return
            
        self.btn_start.setEnabled(False)
        self.log_area.setText("Iniciando análisis YOLO...\nEsto puede tardar unos segundos.")
        
        self.analyzer = YoloAnalyzerWorker(self.default_video, self.model_path, line_pos=self.line_pos)
        self.analyzer.progress_updated.connect(self.progress_bar.setValue)
        self.analyzer.finished_analysis.connect(self.on_analysis_finished)
        self.analyzer.error_occurred.connect(self.on_error)
        self.analyzer.start()

    def on_error(self, err):
        self.log_area.setText(f"ERROR: {err}")
        self.btn_start.setEnabled(True)

    def on_analysis_finished(self, final_counts, count_history, tracking_data, fps):
        self.tracking_data = tracking_data
        self.fps = fps
        
        total_boxes = sum(len(boxes) for boxes in tracking_data.values())
        frames_with_data = sum(1 for boxes in tracking_data.values() if len(boxes) > 0)
        
        self.log_area.setText(f"Análisis OK.\nFrames: {len(tracking_data)}\nDet: {total_boxes}\nFrames c/det: {frames_with_data}\nIniciando reproducción...")
        
        self.player = VideoPlayerWorker(self.default_video, {}, self.tracking_data, fps, line_pos=self.line_pos)
        self.player.frame_ready.connect(self.update_frame)
        self.player.progress_updated.connect(self.progress_bar.setValue)
        self.player.counts_updated.connect(self.update_counts)
        self.player.finished.connect(self.on_playback_finished)
        self.player.start()
        self.update_speed()

    def rewind_10s(self):
        if self.player:
            self.player.seek_backward_10s()
            self.update_counts({"Cemento": 0, "Tubería Presión": 0, "Tubería Sanitaria": 0})

    def forward_10s(self):
        if self.player:
            self.player.seek_forward_10s()
            self.update_counts({"Cemento": 0, "Tubería Presión": 0, "Tubería Sanitaria": 0})

    def restart_video(self):
        if self.player:
            self.player.seek_to_start()
            self.update_counts({"Cemento": 0, "Tubería Presión": 0, "Tubería Sanitaria": 0})

    def update_frame(self, qimg):
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(self.video_frame.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_frame.setPixmap(scaled)

    def update_counts(self, counts):
        self.table_counts.item(0, 1).setText(str(counts.get("Cemento", 0)))
        self.table_counts.item(1, 1).setText(str(counts.get("Tubería Presión", 0)))
        self.table_counts.item(2, 1).setText(str(counts.get("Tubería Sanitaria", 0)))

    def on_playback_finished(self):
        self.log_area.setText("Playback finalizado.")
        self.btn_start.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DebugWindow()
    window.show()
    sys.exit(app.exec())
