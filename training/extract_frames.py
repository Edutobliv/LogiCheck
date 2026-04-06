import cv2
import os
import sys

def extract_frames(video_path, output_folder, interval=0.5):
    """
    Extracts frames from a video every 'interval' seconds.
    """
    if not os.path.exists(video_path):
        print(f"Error: Video file {video_path} not found.")
        return

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps:
        print(f"Error: Could not read FPS for {video_path}")
        return
        
    interval_frames = int(fps * interval)
    count = 0
    saved_count = 0
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if count % interval_frames == 0:
            frame_name = f"{video_name}_frame_{saved_count:04d}.jpg"
            save_path = os.path.join(output_folder, frame_name)
            cv2.imwrite(save_path, frame)
            saved_count += 1
            print(f"Saved: {save_path}", end='\r')
            
        count += 1

    cap.release()
    print(f"\nFinished extracting {saved_count} frames from {video_name}.")

if __name__ == "__main__":
    base_dir = r"C:\Users\samuv\Desktop\Programas_mios\LogiCheck"
    video_dir = os.path.join(base_dir, "resources", "Entrenamiento")
    output_dir = os.path.join(base_dir, "training", "raw_frames")
    
    # Escanear todos los videos en la carpeta Entrenamiento
    videos = [f for f in os.listdir(video_dir) if f.lower().endswith(('.mp4', '.avi', '.mov'))]
    
    print(f"Encontrados {len(videos)} videos para procesar.")
    
    for v in videos:
        v_path = os.path.join(video_dir, v)
        # Extraemos un frame cada 2 segundos para evitar saturación de datos similares
        extract_frames(v_path, output_dir, interval=2.0)
