# TrueNAS Deployment Guide

## Prerequisites

- TrueNAS SCALE 25.10.1 or later
- Docker enabled (Apps feature)
- Radarr running and accessible
- API key from Radarr (Settings > General > API Key)

## Image Distribution Options

### Option A: Push to Registry (Recommended)

```bash
# On your development machine
podman build -t your-dockerhub-username/movie-manager:latest .
podman push your-dockerhub-username/movie-manager:latest

# In TrueNAS YAML, use:
# image: your-dockerhub-username/movie-manager:latest
```

### Option B: Build on TrueNAS

```bash
# Copy source files to TrueNAS
scp -r ./* root@truenas:/mnt/tank/apps/movie-manager/src/

# SSH to TrueNAS and build
ssh root@truenas
cd /mnt/tank/apps/movie-manager/src
docker build -t movie-manager:latest .
```

### Option C: Export/Import Image

```bash
# On development machine
podman build -t movie-manager:latest .
podman save movie-manager:latest | gzip > movie-manager.tar.gz
scp movie-manager.tar.gz root@truenas:/tmp/

# On TrueNAS
docker load < /tmp/movie-manager.tar.gz
```

## Network Configuration for Radarr

### Step 1: Discover Radarr's Network

```bash
# SSH to TrueNAS
ssh root@truenas

# Find Radarr container
docker ps | grep -i radarr
# Example output: abc123  radarr:latest  ...

# Find its network
docker inspect abc123 --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}'
# Example output: ix-radarr_default
```

### Step 2: Choose Connection Method

| Method | RADARR_URL | When to Use |
|--------|------------|-------------|
| Same network | `http://radarr:7878` | Radarr is TrueNAS Docker app |
| Host IP | `http://192.168.1.100:7878` | Radarr on host network |
| External | `http://192.168.1.50:7878` | Radarr on different machine |

### Understanding Docker DNS

- Docker provides DNS resolution within networks
- Container name "radarr" resolves to Radarr's container IP
- Only works when containers share the same Docker network
- If not on same network, use IP address instead

## Deploying to TrueNAS

1. Navigate to: Apps > Discover Apps > Install via YAML
2. Paste your modified docker-compose.yml content
3. Create data directory: `mkdir -p /mnt/tank/apps/movie-manager/data`
4. Set environment variables directly in YAML:

```yaml
environment:
  - RADARR_URL=http://192.168.1.100:7878
  - RADARR_API_KEY=your-actual-api-key-here
  - KEEP_LIST_PATH=/data/.keep-list.json
  - TZ=America/New_York
```

**Security Note**: API keys in YAML are visible to anyone with TrueNAS admin access.

## Configuring Scheduled Execution (Cron)

Navigate to: System > Advanced Settings > Cron Jobs

### Daily Scan at 3 AM

- **Command:** `docker exec movie-manager python radarr_horror_filter.py scan --verbose`
- **Schedule:** `0 3 * * *`
- **User:** root

### Weekly Delete (Sunday 4 AM) - DRY RUN

- **Command:** `docker exec movie-manager python radarr_horror_filter.py delete --verbose`
- **Schedule:** `0 4 * * 0`

### Weekly Delete (Sunday 4 AM) - ACTUAL DELETE

- **Command:** `docker exec movie-manager python radarr_horror_filter.py delete --execute --yes --verbose`
- **Schedule:** `0 4 * * 0`

**Important**: The `--yes` flag skips confirmation prompts (required for cron).

## Testing the Deployment

```bash
# SSH to TrueNAS
ssh root@truenas

# Verify container is running
docker ps | grep movie-manager

# Test help command
docker exec movie-manager python radarr_horror_filter.py --help

# Test Radarr connectivity
docker exec movie-manager python radarr_horror_filter.py scan --verbose

# Verify keep list location
docker exec movie-manager cat /data/.keep-list.json
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Connection refused" | Wrong RADARR_URL | Check IP/port, verify Radarr is running |
| "Name resolution failed" | Not on same network | Use IP instead of hostname, or join Radarr's network |
| "Unauthorized" | Wrong API key | Get fresh API key from Radarr Settings |
| "Permission denied" on /data | Volume mount issue | `chown 1000:1000 /mnt/tank/apps/movie-manager/data` |
| Container exits immediately | Missing `tail -f` | Ensure command includes `tail -f /dev/null` |
| Keep list not persisting | Volume not mounted | Verify volume in `docker inspect movie-manager` |

## Updating the Container

```bash
# If using registry
docker pull your-username/movie-manager:latest
# Then restart via TrueNAS Apps UI

# If built locally
cd /mnt/tank/apps/movie-manager/src
git pull  # or copy new files
docker build -t movie-manager:latest .
docker restart movie-manager
```
