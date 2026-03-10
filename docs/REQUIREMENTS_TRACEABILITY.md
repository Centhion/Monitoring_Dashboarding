# Requirements Traceability Matrix

## Overview

Maps every requirement from the internal team analysis (`docs/REQUIREMENTS_RESPONSE.md`) to the specific phase, configuration file, or component that delivers it. This matrix demonstrates complete coverage of the build-vs-buy feature gap.

## Requirement Categories

### Server Monitoring (Core)

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| CPU utilization monitoring | Covered | Phase 1 | `configs/alloy/windows/base.alloy`, `configs/alloy/linux/base.alloy` |
| Memory utilization monitoring | Covered | Phase 1 | `configs/alloy/windows/base.alloy`, `configs/alloy/linux/base.alloy` |
| Disk space monitoring | Covered | Phase 1 | `configs/alloy/windows/base.alloy`, `configs/alloy/linux/base.alloy` |
| Network interface monitoring | Covered | Phase 1 | `configs/alloy/windows/base.alloy`, `configs/alloy/linux/base.alloy` |
| Windows Service status | Covered | Phase 1 | `configs/alloy/windows/base.alloy` |
| Linux systemd unit status | Covered | Phase 1 | `configs/alloy/linux/base.alloy` |
| Future forecasting (predict_linear) | Covered | Phase 9C | Windows/Linux/Infra overview dashboards (predict_linear panels) |

### Role-Specific Monitoring

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| Domain Controller (AD DS, DNS, replication) | Covered | Phase 1 | `configs/alloy/windows/role_dc.alloy` |
| SQL Server (perf counters, databases) | Covered | Phase 1 | `configs/alloy/windows/role_sql.alloy` |
| IIS Web Server (requests, app pools, logs) | Covered | Phase 1 + 7F | `configs/alloy/windows/role_iis.alloy`, `dashboards/windows/iis_overview.json` |
| File Server (SMB, DFS, disk I/O) | Covered | Phase 1 | `configs/alloy/windows/role_fileserver.alloy` |
| Docker host (containers, container logs) | Covered | Phase 1 | `configs/alloy/linux/role_docker.alloy` |

### Log Collection

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| Windows Event Log (System, Application, Security) | Covered | Phase 1 | `configs/alloy/windows/logs_eventlog.alloy` |
| Linux journal/syslog | Covered | Phase 1 | `configs/alloy/linux/logs_journal.alloy` |
| IIS W3C access logs | Covered | Phase 1 | `configs/alloy/windows/role_iis.alloy` |
| Log aggregation and search (Loki) | Covered | Phase 2 | `configs/loki/loki.yml` |

### Alerting and Notification

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| CPU/memory/disk threshold alerts | Covered | Phase 3 | `alerts/prometheus/windows_alerts.yml`, `alerts/prometheus/linux_alerts.yml` |
| Service/process down alerts | Covered | Phase 3 | `alerts/prometheus/role_alerts.yml` |
| Microsoft Teams notifications | Covered | Phase 3 | `configs/alertmanager/alertmanager.yml`, `configs/alertmanager/templates/teams.tmpl` |
| Email notifications (per-site routing) | Covered | Phase 3.1 | `configs/alertmanager/alertmanager.yml` |
| Alert severity levels (critical, warning, info) | Covered | Phase 3 | All alert rule files |
| Alert deduplication (mass-outage suppression) | Covered | Phase 9D | `configs/prometheus/outage_recording_rules.yml`, `alerts/prometheus/outage_alerts.yml` |
| Maintenance windows (scheduled silences) | Covered | Phase 9E | `scripts/maintenance_window.py`, `configs/grafana/notifiers/notifiers.yml` |
| Maintenance windows (recurring mute timings) | Covered | Phase 9E | `configs/grafana/notifiers/notifiers.yml` |

### Dashboarding

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| Windows server overview dashboard | Covered | Phase 4 | `dashboards/windows/windows_overview.json` |
| Linux server overview dashboard | Covered | Phase 4 | `dashboards/linux/linux_overview.json` |
| Infrastructure overview (fleet health) | Covered | Phase 4 | `dashboards/overview/infrastructure_overview.json` |
| Log explorer dashboard | Covered | Phase 4 | `dashboards/overview/log_explorer.json` |
| Enterprise NOC (multi-site) | Covered | Phase 7H | `dashboards/overview/enterprise_noc.json` |
| Per-site drill-down | Covered | Phase 7H | `dashboards/overview/site_overview.json` |
| IIS dedicated dashboard | Covered | Phase 7F | `dashboards/windows/iis_overview.json` |
| Network infrastructure dashboard | Covered | Phase 7A | `dashboards/network/network_overview.json` |
| Hardware health dashboard | Covered | Phase 7B | `dashboards/hardware/hardware_overview.json` |
| Certificate monitoring dashboard | Covered | Phase 7C | `dashboards/certs/certificate_overview.json` |
| SLA availability dashboard | Covered | Phase 9C | `dashboards/overview/sla_availability.json` |
| Probing overview dashboard | Covered | Phase 9C | `dashboards/overview/probing_overview.json` |
| Audit trail dashboard | Covered | Phase 9G | `dashboards/overview/audit_trail.json` |

### Agentless / Synthetic Monitoring

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| ICMP ping probes | Covered | Phase 9A | `configs/alloy/certs/blackbox_modules.yml` (icmp_check module) |
| TCP port probes | Covered | Phase 9A | `configs/alloy/certs/blackbox_modules.yml` (tcp_check module) |
| UDP/DNS probes | Covered | Phase 9A | `configs/alloy/certs/blackbox_modules.yml` (udp_dns_check module) |
| HTTP/HTTPS synthetic probes | Covered | Phase 9A | `configs/alloy/certs/blackbox_modules.yml` (http_synthetic module) |
| Probe failure alerts | Covered | Phase 9A | `alerts/prometheus/probe_alerts.yml` |
| Probe recording rules (success rate, latency) | Covered | Phase 9A | `configs/prometheus/probe_recording_rules.yml` |

### File and Process Monitoring

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| File/folder size monitoring (Windows) | Covered | Phase 9B | `configs/alloy/windows/role_file_size.alloy` |
| File/folder size monitoring (Linux) | Covered | Phase 9B | `configs/alloy/linux/role_file_size.alloy` |
| Process monitoring (Windows) | Covered | Phase 9B | `configs/alloy/windows/role_process.alloy` |
| Process monitoring (Linux) | Covered | Phase 9B | `configs/alloy/linux/role_process.alloy` |
| File size / process alerts | Covered | Phase 9B | `alerts/prometheus/endpoint_alerts.yml` |

### SLA and Availability Reporting

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| Per-host availability (hourly/daily/weekly/monthly) | Covered | Phase 9C | `configs/prometheus/sla_recording_rules.yml` |
| Per-role availability aggregation | Covered | Phase 9C | `configs/prometheus/sla_recording_rules.yml` |
| Per-site availability aggregation | Covered | Phase 9C | `configs/prometheus/sla_recording_rules.yml` |
| SLA threshold indicators (99.9%, 99.5%, 99.0%) | Covered | Phase 9C | `dashboards/overview/sla_availability.json` |
| Downtime minutes calculation | Covered | Phase 9C | `configs/prometheus/sla_recording_rules.yml` |

### Network Device Monitoring

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| SNMP polling (switches, firewalls, APs, UPS) | Covered | Phase 7A | `configs/alloy/gateway/site_gateway.alloy` |
| Interface utilization and errors | Covered | Phase 7A | `configs/prometheus/snmp_recording_rules.yml` |
| Device unreachable / reboot alerts | Covered | Phase 7A | `alerts/prometheus/snmp_alerts.yml` |
| SNMP trap ingestion | Covered | Phase 9F | `configs/snmptrapd/snmptrapd.conf`, `configs/alloy/gateway/role_snmp_traps.alloy` |
| Trap-based alerts (linkDown, authFailure) | Covered | Phase 9F | `alerts/grafana/snmp_trap_alerts.yml` |

### Hardware Health Monitoring

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| Redfish BMC monitoring (iLO, iDRAC) | Covered | Phase 7B | `configs/alloy/gateway/site_gateway.alloy` |
| Chassis temperature and power monitoring | Covered | Phase 7B | `configs/prometheus/hardware_recording_rules.yml` |
| Hardware health alerts | Covered | Phase 7B | `alerts/prometheus/hardware_alerts.yml` |

### Certificate Monitoring

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| SSL/TLS certificate expiry tracking | Covered | Phase 7C | `configs/alloy/roles/role_cert_monitor.alloy` |
| Certificate expiry alerts (30d, 7d, expired) | Covered | Phase 7C | `alerts/prometheus/cert_alerts.yml` |
| Internal PKI and public cert support | Covered | Phase 7C | `configs/alloy/certs/blackbox_modules.yml` |

### Audit and Compliance

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| Login/logout event tracking | Covered (Tier 1) | Phase 9G | `configs/alloy/roles/role_grafana_audit.alloy` |
| Dashboard CRUD tracking | Covered (Tier 2 partial) | Phase 9G | `configs/alloy/roles/role_grafana_audit.alloy` |
| Alert rule change tracking | Covered (Tier 2 partial) | Phase 9G | `configs/alloy/roles/role_grafana_audit.alloy` |
| Detailed change diffs | Not covered | Requires Grafana Enterprise | -- |
| Compliance-grade audit trail | Not covered | Requires Grafana Enterprise + SIEM | -- |

### Access Control

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| Folder-based RBAC | Pending | Phase 8 | `configs/grafana/provisioning/` (planned) |
| LDAP/AD group synchronization | Pending | Phase 8 | `configs/grafana/ldap.toml` (planned) |
| Per-site dashboard isolation | Pending | Phase 8 | Requires Phase 8 implementation |

### Deployment and Operations

| Requirement | Status | Delivered By | Files |
|------------|--------|-------------|-------|
| Docker Compose local testing | Covered | Phase 5.5 | `deploy/docker/docker-compose.yml` |
| Helm chart for Kubernetes | Covered | Phase 5.8 | `deploy/helm/monitoring-stack/` |
| Configuration validation | Covered | Phase 5 | `scripts/validate_all.py` |
| Fleet deployment tooling | Pending | Phase 5.7 | `ansible/` (planned) |
| Cloud monitoring (AWS/Azure) | Stub | Phase 7E | `configs/alloy/cloud/*.alloy.example` |

## Coverage Summary

| Category | Requirements | Covered | Pending | Not Covered |
|----------|-------------|---------|---------|-------------|
| Server Monitoring | 7 | 7 | 0 | 0 |
| Role-Specific | 5 | 5 | 0 | 0 |
| Log Collection | 4 | 4 | 0 | 0 |
| Alerting | 8 | 8 | 0 | 0 |
| Dashboarding | 13 | 13 | 0 | 0 |
| Synthetic Monitoring | 6 | 6 | 0 | 0 |
| File/Process Monitoring | 5 | 5 | 0 | 0 |
| SLA/Availability | 5 | 5 | 0 | 0 |
| Network Devices | 5 | 5 | 0 | 0 |
| Hardware Health | 3 | 3 | 0 | 0 |
| Certificate Monitoring | 3 | 3 | 0 | 0 |
| Audit/Compliance | 5 | 3 | 0 | 2 |
| Access Control | 3 | 0 | 3 | 0 |
| Deployment/Operations | 5 | 3 | 2 | 0 |
| **Total** | **77** | **70** | **5** | **2** |

**Coverage**: 91% of requirements are delivered. 6% are pending implementation (Phase 8 RBAC, Phase 5.7 fleet tooling). 3% require Grafana Enterprise (full audit diffs, compliance-grade trail).
