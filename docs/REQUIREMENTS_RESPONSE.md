# Monitoring Platform Requirements -- Team Review Response

> **Purpose**: Annotated response to the team's monitoring platform requirements list.
> Contains position statements, clarifying questions, gap analysis against our current
> PoC, and a strategy for closing remaining gaps without vendor licensing.
>
> **Status**: Draft for team review. Requirements list is not yet locked.
>
> **Date**: 2026-03-09

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Build vs Buy Context](#build-vs-buy-context)
3. [Gap Closure Strategy](#gap-closure-strategy)
4. [Requirements Response -- Monitoring](#requirements-response----monitoring)
5. [Requirements Response -- Alerting](#requirements-response----alerting)
6. [Requirements Response -- Reporting](#requirements-response----reporting)
7. [Requirements Response -- Architecture](#requirements-response----architecture)
8. [Requirements Response -- AAA](#requirements-response----aaa)
9. [Requirements Response -- Integrations](#requirements-response----integrations)
10. [Open Questions for Team Decision](#open-questions-for-team-decision)

---

## Executive Summary

Our internal Grafana observability stack (Alloy, Prometheus, Loki, Alertmanager, Grafana)
currently covers approximately 80-85% of the requirements list. The remaining gaps fall
into two categories:

**Gaps with practical internal alternatives** (can be closed with targeted engineering):
- Synthetic service testing (blackbox HTTP probes)
- File and folder size monitoring (Alloy textfile collector)
- Program/process monitoring (process exporter)
- SNMP trap ingestion (trap-to-Loki pipeline)
- Recurring maintenance windows (Grafana mute timings or cron-based API silences)
- Alert deduplication (enhanced inhibition rules + mass-outage recording rules)
- Basic audit logging (Grafana server logs forwarded to Loki)
- Disk capacity forecasting (PromQL predict_linear panels)

**Gaps requiring business decisions before engineering**:
- Cloud integrations (Azure/AWS) -- depends on cloud adoption timeline
- ESXi/Nutanix/SimpliVity scope -- team must clarify hardware-only vs hypervisor-layer
- Audit logging granularity -- team must define acceptable fidelity level
- WAN-down resilience model -- team must decide per-site infrastructure footprint
- LogicMonitor overlap -- existing licensing should be investigated before committing

The estimated cost to close the engineering gaps internally is measured in weeks of
configuration work, not months of development. The alternative -- expanding vendor
licensing across 500-2000 endpoints -- carries a recurring annual cost that is difficult
to justify for the incremental feature delta.

---

## Build vs Buy Context

### Existing Vendor Footprint

Two commercial monitoring platforms already exist in the organization:

1. **LogicMonitor** -- Currently used for SQL Server monitoring. Licensing model,
   device count, and contract ownership are unknown. This is an open investigation
   item (see Open Questions).

2. **Datadog** -- Currently used by data/development teams. Strong for APM, cloud
   infrastructure, and log analytics. Less suited for traditional infrastructure
   monitoring (SNMP, hardware health, Windows services) which is our primary scope.

### Cost Comparison Framework

| Factor | Internal Grafana Stack | Vendor Expansion (LogicMonitor or equivalent) |
|--------|----------------------|----------------------------------------------|
| Licensing cost | Zero (all OSS components) | $15-45/host/month. At 1000 hosts: $180K-540K/year |
| Infrastructure cost | Nutanix NKP cluster resources (already provisioned) | Varies by deployment model (SaaS vs on-prem) |
| Engineering effort (remaining) | 4-6 weeks of configuration work to close gaps | Vendor onboarding, migration, custom integration |
| Ongoing maintenance | Internal team manages configs, upgrades, dashboards | Vendor handles platform; team manages config |
| Customization depth | Full control (every config, dashboard, alert, label) | Constrained by vendor UI/API; custom metrics cost extra |
| Data sovereignty | All data on our Nutanix infrastructure | SaaS sends telemetry to vendor cloud |
| Kubernetes deployment | Helm chart on Nutanix NKP (already built) | Vendor agent compatibility with NKP unverified |

### Recommendation

Investigate LogicMonitor's current licensing before making a final decision. If LM
has capacity in its contract and covers infrastructure monitoring (not just SQL), it
may be worth evaluating as a complement or alternative. If LM licensing scales
per-device, the cost argument favors the internal build.

Datadog is not a candidate for this workload. Its strengths (APM, cloud-native, dev
tooling) do not overlap with our primary requirements (SNMP, Windows services,
hardware health, on-prem infrastructure). Consolidating onto Datadog would require
forcing a cloud-first tool onto an on-prem infrastructure problem.

---

## Gap Closure Strategy

The following table maps each gap from the requirements list to a practical internal
alternative. These alternatives trade some polish for zero licensing cost and full
control. The goal is to reach the same operational outcomes through different means.

| Gap | Vendor Approach | Internal Alternative | Effort | Trade-off |
|-----|----------------|---------------------|--------|-----------|
| Topology-aware alert dedup | Auto-discovered dependency maps (LogicMonitor Service Insights, Dynatrace Smartscape) | Alertmanager inhibition rules with `upstream_device` label + recording rule for mass-outage detection (>X% of site hosts down triggers SitePartialOutage alert) | 1-2 days config + ongoing label maintenance | Requires `upstream_device` labels in inventory. Less automatic than vendor topology discovery. Inventory system (Phase 5.7) can generate the mappings. |
| Recurring maintenance windows | Built-in calendar UI with recurring schedules | Grafana Alerting mute timings (OSS, supports recurring time ranges) OR Python cron script that creates/removes Alertmanager silences via API | 1-2 days | Mute timings are per-alert-rule, not per-host. Cron approach is per-host but requires a small script. |
| SLA calculation and reporting | Built-in SLA dashboards | Recording rules tracking `avg_over_time(up[1d])` per host/service + dedicated SLA dashboard with availability percentages | 2-3 days | No automatic business-hours-only calculation without custom logic. Functional but less polished than vendor reports. |
| Full audit logging | Built-in structured audit trail | Grafana server logs (info level) forwarded to Loki via Alloy. Build Loki query dashboard showing who-changed-what. | 1-2 days | Shows user + action + timestamp but not change diffs. For diffs, Grafana Enterprise required or use dashboard-as-code with git history. |
| ML-based forecasting | Anomaly detection (Datadog, Dynatrace) | PromQL `predict_linear()` panels for disk capacity and resource trending. Covers the "when will this disk fill up" use case. | 0.5 days | Linear extrapolation only, not true anomaly detection. Adequate for capacity planning. |
| Automated remediation | LogicMonitor actions, vendor webhook frameworks | Alertmanager webhook receiver pointing to a lightweight Python handler. Handler executes predefined scripts (restart service, clear temp, etc.) based on alert labels. | 3-5 days for framework | Requires building and maintaining the handler. Limited to predefined actions. |
| Synthetic service testing | Built-in HTTP/HTTPS monitors | Blackbox exporter HTTP probe targets (already deployed for cert monitoring). Add HTTP probe modules for critical service endpoints. | 0.5-1 day per endpoint set | No multi-step transaction testing (login flows). Covers "is this URL returning 200" which handles 90% of synthetic monitoring needs. |
| SNMP trap ingestion | Built-in trap receiver + correlation | snmptrapd receiving traps, formatting to syslog, forwarding to Loki via Alloy. Query traps in Log Explorer dashboard. | 2-3 days | Traps land in Loki as log entries, not as metric events. Alerting on traps requires Loki alerting rules rather than Prometheus rules. |

**Total estimated effort to close all gaps**: 2-3 weeks of focused configuration work.

**Total estimated annual vendor cost for equivalent coverage**: $180K-540K/year at scale.

---

## Requirements Response -- Monitoring

### Agentless / Stimulus Response Status Monitoring

**Requirement**: ICMP, TCP / UDP probing for up/down status.

**Status**: PARTIAL -- TCP probing exists (blackbox exporter for certificate monitoring).
ICMP and UDP probes not configured.

**Response**: Achievable with existing infrastructure. The blackbox exporter already runs
in our site gateway tier. Adding ICMP and UDP probe modules is configuration work, not
new architecture. We need the team to provide a target list (which endpoints need
agentless probing vs agent-based monitoring).

**Action**: Add ICMP/UDP probe modules to gateway config. Team provides target inventory.

---

### Synthetic Service Testing

**Requirement**: Verify services are functional beyond simple up/down.

**Status**: GAP -- No HTTP endpoint health checks configured.

**Response**: The blackbox exporter supports HTTP/HTTPS probes with response code
validation, response body matching, and latency measurement. This covers "is this web
application responding correctly" without needing a full synthetic monitoring product.
Multi-step transaction testing (e.g., "log in, navigate to page, submit form") is out
of scope for this approach and would require a dedicated tool (Grafana Synthetic
Monitoring or similar).

**Action**: Define critical service endpoints that need synthetic checks. Configure
HTTP probe targets in the gateway.

**Clarifying question for team**: Is "URL returns HTTP 200 with expected content"
sufficient for synthetic testing, or do we need multi-step transaction flows?

---

### Resource Utilization (CPU, Memory, Disk)

**Requirement**: CPU, Memory, Disk utilization monitoring including file/folder size.

**Status**: CPU/Memory/Disk COVERED. File and folder size is a GAP.

**Response**: Core resource metrics are fully implemented with warning and critical
thresholds on both Windows and Linux. File and folder size monitoring can be added
via Alloy's Windows `textfile` collector with a scheduled PowerShell script that
writes size metrics, or via a custom Alloy component. Requires the team to define
which paths matter.

**Action**: Team provides list of critical file/folder paths to monitor. Add collection
config to Alloy base or as a dedicated role.

---

### Event Monitoring

**Requirement**: Event monitoring (noted as requiring significant investment).

**Status**: COVERED for standard event sources.

**Response**: Windows Event Log (System, Application, Security channels) and Linux
systemd journal are collected into Loki. The Log Explorer dashboard provides search
and filtering. Extending to additional Windows Event Log channels (e.g., DNS Server,
Directory Service, custom application logs) is a configuration change per channel.
The "lots of work" note in the requirement likely refers to building meaningful
alerting rules on event patterns, which is an ongoing operational investment regardless
of platform.

---

### Log Monitoring

**Requirement**: Centralized log collection and search.

**Status**: COVERED.

**Response**: Loki pipeline fully operational. Windows Event Log, Linux journal, IIS
access logs, and SQL Server error logs all flow to Loki with 30-day retention. Log
Explorer dashboard provides unified search across all sources. Additional log sources
(application-specific log files) can be added via Alloy file tail configurations.

---

### Agent -- OS Support

**Requirement**: Windows, Ubuntu, Rocky, RHEL support.

**Status**: Windows and Ubuntu COVERED. Rocky and RHEL PARTIAL.

**Response**: Grafana Alloy has official packages for RHEL/Rocky (RPM). Our Linux
configurations use standard `node_exporter` and `systemd` integrations which are
distribution-agnostic. Rocky and RHEL should work without modification but need
explicit validation during fleet deployment (Phase 5.7).

**Action**: Include a Rocky/RHEL test server in the initial deployment wave to confirm.

---

### Agent -- Hypervisor Integrations

**Requirement (WANT)**: Nutanix integrations, ESXi integrations, SimpliVity.

**Status**: PARTIAL -- Hardware health covered by Redfish. Hypervisor-layer telemetry
not implemented.

**Response**: Redfish monitoring (Phase 7B) covers the physical server health layer
for any host with an iLO or iDRAC BMC. This includes ESXi hosts, Nutanix nodes, and
SimpliVity nodes at the hardware level (temperature, fans, power supplies, drives,
memory).

What Redfish does NOT cover is the hypervisor/platform layer:
- ESXi: VM inventory, vMotion events, datastore utilization, HA cluster status
- Nutanix: Storage pool capacity, dedup/compression ratios, Prism cluster health
- SimpliVity: Backup status, dedup ratios, federation health

**Clarifying question for team**: Does "Nutanix/ESXi/SimpliVity integration" mean
hardware health monitoring (covered by Redfish) or hypervisor-layer visibility
(requires per-platform API exporters)? If hardware health is sufficient, these items
can be marked as covered. If hypervisor telemetry is needed, these remain as future
integration work with platform-specific exporters.

---

### Agent -- Docker and Kubernetes

**Requirement (WANT)**: Docker and k8s integrations.

**Status**: Docker COVERED. Kubernetes PARTIAL.

**Response**: Docker role config exists with container metrics and log collection.
Kubernetes monitoring (cAdvisor, kube-state-metrics) is not configured but is a
natural extension since the stack itself deploys on Nutanix NKP. This becomes
relevant when the team wants to monitor the Kubernetes cluster hosting the
monitoring stack and other workloads.

---

### Service / Daemon Status and Deeper Integrations

**Requirement**: Service status monitoring with deeper integrations for IIS, MSSQL,
ADDS, DNS.

**Status**: ALL COVERED.

**Response**:
- Windows service monitoring: base Alloy config with alerts for critical services
- Linux systemd unit monitoring: base Alloy config with failed unit alerts
- IIS: Dedicated role config, 3 alert rules, recording rules, dedicated dashboard
- MSSQL: Dedicated role config, 4 alert rules (buffer cache, page life, deadlocks)
- ADDS (want): Covered by Domain Controller role (AD DS replication, LDAP, Kerberos)
- DNS (want): Covered by Domain Controller role (DNS query failure rate alerts)

No additional work required.

---

### Program Status (running, not running)

**Requirement**: Monitor whether specific programs are running.

**Status**: GAP -- Service monitoring covers daemons/services but not arbitrary
executables.

**Response**: Windows services and Linux systemd units are monitored. For non-service
processes (e.g., a scheduled task executable, a legacy application that runs as a
desktop process), we need process-level monitoring. Alloy can integrate with
`windows_exporter` process collector or `process_exporter` on Linux to track specific
process names.

**Clarifying question for team**: What non-service processes need monitoring? This
determines whether we add process collection globally or as a targeted role config.

---

### WinRM and SSH

**Requirement**: Agentless remote collection via WinRM and SSH.

**Status**: GAP (Phase 7G, blocked pending use case review).

**Response**: The agent-based model (Alloy installed on every server) is the primary
collection method. WinRM/SSH collection is a fallback for servers where agent
installation is not feasible (appliances, embedded systems, legacy servers that
cannot run Alloy). Alloy supports remote WMI/WinRM and SSH-based collection but
we have not configured it because the use cases have not been defined.

**Clarifying question for team**: Which servers cannot run the Alloy agent? That
list defines the scope of WinRM/SSH collection. If every server gets an agent, this
requirement may be unnecessary.

---

### SNMP

**Requirement**: SNMP polling, trap ingestion, custom OIDs.

**Status**: Polling COVERED. Traps GAP. Custom OIDs PARTIAL (want).

**Response**:
- SNMP polling: Fully implemented via site gateway (Phase 7A). Cisco, Palo Alto,
  Ubiquiti, APC device templates with recording rules, alerts, and dashboard.
- SNMP trap ingestion: Not implemented. Requires a trap receiver (snmptrapd)
  forwarding to Loki. Traps would appear as log entries, queryable in Log Explorer
  and alertable via Loki alerting rules. This is a different data flow than polled
  metrics but achieves the same outcome (visibility into device-initiated events).
- Custom OIDs (want): The SNMP target template structure supports custom OID
  definitions. No custom OIDs are configured because none have been requested.

**Action**: Team identifies which devices send traps and what trap types matter.
Trap pipeline is 2-3 days of configuration work.

---

### API-based iLO and iDRAC Integrations

**Requirement (WANT)**: Hardware management controller monitoring via API.

**Status**: COVERED via Redfish (Phase 7B).

**Response**: Redfish health monitoring is implemented with gateway config, recording
rules, 8 alert rules, and a dedicated hardware dashboard. Covers BMC reachability,
overall health status, temperature, power, drive health, and memory health for both
HPE iLO and Dell iDRAC controllers. Final exporter selection (community Redfish
exporter vs vendor-specific alternatives) needs evaluation during production deployment.

---

### Certificate Monitoring

**Requirement**: TCP-based (need) and agent-based (want) certificate monitoring.

**Status**: TCP-based COVERED. Agent-based GAP.

**Response**:
- TCP-based: Fully implemented (Phase 7C). Blackbox exporter probes TLS endpoints
  with 90/30/7-day expiry alerts and a certificate inventory dashboard.
- Agent-based (want): On-host certificate file discovery (scanning local certificate
  stores or filesystem paths) is not implemented. Would require an Alloy component
  or custom script that inventories local cert files and exposes expiry as a metric.

**Action for TCP-based**: Team provides the list of internal and public TLS endpoints
to monitor.

---

### Public Cloud Integrations

**Requirement**: Azure and AWS monitoring.

**Status**: GAP (Phase 7E, pending).

**Response**: Not started. Stub configs planned. Prometheus has official exporters for
both CloudWatch (AWS) and Azure Monitor. Implementation depends on cloud adoption
timeline and what workloads exist in each cloud. This is deferred until cloud
infrastructure is in scope.

**Note**: If Datadog is already monitoring cloud workloads for the data/dev teams,
there may be no need to duplicate that coverage in this stack. The boundary should
be clear: this stack monitors on-prem infrastructure; Datadog monitors cloud-native
workloads. Overlap creates confusion, not redundancy.

**Clarifying question for team**: What cloud workloads (if any) are not already
covered by Datadog? That defines the scope of Phase 7E.

---

### Hardware Monitoring (SNMP, API)

**Requirement**: Power supply status, fan status, CPU temperature.

**Status**: COVERED.

**Response**: All three are implemented via Redfish (Phase 7B) with alert thresholds
and dashboard panels. SNMP-based hardware monitoring is also available through the
site gateway for devices that expose hardware health via SNMP (UPS units, network
gear environmental sensors).

---

## Requirements Response -- Alerting

### Configurable Thresholds (Soft/Warn and Hard/Crit)

**Requirement**: Separate warning and critical severity levels.

**Status**: COVERED.

**Response**: All 66 alert rules implement dual thresholds. Example: CPU warning at
85% for 10 minutes, CPU critical at 95% for 5 minutes. Thresholds are defined in
Prometheus alert rule files and can be tuned per environment using label matchers
or recording rule overrides.

---

### Alert Channels

**Requirement**: Teams webhook, email, PagerDuty / similar escalation platform.

**Status**: Teams COVERED. Email COVERED. PagerDuty/escalation GAP.

**Response**:
- Teams: Adaptive Card template with severity color-coding, host/environment context,
  and Grafana dashboard links. Implemented and tested.
- Email: Per-site (datacenter) email distribution routing via Alertmanager. Three
  datacenter routes with separate warning and critical recipient lists.
- PagerDuty: Not configured. Alertmanager has a native PagerDuty receiver -- adding
  it is a 10-line config change requiring only an integration key. However, PagerDuty
  adds licensing cost and is only valuable if the team runs formal on-call rotations
  with escalation chains. If Teams + email reaches the right people, PagerDuty is
  unnecessary overhead.

**Recommendation**: Reclassify PagerDuty as a want/nice-to-have. Note that the
architecture supports adding any escalation platform (PagerDuty, Opsgenie, VictorOps)
as a config change when the team's operational maturity requires it. This is not a
build-time decision.

---

### Alert Deduplication (Hierarchy-Based)

**Requirement**: A switch going down should not throw alerts for all monitored objects
that depend on that switch.

**Status**: PARTIAL.

**Response**: Current implementation includes:
- Severity-based inhibition (server-down suppresses service-level warnings)
- Alert grouping by datacenter + alertname (40 hosts going down simultaneously
  appear as one grouped notification, not 40 separate alerts)

Full topology-aware deduplication (switch X is down, suppress all hosts behind
switch X) requires:
1. An `upstream_device` label on every host, mapping it to its network dependency
2. Alertmanager inhibition rules that suppress host alerts when the upstream
   device's alert is firing
3. Maintenance of the host-to-switch mapping as topology changes

**Practical approach to close this gap**:
- Phase 5.7 (fleet inventory) can generate `upstream_device` label mappings from
  a network topology input (CSV or YAML)
- A recording rule that calculates "percentage of hosts unreachable per datacenter"
  and fires a `SitePartialOutage` alert when a threshold is crossed, providing
  mass-outage detection without per-host topology labels
- Alertmanager inhibition rule: if `SitePartialOutage` fires for a datacenter,
  suppress individual host-down alerts for that datacenter

This combination covers 80-90% of the deduplication value. The remaining edge cases
(single switch affecting a subset of hosts within a datacenter) require the per-host
upstream_device mapping.

**Assessment**: Scalable if the inventory system manages the label mappings. The
mass-outage recording rule approach is zero-maintenance. The per-host mapping
approach scales with the inventory system but requires topology data input. The
team should decide which level of deduplication is required.

**Clarifying question for team**: Is group alert grouping acceptable? If a switch
goes down, all monitored devices dependent on that switch show as down, but there
is only one alert instead of an alert for every monitored device. The dependent
hosts are visible within the grouped alert -- nothing is hidden, the notification
volume is consolidated.

Or is full topology-aware deduplication an absolute requirement -- where dependent
host alerts are actively suppressed (not just grouped) and only the root-cause
device alert fires?

The first approach (grouping + mass-outage detection) is planned for Phase 9 and
requires no ongoing topology maintenance. The second approach (full topology-aware
suppression) requires maintaining a host-to-network-device dependency map in the
inventory system, updated whenever network topology changes.

**This decision could have a direct impact on pricing due to necessary licenses.**
Full topology-aware deduplication is the single strongest justification for paid
platform licensing -- it is the feature vendors invest years of R&D into (LogicMonitor
Service Insights, Dynatrace Smartscape, SolarWinds NetPath). If the team requires
it as an absolute, evaluating paid platforms becomes a more serious conversation and
the associated licensing costs apply. If alert grouping is acceptable, it eliminates
the largest technical gap between our internal stack and commercial alternatives,
and the cost case for vendor licensing becomes difficult to justify.

---

### Alert Silencing / Maintenance Windows

**Requirement**: Scheduled (single time and recurring), manual ad hoc, dynamic scopes.

**Status**: Manual ad hoc COVERED. Scheduled single-time PARTIAL. Recurring WANT/GAP.
Dynamic scopes PARTIAL.

**Response**:
- Manual ad hoc: Alertmanager UI supports creating silences with label matchers.
  Operational today.
- Scheduled single-time: Alertmanager silences accept start/end times. Can be created
  in advance via API. No dedicated scheduling UI, but functional.
- Recurring (want): Alertmanager has no native recurring silence. Two alternatives:
  - Grafana Alerting mute timings (OSS feature): supports recurring time windows
    (e.g., "every Sunday 02:00-06:00") applied to notification policies.
  - Cron-based API script: Python script on a schedule that creates time-bounded
    Alertmanager silences for recurring maintenance windows.
- Dynamic scopes: Silences support label matchers, so you can silence by datacenter,
  role, hostname, environment, or any combination. Example: silence all alerts where
  `datacenter=dc-east AND role=sql` for a SQL maintenance window. No GUI abstraction
  for non-technical users, but the capability exists.

**Action**: Implement Grafana mute timings for known recurring windows (patching
schedules). Document the silence API workflow for ad-hoc and scheduled windows.

---

## Requirements Response -- Reporting

### Customizable Dashboards

**Requirement**: Long-term historical (want), short-term (30 days) historical,
real-time, future forecasting (want).

**Status**: Short-term and real-time COVERED. Long-term and forecasting are WANTS/GAPS.

**Response**:
- Short-term (30 days): Prometheus and Loki both configured for 30-day retention.
  All 10 dashboards support historical queries within this window.
- Real-time: All dashboards support configurable auto-refresh intervals (5s to 5m).
- Long-term historical (want): Requires Mimir (Phase 6) or Thanos for retention
  beyond 30 days. Architecture is documented and the migration path is non-disruptive
  (dual-write from Alloy to both Prometheus and Mimir). Defer until business need
  for >30 day historical queries is confirmed. Nutanix Objects provides S3-compatible
  storage for Mimir's object store backend.
- Future forecasting (want): PromQL `predict_linear()` function can be added to
  existing dashboards for disk capacity and resource trending. Shows "at current
  rate, this disk fills in X days." Covers capacity planning use cases. True
  anomaly detection (ML-based) is out of scope without additional tooling.

**Action**: Add `predict_linear` panels to disk and capacity dashboards (low effort).
Evaluate Mimir timeline when retention requirements are defined.

---

### SLA Calculation and Reporting

**Requirement (WANT)**: SLA dashboards with availability percentages.

**Status**: GAP.

**Response**: Not implemented. Can be built with:
1. Recording rules that calculate daily/weekly/monthly uptime ratios per host and
   per service using `avg_over_time(up[1d])`.
2. A dedicated SLA dashboard showing availability percentages by host, role, site,
   and time period.
3. Threshold indicators (99.9%, 99.5%, 99.0%) with color coding.

This provides functional SLA reporting without vendor tooling. Trade-off: no
automatic business-hours-only calculation without custom recording rule logic, and
no PDF/email SLA report generation without additional scripting.

**Action**: Build SLA recording rules and dashboard when the team defines which
services/hosts have SLA targets and what the targets are.

---

## Requirements Response -- Architecture

### On-Prem: HA and Distributed Model

**Requirement**: High availability and distributed deployment model.

**Status**: PARTIAL -- Architecture documented, single-replica deployed.

**Position**: Agreed that distributed model is required. If we are providing
monitoring for resort operations, polling instances must be local. The central
backend runs on Nutanix NKP with the Helm chart already built.

**Response**:
- HA for central backend: Prometheus can be run as dual replicas with identical
  configs (built-in support via `prometheus_replica` external label, already in our
  config). Alertmanager supports native clustering (gossip protocol). Grafana HA
  requires a shared database (PostgreSQL). Loki supports replication in microservice
  mode. All achievable on NKP.
- Distributed collection: Per-site Alloy agents and gateways (already built) provide
  local collection and SNMP/probe polling at each site.

**Action**: HA configuration is a Phase B Helm chart task (already planned). Production
deployment should validate dual-replica Prometheus and Alertmanager clustering.

---

### Cloud-Only Deployment

**Requirement**: If cloud, need local access to monitoring when WAN is down and
accurate monitoring data during outage.

**Status**: Cloud-only is NOT viable for our use case.

**Position**: Cloud-only deployment does not work for our environment. The reasons:

1. **WAN dependency**: If the link between a resort site and a cloud-hosted backend
   goes down, we lose both dashboard access and metric continuity. The monitoring
   system becomes a casualty of the outage it should be detecting.

2. **Polling latency and bandwidth**: Agentless checks (ICMP, SNMP, TCP probes) from
   a cloud backend to on-prem resort infrastructure traverse the WAN for every poll
   cycle. Unreliable, high-latency, and bandwidth-intensive.

3. **Remote troubleshooting dependency**: If our team is remotely troubleshooting a
   resort during a WAN outage, monitoring is our source of truth. A gap in metrics
   during the exact window that matters undermines the value of the entire platform.

4. **Backfill limitations**: Alloy agents buffer metrics locally during backend
   unavailability (write-ahead log) and backfill when connectivity restores. However,
   backfilled data is usable after the fact, not during active troubleshooting. If
   we are willing to accept backfill-only during WAN outages, the current architecture
   works. If not, local queryable infrastructure is required at each site, which
   increases the on-prem footprint.

5. **WAN redundancy**: Cloud-only would require multiple WAN ingress/egress points
   per site to mitigate single-link failure. This adds network cost and complexity
   that may exceed the cost of local monitoring infrastructure.

**Architecture decision**: Hub-and-spoke model with centralized backend on Nutanix
NKP and local collection tiers at each site. Alloy agents and gateways run locally
at every site. Central Prometheus/Loki/Grafana/Alertmanager on NKP.

**Open question**: For resort sites with known WAN reliability concerns, do we need
a local Prometheus + Grafana instance for dashboard access during outages? This is
the difference between "data is buffered and backfilled" (current) and "dashboards
are accessible locally during outage" (larger per-site footprint). The team should
identify which sites, if any, require Option B (local Prometheus) or Option C (full
local stack).

---

## Requirements Response -- AAA

### SAML SSO with Automated Provisioning

**Requirement**: SAML SSO with automated user provisioning.

**Status**: GAP -- Not configured. Architecture supports it.

**Response**: Grafana supports two authentication paths:
- **OAuth2/OIDC** (Grafana OSS, free): Works with Entra ID (Azure AD). Supports
  JIT provisioning (auto-create users on first login with role mapping from AD
  group claims). This is the recommended path for our hybrid AD/Entra ID environment.
- **SAML** (Grafana Enterprise, licensed): Full SAML 2.0 with attribute mapping.
  Only required if the organization mandates SAML specifically.

The existing RBAC architecture (Phase 8) documents LDAP sync for group-to-team
mapping, which works with both authentication methods.

**Clarifying question for team**: Does the requirement specify SAML specifically, or
is "SSO via our identity provider (Entra ID)" acceptable? If Entra ID OAuth/OIDC
meets the need, this is solvable with OSS Grafana at zero licensing cost.

---

### RBAC

**Requirement**: Role-based access control.

**Status**: PARTIAL -- Fully designed (Phase 8), not implemented.

**Response**: Phase 8 architecture covers:
- Folder-based dashboard permissions (Enterprise NOC, per-site folders, shared)
- Grafana Teams mapped to AD security groups
- LDAP/AD group synchronization for hybrid AD/Entra ID
- Template variable scoping per team (users only see data for their sites)
- Three access tiers: Global Admins, Site Admins, Site Viewers

Implementation is blocked on 8 human actions (AD group creation, LDAP credentials,
group mapping decisions). The architecture is fully documented in ARCHITECTURE.md
and can be implemented as soon as prerequisites are met.

**Action**: Complete Phase 8 human actions to unblock implementation.

---

### User and Admin Action Auditing

**Requirement**: Audit trail for user and admin actions.

**Status**: GAP -- Requires granularity decision from the team.

**Response**: The acceptable solution depends entirely on the granularity the team
defines. There are three tiers:

**Tier 1 -- Login and access auditing** (Grafana OSS, no additional cost):
- Who logged in, when, from which IP
- Failed login attempts
- Session creation and expiration
- Implementation: Grafana server logs forwarded to Loki, queried via dashboard

**Tier 2 -- Configuration change auditing** (Grafana OSS with Loki pipeline, or
Grafana Enterprise):
- Who created, modified, or deleted a dashboard
- Who changed an alert rule or threshold
- Who created or removed a silence/maintenance window
- Who modified team membership or folder permissions
- Implementation (OSS path): Grafana API audit logs to Loki with a dedicated
  audit dashboard. Shows user + action + target + timestamp. Does not show
  the content of the change (no diff).
- Implementation (Enterprise path): Built-in structured audit trail with full
  detail.

**Tier 3 -- Compliance-grade audit trail** (Grafana Enterprise + external SIEM):
- All of Tier 2 plus change diffs (what specifically changed)
- Tamper-proof, exportable audit log
- Defined retention policy
- SOX, HIPAA, or PCI compliance attestation
- Implementation: Grafana Enterprise audit logging + forward to SIEM for
  retention and tamper-proofing.

**Recommendation**: The team should specify which tier satisfies the business
requirement. Tier 1 is free and immediate. Tier 2 is achievable with the Loki
pipeline approach at the cost of no change diffs. Tier 3 requires Grafana
Enterprise licensing and should only be pursued if regulatory compliance mandates it.

**Clarifying question for team**: What is the audit logging requirement driven by?
If it is operational accountability ("who broke this dashboard"), Tier 2 via Loki
is sufficient. If it is regulatory compliance, define the regulation so we can scope
Tier 3 properly.

---

## Requirements Response -- Integrations

### Robust Exposed API

**Requirement**: API for custom automations and integrations.

**Status**: INHERENT -- Covered by the stack's native APIs.

**Response**: Every component in the stack exposes a comprehensive REST API:
- Grafana: Dashboard CRUD, datasource management, user/team management, alerting
- Prometheus: Query (PromQL), metadata, targets, rules, alerts
- Loki: Query (LogQL), labels, series, tail (streaming)
- Alertmanager: Alerts, silences, receivers, status

No custom API wrapper is needed. Third-party tools can integrate directly with any
component. API documentation is maintained by each upstream project.

---

### Manual and Automated Remediations

**Requirement (WANT)**: Custom scripts triggered by alerts or manual action.

**Status**: GAP.

**Response**: Alertmanager supports webhook receivers that can trigger external
systems on alert firing. A lightweight remediation framework would consist of:
1. An Alertmanager webhook receiver pointing to a Python/Go handler service
2. The handler maps alert labels to predefined remediation scripts
3. Scripts execute predefined safe actions (restart a service, clear temp files,
   extend a disk, etc.)
4. Execution results logged to Loki for audit trail

This is a want/nice-to-have and should be deferred until the core monitoring
platform is stable in production. Remediation automation built on an unstable
platform creates more problems than it solves.

**Action**: Defer to a post-deployment phase. Design the webhook handler framework
after the team defines which remediations are safe to automate.

---

## Open Questions for Team Decision

The following items require team input before the requirements list is locked.
Each question is numbered for reference in team discussion.

### Q1: LogicMonitor Investigation

LogicMonitor is already licensed for SQL monitoring in our environment. Before
committing to the internal build path, the team should investigate:
- What is the current LM licensing model (per-device, flat contract, bundled)?
- Who owns the LM relationship (which team, which budget)?
- What is the device capacity vs current usage?
- Does LM cover infrastructure monitoring (SNMP, hardware, Windows services)
  beyond SQL?
- What would expanding LM to 500-2000 endpoints cost annually?

This investigation determines whether "expand LM" is a viable alternative to
"build internally" or whether LM licensing at scale hits the same cost problem
as other vendors.

### Q2: Datadog Boundary

Datadog is used by data/development teams. The monitoring stack we are building
targets on-prem infrastructure. The team should confirm:
- Is there any overlap between Datadog coverage and our target scope?
- Are there cloud workloads that Datadog already monitors which we would
  otherwise need to cover in Phase 7E (cloud integrations)?
- Should we formally define the boundary: "Datadog = cloud/app monitoring,
  Grafana stack = infrastructure monitoring"?

### Q3: Hypervisor Integration Scope

The requirements list includes Nutanix, ESXi, and SimpliVity integrations
(all marked as wants). Redfish already monitors the physical hardware health
of these servers. The team should clarify:
- Does "integration" mean hardware health (covered by Redfish)?
- Or does it mean hypervisor-layer telemetry (VM inventory, storage pools,
  cluster health)?
- If hypervisor-layer, which platforms are priorities?

### Q4: PagerDuty Disposition

The requirements list includes PagerDuty as a need. Given that Teams webhook
and per-site email routing are implemented:
- Does the team run or plan to run formal on-call rotations?
- Is phone/SMS alerting required (the primary differentiator of PagerDuty)?
- Recommendation: Reclassify as a want with a note that the architecture
  supports adding an escalation platform via config change when needed.

### Q5: Alert Deduplication Depth

Topology-aware alert deduplication (switch down suppresses dependent hosts)
is partially implemented. The team should decide:
- Is alert grouping (40 hosts appear as one notification) sufficient?
- Is mass-outage detection (>X% of site down triggers SitePartialOutage)
  sufficient?
- Or is per-host dependency mapping (host A depends on switch B) required?
- If per-host mapping is required, the team must provide or maintain the
  network topology data.

### Q6: WAN-Down Resilience Level

Local Alloy agents buffer data during WAN outages and backfill when restored.
The team should decide:
- Is "data backfills after WAN restoration" acceptable for most sites?
- Which sites (if any) need local dashboard access during WAN outages?
- Is the team willing to deploy and maintain local Prometheus + Grafana
  instances at those sites?

### Q7: Audit Logging Granularity

See the Tier 1/2/3 breakdown in the AAA section. The team should select:
- Tier 1 (login auditing) -- free, immediate
- Tier 2 (configuration change auditing) -- moderate effort, OSS or Enterprise
- Tier 3 (compliance-grade) -- requires Enterprise licensing + SIEM
- What is the business driver for audit logging (operational accountability
  vs regulatory compliance)?

### Q8: Program Status Monitoring Scope

The requirement distinguishes "program status" from "service/daemon status."
The team should provide:
- Which non-service processes need monitoring?
- Examples: scheduled task executables, legacy applications running outside
  a service manager, batch jobs?

### Q9: WinRM/SSH Use Cases

Agentless collection is blocked pending use case review. The team should confirm:
- Which servers (if any) cannot run the Alloy agent?
- If all servers will receive an agent, this requirement may be unnecessary.

### Q10: Synthetic Testing Depth

The team should define:
- Is HTTP response code validation sufficient (URL returns 200)?
- Or are multi-step transaction tests required (login, navigate, submit)?
- Which service endpoints need synthetic monitoring?

---

## Alignment with Project Thought Process

The requirements document states three guiding principles:

> 1. Our monitoring system should only generate the absolute minimal number of
>    alerts possible.
> 2. Every alert generated must be relevant to the recipient, accurate, and
>    actionable.
> 3. Our monitoring system must have very comprehensive, easily tunable monitoring
>    capabilities.

**Assessment against our stack**:

Principle 1 is addressed by dual-threshold alerting (warn/crit), alert grouping,
and inhibition rules. The mass-outage recording rule approach further reduces alert
volume during major incidents.

Principle 2 is addressed by per-site email routing (alerts go to the team
responsible for that datacenter), Teams adaptive cards with full context
(host, environment, datacenter, severity, dashboard link), and alert annotations
with runbook links.

Principle 3 is addressed by the modular Alloy architecture (drop in a role config
to add monitoring for a new service type), the standard label taxonomy (filter and
aggregate on any dimension), and the extensible gateway tier (add new SNMP targets,
probe endpoints, or Redfish BMCs by editing target files). The stack is designed to
monitor anything that exposes metrics, logs, or responds to probes -- most
capabilities are a configuration change, not a development project.
