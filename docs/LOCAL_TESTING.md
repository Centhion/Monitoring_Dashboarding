# Local Testing Guide (Docker Compose PoC)

This guide covers running the full monitoring stack locally via Docker Desktop for pre-Kubernetes validation. The stack runs in ~2 GB of RAM alongside your normal workloads.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Docker Desktop | 4.x+ | Windows with WSL2 backend recommended |
| Docker Compose | v2.x+ | Included with Docker Desktop |
| Python 3.10+ | 3.10+ | For setup script and validators |
| Grafana Alloy | Latest | Optional -- for end-to-end metrics/logs testing |

---

## Quick Start

```bash
# 1. Clone and enter the repo
cd Monitoring_Dashboarding

# 2. (Optional) Create .env from template
cp .env.example .env
# Edit .env to set TEAMS_WEBHOOK_URL if you want notification testing

# 3. Start the stack (one command)
python scripts/poc_setup.py

# 4. Open Grafana
# http://localhost:3000  (admin / admin)
```

The setup script handles:
- Docker prerequisite checks
- Container startup
- Health check polling (up to 120s timeout)
- Prometheus rule loading validation
- Grafana datasource provisioning validation

---

## Services

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| Grafana | http://localhost:3000 | admin / admin | Dashboards, Explore, alerting UI |
| Prometheus | http://localhost:9090 | None | Metrics storage, rule evaluation, PromQL |
| Alertmanager | http://localhost:9093 | None | Alert routing, silencing |
| Loki | http://localhost:3100 | None (API only) | Log storage (query via Grafana) |

---

## Memory Budget

The stack is memory-limited to run on developer workstations:

| Service | Memory Limit | Typical Usage |
|---------|-------------|---------------|
| Prometheus | 768 MB | 200-400 MB with light load |
| Loki | 512 MB | 100-300 MB with light load |
| Grafana | 512 MB | 150-250 MB |
| Alertmanager | 64 MB | 20-40 MB |
| **Total** | **~1.9 GB** | **~500 MB - 1 GB typical** |

If you need to reduce memory usage further, edit the `deploy.resources.limits.memory` values in `deploy/docker/docker-compose.yml`.

---

## Running Alloy Locally

To test the full data pipeline (Alloy -> Prometheus/Loki -> Grafana dashboards), run Alloy on your Windows machine.

### Download Alloy

1. Go to: https://github.com/grafana/alloy/releases
2. Download the Windows amd64 zip
3. Extract `alloy.exe` to a directory in your PATH (or use the full path)

### Run Alloy

```bash
# From the repo root
alloy run configs/alloy/local/
```

This starts Alloy with a single config file that:
- Collects Windows metrics (CPU, memory, disk, network, services)
- Collects Windows Event Logs (System, Application)
- Sends metrics to `http://localhost:9090/api/v1/write` (Prometheus)
- Sends logs to `http://localhost:3100/loki/api/v1/push` (Loki)
- Applies labels: `environment=local-poc`, `datacenter=developer-workstation`, `role=workstation`

### Verify Data in Grafana

1. Open http://localhost:3000
2. Go to **Explore** (compass icon in left sidebar)
3. Select **Prometheus** datasource
4. Query: `instance:windows_cpu_utilization:ratio`
   - If recording rules are working, you should see your workstation's CPU utilization
5. Select **Loki** datasource
6. Query: `{job="windows_eventlog"}`
   - You should see Windows Event Log entries streaming in

### Verify Dashboards

1. Go to **Dashboards** in the left sidebar
2. Open **Windows > Windows Server Overview**
3. Select your hostname from the **hostname** dropdown
4. Panels should populate with real data from your workstation

---

## Management Commands

The Docker Compose file lives at `deploy/docker/docker-compose.yml`. Use the convenience wrappers (`./dc.sh` on Linux/macOS, `.\dc.ps1` on Windows) to avoid typing the full path, or pass `-f` explicitly.

```bash
# Check health of running stack
python scripts/poc_setup.py --status

# Stop stack (data preserved in Docker volumes)
python scripts/poc_setup.py --stop

# Stop stack AND delete all data (fresh start)
python scripts/poc_setup.py --reset

# View container logs (all commands run from repo root)
./dc.sh logs -f                    # All services
./dc.sh logs -f prometheus         # Prometheus only
./dc.sh logs -f grafana            # Grafana only

# Restart a single service (after config change)
./dc.sh restart prometheus
./dc.sh restart grafana

# Pull latest images
./dc.sh pull

# Or use the explicit -f flag directly:
# docker compose -f deploy/docker/docker-compose.yml logs -f
```

---

## Configuration Changes

When you modify config files, restart the affected service:

| File Changed | Restart Command |
|-------------|-----------------|
| `configs/prometheus/prometheus.yml` | `docker compose -f deploy/docker/docker-compose.yml restart prometheus` |
| `configs/prometheus/recording_rules.yml` | `docker compose -f deploy/docker/docker-compose.yml restart prometheus` |
| `alerts/prometheus/*.yml` | `docker compose -f deploy/docker/docker-compose.yml restart prometheus` |
| `configs/loki/loki.yml` | `docker compose -f deploy/docker/docker-compose.yml restart loki` |
| `configs/alertmanager/alertmanager.yml` | `docker compose -f deploy/docker/docker-compose.yml restart alertmanager` |
| `configs/grafana/datasources/*` | `docker compose -f deploy/docker/docker-compose.yml restart grafana` |
| `configs/grafana/dashboards/*` | `docker compose -f deploy/docker/docker-compose.yml restart grafana` |
| `configs/grafana/notifiers/*` | `docker compose -f deploy/docker/docker-compose.yml restart grafana` |
| `dashboards/**/*.json` | `docker compose -f deploy/docker/docker-compose.yml restart grafana` |

Prometheus also supports config reload without restart:

```bash
curl -X POST http://localhost:9090/-/reload
```

---

## Troubleshooting

### Stack fails to start

```bash
# Check Docker is running
docker info

# Check for port conflicts
netstat -an | findstr "3000 3100 9090 9093"

# View startup errors
docker compose -f deploy/docker/docker-compose.yml logs
```

### "No Data" in Grafana panels

1. **Check datasource health**: Grafana > Settings > Data Sources > Prometheus/Loki > Test
2. **Check recording rules**: http://localhost:9090/rules -- verify rules are loaded
3. **Check Alloy is running**: If no Alloy agent is sending data, only self-monitoring metrics exist
4. **Check template variables**: Dropdown should show values from the `environment` and `hostname` labels

### Prometheus shows 0 rules

- Verify volume mounts: `docker compose -f deploy/docker/docker-compose.yml exec prometheus ls /etc/prometheus/rules/`
- Check for YAML syntax errors: `docker compose -f deploy/docker/docker-compose.yml logs prometheus | grep "error"`
- Run validator: `python scripts/validate_prometheus.py`

### Grafana shows "Datasource not found"

- Verify provisioning: `docker compose -f deploy/docker/docker-compose.yml exec grafana ls /etc/grafana/provisioning/datasources/`
- Check logs: `docker compose -f deploy/docker/docker-compose.yml logs grafana | grep "provisioning"`
- Ensure Prometheus and Loki are healthy before Grafana starts (handled by `depends_on` in Compose)

### Alertmanager shows webhook errors

- Expected if `TEAMS_WEBHOOK_URL` is not set (uses placeholder URL)
- Set a real webhook URL in `.env` to test Teams notifications
- Check: `docker compose -f deploy/docker/docker-compose.yml logs alertmanager | grep "webhook"`

### Container is restarting (OOM)

- Check memory usage: `docker stats`
- Increase limits in `deploy/docker/docker-compose.yml` if needed
- Reduce Prometheus retention: change `--storage.tsdb.retention.time` to `7d`

---

## Differences from Production (Kubernetes)

| Aspect | Local (Docker Compose) | Production (Kubernetes) |
|--------|----------------------|------------------------|
| Storage | Docker named volumes | Persistent Volume Claims |
| Networking | Docker bridge network | Kubernetes Service DNS |
| Config delivery | Bind mounts from repo | ConfigMaps / Helm values |
| Scaling | Single instance | Replicas with HA |
| Retention | 15 days / 5 GB | 30 days / 50 GB |
| Memory limits | ~2 GB total | Based on cluster capacity |
| TLS | None (localhost) | Ingress controller with certs |
| Auth | admin/admin | AD/LDAP integration |

The config files are identical -- the only differences are resource limits and infrastructure-level settings managed by Kubernetes.

---

## Validation Before Deployment

Before deploying configs to Kubernetes, run the full validation suite:

```bash
# Validate all configs
python scripts/validate_all.py --strict

# Run tests
python -m pytest tests/test_validators.py -v
```

This catches syntax errors, missing fields, and convention violations before they reach the cluster.

---

*Last Updated: 2026-02-19*
