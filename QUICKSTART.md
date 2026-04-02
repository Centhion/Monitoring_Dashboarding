# Quick Start Guide

Get the monitoring stack running in minutes.

---

## Prerequisites

- Docker Engine or Docker Desktop (with Docker Compose v2)
- Python 3.10+
- `pip install -r requirements.txt`

## Deploy

```bash
git clone https://github.com/<YOUR_ORG>/Monitoring_Dashboarding.git
cd Monitoring_Dashboarding

# Step 1: Configure (interactive prompts for sites, SMTP, Teams webhook)
python scripts/deploy_configure.py

# Or non-interactive from a config file:
# cp deploy/site_config.example.yml deploy/site_config.yml
# python scripts/deploy_configure.py --config deploy/site_config.yml

# Step 2: Start the stack
python scripts/stack_manage.py

# Step 3: Open Grafana at http://localhost:3000 (admin / admin)
```

### Demo Data Options

```bash
# Prometheus/Loki synthetic data (populates Windows, Linux, NOC, SLA, etc.)
python scripts/stack_manage.py --demo-data

# SCOM DW simulator (populates all SCOM dashboards with synthetic SQL data)
python scripts/stack_manage.py --scom-demo

# Both at once (full demo -- all dashboards populated)
python scripts/stack_manage.py --scom-demo --demo-data
```

## Manage

```bash
python scripts/stack_manage.py --status    # Health check all services
python scripts/stack_manage.py --stop      # Stop (keep data)
python scripts/stack_manage.py --reset     # Stop and delete all data
```

## Services

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana | http://localhost:3000 | Dashboards, alerting UI |
| Prometheus | http://localhost:9090 | Metrics storage, PromQL |
| Alertmanager | http://localhost:9093 | Alert routing, silencing |
| Loki | http://localhost:3100 | Log storage (query via Grafana) |
| Blackbox | http://localhost:9115 | Synthetic probes |

### Optional Profiles

```bash
# SCOM DW simulator
docker compose -f deploy/docker/docker-compose.yml --profile scom-demo up -d
docker compose -f deploy/docker/docker-compose.yml --profile scom-demo down -v --remove-orphans

# SNMP trap receiver
docker compose -f deploy/docker/docker-compose.yml --profile snmp up -d
docker compose -f deploy/docker/docker-compose.yml --profile snmp down -v --remove-orphans

# Redfish BMC exporter
docker compose -f deploy/docker/docker-compose.yml --profile hardware up -d
docker compose -f deploy/docker/docker-compose.yml --profile hardware down -v --remove-orphans
```

## Dashboards

| Directory | Content |
|-----------|---------|
| `dashboards/enterprise/` | NOC, SLA, Probing, Audit Trail |
| `dashboards/servers/` | Windows, Linux, IIS, SQL, DC, DHCP, CA, File Server, Docker, Log Explorer |
| `dashboards/infrastructure/` | Site Overview, Infrastructure Overview, Network, Hardware, Certificates |
| `dashboards/scom/operations/` | SCOM Operations, Fleet, Site, Alerts, Health State, Events, Incident Investigation |
| `dashboards/scom/servers/` | SCOM Server Overview, Fleet, AD/DC, DHCP, DNS, DFS, Exchange, IIS |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Stack fails to start | Check `docker info`; check port conflicts on 3000/3100/9090/9093 |
| "No Data" in panels | Check datasource health in Grafana Settings; verify recording rules at http://localhost:9090/rules |
| SCOM dashboards empty | Wait for seed to finish: `docker logs --tail 5 mon-scom-dw-seed` |
| Container OOM restart | Check `docker stats`; increase limits in `docker-compose.yml` |

## Next Steps

- See `ARCHITECTURE.md` for stack design and data flow
- See `docs/ALLOY_DEPLOYMENT.md` for deploying agents to servers
- See `docs/ALERT_RUNBOOKS.md` for alert investigation procedures
- See `docs/operations/` for admin guides, troubleshooting, and threshold tuning
