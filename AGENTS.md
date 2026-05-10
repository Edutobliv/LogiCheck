# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

LogiCheck is an AI-powered logistics auditing system for hardware stores and warehouses. It uses YOLO26 computer vision to count cement bags and PVC pipes in real-time from video streams or RTSP cameras, comparing counts against PDF invoices.

## Commands

Use the project virtual environment for Python commands. Prefer invoking the
interpreter directly so Codex uses the same dependencies as the app, including
Torch/Ultralytics:

```powershell
.\.venv\Scripts\python.exe
```

```powershell
# Run the application (from project root)
.\.venv\Scripts\python.exe main.py

# Build executable
pyinstaller LogiCheck.spec

# Create database (first run or reset)
.\.venv\Scripts\python.exe create_db.py

# Run tests
.\.venv\Scripts\python.exe -m unittest
```

## Architecture

### Entry Point
- `main.py` - Application bootstrap: login dialog → splash screen (YOLO preload) → main window

### Core Modules (`core/`)
- `auth.py` - SQLite user authentication with SHA-256 password hashing
- `permissions.py` - Role-based access control (admin, op_factura, op_video, gerente, dueno)
- `logger.py` - Activity logging to SQLite (`activity_logs` table)
- `audit_store.py` - Audit persistence (`auditorias` table)
- `yolo_manager.py` - YOLO inference workers:
  - `YoloAnalyzerWorker` - Video file analysis
  - `VideoPlayerWorker` - Playback with overlay rendering
  - `RtspCameraWorker` - Live RTSP stream processing
- `invoice_parser.py` - PDF invoice extraction using PyMuPDF
- `report_exporter.py` - Excel/PDF audit reports via openpyxl/fpdf2
- `notifier.py` - Telegram/WhatsApp notifications

### UI Modules (`ui/`)
- `main_window.py` - Main application window with sidebar navigation
- `login_dialog.py` - Authentication dialog
- `splash_screen.py` - Loading screen with conditional YOLO preloading
- `users_page.py` - User management (admin only)
- `logs_page.py` - Activity log viewer
- `dahua_history_dialog.py` - Dahua camera historical footage playback

### YOLO Detection Categories
The system tracks three product categories:
1. **Cemento** - Cement bags (keywords: bulto, cemento, bag)
2. **Tubería Presión** - Pressure pipes (keywords: tubo presión, hidráulico)
3. **Tubería Sanitaria** - Sanitary pipes (keywords: tubo sanitario, desagüe)

### Database Schema
- `logicheck_users.db` - SQLite database containing:
  - `usuarios` - User accounts with role and permission overrides
  - `activity_logs` - Action audit trail
  - `auditorias` - Audit session results

### Key Data Flows
1. **Live Monitoring**: RTSP stream → YOLO tracking → Count updates → UI
2. **Invoice Processing**: PDF upload → PyMuPDF extraction → Category matching → Comparison
3. **Audit Flow**: Video analysis → Compare vs invoice → Discrepancy detection → Report export → Notification

## Development Notes

- Model weights stored at `training/runs/bultos_cemento/weights/best.pt`
- QSS themes in `resources/style.qss` (dark) and `resources/style_light.qss`
- The splash screen preloads YOLO model into CUDA only for users with `video.iniciar` permission
- Crossing detection uses bidirectional counting (entering/exiting zone) to track items passing a count line
