# How the Monitoring Stack Works

A simplified overview for engineers and senior sysadmins who need to understand the platform's internals. This covers how data flows, what each component does, and where configuration files live.

---

## Data Flow

```
Monitored Servers                    Monitoring Stack (Docker Host)
+------------------+                 +---------------------------+
|                  |   metrics       |                           |
|  Grafana Alloy   | ------------->  |  Prometheus               |
|  (agent)         |   (push)        |  (metrics database)       |
|                  |                 |                           |
|                  |   logs          |                           |
|                  | ------------->  |  Loki                     |
|                  |   (push)        |  (log database)           |
+------------------+                 |                           |
                                     |  Alertmanager             |
Site Gateways                        |  (notification routing)   |
+------------------+                 |                           |
|  SNMP polling    |   metrics       |  Grafana                  |
|  Redfish polling | ------------->  |  (dashboards + UI)        |
|  Blackbox probes |   (push)        |                           |
+------------------+                 +---------------------------+
                                              |
                                              v
                                     +------------------+
                                     |  Teams + Email   |
                                     |  (notifications) |
                                     +------------------+
```

### How Data Moves

1. **Alloy agents** run on every monitored server. They collect metrics (CPU, memory, disk, services) and logs (Windows Event Log, Linux journal).
2. Agents **push** data to Prometheus (metrics) and Loki (logs) via HTTP. There is no polling from the monitoring stack to the agents.
3. **Prometheus** stores metrics and evaluates alert rules every 15 seconds. When a rule condition is true for the configured `for` duration, Prometheus sends the alert to Alertmanager.
4. **Alertmanager** groups alerts by site and type, then delivers notifications to Teams (webhook) and email (SMTP).
5. **Grafana** queries Prometheus and Loki to render dashboards. It does not store any metrics or logs -- it is purely a UI layer.
6. **Site gateways** (optional) run SNMP polling for network devices, Redfish polling for hardware health, and Blackbox probes for endpoint availability. They push results to Prometheus like any other agent.

### Key Architectural Decisions

- **Push-based, not pull-based**: Agents push to the central stack. This means agents only need outbound HTTP access -- no inbound ports need to be opened on monitored servers.
- **Single Docker host**: All stack components run as Docker containers on one host. No Kubernetes, no clustering. This keeps operations simple.
- **Config-as-code**: All dashboards, alert rules, and routing configs are files in the git repository. Changes are made in git, not in the UI.

---

## Components

| Component | Port | What It Does | Data Stored |
|-----------|------|-------------|-------------|
| **Prometheus** | 9090 | Stores metrics, evaluates alert rules, serves metric queries | Time-series metrics (30-day retention, 50GB max) |
| **Loki** | 3100 | Stores logs, serves log queries | Log entries (30-day retention) |
| **Alertmanager** | 9093 | Routes alerts to Teams/email, manages silences | Alert state (in-memory, backed by disk) |
| **Grafana** | 3000 | Dashboards, alerting UI, user management | Dashboard settings, users, API keys (SQLite DB) |
| **Alloy** | 12345 | Agent on each server, collects and pushes metrics/logs | None (stateless forwarder) |

---

## Where Configuration Files Live

### Stack Configuration (on the Docker host)

| Path | What It Configures |
|------|-------------------|
| `deploy/docker/docker-compose.yml` | Container definitions, ports, volumes, environment variables |
| `.env` | Environment variables for Docker Compose (passwords, webhook URLs) |
| `configs/prometheus/prometheus.yml` | Prometheus server settings, scrape intervals, retention |
| `configs/prometheus/recording_rules.yml` | Pre-computed metrics for dashboard performance |
| `configs/loki/loki.yml` | Loki server settings, storage, retention, limits |
| `configs/alertmanager/alertmanager.yml` | Alert routing tree, receivers, inhibition rules |
| `configs/alertmanager/templates/teams.tmpl` | Teams notification card format |
| `configs/grafana/datasources/` | Prometheus, Loki, and SCOM DW datasource definitions |
| `configs/grafana/dashboards/dashboards.yml` | Dashboard provisioning (maps folders to file paths) |
| `configs/grafana/notifiers/notifiers.yml` | Grafana notification policies and contact points |

### Alert Rules

| Path | What It Contains |
|------|-----------------|
| `alerts/prometheus/windows_alerts.yml` | Windows OS alerts (CPU, memory, disk, services) |
| `alerts/prometheus/linux_alerts.yml` | Linux OS alerts |
| `alerts/prometheus/role_alerts.yml` | Role-specific alerts (AD, SQL, IIS, file server, Docker) |
| `alerts/prometheus/infra_alerts.yml` | Infrastructure self-monitoring alerts |
| `alerts/prometheus/hardware_alerts.yml` | Redfish/BMC hardware alerts |
| `alerts/prometheus/snmp_alerts.yml` | SNMP network device alerts |
| `alerts/prometheus/cert_alerts.yml` | TLS certificate expiry alerts |
| `alerts/prometheus/probe_alerts.yml` | HTTP/ICMP/TCP/DNS probe alerts |
| `alerts/prometheus/outage_alerts.yml` | Site and role outage detection |
| `alerts/prometheus/endpoint_alerts.yml` | File/directory size and process monitoring |
| `alerts/grafana/snmp_trap_alerts.yml` | SNMP trap alerts (Grafana-managed, Loki queries) |

### Dashboard JSON

| Path | Grafana Folder |
|------|---------------|
| `dashboards/enterprise/` | Enterprise (NOC, SLA, probing, audit) |
| `dashboards/servers/` | Servers (Windows, Linux, role dashboards, log explorer) |
| `dashboards/infrastructure/` | Infrastructure (site overview, network, hardware, certs) |
| `dashboards/scom/` | SCOM Monitoring (SCOM DW dashboards) |

### Agent Configuration (on each monitored server)

| Path | What It Contains |
|------|-----------------|
| `configs/alloy/common/` | Shared components (labels, remote_write, loki_push) |
| `configs/alloy/windows/` | Windows base metrics, event log collection, role configs |
| `configs/alloy/linux/` | Linux base metrics, journal collection, role configs |

---

## Alloy Agent Reference

### Role Configs

Each server role has a dedicated Alloy configuration that collects role-specific metrics:

| Role | Config File | What It Monitors | Dashboard |
|------|------------|-----------------|-----------|
| Domain Controller | `role_dc.alloy` | AD DS (LDAP, replication), DNS, DHCP (if co-located) | DC Overview |
| SQL Server | `role_sql.alloy` | Buffer pool, wait stats, database sizes, SQL Agent | SQL Overview |
| IIS Web Server | `role_iis.alloy` | HTTP requests, app pools, status codes, W3C logs | IIS Overview |
| File Server | `role_fileserver.alloy` | SMB sessions, share I/O, disk IOPS | File Server Overview |
| DHCP Server | `role_dhcp.alloy` | DHCP messages (discover/offer/request/ack/nak) | DHCP Overview |
| Certificate Authority | `role_ca.alloy` | Certificate requests, issued/failed/pending, CRL | CA Overview |
| Docker Host | `role_docker.alloy` | Container states, engine metrics, per-container stats | Docker Overview |
| Generic | (base.alloy only) | OS-level metrics only | Windows/Linux Overview |

### Label Taxonomy

Every metric and log entry is tagged with these labels:

| Label | Source | Example | Purpose |
|-------|--------|---------|---------|
| `hostname` | Auto-detected | `srv-sql-03` | Identifies the server |
| `datacenter` | `ALLOY_DATACENTER` env var | `dv` | Identifies the site |
| `role` | `ALLOY_ROLE` env var | `sql` | Identifies the server function |
| `environment` | `ALLOY_ENV` env var | `prod` | Identifies prod vs staging vs dev |
| `os` | Auto-detected | `windows`, `linux` | Operating system |
| `job` | Auto-set by Alloy | `windows_base`, `linux_base` | Collection source |

Labels drive everything: dashboard filters, alert routing, inhibition rules, and RBAC. Correct labeling is critical.

### How Alloy Works

Alloy is a single binary that runs as a service. It:
1. Reads all `.alloy` files from its config directory
2. Starts metric collectors based on the configs present (Windows exporter, node exporter, role-specific collectors)
3. Pushes metrics to Prometheus every 15 seconds via `remote_write`
4. Pushes logs to Loki continuously via the `loki.write` component
5. Reports its own health via a local HTTP endpoint (port 12345)

Alloy is stateless. If it stops, data collection pauses. When it restarts, collection resumes. There is a gap in data for the period it was down, but no data corruption.

---

## Recording Rules

Recording rules are pre-computed metrics that run inside Prometheus. They take raw metrics and produce simplified, aggregated versions that dashboards query.

**Why they exist**: Raw metrics like `windows_cpu_time_total` are counters that need rate calculation and aggregation. Recording rules do this computation once and store the result, so every dashboard panel doesn't have to repeat the same expensive query.

**Where they are defined**: `configs/prometheus/recording_rules.yml`

**Naming convention**: `scope:metric_description:aggregation`

Example: `instance:windows_cpu_utilization:ratio` = per-instance Windows CPU utilization as a ratio (0 to 1).

Sysadmins don't need to interact with recording rules. They run automatically in Prometheus. Engineers may need to add new recording rules when creating new dashboards or alert rules.
