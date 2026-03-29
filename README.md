# 🚛 LogiCheck IA: Sistema de Auditoría y Seguridad Inteligente

**LogiCheck** es una plataforma avanzada de visión artificial diseñada específicamente para la automatización de inventarios y seguridad perimetral en ferreterías y centros logísticos. Utilizando modelos de Deep Learning (YOLOv11), el sistema supervisa el flujo de mercancía en tiempo real a través de cámaras RTSP.

---

## 🚀 Características Principales

### 👁️ Monitoreo y Visión Artificial
- **Compatibilidad RTSP Multi-canal:** Soporte para hasta 11 cámaras de alta definición con reconexión automática y cambio de stream sin interrupciones.
- **Detección Especializada:** Optimizado para el conteo preciso de bultos (cemento), tubería de presión y tubería sanitaria.
- **Zona de Conteo Interactiva:** Interfaz de 4 ejes (Arriba, Abajo, Izquierda, Derecha) para delimitar con exactitud el área de detección según la perspectiva de cada cámara.

### 🛡️ Seguridad y Vigilancia Activa
- **Detección de Movimiento No Autorizado:** Alerta inmediata si se detecta movimiento de mercancía sin una factura cargada en el sistema.
- **Evidencia Visual Automática:** Captura instantánea de fotos (Snapshots) cuando el sistema detecta una anomalía o alcanza una meta.

### 📲 Sistema de Notificaciones Dual
- **✈️ Telegram (Alertas Instantáneas):**
    - Notificaciones en < 1 segundo de "Metas alcanzadas".
    - Envío automático de **Fotos de Evidencia** en caso de posibles robos o movimientos no autorizados.
- **📲 WhatsApp (Reportes Profesionales):**
    - Generación de tickets detallados de carga/descarga con emojis y comparativas contra factura.
    - Resumen estético para compartir con transportadores o gerencia.

### 📊 Gestión Administrativa
- **Integración PDF:** Lector inteligente de facturas para comparar el conteo IA contra el inventario teórico.
- **Panel de Auditoría:** Registro histórico de todas las sesiones, fotos de evidencia y logs de actividad por usuario.
- **Dashboard de Tendencias:** Gráficas modernas de eficiencia operativa y precisión de carga.

---

## 🛠️ Stack Tecnológico
- **Lenguaje:** Python 3.12+
- **Interfaz (GUI):** PySide6 (Qt) con diseño *Premium Glow* y modo oscuro.
- **IA/Visión:** Ultralytics YOLOv11, OpenCV (Detección y Tracking).
- **Notificaciones:** Telegram Bot API (Requests) y CallMeBot API.
- **Base de Datos:** SQLite3 para logs de actividad y gestión de usuarios.

---

## ⚙️ Configuración del Sistema

### 1. Requisitos
Crea un entorno virtual e instala las dependencias:
```powershell
python -m venv .venv
.venv\scripts\activate
pip install -r requirements.txt
```

### 2. Notificaciones (Telegram)
Para recibir alertas con fotos en tu móvil:
1. Crea un bot hablando con `@BotFather` y obtén tu **TOKEN**.
2. Obtén tu **ID de chat** con `@userinfobot`.
3. Configura estos datos en `core/notifier.py`.

### 3. Notificaciones (WhatsApp)
1. Escribe al número de CallMeBot en WhatsApp para obtener tu **API Key**.
2. Configura tu número y clave en `core/notifier.py`.

---

## 📂 Estructura del Proyecto
- `ui/`: Interfaz gráfica completa y lógica de ventanas.
- `core/`: Motores de IA, sistema de logs, exportación de reportes y notificaciones.
- `resources/`: Estilos CSS/QSS y recursos de audio.
- `training/`: Scritps para el re-entrenamiento y refinamiento del modelo YOLO.
- `captures/`: Historial de evidencia visual capturada automáticamente.

---

**Desarrollado para la eficiencia y seguridad en el sector ferretero.** 🧱🏢
