# Quick Start Guide

Get the monitoring stack running in minutes. Choose your deployment target below.

---

## A. Local Testing (Docker Compose) -- 5 Minutes

Run the full stack on your workstation for pre-production validation.

### Prerequisites

- Docker Desktop 4.x+ (with Docker Compose v2)
- Python 3.10+
- `pip install -r requirements.txt` (pyyaml + python-snappy)

### Steps

```bash
# 1. Fork and clone
git clone https://github.com/<YOUR_ORG>/Monitoring_Dashboarding.git
cd Monitoring_Dashboarding
pip install -r requirements.txt

# 2. Configure the stack (interactive prompts for sites, SMTP, Teams webhook)
python scripts/deploy_configure.py
# Or use the example config: python scripts/deploy_configure.py --config deploy/site_config.example.yml

# 3. Start the stack
python scripts/poc_setup.py

# 4. (Optional) Start with demo data -- dashboards populate immediately
python scripts/poc_setup.py --demo-data

# 5. Open Grafana
#    http://localhost:3000  (admin / admin)
```

The deployment wrapper generates `.env`, `alertmanager.yml`, `notifiers.yml`, and `inventory/sites.yml` from your inputs. The setup script starts all containers, waits for health checks, and validates the stack. With `--demo-data`, synthetic metrics and logs are pushed continuously so all 19 dashboards populate without deploying real agents.

### Test with Real Data

To test the full pipeline with live metrics and logs from your workstation:

```bash
# Download Grafana Alloy from https://github.com/grafana/alloy/releases
# Then run from the repo root:
alloy run configs/alloy/local/
```

After 30 seconds, open Grafana and check:
- **Explore > Prometheus**: `instance:windows_cpu_utilization:ratio`
- **Explore > Loki**: `{job="windows_eventlog"}`
- **Dashboards > Windows > Windows Server Overview**: Select your hostname

### Management

```bash
python scripts/poc_setup.py --status    # Health check
python scripts/poc_setup.py --stop      # Stop (keep data)
python scripts/poc_setup.py --reset     # Stop and delete data

# Direct docker compose commands:
docker compose -f deploy/docker/docker-compose.yml logs -f           # All services
docker compose -f deploy/docker/docker-compose.yml logs -f grafana   # Grafana only
docker compose -f deploy/docker/docker-compose.yml restart prometheus # Restart after config change
```

### Services

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| Grafana | http://localhost:3000 | admin / admin | Dashboards, Explore, alerting UI |
| Prometheus | http://localhost:9090 | None | Metrics storage, rule evaluation, PromQL |
| Alertmanager | http://localhost:9093 | None | Alert routing, silencing |
| Loki | http://localhost:3100 | None (API only) | Log storage (query via Grafana) |
| Blackbox Exporter | http://localhost:9115 | None | Synthetic probes (ICMP, TCP, HTTP, TLS) |

Optional profiles (disabled by default):

```bash
docker compose -f deploy/docker/docker-compose.yml --profile snmp up -d       # SNMP trap receiver
docker compose -f deploy/docker/docker-compose.yml --profile hardware up -d    # Redfish exporter
```

### Memory Budget

The stack is memory-limited to run on developer workstations (~2 GB total):

| Service | Memory Limit | Typical Usage |
|---------|-------------|---------------|
| Prometheus | 768 MB | 200-400 MB |
| Loki | 512 MB | 100-300 MB |
| Grafana | 512 MB | 150-250 MB |
| Alertmanager | 64 MB | 20-40 MB |
| Blackbox Exporter | 64 MB | 10-20 MB |

### Config Changes

When you modify config files, restart the affected service:

| File Changed | Restart |
|-------------|---------|
| `configs/prometheus/*.yml` or `alerts/prometheus/*.yml` | `docker compose ... restart prometheus` |
| `configs/loki/loki.yml` | `docker compose ... restart loki` |
| `configs/alertmanager/*.yml` | `docker compose ... restart alertmanager` |
| `configs/grafana/**` or `dashboards/**/*.json` | `docker compose ... restart grafana` |

Prometheus also supports hot reload: `curl -X POST http://localhost:9090/-/reload`

### Troubleshooting

| Problem | Fix |
|---------|-----|
| Stack fails to start | Check `docker info` is running; check port conflicts on 3000/3100/9090/9093 |
| "No Data" in Grafana panels | Check datasource health in Settings > Data Sources; verify Alloy is sending data; check recording rules at http://localhost:9090/rules |
| Prometheus shows 0 rules | Verify volume mounts: `docker compose exec prometheus ls /etc/prometheus/rules/`; run `python scripts/validate_prometheus.py` |
| Grafana "Datasource not found" | Verify provisioning: `docker compose exec grafana ls /etc/grafana/provisioning/datasources/`; ensure Prometheus/Loki are healthy |
| Alertmanager webhook errors | Expected if `TEAMS_WEBHOOK_URL` is not set (uses placeholder); set a real URL in `.env` to test |
| Container OOM restart | Check `docker stats`; increase limits in `docker-compose.yml` or reduce retention |

### Differences from Production (Kubernetes)

| Aspect | Local (Docker Compose) | Production (Kubernetes) |
|--------|----------------------|------------------------|
| Storage | Docker named volumes | Persistent Volume Claims |
| Networking | Docker bridge network | Kubernetes Service DNS |
| Config delivery | Bind mounts from repo | ConfigMaps / Helm values |
| Scaling | Single instance | Replicas with HA |
| Retention | 15 days / 5 GB | 30 days / 50 GB |
| TLS | None (localhost) | Ingress controller with certs |
| Auth | admin/admin | AD/LDAP integration |

---

## B. Production Kubernetes (Helm) -- 15 Minutes

Deploy to a Kubernetes cluster using the included Helm chart.

### Prerequisites

- Kubernetes cluster with kubectl access
- Helm 3.x+
- Persistent volume provisioner (for TSDB and log storage)
- Network path from Alloy agents to the cluster

### Steps

```bash
# 1. Fork and clone
git clone https://github.com/<YOUR_ORG>/Monitoring_Dashboarding.git
cd Monitoring_Dashboarding

# 2. Package the chart (copies configs into the chart)
./deploy/helm/package-chart.sh          # Linux/macOS
.\deploy\helm\package-chart.ps1         # Windows

# 3. Review a values overlay
#    Choose one: values-minimal.yaml, values-development.yaml, values-production.yaml
cat deploy/helm/examples/values-production.yaml

# 4. Install with your values
helm install monitoring ./deploy/helm/monitoring-stack \
  -f deploy/helm/examples/values-production.yaml \
  --set alertmanager.notifications.teamsWebhookUrl="https://your-teams-webhook-url" \
  --set grafana.admin.password="your-secure-password" \
  -n monitoring --create-namespace

# 5. Verify pods are running
kubectl get pods -n monitoring

# 6. Port-forward to Grafana
kubectl port-forward svc/monitoring-monitoring-stack-grafana 3000:3000 -n monitoring
# Open http://localhost:3000
```

### Value Overlay Examples

| File | Use Case | PVC Size | Retention |
|------|----------|----------|-----------|
| `values-minimal.yaml` | Quick test, only 2 required fields | 10Gi (default) | 15d |
| `values-development.yaml` | Dev/staging, low resource usage | 5Gi | 7d |
| `values-production.yaml` | Production, realistic sizing | 50Gi | 30d |

### Upgrade

After modifying configs, dashboards, or alert rules:

```bash
# Re-package to pick up config changes
./deploy/helm/package-chart.sh

# Upgrade the release
helm upgrade monitoring ./deploy/helm/monitoring-stack \
  -f deploy/helm/examples/values-production.yaml \
  -n monitoring
```

See `docs/BACKEND_DEPLOYMENT.md` for detailed component documentation.

---

## C. What to Customize

After deployment, these are the most common customization points:

### Alert Thresholds

Edit files in `alerts/prometheus/`:

| File | What It Covers |
|------|---------------|
| `windows_alerts.yml` | CPU, memory, disk for Windows servers |
| `linux_alerts.yml` | CPU, memory, disk for Linux servers |
| `infra_alerts.yml` | Cross-platform infrastructure alerts |
| `role_alerts.yml` | Role-specific alerts (DC, SQL, IIS, etc.) |

Default thresholds: CPU warning at 85%, critical at 95%. Memory and disk follow the same pattern.

### Dashboards

Dashboard JSON files live in `dashboards/`:

| Directory | Dashboards |
|-----------|-----------|
| `dashboards/windows/` | Windows Server Overview, IIS Overview |
| `dashboards/linux/` | Linux Server Overview |
| `dashboards/overview/` | Enterprise NOC, Site Overview, Infrastructure Overview, SLA Availability, Probing Overview, Audit Trail, Log Explorer |
| `dashboards/network/` | Network Infrastructure |
| `dashboards/hardware/` | Hardware Health |
| `dashboards/certs/` | Certificate Overview |

Edit in Grafana UI, then export JSON and save to the appropriate directory.

### Notification Channels

- **Teams webhook**: Set via `TEAMS_WEBHOOK_URL` environment variable (`.env` for Docker Compose, `alertmanager.notifications.teamsWebhookUrl` for Helm)
- **Email fallback**: Configure SMTP settings in the same locations
- **Alertmanager routing**: Edit `configs/alertmanager/alertmanager.yml` for route tree and inhibition rules

### Alloy Agent Roles

Role-specific Alloy configs in `configs/alloy/windows/` and `configs/alloy/linux/`:

| Config | Metrics Collected |
|--------|------------------|
| `role_dc.alloy` | Active Directory health, LDAP, DNS, replication |
| `role_sql.alloy` | SQL Server instance metrics, wait stats, buffer pool |
| `role_iis.alloy` | IIS request rates, response times, app pool status |
| `role_generic.alloy` | Base OS metrics (all servers get this) |

Add new roles by creating a `role_<name>.alloy` file following the existing patterns.

---

## D. Adding Servers

To onboard new servers into the monitoring platform:

1. **Define the server** in `inventory/hosts.yml` with its site, role(s), and environment
2. **Run the Ansible playbook** to deploy and configure Alloy with the correct tags
3. **Verify data flow** in Grafana -- the server should appear in template variable dropdowns within 60 seconds

See `docs/ALLOY_DEPLOYMENT.md` for the complete agent deployment and fleet onboarding guide.

---

## Architecture

```
Alloy agents (Windows/Linux servers)
    |
    |  remote_write (metrics)     push API (logs)
    v                             v
+-----------+              +-----------+
| Prometheus|              |   Loki    |
+-----------+              +-----------+
    |                           |
    |  alert rules fire         |
    v                           |
+-----------+                   |
|Alertmanager| -> Teams/Email   |
+-----------+                   |
                                |
+-----------+-------------------+
|         Grafana               |
|  (dashboards, explore, alerts)|
+-------------------------------+
```

Both Docker Compose and Helm deployments use the **same configuration files** -- the only differences are infrastructure-level settings (storage, networking, resource limits).
