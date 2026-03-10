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

# Set up environment
cp .env.example .env
# Edit .env with your environment-specific values (webhook URLs, endpoints, etc.)

# Start the full stack locally via Docker Compose
python scripts/poc_setup.py

# Open Grafana at http://localhost:3000 (admin / admin)
```

## Structure

| Directory | Purpose |
|-----------|---------|
| `configs/alloy/` | Grafana Alloy agent configurations (Windows, Linux, and site gateway) |
| `configs/prometheus/` | Prometheus server configuration and recording rules |
| `configs/loki/` | Loki server configuration |
| `configs/alertmanager/` | Alertmanager routing, receivers, and inhibition rules |
| `configs/grafana/` | Grafana provisioning (datasources, dashboards, notifiers) |
| `dashboards/` | Grafana dashboard JSON (windows/, linux/, overview/, network/, hardware/, certs/, assets/) |
| `alerts/` | Prometheus alerting rules and Grafana alert policies |
| `deploy/docker/` | Docker Compose stack for local testing and PoC |
| `deploy/helm/` | Helm chart and value overlays for Kubernetes deployment |
| `scripts/` | Python tooling for config validation, generation, and testing |
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

## Dashboards

| Dashboard | UID | Folder | Purpose |
|-----------|-----|--------|---------|
| Enterprise NOC | `enterprise-noc` | Infrastructure | Multi-site health grid with drill-down links per datacenter |
| Site Overview | `site-overview` | Infrastructure | Single-site deep view with server, IIS, and log panels |
| Infrastructure Overview | `infra-overview` | Infrastructure | Fleet-wide server metrics, top problem servers, alerts |
| Windows Server Overview | `windows-overview` | Windows Servers | Per-host Windows CPU, memory, disk, network, services |
| Linux Server Overview | `linux-overview` | Linux Servers | Per-host Linux CPU, memory, disk, network, systemd |
| IIS Overview | `iis-overview` | Windows Servers | IIS request rates, error ratios, connections, access logs |
| Certificate Overview | `cert-overview` | Certificates | SSL/TLS certificate expiry tracking with probe health |
| Network Infrastructure | `network-overview` | Network | SNMP device inventory, interface status, traffic, utilization |
| Hardware Health | `hardware-overview` | Hardware | Redfish BMC health, temperatures, power, component status |
| SLA Availability | `sla-availability` | Infrastructure | Host/role/site uptime percentages with SLA threshold indicators |
| Probing Overview | `probing-overview` | Infrastructure | Synthetic probe status grid, success rates, and latency analysis |
| Audit Trail | `audit-trail` | Infrastructure | Grafana user activity: logins, dashboard changes, API requests |
| Log Explorer | `log-explorer` | Infrastructure | Cross-platform log search across Windows Event Log, Linux journal, and IIS |

All dashboards include a cross-navigation link bar. Template variables (`environment`, `datacenter`, `hostname`) propagate between dashboards for seamless drill-down.

## Documentation

- See `QUICKSTART.md` for getting started (Docker Compose local testing and Helm K8s deployment)
- See `ARCHITECTURE.md` for design patterns, stack details, and decisions
- See `docs/PROJECT_PLAN.md` for current status and task tracking
- See `docs/ALLOY_DEPLOYMENT.md` for Alloy agent deployment on Windows and Linux
- See `docs/BACKEND_DEPLOYMENT.md` for Prometheus, Loki, Alertmanager, and Grafana deployment
- See `docs/ALERT_RUNBOOKS.md` for alert investigation and remediation procedures
- See `docs/DASHBOARD_GUIDE.md` for dashboard customization and creation
- See `docs/VALIDATION_TOOLING.md` for config validation scripts and CI integration
- See `docs/LOCAL_TESTING.md` for Docker Compose PoC setup and Alloy local testing
- See `docs/ALERT_DEDUP.md` for mass-outage detection and alert suppression architecture
- See `docs/MAINTENANCE_WINDOWS.md` for scheduled and ad-hoc alert silencing workflows
- See `docs/AUDIT_LOGGING.md` for Grafana audit trail setup and LogQL query examples
- See `docs/SNMP_TRAPS.md` for SNMP trap ingestion pipeline setup
- See `docs/CLOUD_MONITORING.md` for AWS CloudWatch and Azure Monitor integration
- See `docs/REQUIREMENTS_TRACEABILITY.md` for full requirements coverage matrix
- See `docs/FLEET_ONBOARDING.md` for adding sites, servers, and devices to the platform
- See `docs/SNMP_MONITORING.md` for SNMP network device monitoring setup
- See `docs/HARDWARE_MONITORING.md` for Redfish BMC hardware health monitoring
- See `docs/CERTIFICATE_MONITORING.md` for SSL/TLS certificate expiry monitoring
- See `docs/AGENTLESS_MONITORING.md` for monitoring devices without agents
- See `docs/RBAC_GUIDE.md` for Grafana RBAC and LDAP/AD integration

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
