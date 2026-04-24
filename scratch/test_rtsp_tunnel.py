"""
Test rápido de conexión RTSP a través del túnel Tailscale.
Verifica si OpenCV puede abrir el stream RTSP por TCP.
"""
import os
import cv2
import time

# Forzar transporte TCP con opciones robustas para túneles
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"
    "stimeout;15000000|"
    "analyzeduration;5000000|"
    "probesize;5000000|"
    "fflags;nobuffer"
)

# URL a través del túnel Tailscale + netsh portproxy
url = "rtsp://Samuel:Samuel123.@100.111.182.33:443/cam/realmonitor?channel=1&subtype=1"

print(f"[TEST] Intentando abrir: {url}")
print(f"[TEST] OPENCV_FFMPEG_CAPTURE_OPTIONS = {os.environ.get('OPENCV_FFMPEG_CAPTURE_OPTIONS')}")
print(f"[TEST] OpenCV version: {cv2.__version__}")
print()

start = time.time()
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
elapsed = time.time() - start

if cap.isOpened():
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[TEST] ✅ ¡CONECTADO! en {elapsed:.1f}s")
    print(f"[TEST]    FPS: {fps}, Resolución: {w}x{h}")
    
    ret, frame = cap.read()
    if ret:
        print(f"[TEST] ✅ Frame leído correctamente: {frame.shape}")
        cv2.imwrite("scratch/test_frame.jpg", frame)
        print("[TEST] Frame guardado en scratch/test_frame.jpg")
    else:
        print("[TEST] ❌ No se pudo leer un frame")
    cap.release()
else:
    print(f"[TEST] ❌ No se pudo abrir el stream (tardó {elapsed:.1f}s)")
    print()
    print("[TEST] Intentando variaciones...")
    
    # Variante: sin punto en la contraseña
    urls_alternativas = [
        ("Sin punto en pass", "rtsp://Samuel:Samuel123@100.111.182.33:443/cam/realmonitor?channel=1&subtype=1"),
        ("Canal 9", "rtsp://Samuel:Samuel123.@100.111.182.33:443/cam/realmonitor?channel=9&subtype=1"),
        ("Canal 10", "rtsp://Samuel:Samuel123.@100.111.182.33:443/cam/realmonitor?channel=10&subtype=1"),
        ("Subtype 0 (main)", "rtsp://Samuel:Samuel123.@100.111.182.33:443/cam/realmonitor?channel=1&subtype=0"),
    ]
    
    for desc, alt_url in urls_alternativas:
        print(f"\n[TEST] Probando: {desc}")
        print(f"       URL: {alt_url}")
        start = time.time()
        cap2 = cv2.VideoCapture(alt_url, cv2.CAP_FFMPEG)
        elapsed2 = time.time() - start
        if cap2.isOpened():
            print(f"[TEST] ✅ ¡CONECTADO con '{desc}'! en {elapsed2:.1f}s")
            ret, frame = cap2.read()
            if ret:
                print(f"[TEST] ✅ Frame: {frame.shape}")
            cap2.release()
            break
        else:
            print(f"[TEST] ❌ Falló ({elapsed2:.1f}s)")
        cap2.release()

print("\n[TEST] Fin del diagnóstico.")
