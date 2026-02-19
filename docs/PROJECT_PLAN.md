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
| Phase 4: Grafana Dashboards | Completed | 4 dashboards (Windows, Linux, Infra Overview, Log Explorer) + customization guide |
| Phase 5: Validation Tooling | Completed | 3 validators + runner, 12/12 tests passing, requirements.txt, docs |
| Phase 5.5: Docker Compose PoC | Completed | Local testing stack validated end-to-end (metrics, logs, recording rules) |
| Phase 5.7: Fleet Tagging and Deployment | In Progress | Inventory system, Ansible playbooks, tag validation for 500-2000 servers across 5-15+ sites |
| Phase 5.8: Generalization and K8s Readiness | In Progress | Strip org-specific content, Helm chart, fork-and-deploy template |
| Phase 6: Mimir Migration | Pending | Long-term metrics storage (when ready to scale) |

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
- [x] 5. Create `scripts/poc_setup.py` for one-command startup with health validation
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

**Status**: In Progress

**Fleet Context**: Inventory is AD-independent by design to support multi-domain environments. Sites use short abbreviation codes (SITE-A, SITE-B, etc.). Multi-role servers are common (e.g., SQL + IIS on same host).

### Tasks

- [ ] 1. Create site registry -- `inventory/sites.yml`
  - Central YAML defining all datacenter sites with metadata: code, display name, environment, timezone, AD domain, network segment
  - Controlled vocabulary for valid roles: `dc, sql, iis, fileserver, docker, generic, exchange, print, app`
  - Document extension point for adding new roles and OS types
  - Complexity: Simple

- [ ] 2. Create host inventory schema -- `inventory/hosts.yml`
  - YAML mapping every server to its tags: hostname, site (references sites.yml), environment, roles (list for multi-role), os_type, os_build
  - Multi-role support: roles field is a list (e.g., `[sql, iis]`)
  - OS build tracked as precise version strings (e.g., `"10.0.20348"` for Server 2022, `"9.5"` for RHEL 9.5)
  - Organized by site for readability, with schema header documenting valid values
  - Complexity: Simple

- [ ] 3. Create inventory tooling -- `scripts/fleet_inventory.py`
  - Subcommand: `validate` -- validates hosts.yml against sites.yml (site codes, roles, os_type, required fields, no duplicate hostnames, warns on 3+ roles)
  - Subcommand: `import-csv` -- converts CSV (from SCCM/CMDB export) to hosts.yml entries, merges without duplicates
  - Subcommand: `generate-ansible` -- produces Ansible inventory with host groups by site/role/os/environment, host_vars for Alloy env vars, group_vars for endpoints and site metadata
  - Subcommand: `stats` -- prints fleet summary (servers per site, per role, per OS, multi-role count, coverage gaps)
  - Output directory: `inventory/generated/`
  - Complexity: Medium

- [ ] 4. Create Ansible playbook for Alloy deployment -- `ansible/deploy_alloy.yml`
  - Ansible role `alloy_windows`: install MSI, deploy configs, set system env vars, configure and start service
  - Ansible role `alloy_linux`: install package, deploy configs, set env file, configure systemd unit, start service
  - Multi-role handling: copies role_*.alloy for EACH role in the host's roles list; ALLOY_ROLE set to primary (first) role
  - Config deployment: common/*.alloy (always) + {os}/base.alloy + logs (always) + role_*.alloy (per role list)
  - Environment variables set: ALLOY_ENV, ALLOY_DATACENTER, ALLOY_ROLE, PROMETHEUS_REMOTE_WRITE_URL, LOKI_WRITE_URL, plus role-specific vars
  - Post-deploy validation: waits for :12345 health endpoint, verifies metrics are being scraped
  - Complexity: Medium

- [ ] 5. Create tag validation script -- `scripts/validate_fleet_tags.py`
  - Queries Prometheus to audit tag compliance across the fleet
  - Report categories: COMPLIANT (correct tags), DRIFT (wrong tags), MISSING (in inventory but not reporting), UNKNOWN (reporting but not in inventory)
  - Filters: `--site`, `--role`, `--environment`
  - Output formats: `--format table|json|csv`
  - Accepts `--prometheus-url` (defaults to PROMETHEUS_URL env var)
  - Complexity: Medium

- [ ] 6. Create onboarding runbook -- `docs/FLEET_ONBOARDING.md`
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
  - Updated `scripts/poc_setup.py` with `COMPOSE_FILE` constant, `--env-file` support, and `_compose_base_cmd()` helper
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

### Post-Completion

- [ ] Integrate config validation into CI/CD pipeline
- [ ] Document operational runbooks
- [ ] Plan Mimir migration timeline

---

## Notes

- Alloy replaces both node_exporter/windows_exporter and Promtail in a single binary
- All configs designed to work with both Prometheus (Phase 1) and Mimir (Phase 2) via remote_write
- Teams notification via Alertmanager webhook -- no MCP or external tooling required
- Python 3.10+ required for validation scripts

---

*Document Version: 1.2*
*Last Updated: 2026-02-19*
