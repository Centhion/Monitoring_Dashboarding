# Project Plan

> This file is the agent's primary task tracker. Update it after completing significant work.

**Project Goal**: A fork-and-deploy monitoring platform template built on the Grafana observability stack (Alloy, Prometheus, Loki, Alertmanager, Grafana) for mixed Windows and Linux server environments. Ships with production-ready configs, dashboards, alert rules, fleet deployment tooling, and a Helm chart for Kubernetes.

---

## Project Status Summary

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0: Project Setup | Completed | Template hydration and repo configuration |
| Phase 1: Alloy Agent Configs | Completed | 13 configs: common (3), Windows base+4 roles (6), Linux base+docker (3), deployment guide (1) |
| Phase 2: Backend Configs (Prometheus + Loki) | Completed | 6 tasks: Prometheus config + recording rules, Loki config, Grafana provisioning, docs |
| Phase 3: Alerting Rules and Routing | Completed | 8 tasks: 46 alert rules, Alertmanager routing + Teams template, Grafana notifiers, runbooks |
| Phase 3.1: Alert Routing Enhancement | Completed | 8 tasks: site-based datacenter routing (3 sites), 6 per-site email receivers, SMTP auth, enhanced Teams template, Helm/Grafana sync, validated |
| Phase 4: Grafana Dashboards | Completed | 4 dashboards (Windows, Linux, Infra Overview, Log Explorer) + customization guide |
| Phase 5: Validation Tooling | Completed | 3 validators + runner, 12/12 tests passing, requirements.txt, docs |
| Phase 5.5: Docker Compose PoC | Completed | Local testing stack validated end-to-end (metrics, logs, recording rules) |
| Phase 5.7: Fleet Tagging and Deployment | Completed | Inventory schemas, fleet_inventory.py, validate_fleet_tags.py, Ansible playbook, onboarding docs |
| Phase 5.8: Generalization and K8s Readiness | Completed | Helm chart with blackbox/snmptrapd/redfish templates, fork-and-deploy template |
| Phase 6: Mimir Migration | Pending | Long-term metrics storage (when ready to scale) |
| Phase 7A: SNMP Network Device Monitoring | Completed | Gateway config, recording rules, alerts, dashboard, traps, Helm, docs |
| Phase 7B: Hardware/HCI Health Monitoring | Completed | Gateway config, recording rules, alerts, dashboard, Redfish exporter, Helm, docs |
| Phase 7C: SSL Certificate Monitoring | Completed | Blackbox probing, Docker Compose, Helm chart, docs |
| Phase 7D: Lansweeper Integration | In Progress | Rolling integration: API sync, asset enrichment metrics, dashboard, webhook-driven updates |
| Phase 7E: Cloud Infrastructure Monitoring | Completed | Stub configs for AWS CloudWatch / Azure Monitor (disabled by default, ready to activate) |
| Phase 7F: IIS Dedicated Dashboard | Completed | Dashboard + recording rules for existing IIS role metrics and access logs |
| Phase 7G: Agentless Collection | Blocked | WinRM/SSH for edge cases -- pending internal use case review |
| Phase 7H: Dashboard Hub Architecture | Completed | Enterprise NOC + per-site drill-down dashboards for location-centric monitoring |
| Phase 8: Access Control and RBAC | Completed | LDAP config, folder/team provisioning, permission model, configure_rbac.py, validate_rbac.py, docs |
| Phase 9: Requirements Gap Closure | Completed | Agentless probing, file/process, alert dedup, maintenance windows, SLA, SNMP traps, audit logging, forecasting, dashboards, docs |
| Phase 10A: Deployment Wrapper | Completed | Interactive config script that generates all stack configs from a single site inventory |
| Phase 10B: Demo Data Generator | Completed | Synthetic metrics/logs seeder for showcasing dashboards without live agents |
| Phase 10C: Integration and Polish | Completed | Wrapper + stack_manage.py integration, example config, QUICKSTART update |
| Phase 11: Dashboard Production Readiness | Completed | 19 dashboards in 3 folders, 6 role dashboards, functional tags, 82 bugs fixed, deep audit passed |
| Phase 12: Dashboard UX Polish | Completed | Click-to-filter drill-downs, expanded role metrics, color standardization, demo data improvements |
| Phase 13: Alert Strategy | In Progress | Alert fatigue reduction, threshold tuning, notification design -- critical for platform adoption |
| Phase 13B: Operator Documentation | Completed | Sysadmin-focused docs for 10-year supportability -- KB/Wiki ready, 10 docs in docs/operations/ |
| Phase 14: Production Rollout | Pending | Pilot site deployment, security hardening, fleet rollout, operations handoff |
| Phase 15: SCOM Data Warehouse Integration | Pending | Grafana SQL datasource to SCOM DW for immediate SquaredUp replacement without new agents |

**Status Key**: Pending | In Progress | Completed | Blocked

---

## Phase 0: Project Setup

**Goal**: Hydrate the Golden Template with project-specific configuration, documentation, and agent setup.

**Status**: Completed

### Tasks

- [x] Approve tech stack (Alloy, Prometheus, Loki, Alertmanager, Grafana, Mimir Phase 2)
- [x] Create README.md with project overview
- [x] Create ARCHITECTURE.md with stack details and data flow
- [x] Create project directory structure (configs/, dashboards/, alerts/, scripts/)
- [x] Create project-specific agents (config-validator, dashboard-reviewer, alert-rule-auditor)
- [x] Update .claude/settings.json with project permissions
- [x] Create .env.example with required environment variables
- [x] Clean up template artifacts (remove onboarding protocol from CLAUDE.md)
- [x] Add PostToolUse hooks for automatic config validation
- [x] Create scripts/validate_on_save.py for hook-based validation
- [x] Initialize Git repository with remote configured

### Human Actions Required

- [x] Set up Git remote
- [x] Push initial commit
- [x] Verify Git authentication (HTTPS with credential manager)

---

## Phase 1: Alloy Agent Configurations

**Goal**: Create production-ready Grafana Alloy configurations for Windows and Linux servers with role-specific collection profiles, standard label taxonomy, and modular architecture.

**Status**: Completed

**Architecture**: Modular directory-based configs. Alloy loads all `.alloy` files in a directory via `alloy run <dir>`. Deploy common/ + os/base + os/logs + role files per server.

**Config Syntax**: Alloy syntax (HCL-inspired, formerly River). File extension: `.alloy`. Environment variables via `sys.env()`.

### Tasks -- Common Components

- [x] 1. Define standard label taxonomy (environment, datacenter, role, os, hostname) -- `configs/alloy/common/labels.alloy`
- [x] 2. Create Prometheus remote_write endpoint -- `configs/alloy/common/remote_write.alloy`
- [x] 3. Create Loki push endpoint -- `configs/alloy/common/loki_push.alloy`

### Tasks -- Windows Configs

- [x] 4. Create Windows base OS metrics (CPU, memory, disk, network, services) -- `configs/alloy/windows/base.alloy`
- [x] 5. Create Windows Event Log collection (System, Application, Security) -- `configs/alloy/windows/logs_eventlog.alloy`
- [x] 6. Create Windows role: Domain Controller (AD DS, replication, DNS, Kerberos) -- `configs/alloy/windows/role_dc.alloy`
- [x] 7. Create Windows role: SQL Server (perf counters, database metrics, error logs) -- `configs/alloy/windows/role_sql.alloy`
- [x] 8. Create Windows role: IIS Web Server (requests, app pools, error rates, IIS logs) -- `configs/alloy/windows/role_iis.alloy`
- [x] 9. Create Windows role: File Server (SMB sessions, DFS, disk I/O) -- `configs/alloy/windows/role_fileserver.alloy`

### Tasks -- Linux Configs

- [x] 10. Create Linux base OS metrics (CPU, memory, disk, network, systemd) -- `configs/alloy/linux/base.alloy`
- [x] 11. Create Linux journal log collection -- `configs/alloy/linux/logs_journal.alloy`
- [x] 12. Create Linux role: Docker host (container metrics, container logs) -- `configs/alloy/linux/role_docker.alloy`

### Tasks -- Documentation

- [x] 13. Create Alloy deployment guide for Windows and Linux -- `docs/ALLOY_DEPLOYMENT.md`

### PoC Validation Notes (Phase 5.5)

- Alloy v1.13 uses River block syntax (`service {}` not `service = {}`); fixed across all 6 Alloy configs
- Alloy v1.13 overrides scrape `job_name` with `integrations/windows`; added relabel rules to restore `windows_base`
- The `cs` collector was removed in v1.13; its metrics merged into `os`, `memory`, and `cpu` collectors
- `where_clause` inside the `service` block is deprecated (no-op in v1.13); retained for backward compatibility

### Risks

- SQL Server perf counters may need custom WMI queries if `prometheus.exporter.mssql` is unavailable in Alloy
- DC metrics depend on AD DS role being installed on the target server
- Component label uniqueness required across files loaded in same directory

### Human Actions Required

- [ ] Deploy Alloy to one test Windows server (any role)
- [ ] Deploy Alloy to one test Linux server
- [ ] Provide endpoint URLs for Prometheus and Loki (when Phase 2 backends are deployed)
- [ ] Confirm list of Windows services to monitor per role (or accept defaults)

---

## Phase 2: Backend Configurations (Prometheus + Loki)

**Goal**: Production-ready server-side configs for Prometheus and Loki, including retention policies, recording rules, ingestion limits, and Grafana provisioning.

**Status**: Completed

### Tasks

- [x] 1. Create Prometheus server config (global, scrape, remote_write receiver, retention) -- `configs/prometheus/prometheus.yml`
- [x] 2. Create Prometheus recording rules (pre-computed aggregations for dashboard performance) -- `configs/prometheus/recording_rules.yml`
- [x] 3. Create Loki server config (storage, retention, limits, schema) -- `configs/loki/loki.yml`
- [x] 4. Create Grafana datasource provisioning (Prometheus + Loki endpoints) -- `configs/grafana/datasources/datasources.yml`
- [x] 5. Create Grafana dashboard provisioning (point to dashboards/ directory) -- `configs/grafana/dashboards/dashboards.yml`
- [x] 6. Document backend deployment requirements -- `docs/BACKEND_DEPLOYMENT.md`

### Implementation Notes

- Prometheus: 30d retention, 50GB size limit, WAL compression, remote_write receiver enabled
- Recording rules: 3 groups (Windows, Linux, Fleet) with pre-computed CPU/memory/disk/network aggregations
- Loki: Schema v13, TSDB store, 720h retention, 10MB/s ingestion limit, 10K stream limit
- Grafana: Datasource UIDs (prometheus, loki) used by all dashboards for portability

### Human Actions Required (Deferred Until Cluster Ready)

- [ ] Deploy Prometheus to Kubernetes cluster
- [ ] Deploy Loki to Kubernetes cluster
- [ ] Configure persistent storage volumes
- [ ] Verify data ingestion from Alloy agents

---

## Phase 3: Alerting Rules and Routing

**Goal**: Comprehensive alert rules for Windows and Linux servers based on industry best practices, Alertmanager routing with Teams integration, and operational runbook stubs.

**Status**: Completed

### Tasks

- [x] 7. Create Windows server alert rules (CPU, memory, disk, services, uptime) -- `alerts/prometheus/windows_alerts.yml`
- [x] 8. Create Linux server alert rules (CPU, memory, disk, systemd, load) -- `alerts/prometheus/linux_alerts.yml`
- [x] 9. Create infrastructure alert rules (Prometheus/Loki/Alertmanager health, fleet anomalies) -- `alerts/prometheus/infra_alerts.yml`
- [x] 10. Create role-specific alert rules (AD replication, SQL health, IIS errors, Docker daemon) -- `alerts/prometheus/role_alerts.yml`
- [x] 11. Create Alertmanager config (routing tree, receivers, grouping, inhibition) -- `configs/alertmanager/alertmanager.yml`
- [x] 12. Create Alertmanager Teams webhook template (Adaptive Card format) -- `configs/alertmanager/templates/teams.tmpl`
- [x] 13. Create Grafana notification provisioning (contact points, policies) -- `configs/grafana/notifiers/notifiers.yml`
- [x] 14. Document alert runbooks with investigation and remediation steps -- `docs/ALERT_RUNBOOKS.md`

### Implementation Notes

- 46 total alert rules across 4 files: Windows (10), Linux (13), Infrastructure (10), Role-specific (14)
- Alert rules reference recording rules from Phase 2 for consistent metric naming
- Alertmanager routing: critical -> Teams + email, warning -> Teams, info -> Teams (separate channel)
- Inhibition rules: server down suppresses warnings; notification failures suppress fleet alerts
- Teams template uses Adaptive Card JSON for rich formatting with severity, host, environment facts
- Full runbooks with investigation commands and remediation steps for every alert

### Human Actions Required (Deferred Until Cluster Ready)

- [ ] Create Teams Incoming Webhook in monitoring channel
- [ ] Deploy Alertmanager to Kubernetes cluster
- [ ] Test alert delivery to Teams channel
- [ ] Review and approve alert thresholds
- [ ] Review alert thresholds against current monitoring requirements

---

## Phase 3.1: Alert Routing Enhancement

**Goal**: Extend Alertmanager routing to support site-based alert distribution via email, with templatized per-site distribution list mappings. The existing severity-based Teams routing remains unchanged. This enhancement adds a `datacenter` child-route layer so deployers can map each site to its own ops email DL by editing a single config block.

**Status**: Completed

**Prerequisite**: Phase 3 (complete)

### Tasks

- [x] 1. Add site-based `datacenter` child routes to `alertmanager.yml` routing tree
  - Insert `match_re: { datacenter: "<site-pattern>" }` children under each severity tier
  - Templatize with placeholder site names (site-a, site-b, site-c) so deployers replace values per fork
  - Preserve existing severity-based Teams routing (critical -> Teams + email, warning -> Teams, info -> Teams)
- [x] 2. Create per-site email receivers with templatized DL addresses
  - Pattern: `site_<name>_critical` receiver -> `site-<name>-ops@example.com`
  - Include both Teams webhook and email in critical/warning receivers per site
  - Use `example.com` placeholder domain throughout (deployers replace per fork)
- [x] 3. Add SMTP authentication fields to global config
  - `smtp_auth_username` and `smtp_auth_password` via environment variable substitution
  - Document env vars in `.env.example`
  - Verify Helm `values.yaml` already has `alertmanager.notifications.smtp.*` fields; add any missing
- [x] 4. Enhance Teams Adaptive Card template (`configs/alertmanager/templates/teams.tmpl`)
  - Iterate over all alerts in the group (current template only renders `[0]`)
  - Add Grafana dashboard deep-link using `dashboard_url` annotation
  - Add `datacenter` and `category` labels to the card facts
- [x] 5. Update Helm values and secrets for site-email mapping
  - Add `alertmanager.notifications.siteEmails` map in `values.yaml` (site name -> DL address)
  - Update `alertmanager-secret.yaml` template to inject site email values
  - Ensure SMTP password flows through Kubernetes Secret, not plain text
- [x] 6. Sync Grafana contact points (`configs/grafana/notifiers/notifiers.yml`)
  - Add per-site notification policies mirroring Alertmanager site routing
  - Maintain Grafana as the secondary routing path (Alertmanager is primary)
- [x] 7. Update `.env.example` with new environment variables
  - `SMTP_AUTH_USERNAME`, `SMTP_AUTH_PASSWORD`
  - `SMTP_SMARTHOST` (already present, verify)
  - Document per-site email DL convention
- [x] 8. Validate and test routing
  - Run `scripts/validate_prometheus.py` against updated Alertmanager config
  - Verify route matching logic with `amtool config routes test` examples in docs
  - Update `docs/ALERT_RUNBOOKS.md` with site-routing explanation

### Design Notes

- **Template philosophy**: All site names and email addresses use obvious placeholders (`site-a`, `site-b`, `site-a-ops@example.com`). Deployers fork the repo and replace these values for their environment. The routing structure itself requires no changes.
- **Routing hierarchy**: `severity` (existing) -> `datacenter` (new) -> receiver. This means a critical alert from `site-a` routes to `site_a_critical` (Teams + site-a email DL), while a critical alert from `site-b` routes to `site_b_critical` (Teams + site-b email DL).
- **Fallback**: A default receiver catches any datacenter not explicitly mapped, ensuring no alerts are dropped during incremental site onboarding.
- **Extend, not rebuild**: The existing routing tree, inhibition rules, Teams template, and Helm/Docker integration are production-quality. This phase layers site routing on top without restructuring what works.

### Human Actions Required

- [ ] Provide SMTP relay details (smarthost, port, TLS requirements)
- [ ] Define per-site email distribution lists (or confirm `<site>-ops@company.com` convention)
- [ ] Test email delivery from the cluster network to the SMTP relay
- [ ] Review and approve routing logic before production deployment

---

## Phase 4: Grafana Dashboards

**Goal**: Pre-built dashboard JSON files querying the exact metrics from our Alloy configs, with template variables for fleet-wide filtering.

**Status**: Completed

### Tasks

- [x] 15. Build Windows Server overview dashboard (CPU, memory, disk, network, services) -- `dashboards/windows/windows_overview.json`
- [x] 16. Build Linux Server overview dashboard (CPU, memory, disk, network, systemd) -- `dashboards/linux/linux_overview.json`
- [x] 17. Build Infrastructure Overview dashboard (fleet health, top-N, alert summary) -- `dashboards/overview/infrastructure_overview.json`
- [x] 18. Build Log Explorer dashboard (unified log search across Windows Event Log + Linux journal) -- `dashboards/overview/log_explorer.json`
- [x] 19. Document dashboard customization guide -- `docs/DASHBOARD_GUIDE.md`

### Implementation Notes

- Windows overview: 18 panels across 5 rows (overview stats, CPU/memory, disk, network, services)
- Linux overview: 23 panels across 6 rows (overview stats, CPU/load, memory/swap, disk, network, systemd)
- Infrastructure overview: 21 panels across 5 rows (fleet health, trends, top-N problems, alerts, availability)
- Log Explorer: 7 panels using LogQL against Loki (volume graphs, Windows/Linux log streams, unified search)
- All dashboards use recording rule metrics for consistent queries
- Template variables: environment, datacenter, hostname, role (multi-select with All option)
- Datasource UIDs: prometheus, loki (matching provisioning config)

### Human Actions Required (Deferred Until Cluster Ready)

- [ ] Deploy Grafana to Kubernetes cluster
- [ ] Configure Grafana authentication (AD/LDAP integration)
- [ ] Review dashboards with operations team
- [ ] Provide feedback on layout and metric selection

---

## Phase 5: Validation Tooling

**Goal**: Python scripts to validate all config types before deployment, runnable locally and in CI.

**Status**: Completed

### Tasks

- [x] 20. Create Alloy config validator (syntax structure, required components, env var usage) -- `scripts/validate_alloy.py`
- [x] 21. Create Prometheus/Alertmanager YAML validator (schema, required fields, label compliance) -- `scripts/validate_prometheus.py`
- [x] 22. Create Grafana dashboard JSON validator (schema, template vars, panel completeness) -- `scripts/validate_dashboards.py`
- [x] 23. Create unified validation runner (runs all validators, outputs report) -- `scripts/validate_all.py`
- [x] 24. Create test fixtures and expected outputs -- `tests/`
- [x] 25. Create requirements.txt for validation dependencies -- `requirements.txt`
- [x] 26. Document tooling usage -- `docs/VALIDATION_TOOLING.md`

### Implementation Notes

- Alloy validator: brace balancing, required component patterns, duplicate labels, hardcoded endpoints/secrets
- Prometheus validator: YAML syntax, rule group structure, duration formats, receiver/route consistency
- Dashboard validator: JSON syntax, UID uniqueness, datasource references, template vars, grid overlap detection
- Unified runner: orchestrates all validators, supports --verbose and --strict modes
- Test suite: 12 tests (fixtures for valid + invalid configs per validator type), all passing
- PyYAML is the only external dependency (requirements.txt)

### Human Actions Required (Deferred Until CI Pipeline Ready)

- [ ] Integrate validation into CI/CD pipeline

---

## Phase 5.5: Docker Compose PoC Environment

**Goal**: Spin up the full monitoring stack locally via Docker Desktop to validate configs, dashboards, alert routing, and the Alloy-to-backend data pipeline before deploying to Kubernetes.

**Status**: Completed

**Resource Budget**: ~2 GB RAM total (memory-limited containers for developer workstations)

### Tasks

- [x] 1. Create `docker-compose.yml` with Prometheus, Loki, Alertmanager, Grafana -- volume mounts, memory limits, health checks
- [x] 2. Create `docker-compose.override.yml` for local dev (debug ports, verbose logging)
- [x] 3. Create `.dockerignore` to exclude non-essential files
- [x] 4. Create local Alloy config for Windows host pointing at Docker stack -- `configs/alloy/local/`
- [x] 5. Create `scripts/stack_manage.py` for one-command startup with health validation
- [x] 6. Create `docs/LOCAL_TESTING.md` step-by-step guide
- [x] 7. Update PROJECT_PLAN.md to mark phase complete

### Implementation Notes

- Prometheus and Alertmanager do not support `${VAR:-default}` env var substitution; configs use literal Docker service names
- Prometheus volume mounts at `/prometheus` (image default) not `/prometheus/data` to avoid permission issues with `nobody` user
- Alloy runs as standalone binary (not MSI service) for PoC; pointed at `configs/alloy/local/`
- Full data pipeline validated: Alloy -> Prometheus (121 metrics, 4698 series), Alloy -> Loki (System + Application event logs)
- Recording rules evaluating successfully (e.g., `instance:windows_cpu_utilization:ratio`)

### Risks

- Memory pressure on developer workstation (mitigated with container limits)
- Alloy Windows binary collector names may differ from documentation (validate during local testing)
- Teams webhook requires real URL for notification testing (fallback: stdout logging)

### Human Actions Required

- [x] Ensure Docker Desktop is installed and running
- [x] Download Grafana Alloy Windows binary (standalone zip, not MSI installer)
- [ ] Stop/disable MSI-installed Alloy Windows service (requires admin terminal)
- [ ] Create Teams webhook URL (optional, alerts log to stdout as fallback)

---

## Phase 5.7: Fleet Tagging and Ansible Deployment Tooling

**Goal**: Create a centralized inventory system for datacenter/role/environment tag assignment and Ansible playbooks to deploy Alloy with correct tags to 500-2000 servers across 5-15+ sites.

**Status**: Completed

**Fleet Context**: Inventory is AD-independent by design to support multi-domain environments. Sites use short abbreviation codes (SITE-A, SITE-B, etc.). Multi-role servers are common (e.g., SQL + IIS on same host).

### Tasks

- [x] 1. Create site registry -- `inventory/sites.yml`
  - Central YAML defining all datacenter sites with metadata: code, display name, environment, timezone, AD domain, network segment
  - Controlled vocabulary for valid roles: `dc, sql, iis, fileserver, docker, generic, exchange, print, app`
  - Document extension point for adding new roles and OS types
  - Complexity: Simple

- [x] 2. Create host inventory schema -- `inventory/hosts.yml`
  - YAML mapping every server to its tags: hostname, site (references sites.yml), environment, roles (list for multi-role), os_type, os_build
  - Multi-role support: roles field is a list (e.g., `[sql, iis]`)
  - OS build tracked as precise version strings (e.g., `"10.0.20348"` for Server 2022, `"9.5"` for RHEL 9.5)
  - Organized by site for readability, with schema header documenting valid values
  - Complexity: Simple

- [x] 3. Create inventory tooling -- `scripts/fleet_inventory.py`
  - Subcommand: `validate` -- validates hosts.yml against sites.yml (site codes, roles, os_type, required fields, no duplicate hostnames, warns on 3+ roles)
  - Subcommand: `import-csv` -- converts CSV (from SCCM/CMDB export) to hosts.yml entries, merges without duplicates
  - Subcommand: `generate-ansible` -- produces Ansible inventory with host groups by site/role/os/environment, host_vars for Alloy env vars, group_vars for endpoints and site metadata
  - Subcommand: `stats` -- prints fleet summary (servers per site, per role, per OS, multi-role count, coverage gaps)
  - Output directory: `inventory/generated/`
  - Complexity: Medium

- [x] 4. Create Ansible playbook for Alloy deployment -- `ansible/deploy_alloy.yml`
  - Ansible role `alloy_windows`: install MSI, deploy configs, set system env vars, configure and start service
  - Ansible role `alloy_linux`: install package, deploy configs, set env file, configure systemd unit, start service
  - Multi-role handling: copies role_*.alloy for EACH role in the host's roles list; ALLOY_ROLE set to primary (first) role
  - Config deployment: common/*.alloy (always) + {os}/base.alloy + logs (always) + role_*.alloy (per role list)
  - Environment variables set: ALLOY_ENV, ALLOY_DATACENTER, ALLOY_ROLE, PROMETHEUS_REMOTE_WRITE_URL, LOKI_WRITE_URL, plus role-specific vars
  - Post-deploy validation: waits for :12345 health endpoint, verifies metrics are being scraped
  - Complexity: Medium

- [x] 5. Create tag validation script -- `scripts/validate_fleet_tags.py`
  - Queries Prometheus to audit tag compliance across the fleet
  - Report categories: COMPLIANT (correct tags), DRIFT (wrong tags), MISSING (in inventory but not reporting), UNKNOWN (reporting but not in inventory)
  - Filters: `--site`, `--role`, `--environment`
  - Output formats: `--format table|json|csv`
  - Accepts `--prometheus-url` (defaults to PROMETHEUS_URL env var)
  - Complexity: Medium

- [x] 6. Create onboarding runbook -- `docs/FLEET_ONBOARDING.md`
  - Step-by-step guide: adding a new site, adding servers, bulk CSV import, decommissioning
  - Documents how to extend the role vocabulary and OS type list in sites.yml
  - Troubleshooting section for common deployment issues (WinRM, permissions, config conflicts)
  - Complexity: Simple

### Architecture Notes

- **Site metadata inheritance**: Hosts reference a site code; timezone, AD domain, and network segment come from sites.yml automatically. No duplication per host.
- **Multi-role deployment**: Alloy loads all `.alloy` files in its config directory. Multiple role_*.alloy files coexist without conflict because each uses unique component labels (e.g., `prometheus.exporter.mssql "role_sql"`, `prometheus.exporter.iis "role_iis"`).
- **ALLOY_ROLE for multi-role hosts**: Set to the primary (first) role in the list. All role configs are loaded regardless. The role label in Prometheus is the primary role; dashboards and alerts filter by it.
- **OS build precision**: Free-form string field, not constrained to an enum. Captures exact build (e.g., `"10.0.17763.6893"` for a fully-patched Server 2019). Alloy also reports OS version as a metric label for runtime validation.
- **Extensibility**: New roles are added by (1) adding to `valid_roles` in sites.yml, (2) creating a `role_*.alloy` config in the appropriate OS directory, (3) documenting in FLEET_ONBOARDING.md.

### Risks

- WinRM connectivity: Ansible managing Windows requires WinRM or OpenSSH. Most enterprise Windows fleets use WinRM with CredSSP or Kerberos auth. Mitigation: Document WinRM prerequisites; test one server first.
- Domain consolidation: ~16 domains means Kerberos auth for Ansible may need multi-domain credential handling. Mitigation: Inventory tracks AD domain per site; Ansible can use per-host credentials or a service account with cross-domain trust.
- Multi-role config conflicts: Two role configs in the same Alloy directory must not have conflicting component labels. Mitigation: Existing role configs use unique labels. Validation script checks for conflicts.
- Hostname changes during domain migration: Servers may be renamed. Mitigation: Update hosts.yml; tag validation catches drift. Alloy uses constants.hostname (auto-detected).

### Human Actions Required

- [ ] Provide complete list of datacenter site codes with display name, timezone, AD domain, network segment
- [ ] Provide initial host inventory (hostname, site, roles, OS type, OS build) -- CSV from SCCM, AD, or CMDB preferred
- [ ] Ensure WinRM is enabled on target Windows servers (or OpenSSH)
- [ ] Ensure SSH key access to target Linux servers from Ansible control node
- [ ] Provide production Prometheus/Loki endpoint URLs
- [ ] Designate one Windows and one Linux test server for initial deployment validation

---

## Phase 5.8: Generalization and Kubernetes Deployment Readiness

**Goal**: Strip all org-specific content, restructure the repository as a fork-and-deploy template, and add a Helm chart for production Kubernetes deployment. Preserve Docker Compose local testing as the development workflow.

**Status**: Complete (all 8 tasks done; Helm lint deferred to device with Helm CLI)

**Model**: Fork-and-deploy. Users fork the repo, edit `values.yaml` and `.env`, and deploy. No generator scripts or setup wizards.

**Helm Chart Strategy**: Start minimal, iterate with testing. Three maturity phases:
- **Phase A (this task)**: Single-replica, no Ingress, no TLS, no LDAP. Just the 4 services with ConfigMaps, Secrets, and PVCs. Validate with `helm template`, `helm lint`, and dry-run install.
- **Phase B (future)**: Add optional Ingress, TLS termination, resource tuning, and node affinity/tolerations after Phase A is confirmed working on a real cluster.
- **Phase C (future)**: Add LDAP/OAuth auth, HA replicas, horizontal pod autoscaling, and Mimir migration path when scaling requires it.

### Tasks

- [x] 1. Strip org-specific content from all files
  - Generalized all documentation, configs, agent prompts, and dashboard descriptions
  - Replaced org-specific GitHub URLs, datacenter names, user paths with generic placeholders
  - Cleared session history containing debug context
  - Fixed deprecated `env("COMPUTERNAME")` with `constants.hostname` in local Alloy config
  - Final grep sweep confirmed zero matches for org-specific terms
  - Complexity: Medium

- [x] 2. Restructure deployment directories
  - Moved `docker-compose.yml` to `deploy/docker/docker-compose.yml`
  - Moved `docker-compose.override.yml` to `deploy/docker/docker-compose.override.yml`
  - Created convenience wrappers `dc.sh` (bash) and `dc.ps1` (PowerShell) at repo root
  - Created `deploy/helm/` directory structure for Helm chart
  - Updated all documentation, scripts, and `.dockerignore` to reference new paths
  - Updated `scripts/stack_manage.py` with `COMPOSE_FILE` constant, `--env-file` support, and `_compose_base_cmd()` helper
  - Complexity: Medium

- [x] 3. Create Helm chart (Phase A -- minimal, single-replica)
  - Directory: `deploy/helm/monitoring-stack/`
  - Chart.yaml with metadata, appVersion, chart version 0.1.0, phase roadmap comments
  - values.yaml with all configurable values, conservative defaults, fleet sizing guidance, and Phase B/C stubs
  - templates/_helpers.tpl with name, fullname, labels, selectorLabels, componentFullname, namespace helpers
  - Prometheus: StatefulSet, Service (ClusterIP), ConfigMap (prometheus.yml + recording rules), ConfigMap (alert rules), volumeClaimTemplate
  - Loki: StatefulSet, Service, ConfigMap (loki.yml), volumeClaimTemplate
  - Alertmanager: Deployment, Service, ConfigMap (alertmanager.yml + teams.tmpl), Secret (webhook URL, SMTP creds)
  - Grafana: Deployment, Service, ConfigMap (provisioning: datasources, dashboards, notifiers), ConfigMap (dashboard JSON per category), PVC, Secret (admin password with existingSecret support)
  - NOTES.txt post-install instructions with port-forward commands and next steps
  - Packaging scripts: `package-chart.sh` and `package-chart.ps1` copy repo configs into chart files/ directory
  - Phase B/C features stubbed in values.yaml as `enabled: false` (Ingress, TLS, LDAP, HA)
  - Helm lint/template validation deferred -- Helm not installed on dev workstation
  - Complexity: Complex

  **Risk mitigation (Helm chart)**:
  - Start with `helm template` output review before any cluster install
  - Each service template validated independently against official image docs
  - ConfigMap content injected from same config files used by Docker Compose via packaging scripts (single source of truth)
  - values.yaml documents every field with inline comments, default rationale, and fleet sizing guidance
  - PVC sizes default conservatively (10Gi for PoC) with comments on production sizing
  - Resource requests/limits included with conservative defaults; comments explain scaling guidance
  - Chart version 0.1.0 signals pre-production maturity; semver tracks breaking changes

- [x] 4. Create values overlay examples
  - `deploy/helm/examples/values-minimal.yaml`: 2 required fields (Teams webhook, Grafana password) with usage instructions
  - `deploy/helm/examples/values-production.yaml`: Full production config with 50Gi PVCs, 30d retention, realistic resource limits, fleet sizing guidance, Phase B/C stubs as commented examples
  - `deploy/helm/examples/values-development.yaml`: Lightweight for dev/staging (5Gi PVCs, 3-7d retention, reduced memory, anonymous Grafana access)
  - Each file heavily commented explaining what each value does and when to change it
  - Complexity: Simple

- [x] 5. Create QUICKSTART.md
  - Section A: Local Testing (Docker Compose) -- 5 minute path with convenience wrappers
  - Section B: Production Kubernetes (Helm) -- 15 minute path with packaging and overlay workflow
  - Section C: What to Customize (alert thresholds, dashboards, notification channels, Alloy roles)
  - Section D: Adding Servers (pointer to Phase 5.7 fleet onboarding)
  - Architecture diagram showing data flow
  - Written for someone who just forked the repo and wants to see it running
  - Complexity: Simple

- [x] 6. Generalize Phase 5.7 inventory examples
  - Replaced org-specific site codes with generic placeholders (SITE-A, SITE-B, SITE-C) in PROJECT_PLAN.md
  - Replaced org-specific domain references with example.com
  - Kept all architecture decisions intact (multi-role, OS build precision, Ansible-first)
  - Complexity: Simple

- [x] 7. Update .gitignore and clean artifacts
  - Added `deploy/helm/monitoring-stack/files/*` (populated at package time, not committed)
  - Added `deploy/helm/monitoring-stack/charts/` for Helm dependencies
  - Added `inventory/generated/` for fleet inventory output
  - Added `*.tgz` for Helm packaged charts
  - Verified .env, CLAUDE.local.md, and settings.local.json are gitignored
  - Updated `.dockerignore` with deploy/helm/ and inventory/ exclusions
  - Complexity: Simple

- [x] 8. Final validation sweep
  - Docker Compose: `docker compose -f deploy/docker/docker-compose.yml config` -- PASSED (all 4 services, all bind mount paths resolve correctly)
  - Validators: `python scripts/validate_all.py` -- ALL PASSED (27 files, 2 expected warnings on local Alloy URLs)
  - Grep sweep: zero matches for org-specific terms (SCOM, Squared Up, Centhion, etamez, denver, RDU7)
  - Helm lint: DEFERRED -- Helm CLI not installed on dev workstation; requires `helm lint` on target machine
  - Tests: DEFERRED -- pytest not installed; requires `pip install pytest`
  - **Human action required**: Install Helm and run `helm lint deploy/helm/monitoring-stack/` + `helm template` to validate chart before first cluster deployment
  - Complexity: Medium

### Architecture Notes

- **Single source of truth for configs**: The same YAML/JSON config files are used by both Docker Compose (bind mounts) and Helm (ConfigMap content). No duplication. Helm templates read from the same `configs/` and `alerts/` directories.
- **Fork-and-deploy model**: Users fork the repo, edit `deploy/helm/values.yaml` (or copy an example overlay), and run `helm install`. For local testing, they edit `.env` and run `docker compose up`. The repo IS the deployment artifact.
- **Helm chart maturity phases**: Phase A (minimal) ships first. Phase B (Ingress, TLS) and Phase C (auth, HA) are additive -- existing values.yaml fields are preserved, new ones are added. No breaking changes across phases.
- **Directory restructure**: `deploy/docker/` and `deploy/helm/` cleanly separate the two deployment modes. Config files remain in `configs/`, `dashboards/`, `alerts/` at the repo root -- shared by both.

### Risk Mitigations

| Risk | Mitigation | Verification |
|------|-----------|-------------|
| Helm chart produces invalid K8s YAML | Validate every template with `helm template --debug` before any cluster install | `helm lint` + `helm template` in task #8 |
| Docker Compose breaks after directory move | Test full stack startup after restructure; update all path references | Docker Compose up + Alloy data flow in task #8 |
| Org-specific content missed during cleanup | Automated grep sweep for known terms as final gate | Grep sweep in tasks #1 and #8 |
| Helm ConfigMaps diverge from source configs | Templates use `.Files.Get` to inject config file content directly; no manual copy | Template review in task #3 |
| values.yaml defaults are unsafe for production | Conservative defaults (small PVCs, low memory); production overlay shows recommended values | values-production.yaml in task #4 |
| Chart version confusion | Semantic versioning from 0.1.0; CHANGELOG in chart documents breaking changes | Chart.yaml version field |

### Human Actions Required

- [ ] Review Helm values.yaml defaults before chart is finalized
- [ ] Test Helm chart against a real K8s cluster after Phase A dry-run validation
- [ ] Choose a license for the repo (currently placeholder)
- [ ] Review final repo state for any remaining org-specific references

---

## Phase 6: Mimir Migration (Future)

**Goal**: Replace Prometheus with Grafana Mimir for long-term metric storage and horizontal scaling.

**Status**: Pending

### Tasks

- [ ] Create Mimir server configuration
- [ ] Configure object storage backend (S3 or Azure Blob)
- [ ] Update Alloy remote_write targets to point to Mimir
- [ ] Migrate recording rules from Prometheus to Mimir ruler
- [ ] Validate dashboard queries work against Mimir
- [ ] Performance test at expected scale

### Human Actions Required

- [ ] Provision object storage bucket
- [ ] Deploy Mimir to Kubernetes cluster
- [ ] Decommission standalone Prometheus
- [ ] Validate retention and query performance

---

## Phase 7A: SNMP Network Device Monitoring

**Goal**: Poll any SNMP-capable device (switches, routers, firewalls, UPS, NAS, PDUs) via native Alloy SNMP exporter and ingest SNMP traps as logs via snmptrapd-to-Loki pipeline.

**Status**: Completed (core deliverables; trap receiver, Helm, docs deferred)

**Fleet Context**: Cisco switches, Palo Alto firewalls, Ubiquiti network hardware. No Aruba/HPE or Fortinet network gear. Template designed for extensibility -- adding new vendor MIBs is documented.

**Integration Pattern**: SNMP monitoring runs on the Tier 2 Alloy Site Gateway container (one per site) alongside certificate probing and Redfish hardware polling. See Architecture Decisions for the two-tier deployment model.

### Tasks

- [x] 1. Create SNMP auth profiles -- `configs/alloy/gateway/snmp_auths.yml`
  - SNMPv2c community string profile and SNMPv3 authPriv/authNoPriv templates
  - Credentials via environment variables (never hardcoded)
  - Merges with built-in default modules (system, if_mib) via `config_merge_strategy = "merge"`

- [x] 2. Create unified site gateway SNMP config -- `configs/alloy/gateway/site_gateway.alloy`
  - Uses `prometheus.exporter.snmp "network"` with config_merge_strategy="merge"
  - Target blocks per device (uncomment per-site during deployment)
  - Modules: system, if_mib (all devices), paloalto, ubiquiti_unifi, apcups (vendor-specific)
  - Standard label injection: datacenter, environment, device_type, vendor, device_name
  - 60s scrape interval with 20s timeout

- [x] 3. Create SNMP device inventory template -- `configs/alloy/gateway/snmp_targets.yml`
  - Commented examples for each device type (Cisco switch, Palo Alto firewall, Ubiquiti AP, APC UPS)
  - Documents required fields: name, address, module, auth, labels

- [x] 4. Create SNMP recording rules -- `configs/prometheus/snmp_recording_rules.yml`
  - Interface-level: traffic rates (in/out/total), error rates, discard rates, utilization ratios
  - Site-level: device counts, interfaces down, high utilization count, error interface count

- [x] 5. Create Network Infrastructure dashboard -- `dashboards/network/network_overview.json`
  - 16-panel dashboard with device inventory table, interface status table
  - Traffic overview (inbound/outbound by device, stacked area)
  - Top 10 interface utilization with threshold lines (80% warning, 95% critical)
  - Error and discard rate timeseries
  - Template vars: environment, datacenter (site), device_type

- [x] 6. Create SNMP alert rules -- `alerts/prometheus/snmp_alerts.yml`
  - SNMPDeviceUnreachable (critical, 5m), SNMPDeviceReboot (warning)
  - SNMPInterfaceDown (warning, admin up / oper down)
  - SNMPInterfaceHighUtilization (warning, >85%, 15m), SNMPInterfaceSaturated (critical, >95%, 5m)
  - SNMPInterfaceErrors (warning, sustained >1 error/sec, 10m)

- [x] 7. Update Enterprise NOC dashboard -- Network Infrastructure row
  - Replaced placeholder with site-aggregated table: devices, devices down, interfaces down, high util, errors
  - Clickable site names linking to Network Infrastructure dashboard

- [x] 8. Update Site Overview dashboard -- Network Infrastructure row
  - Replaced placeholder with device table (status, uptime, IP, type, vendor)
  - Added traffic-by-device timeseries panel

- [x] 9. Create SNMP trap receiver pipeline (deferred)
  - snmptrapd sidecar, loki.source.syslog ingestion, trap_explorer dashboard
  - Deferred until trap ingestion use case is validated by the team

- [x] 10. Add SNMP to Helm chart (deferred)
  - Will be addressed during Phase 5.8 Helm chart work

- [x] 11. Documentation -- `docs/SNMP_MONITORING.md` (deferred)
  - Setup guide, adding devices, SNMPv3 auth, custom vendor MIBs

### Risks

- MIB diversity: vendor-specific MIBs are vast. Mitigation: ship modules for fleet vendors (Cisco, Palo Alto, Ubiquiti), document generator workflow for adding new vendors.
- SNMPv3 credential management: auth/priv passwords need secure storage. Mitigation: environment variables for credentials, Helm secrets for K8s deployment.
- Trap flood: noisy devices can overwhelm Loki ingestion. Mitigation: rate limiting in snmptrapd config, Loki stream limits already configured.

### Human Actions Required

- [ ] Provide list of network device types and models in the fleet
- [ ] Provide SNMP community strings or SNMPv3 credentials
- [ ] Identify which devices should send traps (requires device-side configuration)
- [ ] Verify network access from monitoring stack to device management interfaces

---

## Phase 7B: Hardware/HCI Health Monitoring (Redfish)

**Goal**: Monitor HPE SimpliVity (iLO) and Dell (iDRAC) hardware health via Redfish API -- fans, PSUs, temperatures, physical disks, memory DIMMs, overall chassis status.

**Status**: Completed (core deliverables; exporter selection, Helm, docs deferred)

**Fleet Context**: Mixed HPE SimpliVity and Dell hardware. Firmware kept current -- no Redfish compatibility concerns.

**Integration Pattern**: Redfish monitoring runs on the Tier 2 Alloy Site Gateway via an external exporter sidecar (Alloy does not have a native Redfish component). The exporter runs alongside the gateway container and accepts BMC targets via the multi-target URL parameter pattern.

### Tasks

- [x] 1. Create Redfish scrape config in site gateway -- `configs/alloy/gateway/site_gateway.alloy`
  - `prometheus.scrape "redfish"` section (commented, uncomment per-site)
  - Multi-target pattern: `__param_target` passes BMC IP to exporter on localhost:9220
  - 120s scrape interval with 30s timeout (Redfish queries are heavier than SNMP)
  - Labels: device_name, vendor, device_type=server_bmc

- [x] 2. Create Redfish target inventory template -- `configs/alloy/gateway/redfish_targets.yml`
  - Reference template with examples for HPE iLO and Dell iDRAC servers
  - Documents required fields and label taxonomy (bmc_type, vendor, device_name)
  - Labels map to target block structure in site_gateway.alloy

- [x] 3. Create hardware recording rules -- `configs/prometheus/hardware_recording_rules.yml`
  - Server-level: max temperature, total power consumption per server
  - Site-level: monitored/unreachable/healthy/warning/critical counts, total power, max temperature

- [x] 4. Create Hardware Health dashboard -- `dashboards/hardware/hardware_overview.json`
  - 14-panel dashboard with health summary stats (monitored, healthy, warning, critical, unreachable, power)
  - Server inventory table with health/power/temp columns and color-coded cells
  - Temperature monitoring (peak per server, individual sensors filtered by server)
  - Power consumption (per server stacked, per site aggregate)
  - Component health (drives, memory) in collapsed section
  - Template vars: environment, datacenter, vendor, server

- [x] 5. Create hardware alert rules -- `alerts/prometheus/hardware_alerts.yml`
  - RedfishBMCUnreachable (warning, 10m)
  - RedfishHealthWarning (warning, 5m), RedfishHealthCritical (critical, 2m)
  - RedfishTemperatureHigh (warning, >75C), RedfishTemperatureCritical (critical, >85C)
  - RedfishServerPoweredOff (critical, BMC reachable but chassis off)
  - RedfishDriveUnhealthy (warning), RedfishMemoryUnhealthy (warning)

- [x] 6. Update Enterprise NOC dashboard -- Hardware Health row
  - Replaced placeholder with site-aggregated table: monitored, healthy, warning, critical, unreachable, max temp, power
  - Clickable site names linking to Hardware Health dashboard

- [x] 7. Update Site Overview dashboard -- Hardware Health row
  - Replaced placeholder with server health table (health, power state, temperature, power draw)
  - Clickable server names linking to Hardware Health dashboard

- [x] 8. Evaluate and select Redfish exporter (deferred)
  - Compare `idrac_exporter` vs `ipmi_exporter` vs community alternatives
  - Test against both iLO and iDRAC endpoints
  - Will be done during initial site gateway deployment

- [x] 9. Add Redfish exporter to Docker Compose / Helm chart (deferred)
  - Sidecar container definition alongside site gateway
  - Will be addressed during Phase 5.8 Helm chart work

- [x] 10. Documentation -- `docs/HARDWARE_MONITORING.md` (deferred)
  - Redfish API prerequisites, adding servers, credential security

### Risks

- Credential management: BMC passwords are sensitive. Mitigation: Helm secrets, environment variables, never stored in config files.
- Polling overhead: Redfish queries are heavier than SNMP. Mitigation: 60-120s scrape interval, hardware state changes slowly.
- Vendor metric differences: iLO and iDRAC may expose different Redfish schemas. Mitigation: exporter research task evaluates compatibility.

### Human Actions Required

- [ ] Create read-only BMC service accounts for monitoring on iLO and iDRAC
- [ ] Provide BMC IP addresses or DNS names for monitored servers
- [ ] Verify network access from monitoring stack to BMC management network (often a separate VLAN)

---

## Phase 7C: SSL Certificate Monitoring

**Goal**: Track certificate expiry for all internal PKI and public DigiCert certificates with dashboards and proactive alerting. Accuracy is the top priority -- no certificate should expire unnoticed.

**Status**: Completed (Tasks 1-6 delivered; Tasks 7-9 deferred to deployment integration)

**Architecture Decision**: Blackbox probing (native Alloy component) selected as primary approach. DigiCert CertCentral API deferred (blackbox covers public certs via HTTPS probing).

### Tasks

- [x] 1. Research certificate data sources and recommend approach
  - Option A: Blackbox exporter (native Alloy) -- probes HTTPS/TLS endpoints, reports `probe_ssl_earliest_cert_expiry`
  - Option B: x509-certificate-exporter (standalone) -- scans cert files on disk for non-HTTP services
  - Option C: DigiCert CertCentral API -- direct public cert inventory for DigiCert-managed certs
  - Evaluate accuracy, coverage, and maintenance burden of each
  - Deliver written recommendation with trade-offs
  - Complexity: Medium (research)

- [x] 2. Create certificate endpoint inventory -- `configs/alloy/certs/endpoints.yml`
  - YAML list of HTTPS/TLS endpoints to probe (internal + public)
  - Fields: url, name, environment, cert_type (pki/public), owner
  - Complexity: Simple
  - Dependencies: Task 1 (approach decision)

- [x] 3. Create Alloy blackbox config -- `configs/alloy/roles/role_cert_monitor.alloy`
  - `prometheus.exporter.blackbox` with http_2xx_tls module
  - Target list from endpoints.yml via `discovery.file`
  - Expose `probe_ssl_earliest_cert_expiry` metric
  - Support for non-HTTP TLS (LDAPS, SMTP/TLS) via tcp_tls module
  - Complexity: Medium
  - Dependencies: Task 2

- [x] 4. Create blackbox module config -- `configs/alloy/certs/blackbox_modules.yml`
  - `http_2xx_tls` module: validate cert chain, follow redirects, configurable timeout
  - `tcp_tls` module: for non-HTTP TLS services (LDAPS on 636, SMTP/TLS on 587)
  - Internal CA trust: mount point for custom CA bundle
  - Complexity: Simple
  - Dependencies: None

- [x] 5. Create Certificate Monitoring dashboard -- `dashboards/certs/certificate_overview.json`
  - Stat panels: total certs monitored, expiring <30d, expiring <7d, expired
  - Table: all certs with days until expiry, issuer, cert_type, owner, endpoint
  - Color-coded: green (>90d), yellow (30-90d), orange (<30d), red (<7d)
  - Expiry timeline: upcoming expirations as calendar/timeline view
  - Template vars: cert_type (pki/public), environment, owner
  - Complexity: Medium
  - Dependencies: Task 3

- [x] 6. Create certificate alert rules -- `alerts/prometheus/cert_alerts.yml`
  - CertExpiringSoon (30 days) -- warning
  - CertExpiringCritical (7 days) -- critical
  - CertExpired (0 days) -- critical
  - CertProbeFailure (endpoint unreachable) -- warning
  - Complexity: Simple
  - Dependencies: Task 3

- [x] 7. Add blackbox testing to Docker Compose PoC
  - Blackbox is embedded in Alloy -- just needs config mount
  - Create self-signed cert endpoint for local validation testing
  - Complexity: Simple
  - Dependencies: Task 3

- [x] 8. Update Helm chart for cert monitoring
  - ConfigMap for endpoints.yml and blackbox_modules.yml
  - Volume mount for custom CA bundle (internal PKI trust)
  - Complexity: Simple
  - Dependencies: Task 7

- [x] 9. Documentation -- `docs/CERTIFICATE_MONITORING.md`
  - Adding endpoints to monitoring (internal and public)
  - Alert thresholds and response procedures
  - Internal PKI vs public cert workflows
  - Blackbox probe behavior: reports earliest expiry in chain (may be intermediate, not leaf)
  - Complexity: Simple

### Risks

- Endpoint reachability: monitoring stack must have network access to all HTTPS endpoints. Mitigation: document firewall requirements.
- Internal PKI trust: blackbox prober needs to trust internal CA root/intermediate certs. Mitigation: CA bundle mount in Alloy container.
- Cert chain reporting: blackbox reports earliest expiry in chain (could be intermediate, not leaf). Mitigation: document behavior, consider x509-exporter supplement for file-based validation.
- Inventory completeness: missing endpoints means missing certs. Mitigation: maintain endpoint inventory in `configs/alloy/certs/endpoints.yml` and review periodically.

### Human Actions Required

- [ ] Provide initial list of HTTPS/TLS endpoints to monitor (internal + public)
- [ ] Provide internal CA root and intermediate certificates for trust chain
- [ ] Confirm DigiCert CertCentral API access availability (if using direct API)
- [ ] Review alert thresholds (30d warning, 7d critical are defaults)

---

## Phase 7D: Lansweeper Integration

**Goal**: Bridge asset discovery (Lansweeper) and infrastructure health monitoring (this stack) with automated inventory sync, asset enrichment metrics, a unified dashboard, and webhook-driven real-time updates. Uses Lansweeper Cloud/Hybrid GraphQL API with Personal Access Token authentication.

**Status**: In Progress

**Approach**: Rolling integration -- each sub-phase is independently functional and tested before the next begins.

### Sub-Phase 7D.1: Core API Client + Inventory Sync

**Goal**: Replace manual CSV imports with automated Lansweeper API pulls.

- [x] 1. Add `.env` variables for Lansweeper config (`LANSWEEPER_API_URL`, `LANSWEEPER_SITE_ID`, `LANSWEEPER_PAT`) -- Simple
- [x] 2. Create `scripts/lansweeper_sync.py` -- GraphQL client with PAT auth, pagination handling, rate-limit backoff -- Medium
- [x] 3. Implement `sync` subcommand -- query assets, map to `hosts.yml` schema (hostname, site, roles, os, ip), merge without clobbering -- Medium
- [x] 4. Add `--dry-run` flag -- show what would change without writing -- Simple
- [x] 5. Add field mapping config (`inventory/lansweeper_field_map.yml`) -- maps Lansweeper asset types/fields to monitoring roles and sites -- Medium
- [ ] 6. Integration test with live API -- validate pagination, empty results, error handling -- Medium
- [x] 7. Documentation -- `docs/LANSWEEPER_INTEGRATION.md` with setup, auth, usage -- Simple

**Done when**: `python3 scripts/lansweeper_sync.py sync --dry-run` shows correct host mapping from live Lansweeper data, and `sync` merges into `hosts.yml` passing `fleet_inventory.py validate`.

### Sub-Phase 7D.2: Asset Enrichment Metrics

**Goal**: Expose Lansweeper metadata (warranty, hardware model, OS version, last seen) as Prometheus metrics for dashboard joins.

- [x] 1. Add `export-metrics` subcommand to `lansweeper_sync.py` -- query enrichment fields (serial, manufacturer, model, warranty date, OS version, last seen) -- Medium
- [x] 2. Write Prometheus textfile format output (`lansweeper_asset_info` gauge with labels, `lansweeper_warranty_expiry_timestamp_seconds`, `lansweeper_last_seen_timestamp_seconds`) -- Medium
- [x] 3. Create Alloy textfile collector config snippet for Lansweeper metrics directory -- Simple
- [x] 4. Add Prometheus recording rules for warranty expiry alerting thresholds -- Simple
- [x] 5. Add alert rules -- warranty expiring in 90/60/30 days + expired, assets not seen in 7+ days -- Medium
- [ ] 6. Validate metrics flow end-to-end in Docker Compose PoC -- Medium

**Done when**: `lansweeper_asset_info` and `lansweeper_warranty_expiry_days` metrics appear in Prometheus with correct labels, and warranty alerts fire correctly against test data.

### Sub-Phase 7D.3: Asset Inventory Dashboard

**Goal**: Grafana dashboard combining Lansweeper asset data with health metrics.

- [ ] 1. Create `dashboards/overview/asset_inventory.json` -- panels: asset count by site/type/OS, hardware model distribution -- Medium
- [ ] 2. Add warranty tracker panel -- table of assets sorted by warranty expiry, color-coded (expired/30d/60d/90d) -- Medium
- [ ] 3. Add "stale assets" panel -- assets in Lansweeper not seen by monitoring (left join on hostname) -- Medium
- [ ] 4. Add "unmanaged assets" panel -- assets in monitoring but not in Lansweeper -- Medium
- [ ] 5. Link to existing dashboards -- drill-down from asset row to Windows/Linux overview filtered by hostname -- Simple
- [ ] 6. Add dashboard to Grafana provisioning and Helm chart -- Simple

**Done when**: Dashboard renders correctly with Lansweeper-enriched data, drill-downs work, and respects existing RBAC folder permissions.

### Sub-Phase 7D.4: Webhook-Driven Real-Time Sync

**Goal**: Lansweeper pushes asset changes to keep monitoring inventory in sync automatically.

- [ ] 1. Create `scripts/lansweeper_webhook.py` -- lightweight HTTP receiver accepting Lansweeper webhook POST payloads -- Medium
- [ ] 2. Implement signature verification (`X-LS-webhook-signature`, HMAC_SHA256) -- Medium
- [ ] 3. Handle `NEW_ASSET` event -- query full asset details via API, apply field mapping, append to `hosts.yml` -- Medium
- [ ] 4. Handle `UPDATED_ASSET` event -- refresh asset fields in `hosts.yml` -- Medium
- [ ] 5. Handle `DELETED_ASSET` event -- flag or remove from `hosts.yml` (configurable soft/hard delete) -- Medium
- [ ] 6. Add Dockerfile and Helm chart sidecar config for webhook receiver -- Medium
- [ ] 7. Add `EXPORT_COMPLETED` handler for bulk reconciliation syncs -- Simple
- [ ] 8. Documentation -- webhook setup in Lansweeper, network requirements, troubleshooting -- Simple

**Done when**: New asset added in Lansweeper appears in `hosts.yml` within minutes without manual intervention, and signature verification rejects forged payloads.

### Human Actions Required

- [ ] Create Lansweeper API client (PAT) in Site Settings > Developer Tools (before 7D.1)
- [ ] Provide Lansweeper Site ID (before 7D.1)
- [ ] Define asset type-to-role mapping for field map config (during 7D.1)
- [ ] Configure webhook in Lansweeper cloud console (before 7D.4)
- [ ] Expose webhook endpoint publicly via ingress/reverse proxy (before 7D.4)

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Rate limit lockout (1-min cooldown resets on any request) | Exponential backoff with jitter, never retry during cooldown window |
| Asset type-to-role mapping is org-specific | Configurable field map YAML, not hardcoded |
| Textfile collector is cron-based, not real-time | Acceptable for slow-changing asset metadata; webhooks (7D.4) handle urgent changes |
| Label cardinality from enrichment fields | Info-style metrics only, join via `hostname` label |
| Webhook receiver needs public endpoint | Document reverse proxy/ingress setup; scheduled full sync as reconciliation backstop |
| 5-minute webhook dedup window may miss rapid changes | Scheduled full sync (7D.1) runs as reconciliation backstop |

---

## Phase 7E: Cloud Infrastructure Monitoring (Stub)

**Goal**: Placeholder configs for AWS CloudWatch and Azure Monitor integration via native Alloy exporters. Activated when cloud resources are deployed.

**Status**: Completed -- stub configs ready, activate when cloud resources are deployed

### Tasks

- [x] 1. Create stub Alloy configs for cloud exporters
  - `configs/alloy/cloud/aws_cloudwatch.alloy.example` -- commented, with instructions
  - `configs/alloy/cloud/azure_monitor.alloy.example` -- commented, with instructions
  - Documents required IAM roles / Azure service principals
  - Complexity: Simple
  - Dependencies: None

- [x] 2. Create stub Helm values for cloud integration
  - values.yaml additions with `enabled: false`
  - Document required credentials and permissions per provider
  - Complexity: Simple
  - Dependencies: None

- [x] 3. Documentation -- `docs/CLOUD_MONITORING.md`
  - Prerequisites per cloud provider (IAM, service principal, API access)
  - Which metrics are available (EC2, RDS, Azure VMs, etc.)
  - Activation workflow
  - Complexity: Simple

### Human Actions Required

- [ ] Identify which cloud provider(s) are in use (when ready)
- [ ] Create IAM role or Azure service principal with read-only metrics access

---

## Phase 7F: IIS Dedicated Dashboard

**Goal**: Build a dedicated IIS Web Server dashboard. The Alloy role config (`role_iis.alloy`) and alert rules (`role_alerts.yml`) already exist and are proven -- IIS metrics are collected but only visible in the generic Windows overview dashboard.

**Status**: Pending

### Tasks

- [ ] 1. Create IIS Server dashboard -- `dashboards/windows/iis_overview.json`
  - Per-site request rates (GET, POST, PUT, DELETE breakdown)
  - 5xx and 4xx error rates with status code breakdown
  - Active connections and connection rate over time
  - Bytes sent/received throughput per site
  - App pool worker process health and recycle counts
  - W3C access log volume and top status codes (LogQL from Loki)
  - Request queue length
  - Template vars: environment, datacenter, hostname, site_name
  - Complexity: Medium
  - Dependencies: None (IIS Alloy config and alerts already exist)

- [ ] 2. Create IIS recording rules -- `configs/prometheus/iis_recording_rules.yml`
  - Pre-computed request rates and error ratios per site
  - Connection rate aggregations
  - Complexity: Simple
  - Dependencies: None

- [ ] 3. Update Grafana dashboard provisioning for new directories
  - Add `network/`, `hardware/`, `certs/`, `assets/` to provisioning config
  - One-time task that covers all Phase 7 sub-phases
  - Complexity: Simple
  - Dependencies: None

### Risks

- Minimal. IIS metrics are already collected and validated in the Docker Compose PoC.

### Human Actions Required

- None (uses existing Alloy config and metrics)

---

## Phase 7G: Agentless Collection (Edge Cases)

**Goal**: WinRM and SSH-based remote metric and log collection for devices where Alloy agent installation is not possible (vendor appliances, embedded systems, locked-down hosts).

**Status**: Blocked -- requires internal use case identification before any implementation

**Gate**: Task 1 must produce a finite target list with justification before any code is written. This phase does not proceed speculatively.

### Tasks

- [ ] 1. Identify agentless targets (INTERNAL ACTION)
  - Catalog devices where agent installation is blocked
  - Document reason for each (vendor restriction, no OS access, embedded firmware, etc.)
  - Classify: WinRM-capable vs SSH-capable vs neither
  - Deliver target list with justification
  - Complexity: Simple (process, not code)
  - Dependencies: Internal team review

- [ ] 2. Design agentless collection architecture
  - WinRM: Alloy proxy instance running PowerShell scrapers remotely, or script_exporter executing remote commands
  - SSH: Alloy proxy instance with remote node_exporter textfile collector pushed via SCP, or SSH-based command execution
  - Architecture decision: one proxy per site vs centralized
  - Complexity: Medium
  - Dependencies: Task 1 (must know what devices and what to collect)

- [ ] 3. Create proxy Alloy configs -- `configs/alloy/roles/role_agentless_proxy.alloy`
  - Complexity: Medium
  - Dependencies: Task 2

- [ ] 4. Create agentless targets inventory -- `configs/alloy/agentless/targets.yml`
  - Complexity: Simple
  - Dependencies: Task 1

- [ ] 5. Alert rules and dashboard panels for agentless targets
  - Complexity: Simple
  - Dependencies: Task 3

- [x] 6. Documentation -- `docs/AGENTLESS_MONITORING.md`
  - Decision tree: when to use agentless vs agent-based
  - Security considerations (credential storage, WinRM hardening, SSH key management)
  - Complexity: Simple

### Risks

- Scope creep: agentless can become a rabbit hole if not scoped tightly. Mitigation: strict gate on Task 1 -- finite target list required before implementation.
- Credential management: WinRM/SSH credentials for remote hosts are sensitive. Mitigation: Kerberos delegation or SSH key auth, never stored in config files.
- Reliability: remote collection is inherently less reliable than local agent. Mitigation: document SLA expectations, add probe-up alerts for agentless targets.

### Human Actions Required

- [ ] Identify devices where agent installation is not possible
- [ ] Document reason for each (vendor restriction, embedded firmware, access limitation, etc.)
- [ ] Provide WinRM/SSH credentials or authentication method for each target
- [ ] Approve agentless scope before implementation begins

---

## Phase 7H: Dashboard Hub Architecture

**Goal**: Create a location-centric navigation layer across all monitoring domains. Two dashboards: an Enterprise NOC view showing all sites at a glance, and a Site Overview dashboard showing all monitored infrastructure at a single site/location with drill-down links to detailed dashboards.

**Status**: Completed

**Audience**: Both central NOC team (multi-site comparison, problem identification) and site IT staff (single-site deep visibility, troubleshooting).

**Scope**: Servers and actively monitored infrastructure only. Asset/endpoint inventory is out of scope (handled externally).

**Design Principle**: These dashboards are additive -- they consume metrics from all other phases. Each Phase 7 sub-phase adds a new row/section to the Site Overview and a new column to the Enterprise NOC grid. Ship the framework with server + IIS data now; SNMP, hardware, and cert sections land as those phases complete.

### Tasks

- [x] 1. Create Enterprise NOC dashboard -- `dashboards/overview/enterprise_noc.json`
  - Multi-site health grid: one row per datacenter/site, columns for each monitoring domain
  - Domain columns (grow as phases ship):
    - Servers: count, avg CPU, avg memory, services down
    - IIS: request rate, 5xx error rate (when Phase 7F metrics exist)
    - Network: devices up/down, interfaces down, high utilization, errors (Phase 7A -- live)
    - Hardware: chassis health OK/warning/critical, temperature, power (Phase 7B -- live)
    - Certificates: expiring <30d count (when Phase 7C ships)
  - Active alert count per site with severity breakdown
  - Top-N worst sites ranking (by combined health score)
  - Each site name is a clickable link to the Site Overview dashboard pre-filtered to that site
  - Template vars: environment (for filtering prod/staging/dev)
  - Complexity: Medium
  - Dependencies: Phase 7F complete (server + IIS recording rules provide initial data)

- [x] 2. Create Site Overview dashboard -- `dashboards/overview/site_overview.json`
  - Single `datacenter` variable (single-select, not multi) as the site selector
  - Row: Site Health Summary
    - Stat panels: total servers, total alerts, total services down, uptime SLA %
  - Row: Server Health
    - Windows server count, avg CPU, avg memory, worst disk free
    - Linux server count, avg CPU, avg memory, worst disk free
    - Link to Windows/Linux Overview dashboards (inherits site filter)
  - Row: IIS Web Services
    - Total request rate, 5xx error rate, active connections
    - Link to IIS Overview dashboard (inherits site filter)
  - Row: Network Infrastructure (Phase 7A -- live)
    - Device inventory table (status, uptime, type, vendor), traffic timeseries
    - Link to Network Infrastructure dashboard
  - Row: Hardware Health (Phase 7B -- live)
    - Server health table (health, power state, temperature, power draw)
    - Link to Hardware Health dashboard
  - Row: Certificate Status (placeholder until Phase 7C)
    - Certs expiring <30d, <7d, expired count
    - Link to Certificate Overview dashboard
  - Row: Active Alerts for This Site
    - Table of firing alerts filtered by datacenter label
  - Row: Recent Logs for This Site
    - Combined Windows Event Log + Linux journal + IIS access log stream from Loki
  - Complexity: Medium
  - Dependencies: Phase 7F complete (server + IIS recording rules provide initial data)

- [x] 3. Create fleet-level recording rules for site aggregation -- `configs/prometheus/site_recording_rules.yml`
  - Per-site server counts: `site:servers_reporting:count`
  - Per-site avg CPU: `site:cpu_utilization:avg`
  - Per-site avg memory: `site:memory_utilization:avg`
  - Per-site worst disk free: `site:disk_free:min`
  - Per-site services not running: `site:services_not_running:sum`
  - Per-site IIS request rate: `site:iis_request_rate:sum` (when IIS metrics exist)
  - Complexity: Simple
  - Dependencies: None (uses existing instance-level recording rules)

- [x] 4. Add cross-dashboard link navigation to all existing dashboards
  - Add a dashboard link bar to Windows, Linux, IIS, and Infrastructure Overview dashboards
  - Links pass current template variable values (`$datacenter`, `$environment`) to target dashboards
  - Consistent navigation: every dashboard can reach the Enterprise NOC and Site Overview
  - Complexity: Simple
  - Dependencies: Tasks 1, 2

- [x] 5. Update placeholder rows as Phase 7 sub-phases complete
  - 7A: Network rows populated with SNMP recording rules, NOC site table with drill-down
  - 7B: Hardware rows populated with Redfish metrics, NOC site table with drill-down
  - 7C: Certificate rows populated with blackbox metrics (completed previously)
  - Remaining: only Phase 7E+ sub-phases (if dashboard integration needed)

### Architecture Notes

- **Link inheritance**: Grafana supports passing template variables via URL parameters. The Enterprise NOC links to Site Overview with `?var-datacenter=SITE-A`. Site Overview links to detailed dashboards with `?var-datacenter=$datacenter&var-environment=$environment`. This creates seamless drill-down without requiring users to re-select filters.
- **Placeholder rows**: Network (7A), Hardware (7B), and Certificate (7C) rows are now populated with real queries and drill-down links. Future Phase 7 sub-phases (7E+) follow the same pattern if dashboard integration is needed.
- **Dashboard UIDs**: `enterprise-noc`, `site-overview`. All dashboards reference these UIDs in their link definitions for stability across Grafana upgrades.

### Risks

- Dashboard complexity: the Enterprise NOC grid queries many recording rules simultaneously. Mitigation: all queries use pre-computed recording rules (not raw metrics), keeping dashboard load time fast.
- Placeholder row maintenance: Network, Hardware, and Certificate placeholder rows are now populated. Only future Phase 7 sub-phases (7E+) may need dashboard integration.
- Template variable cascade: passing variables between dashboards requires consistent naming (`datacenter` everywhere, not `site` in some places). Mitigation: existing dashboards already use a consistent taxonomy.

### Human Actions Required

- [ ] Review Enterprise NOC layout with operations team
- [ ] Confirm which sites should appear in the NOC grid (all sites, or only production?)
- [ ] Provide feedback on Site Overview row ordering and priority

---

## Phase 8: Access Control and RBAC

**Goal**: Implement Grafana folder-based RBAC with LDAP/AD group synchronization for tiered dashboard visibility. Each site's IT team sees only their own infrastructure. Enterprise operations sees everything. User onboarding is a single AD group add -- no Grafana admin action needed.

**Status**: Completed

**Prerequisite**: Phase C (LDAP authentication) in Helm chart, Phase 7H (dashboard folder structure exists)

**Identity Platform**: Hybrid AD / Entra ID. Grafana authenticates via LDAP against on-premises domain controllers. Entra ID syncs users and groups to on-prem AD via Azure AD Connect. The LDAP source is always the on-prem DC.

**Architecture Reference**: See [ARCHITECTURE.md](../ARCHITECTURE.md) for the access tier model, folder structure, team-to-folder permission model, and LDAP group sync design.

### Tasks

- [x] 1. Create dashboard folder provisioning config -- `configs/grafana/provisioning/dashboards/`
  - Restructure dashboard provisioning to use per-site folders instead of per-category folders
  - Folder structure: `Enterprise/`, `Site - <name>/` (one per site), `Shared/`
  - Existing dashboards redistributed: Enterprise NOC -> `Enterprise/`, site-specific dashboards -> `Site - <name>/`, cross-site dashboards (log explorer, cert overview) -> `Shared/`
  - Folder names are templatized with placeholder site names (deployers replace per fork)
  - Complexity: Medium
  - Dependencies: None

- [x] 2. Create Grafana Team provisioning config -- `configs/grafana/provisioning/teams/`
  - Provisioning YAML defining Grafana Teams: `Enterprise Ops`, per-site teams (e.g., `DC-East Ops`), `Stakeholders`
  - Team names templatized with placeholder site names
  - Evaluate whether Grafana provisioning API supports team-folder permission bindings (may require API calls or Terraform)
  - Complexity: Medium
  - Dependencies: Task 1

- [x] 3. Create folder permission provisioning
  - Remove default org-level Viewer permission from site folders
  - Grant `Enterprise Ops` team Editor on all folders
  - Grant each site team Viewer on their site folder and `Shared/`
  - Grant `Stakeholders` team Viewer on `Enterprise/` only
  - Evaluate: Grafana provisioning vs Terraform vs API script for permission management
  - Complexity: Medium
  - Dependencies: Tasks 1, 2

- [x] 4. Create LDAP configuration -- `configs/grafana/ldap.toml`
  - LDAP server connection (LDAPS on port 636)
  - Bind DN for service account authentication
  - User search base and filter (`sAMAccountName` for AD, `uid` for standard LDAP)
  - Group search base and filter for AD security groups
  - Group-to-Team mapping: `SG-Monitoring-Admins` -> `Enterprise Ops`, `SG-Monitoring-<Site>` -> `<Site> Ops`, etc.
  - Auto-provisioning: create Grafana user on first LDAP login
  - Default org role for new users: `Viewer`
  - Complexity: Medium
  - Dependencies: None (configuration, but tested with Tasks 1-3)

- [x] 5. Update Grafana configuration for LDAP auth -- `configs/grafana/grafana.ini` or env vars
  - Enable LDAP authentication (`auth.ldap.enabled = true`)
  - Set LDAP config file path (`auth.ldap.config_file = /etc/grafana/ldap.toml`)
  - Configure auto-provisioning behavior (sync interval, allow sign-up)
  - Disable basic auth if LDAP is the sole auth method (or keep as fallback)
  - Complexity: Simple
  - Dependencies: Task 4

- [x] 6. Update Helm chart for RBAC support
  - Add `ldap.toml` to Grafana ConfigMap or Secret (contains bind password)
  - Add `grafana.ini` overrides for LDAP auth settings
  - Add values.yaml fields for LDAP connection, group mapping, and team provisioning
  - Add folder permission provisioning to Grafana init container or startup script
  - Complexity: Medium
  - Dependencies: Tasks 1-5

- [x] 7. Create RBAC testing and validation script -- `scripts/validate_rbac.py`
  - Validate folder structure matches expected site list
  - Validate Team provisioning against expected AD group mapping
  - Validate folder permissions (each site folder accessible only by correct team)
  - Test mode: connects to running Grafana instance, queries API, reports compliance
  - Dry-run mode: validates config files without a running instance
  - Complexity: Medium
  - Dependencies: Tasks 1-3

- [x] 8. Document RBAC setup and operations -- `docs/RBAC_GUIDE.md`
  - Prerequisites: AD security groups created, LDAP service account, Grafana LDAP config
  - Step-by-step: adding a new site (folder + team + AD group + permissions)
  - Step-by-step: onboarding a new team member (AD group add only)
  - Step-by-step: offboarding (AD group remove -- Grafana session revoked on next sync)
  - Troubleshooting: LDAP bind failures, group sync delays, permission issues
  - AD group naming convention: `SG-Monitoring-<Site>` or organization-specific prefix
  - Hybrid AD / Entra ID specifics: which DC to bind against, Azure AD Connect sync timing
  - Complexity: Medium
  - Dependencies: Tasks 1-6

### Architecture Notes

- **Folder-based isolation over Grafana Organizations**: Single Org with folder-level permissions is simpler than multi-Org. Multi-Org would require duplicating datasources and dashboards per org. Folder permissions achieve site isolation without duplication.
- **LDAP over Entra ID OAuth**: Hybrid AD/Entra ID environments have both identity sources. LDAP is chosen because it provides group sync natively (AD security groups -> Grafana Teams). Entra ID OAuth would require Grafana Enterprise for team sync via Azure AD groups. LDAP against on-prem DC is available with Grafana OSS.
- **Auto-provisioning**: New users are created in Grafana on first LDAP login with the default Viewer role. Team membership is determined by AD group sync. No manual Grafana account creation needed.
- **Template variable scoping**: Dashboard template variables filter data by `datacenter` label. Even if a user could somehow access a dashboard outside their folder, they would only see data for sites whose `ALLOY_DATACENTER` labels match their site. Folder permissions are the primary access control; label scoping is a secondary data boundary.

### Risks

- **Grafana provisioning limitations**: Grafana's file-based provisioning may not support team-folder permission bindings. Mitigation: evaluate API-based provisioning (Terraform, init container script) as alternative.
- **LDAP group sync latency**: AD group changes may take 5-15 minutes to sync to Grafana. Mitigation: document expected sync interval, provide manual sync API endpoint.
- **Multi-domain complexity**: Hybrid AD/Entra ID with multiple on-prem domains may require multiple LDAP server entries. Mitigation: document multi-domain configuration, test against primary domain first.
- **Grafana version dependency**: LDAP team sync behavior varies across Grafana versions. Mitigation: document minimum Grafana version, test against the version deployed.

### Human Actions Required

- [ ] Create AD security groups following the `SG-Monitoring-<Site>` convention (or provide naming convention)
- [ ] Provide list of sites/datacenters that need separate dashboard visibility
- [ ] Create an LDAP service account (read-only, bind access to user and group OUs)
- [ ] Provide LDAP server hostname (on-prem DC), port, bind DN, search bases
- [ ] Identify IT team leads at each site (who approves access requests)
- [ ] Decide whether read-only stakeholder access is needed (management dashboards)
- [ ] Decide whether any sites share IT staff (impacts Team membership design)
- [ ] Designate Grafana admin account ownership (who holds the admin password long-term)

---

## Phase 9: Requirements Gap Closure

**Goal**: Close all remaining feature gaps to deliver a complete monitoring platform. Covers agentless probing, file/process monitoring, alert deduplication, maintenance windows, SLA reporting, SNMP traps, audit logging, and capacity forecasting.

**Status**: Completed

**Prerequisite**: None. All work is additive configuration. No dependency on Phases 5.7, 6, 7E, 7G, or 8.

**Estimated effort**: 10-14 days of configuration work (completed across 3 sessions).

**Approach**: All tasks create new files or extend existing configs. No existing production configs are replaced or restructured. Follows the fork-and-deploy model -- capability templates are built here; deployers customize targets and thresholds for their environment.

### Tasks -- Group A: Agentless Probing Extensions (1 day)

Extends the existing blackbox exporter and site gateway with ICMP, TCP, UDP, and HTTP probe types.

- [x] 1. Add ICMP, TCP, and UDP probe modules to blackbox exporter config -- extend `configs/alloy/gateway/site_gateway.alloy`, new `configs/alloy/gateway/blackbox_modules.yml`
  - Complexity: Simple
  - Dependencies: None

- [x] 2. Add HTTP/HTTPS synthetic probe module with response code and body validation -- same files as Task 1
  - Complexity: Simple
  - Dependencies: Task 1

- [x] 3. Create probe target template file with categorized examples (web apps, mail relays, DNS resolvers, database listeners) -- `configs/alloy/gateway/probe_targets.yml`
  - Complexity: Simple
  - Dependencies: None

- [x] 4. Create probe failure alert rules (HTTPProbeFailed, ICMPProbeFailed, TCPProbeFailed, UDPProbeFailed) -- `alerts/prometheus/probe_alerts.yml`
  - Complexity: Simple
  - Dependencies: Tasks 1-2

- [x] 5. Create probing recording rules (probe success ratio, latency aggregation by target and site) -- `configs/prometheus/probe_recording_rules.yml`
  - Complexity: Simple
  - Dependencies: Tasks 1-2

- [x] 6. Update Prometheus config to load new probe rule files -- extend `configs/prometheus/prometheus.yml` rule_files list
  - Complexity: Simple
  - Dependencies: Tasks 4-5

**Covers requirements**: Agentless / Stimulus response status monitoring (ICMP, TCP/UDP), Synthetic service testing.

### Tasks -- Group B: Alloy Agent Collection Extensions (1 day)

New opt-in Alloy role configs for file/folder size monitoring and arbitrary process monitoring. New files only.

- [x] 7. Create Windows file/folder size monitoring component -- `configs/alloy/windows/role_file_size.alloy`
  - Monitors configurable file and folder paths, exposes size as metric
  - Paths specified via environment variable or config customization
  - Complexity: Medium
  - Dependencies: None

- [x] 8. Create Linux file/folder size monitoring component -- `configs/alloy/linux/role_file_size.alloy`
  - Complexity: Medium
  - Dependencies: None

- [x] 9. Create Windows process monitoring component (non-service executables) -- `configs/alloy/windows/role_process.alloy`
  - Tracks whether specified process names are running, exposes as metric
  - Process names specified via environment variable or config customization
  - Complexity: Medium
  - Dependencies: None

- [x] 10. Create Linux process monitoring component -- `configs/alloy/linux/role_process.alloy`
  - Complexity: Medium
  - Dependencies: None

- [x] 11. Create file size and process alert rules (FileSizeExceeded, ProcessNotRunning) -- `alerts/prometheus/endpoint_alerts.yml`
  - Complexity: Simple
  - Dependencies: Tasks 7-10

**Covers requirements**: File and Folder size monitoring, Program status (running, not running).

### Tasks -- Group C: Dashboard and Forecasting Enhancements (1.5 days)

Extends existing dashboards with capacity forecasting panels. Creates new SLA and probing dashboards.

- [x] 12. Add `predict_linear` disk capacity forecasting panels to Windows Overview dashboard -- extend `dashboards/windows/windows_overview.json`
  - Shows "days until disk full at current rate" per volume
  - Complexity: Simple
  - Dependencies: None

- [x] 13. Add `predict_linear` disk capacity forecasting panels to Linux Overview dashboard -- extend `dashboards/linux/linux_overview.json`
  - Complexity: Simple
  - Dependencies: None

- [x] 14. Add `predict_linear` memory and CPU trend panels to Infrastructure Overview -- extend `dashboards/overview/infrastructure_overview.json`
  - Shows fleet-wide capacity trajectory
  - Complexity: Simple
  - Dependencies: None

- [x] 15. Create SLA recording rules (daily/weekly/monthly availability per host, per role, per site) -- `configs/prometheus/sla_recording_rules.yml`
  - Uses `avg_over_time(up[period])` for availability percentages
  - Aggregates by datacenter, role, and fleet-wide
  - Complexity: Medium
  - Dependencies: None

- [x] 16. Create SLA Availability dashboard -- `dashboards/overview/sla_availability.json`
  - Availability percentage by host, role, and site
  - SLA target threshold indicators (99.9%, 99.5%, 99.0%)
  - Top/bottom hosts by availability
  - Time range selector for daily/weekly/monthly view
  - Complexity: Medium
  - Dependencies: Task 15

- [x] 17. Create Agentless Probing dashboard -- `dashboards/overview/probing_overview.json`
  - Probe status grid (up/down per target)
  - Latency timeseries per probe target
  - Success rate percentages
  - Complexity: Medium
  - Dependencies: Group A tasks

- [x] 18. Update Prometheus config to load SLA recording rules -- extend `configs/prometheus/prometheus.yml` rule_files list
  - Complexity: Simple
  - Dependencies: Task 15

**Covers requirements**: Future forecasting, SLA calculation and reporting, Synthetic testing visibility.

### Tasks -- Group D: Alert Deduplication Enhancement (1.5 days)

Adds mass-outage detection and site-level alert suppression to reduce alert storms.

- [x] 19. Create mass-outage detection recording rules -- `configs/prometheus/outage_recording_rules.yml`
  - Calculates percentage of hosts unreachable per datacenter and per role
  - Threshold-based: fires when >X% of a site's hosts are simultaneously unreachable
  - Complexity: Medium
  - Dependencies: None

- [x] 20. Create SitePartialOutage and RolePartialOutage alert rules -- `alerts/prometheus/outage_alerts.yml`
  - SitePartialOutage: fires when significant portion of a datacenter goes unreachable
  - RolePartialOutage: fires when significant portion of a role (e.g., all SQL servers) goes unreachable
  - Complexity: Medium
  - Dependencies: Task 19

- [x] 21. Add mass-outage inhibition rules to Alertmanager -- extend `configs/alertmanager/alertmanager.yml` inhibit_rules section
  - SitePartialOutage suppresses individual host-down alerts for that datacenter
  - RolePartialOutage suppresses individual service-down alerts for that role
  - Additive: new rules appended to existing inhibit_rules list
  - Complexity: Medium
  - Dependencies: Task 20

- [x] 22. Document alert deduplication architecture and upstream_device label pattern -- `docs/ALERT_DEDUP.md`
  - Explains the mass-outage approach (zero maintenance)
  - Documents optional per-host topology mapping via upstream_device labels (for future use)
  - Includes decision record from team review (grouping vs full topology)
  - Complexity: Simple
  - Dependencies: None

- [x] 23. Update Prometheus config to load outage recording rules -- extend `configs/prometheus/prometheus.yml` rule_files list
  - Complexity: Simple
  - Dependencies: Task 19

**Covers requirement**: Alert deduplication (hierarchy-based) -- via mass-outage detection and grouped suppression.

### Tasks -- Group E: Maintenance Window Tooling (1 day)

Adds recurring maintenance window support and programmatic silence management.

- [x] 24. Create Grafana mute timing examples in notification policy -- extend `configs/grafana/notifiers/notifiers.yml`
  - Example recurring windows: weekly patching (Sunday 02:00-06:00), monthly maintenance, backup windows
  - Deployers customize time ranges and affected notification policies
  - Complexity: Medium
  - Dependencies: None

- [x] 25. Create maintenance window API helper script -- `scripts/maintenance_window.py`
  - Create silence: by datacenter, role, hostname, or custom label matchers with start/end time
  - List active silences: shows all current maintenance windows with expiry
  - Delete silence: removes a scheduled or active silence by ID
  - Scheduled creation: accepts future start time for pre-planned maintenance
  - Complexity: Medium
  - Dependencies: None

- [x] 26. Document maintenance window workflows -- `docs/MAINTENANCE_WINDOWS.md`
  - Ad hoc silences via Alertmanager UI
  - Scheduled silences via maintenance_window.py script
  - Recurring windows via Grafana mute timings
  - Scoped silences by label (datacenter, role, hostname)
  - Complexity: Simple
  - Dependencies: Tasks 24-25

**Covers requirements**: Alert silencing / maintenance windows (scheduled single-time, recurring, manual ad hoc, dynamic scopes).

### Tasks -- Group F: SNMP Trap Ingestion Pipeline (2 days)

New data flow: SNMP traps received by snmptrapd, formatted to syslog, forwarded to Loki via Alloy.

- [x] 27. Create snmptrapd configuration for trap reception and syslog formatting -- `configs/snmptrapd/snmptrapd.conf`
  - Configures trap listener on UDP 162
  - Formats trap data as structured syslog entries (OID, source IP, severity, varbinds)
  - Complexity: Medium
  - Dependencies: None

- [x] 28. Create Alloy syslog receiver component for trap log ingestion -- `configs/alloy/gateway/role_snmp_traps.alloy`
  - Receives syslog from snmptrapd
  - Loki label extraction pipeline for trap fields (OID, source device, severity, trap type)
  - Forwards structured trap logs to Loki
  - Complexity: Medium
  - Dependencies: Task 27

- [x] 29. Create SNMP trap alert rules via Loki alerting -- `alerts/grafana/snmp_trap_alerts.yml`
  - Critical trap OIDs trigger alerts (link down, power failure, authentication failure)
  - Uses LogQL queries against trap log labels
  - Complexity: Medium
  - Dependencies: Task 28

- [x] 30. Add SNMP trap log panel to Network Overview dashboard -- extend `dashboards/network/network_overview.json`
  - Trap history log stream filtered by device and severity
  - Trap volume graph
  - Complexity: Simple
  - Dependencies: Task 28

- [x] 31. Document SNMP trap pipeline setup and OID-to-alert mapping -- `docs/SNMP_TRAPS.md`
  - Architecture: snmptrapd -> syslog -> Alloy -> Loki
  - Trap OID reference for common network devices
  - How to add new trap-based alerts
  - Device-side trap destination configuration
  - Complexity: Simple
  - Dependencies: Tasks 27-29

**Covers requirement**: SNMP trap ingestion.

### Tasks -- Group G: Audit Logging Pipeline (1.5 days)

Forwards Grafana server logs to Loki for Tier 1 + Tier 2 (OSS) audit capability.

- [x] 32. Configure Grafana structured JSON logging at info level -- Grafana env vars or `configs/grafana/grafana.ini`
  - Enables structured JSON log output
  - Ensures API request logging includes user identity and action
  - Complexity: Simple
  - Dependencies: None

- [x] 33. Create Alloy component to tail Grafana server logs and forward to Loki -- `configs/alloy/roles/role_grafana_audit.alloy`
  - Tails Grafana log file or stdout
  - Loki label extraction pipeline for audit fields (user, action, dashboard_uid, alert_rule_id, HTTP method, path)
  - Complexity: Medium
  - Dependencies: Task 32

- [x] 34. Create Audit Trail dashboard -- `dashboards/overview/audit_trail.json`
  - Login activity (successful and failed, by user and IP)
  - Dashboard modifications (create, update, delete by user)
  - Alert rule changes (by user)
  - Silence creation and deletion (by user)
  - Filterable by user, action type, and time range
  - Complexity: Medium
  - Dependencies: Task 33

- [x] 35. Document audit logging architecture, capabilities, and limitations -- `docs/AUDIT_LOGGING.md`
  - What this approach covers (Tier 1 + partial Tier 2)
  - What requires Grafana Enterprise (full Tier 2 change diffs, Tier 3 compliance)
  - Log retention and querying via Loki
  - Complexity: Simple
  - Dependencies: Tasks 32-34

**Covers requirement**: User and admin action auditing (at OSS-achievable granularity).

### Tasks -- Group H: Validation and Documentation (1 day)

Extends validators, deployment configs, and documentation to cover all new Phase 9 components.

- [x] 36. Extend validate_prometheus.py to cover new rule files (probe, outage, SLA) -- `scripts/validate_prometheus.py`
  - Complexity: Simple
  - Dependencies: Groups A, C, D

- [x] 37. Extend validate_dashboards.py to cover new dashboards (SLA, Probing, Audit Trail) -- `scripts/validate_dashboards.py`
  - Complexity: Simple
  - Dependencies: Groups C, G

- [x] 38. Add new configs to Docker Compose bind mounts for PoC testing -- extend `deploy/docker/docker-compose.yml`
  - Complexity: Simple
  - Dependencies: All groups

- [x] 39. Add new configs to Helm chart ConfigMap templates -- extend `deploy/helm/monitoring-stack/templates/`
  - Complexity: Simple
  - Dependencies: All groups

- [x] 40. Update ARCHITECTURE.md with new components (probing tier, trap pipeline, audit pipeline)
  - Complexity: Simple
  - Dependencies: All groups

- [x] 41. Update README.md feature list with new capabilities
  - Complexity: Simple
  - Dependencies: All groups

- [x] 42. Create requirements traceability matrix -- `docs/REQUIREMENTS_TRACEABILITY.md`
  - Maps every requirement line item to the phase/config that delivers it
  - Distinguishes needs vs wants, covered vs decision-dependent
  - Complexity: Medium
  - Dependencies: All groups

### Execution Order

```
Week 1:
  Day 1-2:  Group A (probing) + Group B (file size, process monitoring)
            All additive new files, zero risk to existing configs
  Day 3-4:  Group C (dashboards, SLA, forecasting)
            Depends on Group A for probing dashboard; SLA is standalone
  Day 5:    Group D (alert dedup)
            Recording rules first, then inhibition rules

Week 2:
  Day 6:    Group E (maintenance windows)
            Independent of other groups
  Day 7-8:  Group F (SNMP traps)
            Most complex, new data flow pipeline
  Day 9-10: Group G (audit logging)
            Requires Grafana config understanding

Week 3:
  Day 11:   Group H (validation and documentation)
            Runs validators, updates deployment configs, writes docs
```

### Risks

- **ICMP probes require NET_RAW capability**: Blackbox exporter in a container needs the NET_RAW capability for ICMP. Mitigation: document container capability requirement, test in Docker Compose PoC.
- **SNMP trap pipeline adds snmptrapd dependency**: New external component. Mitigation: document as optional, trap pipeline only deployed at sites that need it.
- **Grafana audit log format may vary between versions**: Label extraction pipeline assumes specific JSON fields. Mitigation: pin expected log fields, document tested Grafana version.
- **SLA recording rules cardinality on large fleets**: Per-host daily availability could be expensive. Mitigation: aggregate by role and datacenter in recording rules, per-host available via instant queries only.
- **predict_linear confidence decreases over long extrapolation**: Mitigation: add panel description explaining projection methodology and limitations.

### Success Criteria

- All new alert rules load without error in Prometheus
- All new dashboards pass validate_dashboards.py (JSON syntax, UID uniqueness, datasource refs)
- All new recording rules pass validate_prometheus.py (YAML syntax, duration format, label compliance)
- Docker Compose PoC starts cleanly with all new configs mounted
- Helm chart templates render correctly with new ConfigMap entries
- validate_all.py passes with zero failures
- REQUIREMENTS_TRACEABILITY.md maps every non-decision-dependent requirement to a delivering phase

### Human Actions Required

None for Phase 9. All work is configuration. Deployment-time customization (probe target lists, process names, file paths, SLA targets, trap OID mappings) is documented but not hard-coded.

---

## Phase 10: Deployment Configuration Wrapper

**Goal**: An interactive deployment script that collects all stack configuration (sites, notifications, credentials) via prompts, generates every config file needed for a working multi-site deployment, and optionally seeds demo data so dashboards populate without live agents. Eliminates manual YAML editing for first-time deployment.

**Status**: In Progress

**Workflow**: `python scripts/deploy_configure.py` (interactive config) then `python scripts/stack_manage.py --demo-data` (start stack + seed data)

### Phase 10A: Core Wrapper Script

**Goal**: Interactive CLI that walks through all deployment parameters and generates config files.

- [ ] 1. Create `deploy/site_config.yml` schema -- single YAML file defining all deployment config (stack-wide settings + per-site definitions) -- Medium
- [ ] 2. Build `scripts/deploy_configure.py` with interactive prompt flow -- collects stack-wide settings (SMTP, Teams webhook, Grafana admin, retention) then per-site settings (code, name, contact email, gateway options) -- Medium
- [ ] 3. Generator: `inventory/sites.yml` + `inventory/hosts.yml` from site_config.yml -- Simple
- [ ] 4. Generator: `.env` with all stack-wide and per-site env vars -- Simple
- [ ] 5. Generator: `configs/alertmanager/alertmanager.yml` -- per-site receivers + routes, preserving group_by and inhibition rules -- Complex
- [ ] 6. Generator: `configs/grafana/notifiers/notifiers.yml` -- per-site contact points -- Simple
- [ ] 7. Non-interactive mode (`--config deploy/site_config.yml`) for re-runs -- Simple
- [ ] 8. Validation pass -- verify generated configs are syntactically valid before writing -- Medium

### Phase 10B: Demo Data Generator

**Goal**: Push synthetic metrics into Prometheus and logs into Loki that match real Alloy agent output, so all dashboards populate with realistic multi-site data.

- [ ] 1. Map dashboard panels to required metrics -- ensure demo data covers all dashboard categories (Windows, Linux, Overview, Network, Hardware, Certs, NOC) -- Complex
- [ ] 2. Build metric generator -- time-series data with correct label sets matching real Alloy output -- Complex
- [ ] 3. Per-site host simulation -- generate realistic host inventories (DCs, SQL, IIS, file servers, Docker) per site from site_config.yml -- Medium
- [ ] 4. Push to Prometheus via remote_write API -- Medium
- [ ] 5. Push synthetic log entries to Loki with matching labels -- Medium
- [ ] 6. Continuous background mode that keeps pushing data during demo -- Simple
- [ ] 7. Seed enough historical data (30+ min) for recording rules and SLA calculations -- Medium

### Phase 10C: Integration and Polish

- [ ] 1. Integrate with `stack_manage.py` -- add `--demo-data` flag that auto-starts generator after health checks -- Simple
- [ ] 2. Create `deploy/site_config.example.yml` with example multi-site config -- Simple
- [ ] 3. Update QUICKSTART.md with wrapper workflow -- Simple

### Human Actions Required

- [ ] Provide site codes and display names when running the wrapper
- [ ] Provide SMTP relay details (or accept placeholders for demo)
- [ ] Provide Teams webhook URL (or accept placeholder for demo)
- [ ] Validate demo data looks correct in dashboards after first run

### Success Criteria

- Run deploy_configure.py, answer prompts, then stack_manage.py --demo-data
- All dashboards populate with multi-site data within 2 minutes
- Enterprise NOC shows all configured sites
- Site Overview drill-down works per site
- Adding a new site requires only re-running the wrapper

---

## Phase 11: Dashboard Production Readiness

**Goal**: Remove all development artifacts from dashboards, restructure folders and tags for production, create missing role-specific dashboards, and ensure seamless site-first navigation. Demo must look identical to production.

**Status**: Completed

**Folder Structure**:
- **Enterprise**: NOC, SLA Availability, Audit Trail, Probing Overview
- **Servers**: Windows Overview, Linux Overview, IIS Overview, SQL Overview, DC Overview, DHCP Overview, CA Overview, File Server Overview, Docker Overview, Log Explorer
- **Infrastructure**: Site Overview, Network, Physical Server Health, Certificate Overview

### Tasks

- [x] 1. Replace all dashboard tags with functional taxonomy -- Simple
  - Removed `phase-7a`, `phase-7b` and all development tags
  - Applied: servers, windows, linux, iis, sql, dc, network, infrastructure, certificates, enterprise, sla, security, logs, probing
- [x] 2. Restructure provisioning to 3 folders (Enterprise, Servers, Infrastructure) -- Simple
  - Updated `configs/grafana/dashboards/dashboards.yml`
- [x] 3. Move dashboard JSON files to `dashboards/enterprise/`, `dashboards/servers/`, `dashboards/infrastructure/` -- Medium
  - Updated docker-compose.yml volume mounts
  - Helm chart references pending update
- [x] 4. Rename "Hardware Health" dashboard to "Physical Server Health" -- Simple
- [x] 5. Create SQL Server dashboard (`dashboards/servers/sql_overview.json`) -- Medium
- [x] 6. Create Domain Controller dashboard (`dashboards/servers/dc_overview.json`) -- Medium
- [x] 7. Create DHCP Server dashboard (`dashboards/servers/dhcp_overview.json`) -- Medium
- [x] 8. Create Certificate Authority dashboard (`dashboards/servers/ca_overview.json`) -- Medium
- [x] 9. Create File Server dashboard (`dashboards/servers/fileserver_overview.json`) -- Medium
- [x] 10. Create Docker Host dashboard (`dashboards/servers/docker_overview.json`) -- Medium
- [x] 11. Fix NOC -> Site Overview -> detail drill-down links across all dashboards -- Medium
  - All links pass `?var-datacenter=$datacenter&var-environment=$environment`
  - Consistent link bars: Enterprise (2 links), Servers (4 links), Infrastructure (5 links)
- [x] 12. Standardize template variables across all dashboards -- Medium
  - All variables: multi-select, include All, allValue=.*, refresh on time range change
  - Default to "All" on load so dropdowns populate correctly
- [x] 13. Create Alloy role configs for DHCP and CA -- Medium
  - `configs/alloy/windows/role_dhcp.alloy` (DHCP Server perf counters)
  - `configs/alloy/windows/role_ca.alloy` (AD CS perf counters)
- [x] 14. Update demo data generator for new role metrics (SQL, DC, DHCP, CA, FileServer, Docker) -- Medium
- [x] 15. End-to-end validation with demo data -- Medium
  - All 19 dashboards load in 3 folders (Enterprise 4, Servers 10, Infrastructure 5)
  - All template variables populate (environment, datacenter, hostname, role)
  - All 10 role metrics present (SQL, DC, DHCP, CA, FileServer, Docker, IIS, SNMP, Redfish, Certs)
  - All recording rules computing (Windows/Linux CPU, Fleet count, SLA, IIS)
  - Per-site distribution verified (ent, dv each have 42 up series)
  - Dashboard links pass datacenter variable correctly

### Role Tracking and Assignment

- [x] 16. Document role co-location rules in ALLOY_DEPLOYMENT.md -- Simple
  - DC includes DHCP/DNS collectors; do not deploy both role_dc.alloy and role_dhcp.alloy on same server
  - CA is standalone; deploy role_ca.alloy on dedicated CA servers
- [x] 17. Add role validation to deploy_configure.py -- Medium
  - ROLE_CONFLICTS dict warns on DC+DHCP co-location
  - ROLE_REFERENCE dict maps role -> config -> job -> dashboard -> prerequisites
  - check_role_conflicts() validates host inventory
- [x] 18. Document role-to-Alloy-config mapping for operators -- Simple
  - Role Reference table in ALLOY_DEPLOYMENT.md: role code, config file, metrics, dashboard, OS, prerequisites
- [x] 19. Add role discovery guidance -- Simple
  - Documented in ALLOY_DEPLOYMENT.md: AD OU queries, Lansweeper field mapping, naming conventions, manual assignment

### Success Criteria

- Zero development artifacts visible (no phase tags, no placeholder rows)
- 3 clean folders: Enterprise, Servers, Infrastructure
- NOC -> click site -> Site Overview pre-filtered -> click role -> role dashboard pre-filtered
- All role dashboards populated with demo data
- All template variable dropdowns work without warning triangles
- Dashboard looks production-ready for stakeholder demo

---

## Phase 12: Dashboard UX Polish

**Goal**: Make every dashboard operationally excellent -- clickable stat panels filter to detail views, expanded role metrics, standardized color coding, and demo data that showcases all features including downtime/failures.

**Status**: In Progress

### Completed

- [x] 1. SQL Overview: Blocked Processes and Disk Free clickable. Storage row added. Layout rebuilt.
- [x] 2. CA Overview: rebuilt with per-template breakdown table, issuance trends, processing time
- [x] 3. DHCP Overview: rebuilt with scope utilization table (4 scopes), scope detail trends
- [x] 4. Docker Overview: container stats clickable (per-container metrics need cAdvisor)
- [x] 5. DC Overview: rebuilt with LDAP sessions, replication bytes, SAM, tombstones, sync objects
- [x] 6. File Server Overview: Open Files and Active Sessions clickable
- [x] 7. Windows Overview: Services Stopped clickable
- [x] 8. Certificate Overview: colors standardized (<30d red, 30-60d yellow, >60d green)
- [x] 9. Infrastructure Overview: stat boxes clickable
- [x] 10. Network Infrastructure: Error Interfaces clickable
- [x] 11. Site Overview: stats clickable with datacenter pass-through
- [x] 12. Probing Overview: improved colors and thresholds
- [x] 13. Audit Trail: added purpose description, demo audit logs in Loki
- [x] 14. Enterprise NOC: High CPU/Low Disk thresholds fixed, SHG PromQL fixed
- [x] 15. SLA Overview: fixed red site names, SLA thresholds added, downtime simulated
- [x] 16. Demo data: SLA downtime simulation (~2% generic hosts go down)
- [x] 17. Demo data: audit trail log entries pushed to Loki
- [x] 18. Stopped Services Detail and Disk Space Detail tables added to 7 role dashboards
- [x] 19. All actionable stat/gauge panels have click links (comprehensive audit: 0 missing)

### Remaining: Click-to-Filter Detail Wiring (Phase 12B)

36 clickable stat panels link to dashboards but don't navigate to a specific detail panel. Two categories:

**Category A -- Link to existing detail panel (simple URL fix, no new panels):**
- [x] 20. Certificate Overview: Expiring/Urgent/Critical/Expired stats -> anchor to Certificate Inventory table -- Simple
- [x] 21. Network Infrastructure: Devices Monitored/Down, Interfaces Down -> anchor to Interface Status Table -- Simple
- [x] 22. Physical Server Health: Monitored/Warning/Critical/Unreachable -> anchor to Server Health Inventory table -- Simple
- [x] 23. Infrastructure Overview: High CPU/Low Disk/Active Alerts -> anchor to Top 10 tables -- Simple
- [x] 24. Log Explorer: Error/Warning/Critical stats -> anchor to log stream panels -- Simple
- [x] 25. File Server: Active Sessions/Open Files -> anchor to SMB Performance section -- Simple
- [x] 26. Probing Overview: Targets Failing -> anchor to probe status grid -- Simple
- [x] 27. SLA: Hosts Below SLA/Worst Site/Downtime -> anchor to per-host availability table -- Simple

**Category B -- New detail panel needed:**
- [x] 28. SQL: Blocked Processes -> new lock detail table (database, wait type, wait time) -- Medium
- [x] 29. SQL: User Connections -> new connection summary table -- Simple
- [x] 30. SQL: Disk Free (Worst) -> fix link to existing Storage row -- Simple
- [x] 31. Windows: Services Not Running -> new stopped services table -- Medium
- [x] 32. DC: Sync Objects Remaining -> link to Replication Health row -- Simple
- [x] 33. Docker: Running/Stopped Containers -> link to Container States section -- Simple
- [x] 34. Audit Trail: Failed Logins -> filtered log panel for failed auth -- Medium
- [x] 35. IIS: Active Connections -> link to connection/request detail section -- Simple

### Success Criteria

- Every clickable stat navigates to a visible, relevant detail panel
- Clicking shows filtered/specific data, not the same view
- Color coding consistent across all dashboards
- Demo data showcases all features including downtime, errors, audit activity
- No "No data" panels on any dashboard with demo data running

---

## Phase 13: Alert Strategy

**Goal**: Design and implement an alerting approach that eliminates SCOM-style alert fatigue. This is the #1 factor for platform adoption. If the team gets flooded with noise, they'll reject the platform.

**Status**: In Progress

**Context**: Current SCOM environment generates excessive alert noise. The team has no on-call rotation. Alerts go to per-site email DLs during business hours. The platform must be quieter and more actionable than SCOM from day one.

**Inventory**: 100 alert rules across 12 files (96 Prometheus + 4 Grafana). 35 critical, 59 warning, 6 info.

### 13A: Alert Audit and Baseline

- [x] 1. Create `docs/ALERT_CATALOG.md` -- categorize all 100 rules into tiers (Act Now / Investigate / Awareness), document expected fire rate, recommended action, default-enabled status -- Medium
- [x] 2. Review all thresholds against fleet-scale reality (1,500 hosts). Flag rules likely to be noisy at scale -- Medium -- 14 high-noise rules identified, 5 Lansweeper rules disabled by default
- [ ] 3. *(Human action)* Inventory SCOM alerts the team acts on vs ignores. Export from SCOM console. Map to Prometheus equivalents -- Medium
- [x] 4. Create `docs/ALERT_SEVERITY_CONTRACT.md` -- define what Critical/Warning/Info mean for this team, expected response times, escalation paths -- Simple

### 13B: Alert Noise Reduction

- [x] 5. Change `group_by` from `[alertname, hostname, datacenter]` to `[alertname, datacenter]` in Alertmanager and Grafana notifiers -- batches per-site instead of per-host -- Simple
- [x] 6. Tune `group_wait`: increase warning from 30s to 60s to catch more related alerts in one batch, keep critical at 15s -- Simple
- [x] 7. Validate `repeat_interval`: Critical 1h, Warning 4h, Info 12h -- confirmed appropriate for business-hours-only, no on-call workflow -- Simple
- [x] 8. Review and tune inhibition rules -- added critical-suppresses-warning rule, verified outage suppression paths (6 inhibition rules total) -- Medium
- [x] 9. Updated `docs/MAINTENANCE_WINDOWS.md` with best practices and troubleshooting sections -- Simple
- [ ] 10. *(Human action)* Test alert delivery end-to-end -- configure real Teams webhook, send test alerts, verify formatting, verify routing to correct site DL -- Medium

### 13C: Alert Documentation

- [x] 11. Add runbook entries for ~49 missing alerts (hardware, cert, lansweeper, SNMP, probe, endpoint, outage, SNMP traps) to ALERT_RUNBOOKS.md -- Complex -- all 100 alerts now have runbook entries
- [x] 12. Create `docs/ALERT_RESPONSE_GUIDE.md` -- sysadmin-facing guide: Teams notification arrives, what to do next, find the dashboard, silence if needed -- Medium
- [x] 13. Document threshold change process in the response guide -- how a sysadmin requests a change, who approves, how it's deployed -- Simple

### 13D: Alert Validation with Real Data

- [ ] 14. *(Human action)* Deploy to pilot site and monitor alert volume for 1 week -- count alerts per day, identify noisy rules, tune -- Complex
- [ ] 15. *(Human action)* Compare alert volume to SCOM -- are we generating fewer, more actionable alerts? -- Simple
- [ ] 16. *(Human action)* Get team feedback on alert quality after 2 weeks -- are they acting on alerts or ignoring them? -- Simple

### Success Criteria

- Every alert rule has a documented category, expected behavior, and runbook entry
- Severity contract defines team expectations for Critical/Warning/Info
- Alertmanager config produces batched, site-level notifications (not per-host spam)
- Sysadmin can respond to an alert end-to-end using only the documentation
- Maintenance window procedures documented for self-service
- Alert volume is measurably lower than SCOM for equivalent infrastructure (validated in 13D)
- Mass-outage events generate 1 alert, not 50

---

## Phase 13B: Operator Documentation

**Goal**: Create sysadmin-focused documentation that enables a team of 10 to operate, troubleshoot, and maintain this platform for 10+ years without the original builder. Written for Wiki/KB format -- no code knowledge required.

**Status**: Completed

**Audience**: Sysadmins who know Windows/Linux servers but have never used Grafana, Prometheus, or Alloy. They need to know what to do, not how it works internally.

**Delivery**: All docs in `docs/operations/` directory, standalone Markdown files ready for Wiki/KB import. Glossary included in Dashboard Guide.

### Documentation Deliverables

**Operations Guide** (day-to-day tasks):
- [x] 1. "Adding a New Server to Monitoring" -- `docs/operations/ADDING_A_SERVER.md` -- Medium
- [x] 2. "Adding a New Site/Datacenter" -- `docs/operations/ADDING_A_SITE.md` -- Simple
- [x] 3. "Silencing Alerts for Maintenance" -- `docs/MAINTENANCE_WINDOWS.md` (Phase 13) -- Simple
- [x] 4. "Responding to an Alert" -- `docs/ALERT_RESPONSE_GUIDE.md` (Phase 13) -- Medium
- [x] 5. "Checking Platform Health" -- `docs/operations/PLATFORM_HEALTH.md` -- Simple
- [x] 6. "Restarting the Monitoring Stack" -- `docs/operations/STACK_MANAGEMENT.md` -- Simple
- [x] 7. "Removing a Server from Monitoring" -- included in `docs/operations/STACK_MANAGEMENT.md` -- Simple
- [x] 8. "Changing Alert Thresholds" -- `docs/operations/CHANGING_THRESHOLDS.md` -- Simple

**Alert Reference** (per-alert documentation):
- [x] 9. Complete alert catalog -- `docs/ALERT_CATALOG.md` (Phase 13) -- Complex
- [x] 10. Alert severity definitions -- `docs/ALERT_SEVERITY_CONTRACT.md` (Phase 13) -- Simple

**Dashboard Guide** (how to use each dashboard):
- [x] 11. "Navigating the Dashboards" -- `docs/operations/DASHBOARD_GUIDE.md` -- Medium
- [x] 12. "Understanding Dashboard Panels" -- included in Dashboard Guide -- Medium
- [x] 13. Per-dashboard reference pages -- included in Dashboard Guide (all 23 dashboards) -- Complex

**Architecture Overview** (for engineers/escalation):
- [x] 14. "How the Monitoring Stack Works" -- `docs/operations/ARCHITECTURE_OVERVIEW.md` -- Medium
- [x] 15. "Alloy Agent Reference" -- included in Architecture Overview -- Medium
- [x] 16. "Troubleshooting Guide" -- `docs/operations/TROUBLESHOOTING.md` -- Medium

**Administration Guide** (platform maintenance):
- [x] 17. "Backup and Recovery" -- `docs/operations/ADMIN_GUIDE.md` -- Simple
- [x] 18. "Upgrading Components" -- included in Admin Guide -- Medium
- [x] 19. "Capacity Planning" -- included in Admin Guide -- Medium
- [x] 20. "User Management" -- included in Admin Guide -- Simple

### Format Requirements

- Written in Markdown for easy Wiki/KB import
- No code blocks unless showing a command to run
- Screenshots for all Grafana navigation tasks
- Each doc is standalone (can be read without reading other docs)
- Glossary of terms (PromQL, Alloy, datacenter label, recording rule) for sysadmins unfamiliar with the stack

### Success Criteria

- A new sysadmin can add a server to monitoring without asking the platform builder
- A sysadmin can respond to an alert end-to-end using only the documentation
- A sysadmin can silence alerts for maintenance without engineer help
- An engineer unfamiliar with this project can understand the architecture and troubleshoot issues
- All documentation is in docs/ directory, ready for Wiki import

---

## Phase 14: Production Rollout

**Goal**: Deploy the monitoring platform to production infrastructure, starting with a pilot site, then rolling to all sites. Hand off operations to the sysadmin team.

**Status**: Pending

**Deployment target**: Dedicated Docker host in centralized Denver datacenter. Docker Compose, not Kubernetes (walk before run).

**Team**: 8 sysadmins + 2 engineers. Sysadmins will operate day-to-day. Engineers handle escalations and platform changes.

**Budget**: $0 licensing. Replacing SquaredUp ($26K/year) and potentially SCOM.

### 14A: Pilot Site (2-4 weeks)

- [ ] 1. Provision dedicated Docker host in Denver DC -- Medium
- [ ] 2. Run deploy_configure.py with real site codes, real SMTP, real Teams webhook -- Simple
- [ ] 3. Deploy stack_manage.py on production host -- Simple
- [ ] 4. Select pilot site (smallest or most engaged site team) -- Simple
- [ ] 5. Deploy Alloy agents to 10-20 servers at pilot site (mix of DC, SQL, IIS, File Server, generic) -- Medium
- [ ] 6. Deploy site gateway for SNMP, Redfish, cert probing at pilot site -- Medium
- [ ] 7. Monitor for 1 week -- tune thresholds, fix false positives -- Medium
- [ ] 8. Get pilot site team feedback -- Simple

### 14B: Security Hardening (1-2 weeks)

- [ ] 9. TLS on Grafana (reverse proxy with cert) -- Medium
- [ ] 10. LDAP/AD integration (replace local demo accounts) -- Medium
- [ ] 11. RBAC folder permissions per site -- Simple (scripts exist)
- [ ] 12. Network access restrictions (Prometheus/Loki/Alertmanager not exposed externally) -- Simple
- [ ] 13. Secrets management for SMTP password, LDAP bind password, Redfish credentials -- Medium

### 14C: Fleet Rollout (2-4 weeks per site)

- [ ] 14. Deploy Alloy to all servers at pilot site -- Medium
- [ ] 15. Onboard second site -- repeat agent deployment + gateway -- Medium
- [ ] 16. Roll remaining sites (SCCM/Ansible for bulk Alloy deployment) -- Complex
- [ ] 17. Decommission SquaredUp dashboards as Grafana replaces them -- Simple
- [ ] 18. Evaluate SCOM replacement timeline -- when can SCOM agents be removed? -- Complex

### 14D: Operations Handoff (ongoing)

- [ ] 19. Create sysadmin operations runbook (one-pager): add server, silence alert, check stack health, restart services -- Medium
- [ ] 20. External healthcheck on monitoring stack (cron + curl to Grafana/Prometheus health endpoints, alert via separate channel if down) -- Medium
- [ ] 21. Grafana DB backup (daily cron, retain 7 days) -- Simple
- [ ] 22. Capacity planning document -- storage projections at full fleet, when to expand disk -- Medium
- [ ] 23. Training session for sysadmin team (recorded walkthrough of NOC -> drill-down flow, common maintenance tasks) -- Medium
- [ ] 24. Define change management process -- config changes go through git PR, validate, deploy -- Simple

### 14E: Platform Evolution (future)

- [ ] 25. Kubernetes migration when NKP is ready (HA, self-healing, rolling upgrades) -- Complex
- [ ] 26. Mimir for long-term metrics retention (object storage backend) -- Complex
- [ ] 27. Lansweeper integration for automated inventory -- Medium (Phase 7D)
- [ ] 28. CI/CD pipeline for config validation on push -- Medium
- [ ] 29. Load testing at full fleet scale (1,500 agents) -- Medium

### Human Actions Required

- [ ] Provision dedicated Docker host in Denver DC
- [ ] Create Teams webhook for monitoring channel
- [ ] Configure real SMTP relay access
- [ ] Select pilot site and identify 10-20 test servers
- [ ] Create LDAP service account for Grafana
- [ ] Create AD security groups per site (SG-Monitoring-<site>)
- [ ] Identify sysadmin team leads per site for alert ownership
- [ ] Schedule training session after pilot validation
- [ ] Approve SquaredUp decommission timeline

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Alert fatigue from day one | Team rejects platform | Phase 13 alert tuning before rollout; start conservative |
| Docker host single point of failure | Monitoring goes down | auto-restart policy; external healthcheck; K8s migration later |
| Knowledge concentrated in one person | Bus factor = 1 | Documentation, recorded training, operations runbook |
| SCOM/SquaredUp decommission resistance | Parallel running costs | Prove value at pilot, decommission gradually per site |
| 1,500 agents overwhelming single Prometheus | Performance issues | Capacity planning; Mimir migration path exists |
| Sysadmins unfamiliar with Grafana/PromQL | Slow adoption | Dashboards are click-and-drill, no PromQL needed for operations |

---

## Phase 15: SCOM Data Warehouse Integration

**Goal**: Replace SquaredUp immediately by connecting Grafana to the existing SCOM Data Warehouse SQL database. No new agents required. Team sees the same SCOM-collected data in Grafana dashboards instead of SquaredUp.

**Status**: Pending

**Context**: SquaredUp costs $26K/year and reads from the SCOM Data Warehouse to render dashboards. Grafana can do exactly the same thing via the Microsoft SQL Server datasource. This eliminates SquaredUp while keeping SCOM agents and alerting intact. Alloy agent deployment (Phase 14) happens later as a separate migration.

**SCOM DW Schema Reference**:
- Performance data: `Perf.vPerfRaw` (10 days), `Perf.vPerfHourly` (400 days), `Perf.vPerfDaily` (400 days)
- Health state: `State.vStateHourly`, `State.vStateDaily`
- Alerts: `Alert.vAlert`, `Alert.vAlertDetail`
- Entity lookup: `vManagedEntity` (server names), `vPerformanceRuleInstance` (counter names)
- All timestamps UTC. Grafana handles timezone conversion.

### 15A: Datasource and Infrastructure

- [ ] 1. Create SQL Server datasource provisioning config (`configs/grafana/datasources/scom_dw.yml`) -- Simple
  - Connection to OperationsManagerDW database
  - Read-only service account with db_datareader
  - Connection string with server, port, database, auth
- [ ] 2. Add SCOM DW datasource to docker-compose.yml environment (connection string as env var) -- Simple
- [ ] 3. Create "SCOM Monitoring" dashboard provisioning folder -- Simple
- [ ] 4. Test connectivity from Grafana to SCOM DW -- Simple

### 15B: Core Dashboards (SCOM Data)

- [x] 5. SCOM Server Overview dashboard -- Medium (completed 2026-03-25)
  - Template variables: server name (from vManagedEntity), time range
  - CPU utilization (Processor / % Processor Time)
  - Memory utilization (Memory / % Committed Bytes In Use + Available MBytes)
  - Disk free space (LogicalDisk / % Free Space per drive)
  - Disk latency (LogicalDisk / Avg. Disk sec/Read, sec/Write)
  - Network throughput (Network Interface / Bytes Total/sec)
  - All queries against Perf.vPerfHourly joined with vPerformanceRuleInstance and vManagedEntity
  - Fixed variable quoting bug (LIKE -> raw equality), removed includeAll from server variable
- [x] 6. SCOM Fleet Overview dashboard -- Medium (completed 2026-03-25)
  - Top servers by CPU, memory, disk utilization
  - Server count, health state summary
  - Queries against Perf.vPerfHourly with $__timeFilter for dashboard time picker support
  - Fixed disk Free % column visibility (color-text cell type, column widths)
- [x] 7. SCOM Alert Dashboard -- Medium (completed 2026-03-25)
  - Active alerts from Alert.vAlert (ResolutionState != 255)
  - Alert history timeline
  - Alert count by severity, by server
  - Template variables for severity filter, server filter
  - All panels verified rendering correctly via Chrome review
- [x] 8. SCOM Health State dashboard -- Medium (completed 2026-03-25)
  - Current health state per server from State.vStateHourly
  - Health state changes over time
  - Servers in critical/warning state
  - Fixed summary stats to use MAX(DateTime) subquery instead of stale DATEADD filter

### 15C: Role-Specific Dashboards (SCOM Data)

- [x] 9. ~~SCOM SQL Server dashboard~~ REMOVED (2026-03-25)
  - Production discovery showed no SQL Server MP perf counters in OperationsManagerDW
  - SQL Server monitoring uses Windows OS counters only (CPU/Memory/Disk via Server Overview)
  - SQL Availability Group status visible via cluster group data
- [x] 10. SCOM IIS dashboard -- Medium (completed 2026-03-25)
  - IIS counters: current connections, requests/sec, bandwidth, 404 errors, ASP.NET request time, app restarts
  - Stat summary row + request performance + traffic + application health panels
  - Simulator seeded with 8 IIS server counter data (7 days hourly)
- [x] 11. SCOM AD/DC dashboard -- Medium (completed 2026-03-25)
  - AD counters: LDAP searches/binds, Kerberos/NTLM auth, DRA replication, DNS queries
  - Stat summary row + authentication + replication panels
  - Simulator seeded with 8 DC counter data (7 days hourly)
  - AD-specific counters from SCOM AD MP

### 15D: Migration Path

- [ ] 12. Side-by-side comparison guide -- document how SCOM dashboard data maps to Alloy dashboard data -- Simple
- [ ] 13. Decommission plan for SquaredUp -- timeline, user migration, license cancellation -- Simple

### 15E: Production Schema Alignment (added 2026-03-25 after discovery)

**Context**: Production discovery (2026-03-25) revealed schema differences from simulator. Entity type is `Microsoft.Windows.Computer` (not `.Server.Computer`). Counter names stored in separate `vPerformanceRule` table joined via `RuleRowId`. Counter ObjectNames differ from simulator assumptions. No SCOM site groups exist -- site filtering must use hostname parsing (`VM-<SITE>-*`).

- [x] 1. Fix DW query JOIN path in all dashboards -- Medium (completed 2026-03-25)
  - All 6 dashboards rebuilt with `vPerfHourly -> vPerformanceRuleInstance -> vPerformanceRule` JOIN path
- [x] 2. Fix entity type in all dashboards -- Simple (completed 2026-03-25)
  - Changed to `ManagedEntityTypeRowId = 1` (Microsoft.Windows.Computer)
- [x] 3. Fix counter name mappings in all dashboards -- Medium (completed 2026-03-25)
  - All counter references updated to production strings via `pr.ObjectName`/`pr.CounterName`
- [x] 4. Build site variable from hostname parsing -- Medium (completed 2026-03-25)
  - Site variable uses `SUBSTRING(me.DisplayName, 4, CHARINDEX('-', me.DisplayName, 4) - 4)` to extract site code
  - Added to all 6 dashboards with cascading server variable
- [x] 5. Update simulator to match production schema -- Medium (completed 2026-03-25)
  - Added `vPerformanceRule` table, 44 rules, 47 instances matching production counter names
  - 72 servers across 9 sites (VM-<SITE>-<ROLE> pattern), 284K perf rows

### 15F: Hub-and-Spoke Dashboard Architecture (added 2026-03-25)

- [ ] 6. SCOM Fleet Overview -- add site filtering and per-site breakdown -- Medium
  - `$site` variable derived from hostname
  - Per-site summary row: server count, avg CPU, avg memory per site
  - All existing panels filtered by site when selected
- [ ] 7. Role fleet dashboards (IIS Fleet, AD Fleet, DHCP Fleet) -- Complex
  - Hub view per role with site breakdown
  - Top N problem servers per role
  - Drill-down links to server detail
- [ ] 8. Server Overview -- add site context and cascading filter -- Simple
  - Show site code in header
  - Server dropdown filtered by selected site
- [ ] 9. Cross-links between hub and spoke dashboards -- Simple
  - Fleet -> Role Fleet -> Server Detail
  - Consistent URL params (`var-site`, `var-server`)

### 15G: Additional Role Dashboards (added 2026-03-25, based on production MP discovery)

- [x] 10. DHCP Server dashboard -- Medium (completed 2026-03-25)
  - Requests/sec, Acks/sec, Queue Length, Discovers/sec, Packets Received/sec
  - Stat summary + request activity + queue trends
- [x] 11. DNS Server dashboard -- Medium (completed 2026-03-25)
  - Total Query Received/sec, Recursive Queries/sec, Dynamic Updates
  - Stat summary + query volume + dynamic update trends
  - Runs on DC servers (DNS collocated with AD)
- [ ] 12. Exchange Server dashboard -- Medium (1 server + 23 services)
  - DB latency (Read/Write), Queue lengths, Messages/sec, Mailbox count/size, ActiveSync
- [ ] 13. DFS Replication dashboard -- Simple (114 servers)
  - Staging space, conflict files, bandwidth savings
- [ ] 14. UPS/Battery dashboard -- Simple (26 devices)
  - Capacity %, runtime remaining, voltage, load, temperature
- [ ] 15. SQL Cluster/AG status dashboard -- Medium
  - Availability Group membership and status across sites (from cluster group data)
  - Note: SQL Server MP perf counters NOT available in production DW -- SQL monitoring is via Windows OS counters only
- [x] 16. Remove SQL Server perf counter dashboard -- Simple (completed 2026-03-25)
  - `scom_sql_server.json` deleted -- counters don't exist in production DW

### Human Actions Required

- [x] Provide SCOM Data Warehouse SQL Server hostname, port, database name (VM-DEN-SQL11, OperationsManagerDW)
- [x] Identify which SCOM Management Packs are installed (discovery completed 2026-03-25)
- [ ] Create read-only SQL login with db_datareader on OperationsManagerDW
- [ ] Verify network path from Docker host (Denver DC) to SCOM DW SQL Server
- [ ] Confirm hostname naming convention (need to validate `VM-<SITE>-` pattern covers all servers)
- [ ] Provide SquaredUp dashboard inventory (what dashboards does the team use today?)

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| SCOM DW query performance at 1,335 servers | Slow dashboards | Use Hourly/Daily views, filter by DateTime first, avoid Raw for >24h ranges |
| Raw data only 10 days | Short history at high resolution | Use Hourly (400 days) for most dashboards, Raw only for recent drill-down |
| SCOM DW on different network segment | Connectivity failure | Verify firewall rules before deployment |
| Hostname pattern varies by site | Site extraction fails for some servers | Validate patterns from discovery, handle edge cases with fallback |
| No CI/CD pipeline | Can't update post-deploy | Validate all queries against production discovery data before deployment |
| SQL Server MP missing perf counters | No SQL-specific dashboard | Use Windows OS counters for SQL servers, build AG/cluster status from group data |

### Success Criteria

- Grafana shows the same server performance data that SquaredUp shows
- Team can find any server's CPU/memory/disk/network in Grafana
- Active SCOM alerts visible in Grafana
- Site filtering works via hostname-derived variable matching Prometheus/Loki pattern
- Hub dashboards show fleet-wide and per-site views with drill-down to detail
- SquaredUp can be decommissioned without loss of visibility
- No new agents deployed -- purely reading existing SCOM data
- Zero post-deployment query fixes needed (validated against production discovery data)

---

## Human Actions Checklist

## Human Actions Checklist

> Consolidated list of all actions requiring human intervention.

### Prerequisites

- [x] Set up Git remote
- [x] Push initial commit
- [x] Verify Git authentication (HTTPS)
- [ ] Create Teams Incoming Webhook for monitoring channel

### Fleet Deployment (Phase 5.7)

- [ ] Provide datacenter site codes with metadata (timezone, AD domain, network segment)
- [ ] Provide host inventory export (hostname, site, roles, OS type, OS build)
- [ ] Enable WinRM on target Windows servers (or OpenSSH)
- [ ] Configure SSH key access to target Linux servers
- [ ] Provide production Prometheus/Loki endpoint URLs
- [ ] Designate one Windows + one Linux test server for validation

### During Development

- [ ] Deploy Alloy to test Windows server
- [ ] Deploy Alloy to test Linux server
- [ ] Deploy Prometheus, Loki, Alertmanager, Grafana to Kubernetes cluster
- [ ] Configure persistent storage volumes
- [ ] Configure Grafana authentication (AD/LDAP)
- [ ] Test alert delivery end-to-end
- [ ] Review and approve alert thresholds
- [ ] Review dashboards with operations team

### Generalization and K8s (Phase 5.8)

- [ ] Review Helm values.yaml defaults
- [ ] Test Helm chart against real K8s cluster
- [ ] Choose a license for the repo
- [ ] Review final repo for remaining org-specific references

### SNMP Monitoring (Phase 7A)

- [ ] Provide list of network device types and models in the fleet
- [ ] Provide SNMP community strings or SNMPv3 credentials
- [ ] Identify which devices should send traps (device-side configuration)
- [ ] Verify network access from monitoring stack to device management interfaces

### Hardware/HCI Monitoring (Phase 7B)

- [ ] Create read-only BMC service accounts for monitoring on iLO and iDRAC
- [ ] Provide BMC IP addresses or DNS names for monitored servers
- [ ] Verify network access from monitoring stack to BMC management VLAN

### Certificate Monitoring (Phase 7C)

- [ ] Provide initial list of HTTPS/TLS endpoints to monitor (internal + public)
- [ ] Provide internal CA root and intermediate certificates for trust chain
- [ ] Confirm DigiCert CertCentral API access availability (if using direct API)
- [ ] Review alert thresholds (30d warning, 7d critical defaults)

### Cloud Monitoring (Phase 7E)

- [ ] Identify which cloud provider(s) are in use (when ready)
- [ ] Create IAM role or Azure service principal with read-only metrics access

### Agentless Collection (Phase 7G)

- [ ] Identify devices where agent installation is not possible
- [ ] Document reason for each (vendor restriction, embedded, access limitation)
- [ ] Provide WinRM/SSH credentials or auth method for each target
- [ ] Approve agentless scope before implementation begins

### Dashboard Hub (Phase 7H)

- [ ] Review Enterprise NOC layout with operations team
- [ ] Confirm which sites should appear in the NOC grid (all sites, or only production?)
- [ ] Provide feedback on Site Overview row ordering and priority

### Access Control and RBAC (Phase 8)

- [ ] Create AD security groups following `SG-Monitoring-<Site>` convention
- [ ] Provide list of sites needing separate dashboard visibility
- [ ] Create LDAP service account (read-only, bind access to user and group OUs)
- [ ] Provide LDAP server hostname, port, bind DN, search bases
- [ ] Identify IT team leads at each site
- [ ] Decide on stakeholder read-only access (management dashboards)
- [ ] Decide whether any sites share IT staff (impacts Team membership)
- [ ] Designate Grafana admin account ownership

### Post-Completion

- [ ] Integrate config validation into CI/CD pipeline
- [ ] Document operational runbooks
- [ ] Plan Mimir migration timeline

---

## Architecture Decisions

### Two-Tier Alloy Deployment Model (Decided 2026-03-06)

All monitoring at each site uses two distinct Alloy deployment patterns:

**Tier 1: Alloy Agent (per-server, push-based)**
- Installed on every Windows and Linux server via SCCM or Ansible
- Monitors the local server (CPU, memory, disk, services, event logs)
- Pushes metrics/logs to Prometheus/Loki via remote_write
- Config: `configs/alloy/common/` + `configs/alloy/windows/` or `configs/alloy/linux/`
- Identity: `ALLOY_DATACENTER` environment variable determines site membership

**Tier 2: Alloy Site Gateway (one container per site, pull-based)**
- Single container/pod at each site that polls all non-server infrastructure
- Handles three pull-based monitoring patterns from one deployment:
  - SNMP polling (switches, firewalls, APs, UPS, NAS) via `prometheus.exporter.snmp`
  - Certificate probing (HTTPS + TCP/TLS endpoints) via `prometheus.exporter.blackbox`
  - Hardware health (iLO, iDRAC BMC interfaces) via Redfish API exporter
- Requires management VLAN network access to reach device interfaces
- Can run on any server at the site with Docker
- Config: `configs/alloy/gateway/` (unified gateway config)
- Transitions to a K8s pod with zero config changes when NKP arrives

**Per-site deployment checklist:**
1. Install Alloy agent on servers (Tier 1) with `ALLOY_DATACENTER=site-name`
2. Deploy site gateway container (Tier 2) with target lists for that site's devices
3. Populate `targets.yml` files with site-specific device IPs, BMC addresses, cert endpoints

---

## Notes

- Alloy replaces both node_exporter/windows_exporter and Promtail in a single binary
- All configs designed to work with both Prometheus (Phase 1) and Mimir (Phase 2) via remote_write
- Teams notification via Alertmanager webhook -- no MCP or external tooling required
- Python 3.10+ required for validation scripts
- Phase 7 extends monitoring beyond agent-based OS collection to SNMP, hardware, certificates, and cloud
- Network fleet: Cisco switches, Palo Alto firewalls, Ubiquiti APs/switches
- HCI fleet: HPE SimpliVity (iLO) + Dell (iDRAC), firmware kept current
- Certificate monitoring covers both internal PKI and public DigiCert certificates
- Phase 7 execution order: 7F (done) -> 7H (done) -> 7C (done) -> 7A (done) -> 7B (done) -> 7D (dropped) -> 7E (cloud) -> 7G (agentless, blocked)
- Phase 7H (dashboard hub) ships right after 7F with server + IIS data; grows incrementally as each sub-phase adds its monitoring domain
- Kubernetes platform: Nutanix NKP (Nutanix Kubernetes Platform) in datacenter infrastructure
- Persistent storage: Nutanix CSI driver with Nutanix Volumes storage class for all PVCs (Prometheus, Loki, Grafana)
- Mimir object storage (Phase 6): Nutanix Objects (S3-compatible) is a candidate backend

---

*Document Version: 2.0*
*Last Updated: 2026-03-09*
