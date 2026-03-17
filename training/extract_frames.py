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
    video_dir = os.path.join(base_dir, "resources", "Videos")
    output_dir = os.path.join(base_dir, "training", "raw_frames")
    
    videos = ["bulto.mp4", "bulto2.mp4", "bulto_dawkgdhu.mp4"]
    
    for v in videos:
        v_path = os.path.join(video_dir, v)
        if os.path.exists(v_path):
            extract_frames(v_path, output_dir)
        else:
            print(f"Skipping {v}, file not found.")
