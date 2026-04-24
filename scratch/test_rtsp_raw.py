"""
Test RAW de protocolo: verifica que responde en el puerto 443 de la camara
a traves del tunel Tailscale.
"""
import socket
import time

HOST = "100.111.182.33"
PORT = 443

print(f"[1] Conectando TCP a {HOST}:{PORT}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10)

try:
    sock.connect((HOST, PORT))
    print(f"[1] CONECTADO OK")
except Exception as e:
    print(f"[1] FALLO: {e}")
    exit(1)

# Enviar un DESCRIBE RTSP para ver si el servidor responde como RTSP
rtsp_describe = (
    f"DESCRIBE rtsp://Samuel:Samuel123.@{HOST}:{PORT}/cam/realmonitor?channel=1&subtype=1 RTSP/1.0\r\n"
    f"CSeq: 1\r\n"
    f"User-Agent: LogiCheck\r\n"
    f"Accept: application/sdp\r\n"
    f"\r\n"
)

print(f"\n[2] Enviando RTSP DESCRIBE...")
sock.sendall(rtsp_describe.encode())

time.sleep(2)

try:
    response = sock.recv(4096)
    print(f"[2] Respuesta ({len(response)} bytes):")
    # Intentar decodificar como texto
    try:
        text = response.decode("utf-8", errors="replace")
        print(text[:500])
    except:
        print(f"    (datos binarios: {response[:100]})")
except socket.timeout:
    print("[2] TIMEOUT - No hubo respuesta RTSP")
except Exception as e:
    print(f"[2] Error: {e}")

sock.close()

# Ahora probar si es HTTPS en vez de RTSP
print(f"\n[3] Probando si es un servidor HTTPS...")
import ssl
sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock2.settimeout(10)
try:
    sock2.connect((HOST, PORT))
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ssock = ctx.wrap_socket(sock2, server_hostname=HOST)
    print(f"[3] SSL conectado! Es un servidor HTTPS/TLS")
    print(f"    Protocolo: {ssock.version()}")
    # Enviar una peticion HTTP GET
    ssock.sendall(b"GET / HTTP/1.1\r\nHost: " + HOST.encode() + b"\r\n\r\n")
    time.sleep(1)
    resp = ssock.recv(4096)
    print(f"    Respuesta HTTP ({len(resp)} bytes):")
    print(resp.decode("utf-8", errors="replace")[:300])
    ssock.close()
except Exception as e:
    print(f"[3] No es HTTPS: {e}")
    sock2.close()

print("\n[FIN] Diagnostico completado.")
