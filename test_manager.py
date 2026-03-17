import cv2
import time
from core.yolo_manager import YoloAnalyzerWorker, VideoPlayerWorker
from PySide6.QtCore import QCoreApplication
import sys

def mock_analysis_finished(fc, ch, td, fps):
    print("FINISHED ANALYSIS")
    print(f"Tracking Data Keys: {list(td.keys())[:10]} ... {list(td.keys())[-10:] if len(td) > 10 else ''}")
    frames_with_boxes = 0
    for k, boxes in td.items():
        if boxes: frames_with_boxes += 1
    print(f"Frames with boxes: {frames_with_boxes} out of {len(td)}")
    sys.exit()

if __name__ == '__main__':
    app = QCoreApplication([])
    analyzer = YoloAnalyzerWorker('C:/Users/samuv/Desktop/Programas_mios/LogiCheck/resources/Videos/bulto.mp4', 'C:/Users/samuv/Desktop/Programas_mios/LogiCheck/training/runs/bultos_cemento/weights/best.pt', 0.19)
    analyzer.finished_analysis.connect(mock_analysis_finished)
    analyzer.start()
    app.exec()
