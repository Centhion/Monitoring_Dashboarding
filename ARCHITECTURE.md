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
|   |   +-- roles/              # Standalone role configs (cert monitor, audit logging)
|   |   +-- cloud/              # Cloud provider stubs (AWS CloudWatch, Azure Monitor)
|   +-- prometheus/             # Prometheus server config and recording rules
|   +-- snmptrapd/              # snmptrapd trap receiver config (sidecar)
|   +-- loki/                   # Loki server config
|   +-- alertmanager/           # Alertmanager routing and receivers
|   +-- grafana/                # Grafana provisioning
|       +-- datasources/        # Datasource provisioning YAML
|       +-- dashboards/         # Dashboard provisioning YAML (points to dashboards/)
|       +-- notifiers/          # Contact point provisioning
|       +-- ldap.toml           # LDAP/AD authentication template (Phase 8)
|       +-- provisioning/access-control/ # Team and folder permission definitions
+-- dashboards/                  # Grafana dashboard JSON files
|   +-- windows/                # Windows Server dashboards (windows_overview, iis_overview)
|   +-- linux/                  # Linux Server dashboards (linux_overview)
|   +-- overview/               # Hub dashboards (enterprise_noc, site_overview, infra, log_explorer, sla, probing, audit)
|   +-- network/                # Network infrastructure dashboards (Phase 7A)
|   +-- hardware/               # Hardware health dashboards (Phase 7B)
|   +-- certs/                  # Certificate monitoring dashboards (Phase 7C)
+-- alerts/                      # Alert rule definitions
|   +-- prometheus/             # Prometheus alerting rules (YAML)
|   +-- grafana/                # Grafana-managed alert rules (JSON)
+-- scripts/                     # Python tooling
|   +-- validate_alloy.py      # Alloy config structural validator
|   +-- validate_prometheus.py # Prometheus/Alertmanager YAML validator
|   +-- validate_dashboards.py # Grafana dashboard JSON validator
|   +-- validate_all.py        # Unified validation runner
|   +-- validate_on_save.py    # PostToolUse hook for fast syntax checks
|   +-- maintenance_window.py  # Grafana mute timing API helper (create/list/delete)
|   +-- fleet_inventory.py    # Inventory management (validate, report, import CSV)
|   +-- lansweeper_sync.py   # Lansweeper GraphQL API sync (Phase 7D)
|   +-- validate_fleet_tags.py # Tag compliance audit against Prometheus
|   +-- configure_rbac.py     # Apply RBAC folder permissions via Grafana API
|   +-- validate_rbac.py      # Validate RBAC state against config
+-- inventory/                   # Fleet inventory
|   +-- sites.yml              # Site/datacenter registry
|   +-- hosts.yml              # Server inventory (hostname, site, role, OS)
|   +-- hosts.csv.example      # CSV import template
|   +-- lansweeper_field_map.yml # Lansweeper-to-monitoring field mapping (Phase 7D)
+-- ansible/                     # Deployment automation
|   +-- deploy_alloy.yml      # Ansible playbook for Alloy agent deployment
|   +-- inventory.yml          # Ansible inventory template
+-- skills/                      # Universal helper scripts
+-- docs/                        # Documentation
|   +-- PROJECT_PLAN.md         # Task tracking (single source of truth)
|   +-- ALLOY_DEPLOYMENT.md    # Alloy agent deployment guide
|   +-- BACKEND_DEPLOYMENT.md  # Backend service deployment guide
|   +-- ALERT_RUNBOOKS.md      # Alert response procedures
|   +-- DASHBOARD_GUIDE.md     # Dashboard customization guide
|   +-- VALIDATION_TOOLING.md  # Validator usage and CI integration
|   +-- ALERT_DEDUP.md         # Mass-outage detection and alert suppression
|   +-- MAINTENANCE_WINDOWS.md # Scheduled and ad-hoc alert silencing
|   +-- AUDIT_LOGGING.md       # Grafana audit trail setup
|   +-- SNMP_TRAPS.md          # SNMP trap ingestion pipeline
|   +-- CLOUD_MONITORING.md    # AWS/Azure integration stubs
|   +-- REQUIREMENTS_TRACEABILITY.md # Requirements coverage matrix
|   +-- BRANCHING_STRATEGY.md  # Public template vs internal branch model
|   +-- SNMP_MONITORING.md     # SNMP network device monitoring guide
|   +-- HARDWARE_MONITORING.md # Redfish BMC hardware health guide
|   +-- CERTIFICATE_MONITORING.md # SSL/TLS certificate monitoring guide
|   +-- ALLOY_DEPLOYMENT.md    # Agent deployment and fleet onboarding
|   +-- AGENTLESS_MONITORING.md # Monitoring without agents
|   +-- RBAC_GUIDE.md          # Grafana RBAC and LDAP/AD integration
|   +-- LANSWEEPER_INTEGRATION.md # Lansweeper API sync setup and usage (Phase 7D)
+-- tests/                       # Test suite for validators
|   +-- test_validators.py     # 12 test cases for all validators
|   +-- fixtures/              # Valid and invalid config fixtures
+-- requirements.txt             # Python dependencies (pyyaml, pytest)
+-- .env.example                 # Template for environment variables
+-- .gitignore                   # Git exclusions
+-- README.md                    # Project overview
+-- ARCHITECTURE.md              # This file
```

## Label Taxonomy

Every metric and log entry carries these standard labels, set via Alloy agent environment variables on each monitored server. These labels drive dashboard filtering, alert routing, and fleet grouping across the platform.

| Label | Purpose | Example Values | Set By |
|-------|---------|----------------|--------|
| `environment` | Deployment stage | `production`, `staging`, `development` | `ALLOY_ENV` env var |
| `datacenter` | Physical or logical site | `dc-east`, `dc-west`, `cloud-us` | `ALLOY_DATACENTER` env var |
| `role` | Server function | `dc`, `sql`, `iis`, `file`, `docker` | `ALLOY_ROLE` env var |
| `os` | Operating system | `windows`, `linux` | Auto-detected by Alloy |
| `hostname` | Server name | `web01`, `db-prod-03` | Auto-detected (`constants.hostname`) |

**Why labels matter**: Alertmanager routes alerts by `datacenter` to site-specific email distribution lists. Grafana dashboard template variables filter by `environment`, `datacenter`, `role`, and `hostname`. Recording rules aggregate by `datacenter` for site-level metrics. Getting labels right during agent deployment is the most impactful configuration step.

## Data Flow: Future State (Mimir)

The current data flow (above) uses Prometheus as both the metrics store and query backend. Phase 6 introduces Grafana Mimir for long-term storage while Prometheus continues handling scrape, rule evaluation, and short-term queries.

```
Servers (Alloy agent)
  |
  |-- metrics --> Prometheus --remote_write--> Mimir (long-term storage)
  |                   |                         |
  |                   +--> Alert Rules ----+    |
  |                                        |    |
  |                         Alertmanager <-+    |
  |                           |                 |
  |                      Teams / Email          |
  |-- logs -----> Loki                          |
  |                                             |
Grafana (dashboards) <--- queries ---> Mimir + Loki
```

**Migration path**: The migration from Prometheus to Mimir is non-destructive. Prometheus continues running during the transition. The steps are:
1. Deploy Mimir with object storage backend (S3, GCS, or Azure Blob)
2. Add Mimir as a `remote_write` target in Prometheus config (dual-write)
3. Let Mimir accumulate data for the desired retention window
4. Switch Grafana's Prometheus datasource URL to point at Mimir query-frontend
5. Validate dashboards and alerts work unchanged (Mimir is PromQL-compatible)
6. Optionally reduce Prometheus local retention since Mimir holds long-term data

**Rollback**: Point Grafana's datasource back at Prometheus. No data loss -- Prometheus retains its local TSDB during the migration.

**When to migrate**: Prometheus local storage becomes a bottleneck when disk usage exceeds 50-75% regularly, retention beyond 30 days is needed for capacity planning or compliance, or HA is required for the metrics backend.

## Access Control and RBAC Architecture

Production deployments restrict dashboard visibility so each site's IT team sees only their own infrastructure while enterprise operations sees everything. Grafana provides this through folder-level permissions, Teams, and LDAP group synchronization.

### Access Tiers

| Tier | Who | What They See | Grafana Role |
|------|-----|---------------|-------------|
| **Enterprise NOC** | Central ops, platform team | All dashboards, all sites, admin settings | Org Admin or Editor |
| **Site Ops** | Per-site IT team (e.g., dc-east ops) | Only their site's dashboards and alerts | Viewer (scoped to site folder) |
| **Read-Only Stakeholders** | Management, compliance | Enterprise overview dashboards only | Viewer (scoped to overview folder) |

### Folder Structure

Grafana's folder permissions provide the access boundary. Each site gets its own dashboard folder, and Teams control who can see which folders.

```
Dashboards/
  Enterprise/          -- NOC overview, fleet dashboards (enterprise ops only)
  Site - DC East/      -- dc-east Windows, Linux, network dashboards
  Site - DC West/      -- dc-west Windows, Linux, network dashboards
  Site - Cloud US/     -- cloud-us dashboards
  Shared/              -- Cross-site dashboards (log explorer, cert overview)
```

For each site folder, the default org-level Viewer permission is removed and access is granted only to the relevant Team. This ensures a dc-east engineer cannot see dc-west dashboards.

### Team-to-Folder Permission Model

| Grafana Team | Folder Access |
|-------------|---------------|
| `Enterprise Ops` | Editor on all folders |
| `DC-East Ops` | Viewer on `Site - DC East/` and `Shared/` |
| `DC-West Ops` | Viewer on `Site - DC West/` and `Shared/` |
| `Cloud-US Ops` | Viewer on `Site - Cloud US/` and `Shared/` |
| `Stakeholders` | Viewer on `Enterprise/` only |

### LDAP/AD Group Synchronization

For enterprise deployments, Grafana authenticates against Active Directory so user accounts do not need to be managed manually. AD security groups map to Grafana Teams automatically -- adding a user to an AD group grants them the corresponding Grafana Team membership and folder access on next login.

**Identity platform**: Hybrid AD / Entra ID environments use on-premises domain controllers for LDAP bind. Grafana's LDAP integration authenticates against the on-prem AD (port 636 for LDAPS). Entra ID syncs users/groups to on-prem AD via Azure AD Connect, so the LDAP source remains the on-prem domain controller.

**Recommended AD group structure:**

| AD Security Group | Maps to Grafana Team | Dashboard Access |
|-------------------|---------------------|-----------------|
| `SG-Monitoring-Admins` | Enterprise Ops | All folders (Editor) |
| `SG-Monitoring-DCEast` | DC-East Ops | Site - DC East, Shared (Viewer) |
| `SG-Monitoring-DCWest` | DC-West Ops | Site - DC West, Shared (Viewer) |
| `SG-Monitoring-CloudUS` | Cloud-US Ops | Site - Cloud US, Shared (Viewer) |
| `SG-Monitoring-Readonly` | Stakeholders | Enterprise (Viewer) |

**Onboarding workflow**: Adding a new site team member is a single AD group add. No Grafana configuration needed. Users are auto-provisioned on first login with the default Viewer role, and their Team membership (and thus folder access) is determined by AD group sync.

### Template Variable Scoping

The dashboards in this repo use `datacenter` as a template variable. When a site team member opens a dashboard, the variable dropdown only shows data their Alloy agents are sending (because their servers' `ALLOY_DATACENTER` label matches their site). Folder permissions add the access boundary; template variables scope the data within dashboards they can access.

## Design Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| Grafana Alloy over separate node_exporter + Promtail | Single agent binary simplifies deployment across mixed OS fleet. Alloy natively supports Windows. | 2026-02-17 |
| Prometheus Phase 1, Mimir Phase 2 | Start simple with Prometheus local storage. Migrate to Mimir when long-term retention or HA is needed. Alloy remote_write works with both. | 2026-02-17 |
| Loki over Elasticsearch | Lower operational cost for log aggregation. Label-indexed approach sufficient for server monitoring. Native Grafana integration. | 2026-02-17 |
| Configuration-as-code approach | All configs version-controlled for auditability, reproducibility, and team collaboration. Enterprise requirement. | 2026-02-17 |
| Python for tooling | Widely available, good library ecosystem for YAML/JSON validation, team familiarity. | 2026-02-17 |
| Teams webhook over MCP integration | Simple HTTP webhook is sufficient for alert notifications. No external dependency or MCP server needed. | 2026-02-17 |
| Hub-and-spoke dashboard architecture | Enterprise NOC (multi-site grid) and Site Overview (per-site drill-down) provide location-centric navigation. Template variables propagate between dashboards via URL params. Sites auto-populate from `datacenter` label -- no dashboard changes needed to add sites. | 2026-03-06 |
| Site recording rules layer | Pre-aggregate instance metrics to datacenter level (`site:*` namespace) so hub dashboards query cheap pre-computed series instead of scanning all instances. | 2026-03-06 |
| Two-tier Alloy deployment model | Tier 1: Alloy Agent installed per server (push-based, deployed via SCCM/Ansible). Tier 2: Alloy Site Gateway container per site (pull-based, polls SNMP/certs/hardware). Separates agent-based from gateway-based monitoring cleanly. | 2026-03-07 |
| Embedded SNMP exporter over standalone | Alloy natively embeds snmp_exporter via `prometheus.exporter.snmp`, eliminating a separate container. Supports `config_merge_strategy = "merge"` to extend built-in modules (system, if_mib) with custom vendor profiles. | 2026-03-07 |
| External Redfish exporter as sidecar | Alloy has no native Redfish component. A Redfish exporter sidecar runs alongside the site gateway container, accepting BMC targets via the multi-target URL parameter pattern (`__param_target`). | 2026-03-07 |
| Folder-based RBAC over Grafana Organizations | Single Org with folder-level permissions is simpler to manage than multi-Org. Teams + folder permissions provide site isolation without duplicating datasources or dashboards. Multi-Org is only needed for true multi-tenant SaaS, not internal site separation. | 2026-03-07 |
| LDAP group sync over manual Grafana user management | AD security groups map to Grafana Teams automatically. Onboarding is a single AD group add -- no Grafana admin action needed. Supports hybrid AD/Entra ID via on-prem LDAP bind. | 2026-03-07 |
| Nutanix NKP as Kubernetes platform | Production Kubernetes runs on Nutanix Kubernetes Platform (NKP) in datacenter infrastructure. Persistent volumes use Nutanix CSI driver with Nutanix Volumes storage class. Helm chart storageClass values should reference the Nutanix provisioner. | 2026-03-09 |
| Statistical mass-outage detection over topology mapping | Recording rules compute hosts-up ratios per site/role. When a significant percentage drops, site/role-level alerts fire and Alertmanager inhibition rules suppress per-host noise. Zero topology maintenance required. | 2026-03-09 |
| Textfile collector for file/process monitoring | Rather than building custom exporters, uses the textfile collector pattern with external scripts (PowerShell/bash via cron). Scripts write Prometheus-format metrics to a directory that Alloy scrapes. Decouples collection logic from the agent. | 2026-03-09 |
| SNMP trap ingestion via syslog bridge | snmptrapd receives traps (UDP 162), formats to syslog, and forwards to Alloy's loki.source.syslog. This avoids custom trap processing and leverages Loki's LogQL for trap-based alerting via Grafana alerting rules. | 2026-03-09 |
| OSS audit logging via log parsing | Grafana OSS logs user actions to server logs. Alloy tails these JSON logs and forwards to Loki for Tier 1 + partial Tier 2 audit coverage. Full audit trail (change diffs, compliance) requires Grafana Enterprise. | 2026-03-09 |
| Grafana mute timings over Alertmanager silences | Grafana's mute timing API provides programmatic maintenance window management that integrates with notification policies. Alertmanager silences remain available for ad-hoc use. Both methods coexist. | 2026-03-09 |

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
| Net-SNMP (snmptrapd) | Latest | Sidecar for receiving SNMP traps and forwarding to Alloy via syslog (optional, Tier 2 gateway) |

## Phase 2 Additions

When scaling beyond Phase 1:

| Component | Purpose | Trigger |
|-----------|---------|---------|
| Grafana Mimir | Replaces Prometheus for long-term storage | Need >30 days retention or HA |
| Object Storage (S3/Azure Blob/Nutanix Objects) | Mimir backend storage | Required by Mimir |
