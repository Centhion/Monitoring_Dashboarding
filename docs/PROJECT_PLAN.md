# Project Plan

> This file is the agent's primary task tracker. Update it after completing significant work.

**Project Goal**: Build an enterprise-grade monitoring and dashboarding platform using the Grafana observability stack (Alloy, Prometheus, Loki, Alertmanager, Grafana) to replace Microsoft SCOM and Squared Up for mixed Windows/Linux server environments.

---

## Project Status Summary

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0: Project Setup | Completed | Template hydration and repo configuration |
| Phase 1: Alloy Agent Configs | Completed | 13 configs: common (3), Windows base+4 roles (6), Linux base+docker (3), deployment guide (1) |
| Phase 2: Backend Configs (Prometheus + Loki) | Pending | Server-side metric and log storage configs |
| Phase 3: Alerting Rules and Routing | Pending | SCOM parity alerts, Alertmanager routing, Teams integration |
| Phase 4: Grafana Dashboards | Pending | Dashboard JSON definitions and provisioning |
| Phase 5: Validation Tooling | Pending | Python scripts for config linting and testing |
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

- [x] Set up Git remote (https://github.com/Centhion/Monitoring_Dashboarding.git)
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

**Goal**: Configure Prometheus and Loki server-side settings including retention, storage, and recording rules.

**Status**: Pending

### Tasks

- [ ] Create Prometheus server configuration (scrape configs, retention, storage)
- [ ] Create Prometheus recording rules for common aggregations
- [ ] Create Loki server configuration (storage, retention, limits)
- [ ] Define log parsing pipelines in Loki (structured metadata extraction)
- [ ] Document backend deployment requirements

### Human Actions Required

- [ ] Deploy Prometheus to Kubernetes cluster
- [ ] Deploy Loki to Kubernetes cluster
- [ ] Configure persistent storage volumes
- [ ] Verify data ingestion from Alloy agents

---

## Phase 3: Alerting Rules and Routing

**Goal**: Build alert rules that achieve parity with critical SCOM monitors, configure Alertmanager routing, and integrate Teams notifications.

**Status**: Pending

### Tasks

- [ ] Audit existing SCOM monitors and identify critical alerts to replicate
- [ ] Create Prometheus alerting rules for Windows servers (CPU, memory, disk, services)
- [ ] Create Prometheus alerting rules for Linux servers (CPU, memory, disk, systemd)
- [ ] Create Prometheus alerting rules for infrastructure (connectivity, DNS, NTP)
- [ ] Configure Alertmanager routing tree (severity-based routing)
- [ ] Configure Alertmanager receivers (Teams webhook, email fallback)
- [ ] Configure alert grouping and inhibition rules
- [ ] Create Grafana contact points and notification policies
- [ ] Document alert runbooks for each critical alert

### Human Actions Required

- [ ] Create Teams Incoming Webhook in monitoring channel
- [ ] Provide SCOM monitor export/list for audit
- [ ] Deploy Alertmanager to Kubernetes cluster
- [ ] Test alert delivery to Teams channel
- [ ] Review and approve alert thresholds

---

## Phase 4: Grafana Dashboards

**Goal**: Create comprehensive Grafana dashboards for Windows Server, Linux Server, and infrastructure overview.

**Status**: Pending

### Tasks

- [ ] Create Grafana datasource provisioning YAML (Prometheus + Loki)
- [ ] Create dashboard provisioning YAML (point to dashboards/ directory)
- [ ] Build Windows Server overview dashboard (CPU, memory, disk, network, services)
- [ ] Build Linux Server overview dashboard (CPU, memory, disk, network, systemd)
- [ ] Build Infrastructure Overview dashboard (fleet health, top-N, alert summary)
- [ ] Build Log Explorer dashboard (integrated log search with metric correlation)
- [ ] Create dashboard variables (environment, datacenter, hostname filters)
- [ ] Document dashboard customization guide

### Human Actions Required

- [ ] Deploy Grafana to Kubernetes cluster
- [ ] Configure Grafana authentication (AD/LDAP integration)
- [ ] Review dashboards with operations team
- [ ] Provide feedback on layout and metric selection

---

## Phase 5: Validation Tooling

**Goal**: Build Python scripts to validate configurations, lint dashboards, and test alert rules before deployment.

**Status**: Pending

### Tasks

- [ ] Create config validator for Alloy configs (syntax + required fields)
- [ ] Create config validator for Prometheus rules (promtool integration)
- [ ] Create dashboard JSON schema validator
- [ ] Create alert rule coverage checker (compare against SCOM monitor list)
- [ ] Set up test fixtures and expected outputs
- [ ] Document tooling usage

### Human Actions Required

- [ ] Integrate validation into CI/CD pipeline

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

- [x] Set up Git remote (https://github.com/Centhion/Monitoring_Dashboarding.git)
- [x] Push initial commit
- [x] Verify Git authentication (HTTPS)
- [ ] Create Teams Incoming Webhook for monitoring channel
- [ ] Provide SCOM monitor export/list for alert parity audit

### During Development

- [ ] Deploy Alloy to test Windows server
- [ ] Deploy Alloy to test Linux server
- [ ] Deploy Prometheus, Loki, Alertmanager, Grafana to Kubernetes cluster
- [ ] Configure persistent storage volumes
- [ ] Configure Grafana authentication (AD/LDAP)
- [ ] Test alert delivery end-to-end
- [ ] Review and approve alert thresholds
- [ ] Review dashboards with operations team

### Post-Completion

- [ ] Integrate config validation into CI/CD pipeline
- [ ] Document operational runbooks
- [ ] Plan Mimir migration timeline
- [ ] Decommission SCOM/Squared Up (when ready)

---

## Notes

- Alloy replaces both node_exporter/windows_exporter and Promtail in a single binary
- All configs designed to work with both Prometheus (Phase 1) and Mimir (Phase 2) via remote_write
- Teams notification via Alertmanager webhook -- no MCP or external tooling required
- Python 3.10+ required for validation scripts

---

*Document Version: 1.0*
*Last Updated: 2026-02-18*
