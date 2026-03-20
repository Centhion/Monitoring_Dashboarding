# Enterprise Monitoring and Dashboarding Platform

A fork-and-deploy monitoring platform template built on the Grafana observability stack. Ships with production-ready configs, dashboards, alert rules, fleet deployment tooling, and a Helm chart for Kubernetes. Supports mixed Windows and Linux server environments.

## Purpose

Provide centralized infrastructure monitoring, log aggregation, alerting, and dashboarding for enterprise Windows and Linux servers using open-source tooling. All configurations -- dashboards, alert rules, agent configs, and provisioning -- are version-controlled and reproducible.

## Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Agent | Grafana Alloy | Unified telemetry collector on every server (metrics + logs) |
| Metrics | Prometheus (Phase 1), Mimir (Phase 2) | Time-series metrics ingestion and querying |
| Logs | Loki | Label-based log aggregation |
| Alerting | Alertmanager + Grafana Alerting | Alert routing, grouping, deduplication, notifications |
| Visualization | Grafana | Dashboards, exploration, alert management UI |
| Notifications | Microsoft Teams (webhook) | Alert delivery to operations team |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/<YOUR_ORG>/Monitoring_Dashboarding.git
cd Monitoring_Dashboarding

# Configure the stack (interactive -- sets up sites, SMTP, Teams webhook)
python scripts/deploy_configure.py

# Start the stack
python scripts/stack_manage.py

# Start with demo data (dashboards populate with synthetic multi-site data)
python scripts/stack_manage.py --demo-data

# Open Grafana at http://localhost:3000 (admin / admin)
```

The deployment wrapper generates all config files (`.env`, alertmanager routing, Grafana notifiers, site inventory) from interactive prompts. Re-run to add sites or change settings. See `deploy/site_config.example.yml` for the config schema.

## Structure

| Directory | Purpose |
|-----------|---------|
| `configs/alloy/` | Grafana Alloy agent configurations (Windows, Linux, and site gateway) |
| `configs/prometheus/` | Prometheus server configuration and recording rules |
| `configs/loki/` | Loki server configuration |
| `configs/alertmanager/` | Alertmanager routing, receivers, and inhibition rules |
| `configs/grafana/` | Grafana provisioning (datasources, dashboards, notifiers, LDAP, RBAC) |
| `dashboards/` | Grafana dashboard JSON (enterprise/, servers/, infrastructure/) |
| `alerts/` | Prometheus alerting rules and Grafana alert policies |
| `deploy/docker/` | Docker Compose stack for local testing and PoC |
| `deploy/helm/` | Helm chart and value overlays for Kubernetes deployment |
| `inventory/` | Fleet inventory schemas (sites, hosts, CSV import template) |
| `ansible/` | Ansible playbook for Alloy agent deployment across fleets |
| `scripts/` | Python tooling for config validation, fleet management, RBAC, and testing |
| `docs/` | Architecture docs, runbooks, and project tracking |
| `.claude/` | Agent configuration (instructions, skills, agents, rules, commands) |
| `skills/` | Universal helper scripts (Python) |

## Features

- **Configuration as Code**: All monitoring configs, dashboards, and alert rules stored in Git
- **Mixed OS Support**: Alloy agent configs for both Windows Server and Linux
- **Hub-and-Spoke Dashboards**: Enterprise NOC for multi-site overview, Site Overview for per-site drill-down, plus dedicated Windows, Linux, and IIS dashboards with cross-navigation
- **Industry-Standard Alert Rules**: Alert rules based on SRE best practices and community thresholds
- **Teams Integration**: Alert notifications delivered to Microsoft Teams channels
- **Grafana Provisioning**: Datasources, dashboards, and contact points deployed via provisioning YAML
- **Label-Driven Discovery**: Add sites by setting `ALLOY_DATACENTER` on agents -- dashboards auto-populate with no config changes
- **SNMP Network Monitoring**: Poll switches, firewalls, APs, and UPS devices via Alloy's embedded snmp_exporter with per-interface traffic, utilization, and error tracking
- **SNMP Trap Ingestion**: Receive SNMP traps via snmptrapd sidecar, forward through Alloy to Loki for log-based alerting on link-down, auth-failure, and device-reboot events
- **Hardware Health via Redfish**: Monitor iLO/iDRAC BMC interfaces for system health, temperature, power consumption, and component status (drives, memory)
- **SSL/TLS Certificate Monitoring**: Blackbox probing for internal PKI and public certificates with 30d/7d/expired alerting
- **Two-Tier Deployment**: Tier 1 Alloy agents push from servers; Tier 2 site gateway containers pull SNMP, certificates, and hardware metrics per site
- **Agentless Probing**: ICMP, TCP, UDP/DNS, and HTTP/HTTPS synthetic probes via blackbox exporter with success rate and latency tracking
- **File and Process Monitoring**: Textfile collector pattern for monitoring arbitrary file sizes, directory sizes, and process status on both Windows and Linux
- **SLA Availability Reporting**: Pre-computed availability metrics (1h/1d/7d/30d windows) per host, role, and site with configurable SLA threshold indicators
- **Capacity Forecasting**: predict_linear panels on Windows, Linux, and Infrastructure dashboards showing projected disk, CPU, and memory trends
- **Mass-Outage Detection**: Automatic alert suppression during site-wide or role-wide outages via recording rules and Alertmanager inhibition
- **Maintenance Windows**: Grafana mute timings (recurring) and API-driven programmatic silences with a Python helper script
- **Audit Trail**: Grafana server log forwarding to Loki for login tracking, dashboard changes, and API activity visibility
- **Cloud Monitoring Stubs**: Pre-built Alloy configs for AWS CloudWatch and Azure Monitor (disabled by default, ready to activate)
- **Validation Tooling**: Python scripts to lint and validate configs before deployment
- **Fleet Inventory System**: YAML-based site/host registry with CSV import, Ansible playbook for bulk Alloy deployment, and Prometheus tag compliance auditing
- **RBAC and LDAP/AD Integration**: Grafana folder-based access control with LDAP config template, team provisioning, and API-driven permission management scripts
- **Full Docker Compose Stack**: Blackbox exporter, snmptrapd, and Redfish exporter services alongside core Prometheus/Loki/Alertmanager/Grafana
- **Complete Helm Chart**: Kubernetes deployment with templates for all services, value overlays for dev/staging/production, and optional SNMP/Redfish/LDAP components

## Dashboards

### Enterprise (fleet-wide views)

| Dashboard | UID | Purpose |
|-----------|-----|---------|
| Enterprise NOC | `enterprise-noc` | Multi-site health grid with drill-down links per datacenter |
| SLA Availability | `sla-availability` | Host/role/site uptime percentages with SLA threshold indicators |
| Audit Trail | `audit-trail` | Grafana user activity: logins, dashboard changes, API requests |
| Probing Overview | `probing-overview` | Synthetic probe status grid, success rates, and latency analysis |

### Servers (VMs by OS and role)

| Dashboard | UID | Purpose |
|-----------|-----|---------|
| Windows Server Overview | `windows-overview` | Per-host Windows CPU, memory, disk, network, services |
| Linux Server Overview | `linux-overview` | Per-host Linux CPU, memory, disk, network, systemd |
| SQL Server Overview | `sql-overview` | Buffer cache, wait stats, deadlocks, database sizes |
| Domain Controller Overview | `dc-overview` | AD replication, LDAP, DNS queries, Kerberos, service health |
| IIS Web Server Overview | `iis-overview` | Request rates, error ratios, connections, access logs |
| DHCP Server Overview | `dhcp-overview` | DHCP message rates (discover, offer, request, ack, nak) |
| Certificate Authority Overview | `ca-overview` | AD CS certificate issuance, failures, pending requests |
| File Server Overview | `fileserver-overview` | SMB sessions, share I/O, disk IOPS, FSRM quotas |
| Docker Host Overview | `docker-overview` | Container states, engine metrics, resource usage |
| Log Explorer | `log-explorer` | Cross-platform log search across Windows Event Log, Linux journal, and IIS |

### Infrastructure (physical layer and site-level views)

| Dashboard | UID | Purpose |
|-----------|-----|---------|
| Site Overview | `site-overview` | Single-site drill-down with servers, IIS, network, hardware, certs |
| Infrastructure Overview | `infra-overview` | Fleet-wide server metrics, top problem servers, alerts |
| Network Infrastructure | `network-overview` | SNMP device inventory, interface status, traffic, utilization |
| Physical Server Health | `hardware-overview` | Redfish BMC health, temperatures, power, component status |
| Certificate Overview | `cert-overview` | SSL/TLS certificate expiry tracking with probe health |

All dashboards include a cross-navigation link bar. Template variables (`environment`, `datacenter`, `hostname`) propagate between dashboards for seamless drill-down. Navigation flow: Enterprise NOC -> Site Overview -> role-specific dashboard.

## Scripts

Python tooling in `scripts/` for validation, deployment, fleet management, and testing.

### Validation

| Script | Purpose |
|--------|---------|
| `validate_all.py` | Orchestrates all validators and produces a unified report (for local dev and CI) |
| `validate_alloy.py` | Validates Alloy `.alloy` configs -- balanced braces, required components, env var usage, duplicate labels |
| `validate_dashboards.py` | Validates Grafana dashboard JSON -- metadata, UIDs, template variables, panel structure, datasource refs |
| `validate_prometheus.py` | Validates Prometheus/Alertmanager configs -- YAML syntax, label taxonomy, duration formats, no hardcoded secrets |
| `validate_fleet_tags.py` | Queries live Prometheus and compares host labels against inventory to detect drift and unknown hosts |
| `validate_rbac.py` | Compares live Grafana RBAC state against desired state in `folder-permissions.yml` (CI gate) |
| `validate_on_save.py` | Lightweight post-save hook for fast YAML/JSON syntax checks during editing |

### Deployment and Configuration

| Script | Purpose |
|--------|---------|
| `stack_manage.py` | One-command Docker Compose startup -- validates prereqs, starts services, waits for health checks |
| `deploy_configure.py` | Generates config files (`.env`, `sites.yml`, `hosts.yml`, `alertmanager.yml`) interactively or from file |
| `configure_rbac.py` | Applies RBAC permission model to Grafana via API -- creates teams, folders, and folder-level permissions |
| `maintenance_window.py` | Creates, lists, and removes Grafana mute timings for planned maintenance windows |

### Fleet and Inventory

| Script | Purpose |
|--------|---------|
| `fleet_inventory.py` | Manages host inventory (`sites.yml`/`hosts.yml`) -- validates, reports, imports from CSV, generates Ansible inventory |
| `lansweeper_sync.py` | Syncs asset data from Lansweeper Cloud GraphQL API into `inventory/hosts.yml` |

### Testing

| Script | Purpose |
|--------|---------|
| `demo_data_generator.py` | Pushes synthetic metrics and logs into Prometheus and Loki to populate dashboards with realistic demo data |

## Documentation

- See `QUICKSTART.md` for getting started (Docker Compose local testing and Helm K8s deployment)
- See `ARCHITECTURE.md` for design patterns, stack details, and decisions
- See `docs/PROJECT_PLAN.md` for current status and task tracking
- See `docs/ALLOY_DEPLOYMENT.md` for Alloy agent deployment on Windows and Linux
- See `docs/BACKEND_DEPLOYMENT.md` for Prometheus, Loki, Alertmanager, and Grafana deployment
- See `docs/ALERT_RUNBOOKS.md` for alert investigation and remediation procedures
- See `docs/DASHBOARD_GUIDE.md` for dashboard customization and creation
- See `docs/VALIDATION_TOOLING.md` for config validation scripts and CI integration
- See `docs/ALERT_DEDUP.md` for mass-outage detection and alert suppression architecture
- See `docs/MAINTENANCE_WINDOWS.md` for scheduled and ad-hoc alert silencing workflows
- See `docs/AUDIT_LOGGING.md` for Grafana audit trail setup and LogQL query examples
- See `docs/SNMP_TRAPS.md` for SNMP trap ingestion pipeline setup
- See `docs/CLOUD_MONITORING.md` for AWS CloudWatch and Azure Monitor integration
- See `docs/REQUIREMENTS_TRACEABILITY.md` for full requirements coverage matrix
- See `docs/ALLOY_DEPLOYMENT.md` for fleet onboarding (adding sites, servers, and devices)
- See `docs/SNMP_MONITORING.md` for SNMP network device monitoring setup
- See `docs/HARDWARE_MONITORING.md` for Redfish BMC hardware health monitoring
- See `docs/CERTIFICATE_MONITORING.md` for SSL/TLS certificate expiry monitoring
- See `docs/AGENTLESS_MONITORING.md` for monitoring devices without agents
- See `docs/RBAC_GUIDE.md` for Grafana RBAC and LDAP/AD integration
- See `docs/DEPLOYMENT_VALUES.md` for production configuration value reference
- See `docs/BRANCHING_STRATEGY.md` for public template vs internal fork branch model
- See `docs/TESTING_CHECKLIST.md` for post-deployment validation checklist

## Development

This project uses Claude Code with the following commands:

| Command | Description |
|---------|-------------|
| `/setup` | Initial project configuration |
| `/status` | Show Git state and active tasks |
| `/commit` | Generate a commit message |
| `/plan` | Design implementation approach |
| `/handoff` | Generate session summary |

## License

(Add your license here)
