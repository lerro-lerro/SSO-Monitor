# SSO-Monitor Tailscale Configuration

## Overview

This docker-compose setup now supports optional Tailscale IP binding. By default, services are bound to `127.0.0.1` (localhost only), but you can configure them to also bind to your Tailscale IP address for network access.

## Configuration

### Option 1: Using Environment Variables (Recommended)

1. **Create a `.env` file** in the project root:

```bash
cp .env.example .env
```

2. **Edit `.env` and add your Tailscale IP**:

```bash
# Get your Tailscale IP
ip addr show tailscale0 | grep "inet " | awk '{print $2}' | cut -d'/' -f1

# Then add it to .env
TAILSCALE_IP=100.96.95.92
```

### Option 2: Using Export (Temporary)

```bash
export TAILSCALE_IP=100.96.95.92
docker compose up -d
```

## Services Affected

The following services support Tailscale IP binding via the `TAILSCALE_IP` variable:

- **brain** (Port 8080) - Flask web application
- **mongodb** (Port 27017) - MongoDB database
- **mongo-express** (Port 8081) - MongoDB management UI
- **redis** (Port 6379) - Redis cache
- **searxng** (Port 8082) - Search engine
- **jupyter** (Port 8888) - Jupyter notebook server
- **minio** (Port 9090) - MinIO console (S3 storage)

## Finding Your Tailscale IP

If you have Tailscale running:

```bash
ip addr show tailscale0
```

Look for the `inet` address (e.g., `100.96.95.92`).

## Default Behavior

- **If `TAILSCALE_IP` is not set**: Services bind to `127.0.0.1` (localhost only)
- **If `TAILSCALE_IP` is set**: Services bind to your Tailscale IP address
- **Traefik** and **minio S3 endpoint** always bind to `0.0.0.0` for broader access

## Troubleshooting

### Error: "cannot assign requested address"

This error occurs when trying to bind to an IP that doesn't exist on your machine:

1. Verify your Tailscale is running:

   ```bash
   sudo tailscale status
   ```

2. Check your Tailscale IP:

   ```bash
   ip addr show tailscale0
   ```

3. Update `.env` with the correct IP

4. Restart containers:
   ```bash
   docker compose down
   docker compose up -d
   ```

### Services not accessible over Tailscale

1. Ensure your `.env` file has the correct `TAILSCALE_IP`
2. Check if Tailscale is running: `sudo tailscale status`
3. Verify firewall rules allow the ports
4. Test connectivity: `ping 100.96.95.92` (replace with your Tailscale IP)

## Example .env Setup

```ini
TAILSCALE_IP=100.96.95.92
ADMIN_USER=admin
ADMIN_PASS=changeme
BRAIN_EXTERNAL_DOMAIN=brain.docker.localhost
MONGODB_HOST=mongodb
MINIO_HOST=minio
REDIS_HOST=redis
```

Then start:

```bash
docker compose up -d
```

Access services at:

- Brain: `http://100.96.95.92:8080`
- MongoDB: `mongodb://100.96.95.92:27017`
- MinIO: `http://100.96.95.92:9090`
- Redis: `100.96.95.92:6379`
