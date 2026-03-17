from ultralytics import YOLO
import cv2

model = YOLO('C:/Users/samuv/Desktop/Programas_mios/LogiCheck/training/runs/bultos_cemento/weights/best.pt')
cap = cv2.VideoCapture('C:/Users/samuv/Desktop/Programas_mios/LogiCheck/resources/Videos/bulto.mp4')
ret, frame = cap.read()
if ret:
    results = model.track(frame, persist=True)
    result = results[0]
    print("Boxes:", result.boxes)
    if result.boxes is not None:
        print("xyxy:", result.boxes.xyxy)
        print("cls:", result.boxes.cls)
        print("id:", result.boxes.id)
cap.release()
