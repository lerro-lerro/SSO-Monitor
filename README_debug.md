# DEBUG SSO-MONITOR

## Overview
Enabled Playwright headless=False with X11/VNC infrastructure for real-time browser automation visualization across 5 worker containers.

## Modifications Summary

### 1. Docker Configuration (worker/Dockerfile)
- **Base Image**: `mcr.microsoft.com/playwright/python:v1.35.0-jammy`
- **X11/VNC Libraries**: libx11-6, libxext6, libxrender1, x11-utils, xvfb, x11vnc
- **Entrypoint**: Custom `/usr/local/bin/entrypoint.sh` for X11 initialization
- **Package Management**: Pipenv for Python dependencies

### 2. Entrypoint Script (worker/entrypoint.sh)
Initializes X11/Xvfb/x11vnc with unique display per container:
- **Unique Display Assignment**: `DISPLAY_NUM=$((0x${HEX_SUFFIX} % 100 + 99))` from container ID hash (:99-:198 range)
- **Stale Lock Cleanup**: Removes `/tmp/.X${DISPLAY_NUM}-lock` and `/tmp/.X11-unix/X${DISPLAY_NUM}`
- **Xvfb Startup**: 1920x1080x24 with 4-second initialization delay
- **x11vnc Configuration**:
  - `-noshm`: Disable shared memory (prevents OOM on multiple instances)
  - `-onetile`: Single tile to reduce memory footprint
  - `-listen 0.0.0.0`: Listen on all interfaces for host access
  - `-forever`: Keep running for multiple connections
  - `-nopw`: No password authentication
  - `-shared`: Allow simultaneous client connections
  - `-rfbport 5900`: Standard VNC port
- **Startup Verification**: PID checks for both Xvfb and x11vnc before launching Python app

### 3. Docker Compose Configuration (docker-compose.yml)
- **Worker Services**: 3 types (landscape×2, login×2, wildcard×1) = 5 total containers
- **X11 Socket Mounting**: `/tmp/.X11-unix:/tmp/.X11-unix:rw` for each worker
- **VNC Port Mapping**:
  - worker_landscape-1: host:5900 → container:5900
  - worker_landscape-2: host:5901 → container:5900
  - worker_login-1: host:5902 → container:5900
  - worker_login-2: host:5903 → container:5900
  - worker_wildcard-1: host:5904 → container:5900

### 4. Browser Configuration (worker/modules/browser/browser.py)
- **Line 246**: `headless = False` to enable GUI rendering
- **Chromium Flags**: Disabled problematic compression mechanisms:
  - `--disable-brotli`: Disable Brotli compression
  - `--disable-sync`: Disable cloud sync compression
  - `--disable-client-side-phishing-detection`: Prevent security analysis interference

### 5. Image Helper Fix (worker/modules/helper/image.py)
- **Root Cause**: `base64comppng_draw_rectangle()` expected zlib-compressed data but received raw PNG bytes
- **Fix**: Modified function to detect and handle both compressed and raw PNG formats with fallback logic

## VNC Connection Details

| Service | Container Port | Host Port | Connection String |
|---------|-----------------|-----------|-------------------|
| Landscape 1 | 5900 | 5900 | `vnc://localhost:5900` |
| Landscape 2 | 5900 | 5901 | `vnc://localhost:5901` |
| Login 1 | 5900 | 5902 | `vnc://localhost:5902` |
| Login 2 | 5900 | 5903 | `vnc://localhost:5903` |
| Wildcard | 5900 | 5904 | `vnc://localhost:5904` |

**VNC Client**: Install TigerVNC viewer or Remmina
```bash
sudo apt install -y tigervnc-viewer
vncviewer localhost:5900
```

## System Status

✅ **All Systems Operational**
- **Workers**: All 5 containers running and consuming messages from RabbitMQ
- **X11 Displays**: Unique displays (:99-:198 range) assigned per container, no conflicts
- **VNC Ports**: All 5 ports (5900-5904) fully accessible from host
- **Xvfb**: Running with 1920x1080x24 resolution in each container
- **x11vnc**: Listening on all interfaces with shared memory optimization
- **Browser Automation**: Playwright running with headless=False, GUI rendering active
- **Message Processing**: All workers actively processing tasks

## Issues Resolved

1. ✅ **Multiple containers competing for same X11 display**
   - Solution: Hash-based unique display number calculation from container ID

2. ✅ **Stale X11 lock files blocking Xvfb startup**
   - Solution: Cleanup locks and sockets before Xvfb initialization

3. ✅ **x11vnc not accessible from host**
   - Solution: Added `-listen 0.0.0.0` flag for all-interface binding

4. ✅ **x11vnc process crashing with shared memory exhaustion**
   - Solution: Added `-noshm -onetile` flags to disable and optimize memory usage

5. ✅ **Image processing decompression errors**
   - Solution: Modified `base64comppng_draw_rectangle()` to handle raw and compressed PNG data