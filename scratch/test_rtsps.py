"""
Test de RTSPS (RTSP sobre TLS) en el NVR Dahua.
Algunos NVR Dahua sirven RTSP sobre HTTPS (puerto 443 con TLS).
"""
import os
import cv2
import time

# Opciones para RTSP sobre TCP con soporte TLS
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"
    "stimeout;15000000|"
    "analyzeduration;10000000|"
    "probesize;10000000|"
    "fflags;nobuffer"
)

urls = [
    ("RTSPS (TLS) canal 1",    "rtsps://Samuel:Samuel123.@100.111.182.33:443/cam/realmonitor?channel=1&subtype=1"),
    ("RTSPS sin punto en pass", "rtsps://Samuel:Samuel123@100.111.182.33:443/cam/realmonitor?channel=1&subtype=1"),
    ("RTSPS canal 9",           "rtsps://Samuel:Samuel123.@100.111.182.33:443/cam/realmonitor?channel=9&subtype=1"),
    ("RTSP puerto 80",          "rtsp://Samuel:Samuel123.@100.111.182.33:80/cam/realmonitor?channel=1&subtype=1"),
]

# Tambien necesitamos el portproxy para el puerto 80
print("NOTA: Asegurate de tener el portproxy para el puerto que vas a probar.")
print(f"OpenCV version: {cv2.__version__}")
print()

for desc, url in urls:
    print(f"--- Probando: {desc} ---")
    print(f"    URL: {url}")
    start = time.time()
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    elapsed = time.time() - start
    
    if cap.isOpened():
        fps = cap.get(cv2.CAP_PROP_FPS)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"    CONECTADO en {elapsed:.1f}s - FPS:{fps} Res:{w}x{h}")
        ret, frame = cap.read()
        if ret:
            print(f"    Frame leido OK: {frame.shape}")
        cap.release()
        print("    >>> ESTA URL FUNCIONA <<<")
        break
    else:
        print(f"    Fallo ({elapsed:.1f}s)")
    cap.release()
    print()

print("\nDiagnostico completado.")
