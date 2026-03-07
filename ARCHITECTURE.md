# Architecture

This document outlines the architecture and design decisions for the Enterprise Monitoring and Dashboarding Platform.

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Agent | Grafana Alloy | Latest | Unified telemetry collector deployed to every monitored server |
| Metrics Storage (Phase 1) | Prometheus | 2.x | Time-series metrics ingestion, short-term storage, PromQL querying |
| Metrics Storage (Phase 2) | Grafana Mimir | Latest | Long-term metrics storage with horizontal scaling and object storage backend |
| Log Aggregation | Grafana Loki | Latest | Label-indexed log aggregation paired with Grafana |
| Alert Management | Prometheus Alertmanager | Latest | Alert routing, grouping, deduplication, silencing, and notification dispatch |
| Visualization | Grafana | Latest | Dashboards, data exploration, unified alerting UI |
| Notifications | Microsoft Teams Webhooks | N/A | Alert delivery via incoming webhook to Teams channels |
| Tooling | Python 3.x | 3.10+ | Config validation, dashboard generation, testing scripts |

## Data Flow

```
  TIER 1: Per-Server Agents (Push)       TIER 2: Per-Site Gateway (Pull)

+-------------------+  +---------------+  +-----------------------------+
| Windows Servers   |  | Linux Servers |  | Alloy Site Gateway          |
| (Grafana Alloy)   |  | (Grafana Alloy)|  |   SNMP exporter (embedded) |
+--------+----------+  +-------+-------+  |   Blackbox exporter (certs) |
         |                      |          |   Redfish exporter (sidecar)|
         | metrics (remote write)          +-------------+--------------+
         | logs (push)          |                        |
         v                      v          metrics (remote write)
+--------+----------+  +--------+------+               |
| Prometheus        |<-+---------------+---------------+
| (metrics)         |
+--------+----------+  +--------+------+
         |              | Loki         |<--- logs (push) from Tier 1
         | alert rules  | (logs)       |
         v              +--------+-----+
+--------+----------+            |
| Alertmanager      |            |
| (routing/grouping)|            |
+--------+----------+            |
         |                       |
         | webhooks              |
         v                       |
+--------+----------+            |
| Microsoft Teams   |            |
+-------------------+            |
                                 |
         +-----+-----------------+
         |
         v
+--------+----------+
| Grafana           |
| (dashboards,      |
|  exploration,     |
|  alerting UI)     |
+-------------------+
```

## Directory Structure

```
Monitoring_Dashboarding/
+-- .claude/                     # Agent configuration
|   +-- CLAUDE.md               # Main instructions and rules
|   +-- settings.json           # Permissions and hooks
|   +-- commands/               # Slash command definitions
|   +-- agents/                 # Sub-agent prompts
|   |   +-- general/            # Universal agents (security, pre-commit, etc.)
|   |   +-- project/            # Project-specific agents (config-validator, etc.)
|   +-- skills/                 # Skill definitions
|   +-- rules/                  # Modular guidelines
+-- configs/                     # All service configurations
|   +-- alloy/                  # Grafana Alloy agent configs
|   |   +-- common/             # Shared components (labels, remote_write, loki_push)
|   |   +-- windows/            # Windows base + role configs (.alloy)
|   |   +-- linux/              # Linux base + role configs (.alloy)
|   |   +-- gateway/            # Tier 2 site gateway (SNMP, Blackbox, Redfish)
|   |   +-- certs/              # Certificate blackbox probe modules and endpoints
|   |   +-- roles/              # Standalone role configs (cert monitor)
|   +-- prometheus/             # Prometheus server config and recording rules
|   +-- loki/                   # Loki server config
|   +-- alertmanager/           # Alertmanager routing and receivers
|   +-- grafana/                # Grafana provisioning
|       +-- datasources/        # Datasource provisioning YAML
|       +-- dashboards/         # Dashboard provisioning YAML (points to dashboards/)
|       +-- notifiers/          # Contact point provisioning
+-- dashboards/                  # Grafana dashboard JSON files
|   +-- windows/                # Windows Server dashboards (windows_overview, iis_overview)
|   +-- linux/                  # Linux Server dashboards (linux_overview)
|   +-- overview/               # Hub dashboards (enterprise_noc, site_overview, infrastructure_overview, log_explorer)
|   +-- network/                # Network infrastructure dashboards (Phase 7A)
|   +-- hardware/               # Hardware health dashboards (Phase 7B)
|   +-- certs/                  # Certificate monitoring dashboards (Phase 7C)
|   +-- assets/                 # Asset intelligence dashboards (Phase 7D)
+-- alerts/                      # Alert rule definitions
|   +-- prometheus/             # Prometheus alerting rules (YAML)
|   +-- grafana/                # Grafana-managed alert rules (JSON)
+-- scripts/                     # Python tooling
|   +-- validate_alloy.py      # Alloy config structural validator
|   +-- validate_prometheus.py # Prometheus/Alertmanager YAML validator
|   +-- validate_dashboards.py # Grafana dashboard JSON validator
|   +-- validate_all.py        # Unified validation runner
|   +-- validate_on_save.py    # PostToolUse hook for fast syntax checks
+-- skills/                      # Universal helper scripts
+-- docs/                        # Documentation
|   +-- PROJECT_PLAN.md         # Task tracking (single source of truth)
|   +-- ALLOY_DEPLOYMENT.md    # Alloy agent deployment guide
|   +-- BACKEND_DEPLOYMENT.md  # Backend service deployment guide
|   +-- ALERT_RUNBOOKS.md      # Alert response procedures
|   +-- DASHBOARD_GUIDE.md     # Dashboard customization guide
|   +-- VALIDATION_TOOLING.md  # Validator usage and CI integration
+-- tests/                       # Test suite for validators
|   +-- test_validators.py     # 12 test cases for all validators
|   +-- fixtures/              # Valid and invalid config fixtures
+-- requirements.txt             # Python dependencies (pyyaml, pytest)
+-- .env.example                 # Template for environment variables
+-- .gitignore                   # Git exclusions
+-- README.md                    # Project overview
+-- ARCHITECTURE.md              # This file
```

## Design Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| Grafana Alloy over separate node_exporter + Promtail | Single agent binary simplifies deployment across mixed OS fleet. Alloy natively supports Windows. | 2026-02-17 |
| Prometheus Phase 1, Mimir Phase 2 | Start simple with Prometheus local storage. Migrate to Mimir when long-term retention or HA is needed. Alloy remote_write works with both. | 2026-02-17 |
| Loki over Elasticsearch | Lower operational cost for log aggregation. Label-indexed approach sufficient for server monitoring. Native Grafana integration. | 2026-02-17 |
| Configuration-as-code approach | All configs version-controlled for auditability, reproducibility, and team collaboration. Enterprise requirement. | 2026-02-17 |
| Python for tooling | Widely available, good library ecosystem for YAML/JSON validation, team familiarity. | 2026-02-17 |
| Teams webhook over MCP integration | Simple HTTP webhook is sufficient for alert notifications. No external dependency or MCP server needed. | 2026-02-17 |
| Hub-and-spoke dashboard architecture | Enterprise NOC (multi-site grid) and Site Overview (per-resort drill-down) provide location-centric navigation. Template variables propagate between dashboards via URL params. Sites auto-populate from `datacenter` label -- no dashboard changes needed to add sites. | 2026-03-06 |
| Site recording rules layer | Pre-aggregate instance metrics to datacenter level (`site:*` namespace) so hub dashboards query cheap pre-computed series instead of scanning all instances. | 2026-03-06 |
| Two-tier Alloy deployment model | Tier 1: Alloy Agent installed per server (push-based, deployed via SCCM/Ansible). Tier 2: Alloy Site Gateway container per site (pull-based, polls SNMP/certs/hardware). Separates agent-based from gateway-based monitoring cleanly. | 2026-03-07 |
| Embedded SNMP exporter over standalone | Alloy natively embeds snmp_exporter via `prometheus.exporter.snmp`, eliminating a separate container. Supports `config_merge_strategy = "merge"` to extend built-in modules (system, if_mib) with custom vendor profiles. | 2026-03-07 |
| External Redfish exporter as sidecar | Alloy has no native Redfish component. A Redfish exporter sidecar runs alongside the site gateway container, accepting BMC targets via the multi-target URL parameter pattern (`__param_target`). | 2026-03-07 |

## External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Grafana Alloy | Latest | Telemetry collection agent |
| Prometheus | 2.x | Metrics storage and querying |
| Grafana Loki | Latest | Log aggregation |
| Alertmanager | Latest (ships with Prometheus) | Alert routing and notification |
| Grafana | Latest | Visualization and alerting UI |
| Python | 3.10+ | Tooling scripts |
| PyYAML | Latest | YAML parsing for config validation |
| jsonschema | Latest | JSON schema validation for dashboards |
| Redfish Exporter | Latest | Sidecar for polling iLO/iDRAC BMC interfaces via Redfish API (Tier 2 gateway) |

## Phase 2 Additions

When scaling beyond Phase 1:

| Component | Purpose | Trigger |
|-----------|---------|---------|
| Grafana Mimir | Replaces Prometheus for long-term storage | Need >30 days retention or HA |
| Object Storage (S3/Azure Blob) | Mimir backend storage | Required by Mimir |
