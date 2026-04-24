"""
Escaneo completo de puertos abiertos en el NVR (192.168.1.61).
Busca puertos abiertos en rangos donde Dahua suele poner RTSP.
"""
import socket
import sys

TARGET = "192.168.1.61"

# Rangos relevantes para NVR Dahua
ports_to_scan = list(range(1, 1024))  # Puertos conocidos
ports_to_scan += [7070, 8000, 8080, 8443, 8554, 9000, 10554, 34567, 37777, 37778, 49152, 49153, 49154, 49155]

print(f"Escaneando {TARGET} ({len(ports_to_scan)} puertos)...")
print(f"Esto puede tomar unos minutos.\n")

abiertos = []
for i, port in enumerate(ports_to_scan):
    if i % 100 == 0:
        sys.stdout.write(f"\r  Progreso: {i}/{len(ports_to_scan)}...")
        sys.stdout.flush()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        result = sock.connect_ex((TARGET, port))
        if result == 0:
            abiertos.append(port)
            print(f"\n  ** Puerto {port} -> ABIERTO **")
    except:
        pass
    finally:
        sock.close()

print(f"\n\nResultado final: {len(abiertos)} puertos abiertos")
for p in abiertos:
    print(f"  - {p}")

# Intentar RTSP en cada puerto abierto
if abiertos:
    print("\nProbando protocolo RTSP en cada puerto abierto...")
    import time
    for port in abiertos:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        try:
            sock.connect((TARGET, port))
            rtsp_msg = f"OPTIONS rtsp://{TARGET}:{port}/ RTSP/1.0\r\nCSeq: 1\r\n\r\n"
            sock.sendall(rtsp_msg.encode())
            time.sleep(1)
            resp = sock.recv(4096)
            text = resp.decode("utf-8", errors="replace")
            if "RTSP" in text.upper():
                print(f"  Puerto {port}: *** RTSP CONFIRMADO ***")
                print(f"    Respuesta: {text[:200]}")
            else:
                first_bytes = resp[:20]
                print(f"  Puerto {port}: No es RTSP (bytes: {first_bytes.hex()})")
        except Exception as e:
            print(f"  Puerto {port}: Sin respuesta ({e})")
        finally:
            sock.close()

print("\nEscaneo finalizado.")
