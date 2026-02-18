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
+-------------------+     +-------------------+
| Windows Servers   |     | Linux Servers     |
| (Grafana Alloy)   |     | (Grafana Alloy)   |
+--------+----------+     +--------+----------+
         |                          |
         |  metrics (remote write)  |  metrics (remote write)
         |  logs (push)             |  logs (push)
         v                          v
+--------+----------+     +--------+----------+
| Prometheus        |     | Loki              |
| (metrics)         |     | (logs)            |
+--------+----------+     +--------+----------+
         |                          |
         |  alert rules evaluate    |
         v                          |
+--------+----------+               |
| Alertmanager      |               |
| (routing/grouping)|               |
+--------+----------+               |
         |                          |
         |  webhooks                |
         v                          |
+--------+----------+               |
| Microsoft Teams   |               |
+-------------------+               |
                                    |
         +-----+-------------------+
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
|   +-- prometheus/             # Prometheus server config and recording rules
|   +-- loki/                   # Loki server config
|   +-- alertmanager/           # Alertmanager routing and receivers
|   +-- grafana/                # Grafana provisioning
|       +-- datasources/        # Datasource provisioning YAML
|       +-- dashboards/         # Dashboard provisioning YAML (points to dashboards/)
|       +-- notifiers/          # Contact point provisioning
+-- dashboards/                  # Grafana dashboard JSON files
|   +-- windows/                # Windows Server dashboards
|   +-- linux/                  # Linux Server dashboards
|   +-- overview/               # Infrastructure overview dashboards
+-- alerts/                      # Alert rule definitions
|   +-- prometheus/             # Prometheus alerting rules (YAML)
|   +-- grafana/                # Grafana-managed alert rules (JSON)
+-- scripts/                     # Python tooling
|   +-- validate_configs.py     # Config linter and validator
|   +-- generate_dashboard.py   # Dashboard template generator
+-- skills/                      # Universal helper scripts
+-- docs/                        # Documentation
|   +-- PROJECT_PLAN.md         # Task tracking (single source of truth)
|   +-- SSH_AUTHENTICATION.md   # Git auth setup
+-- tests/                       # Test files for config validation
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

## Phase 2 Additions

When scaling beyond Phase 1:

| Component | Purpose | Trigger |
|-----------|---------|---------|
| Grafana Mimir | Replaces Prometheus for long-term storage | Need >30 days retention or HA |
| Object Storage (S3/Azure Blob) | Mimir backend storage | Required by Mimir |
