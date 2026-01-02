#!/bin/bash
set -e

# Environment setup for Python and X11
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export LD_PRELOAD=""

# Generate unique display number based on container ID hash
# Extract last 2 hex digits from container hostname (ID) and convert to decimal
CONTAINER_ID=$(hostname)
# Use last 2 characters of container ID, convert hex to decimal, mod by 100, then add 99
HEX_SUFFIX=${CONTAINER_ID: -2}
DISPLAY_NUM=$((0x${HEX_SUFFIX} % 100 + 99))

# Use virtual display in container
export DISPLAY=:$DISPLAY_NUM

# Clean up stale X11 lock files
rm -f /tmp/.X${DISPLAY_NUM}-lock /tmp/.X11-unix/X${DISPLAY_NUM}

# Start Xvfb virtual display server
echo "Starting Xvfb virtual display server on $DISPLAY..."
Xvfb $DISPLAY -screen 0 1920x1080x24 -ac >/dev/null 2>&1 &
XVFB_PID=$!
sleep 4

# Verify Xvfb is running
if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "ERROR: Xvfb failed to start (PID: $XVFB_PID)"
    exit 1
fi

# Start x11vnc for VNC access
if command -v x11vnc &> /dev/null; then
    echo "Starting x11vnc server on $DISPLAY for VNC access..."
    # Use options that reduce shared memory usage:
    # -onetile: use only one tile (reduces shared memory)
    # -noshm: disable shared memory
    # -listen 0.0.0.0: listen on all interfaces
    x11vnc -display $DISPLAY -forever -nopw -auth none -shared -rfbport 5900 -rfbwait 30 -noshm -onetile -listen 0.0.0.0 2>&1 | tee /tmp/x11vnc.log &
    VNC_PID=$!
    sleep 3
    
    # Verify x11vnc started
    if ! kill -0 $VNC_PID 2>/dev/null; then
        echo "ERROR: x11vnc failed to start (PID: $VNC_PID)"
        cat /tmp/x11vnc.log 2>/dev/null || echo "No x11vnc log available"
        exit 1
    fi
    echo "x11vnc started successfully with PID: $VNC_PID (listening on all interfaces)"
fi

echo "Starting Python application on display $DISPLAY..."
sleep 2

# Execute the Python application
exec python app.py "$@"
