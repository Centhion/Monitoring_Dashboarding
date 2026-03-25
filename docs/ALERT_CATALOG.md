# Alert Catalog

Complete inventory of all 100 alert rules in the monitoring platform. Each rule is categorized by action tier, assessed for fleet-scale noise risk, and annotated with tuning recommendations.

**Reference**: See `ALERT_SEVERITY_CONTRACT.md` for what each severity level means and expected response times.

---

## Reading This Catalog

| Column | Meaning |
|--------|---------|
| **Tier** | Act Now (immediate action), Investigate (address within 4h), Awareness (weekly review) |
| **Severity** | Prometheus label: critical, warning, info |
| **Threshold** | Trigger condition and `for` duration |
| **Noise Risk** | Low / Medium / High -- likelihood of false positives or excessive volume at 1,500-host fleet scale |
| **Default** | Enabled / Disabled -- whether the rule should fire out of the box without site-specific tuning |
| **Notes** | Tuning guidance, fleet-scale considerations, dependencies |

---

## Summary Statistics

| Category | Rules | Critical | Warning | Info |
|----------|-------|----------|---------|------|
| Windows OS | 10 | 3 | 6 | 1 |
| Linux OS | 13 | 3 | 9 | 1 |
| Infrastructure | 12 | 4 | 8 | 0 |
| Role-Specific | 16 | 5 | 11 | 0 |
| Hardware (Redfish) | 8 | 3 | 5 | 0 |
| Certificates | 5 | 2 | 1 | 2 |
| Lansweeper/Assets | 5 | 1 | 2 | 2 |
| SNMP Network | 6 | 2 | 4 | 0 |
| Probes | 7 | 4 | 3 | 0 |
| Endpoint Monitoring | 5 | 2 | 3 | 0 |
| Outage Detection | 4 | 1 | 3 | 0 |
| SNMP Traps (Grafana) | 4 | 1 | 3 | 0 |
| **Total** | **100** | **35** | **59** | **6** |

**Noise Risk Summary**: 14 High, 38 Medium, 48 Low

---

## Windows OS Alerts

Source: `alerts/prometheus/windows_alerts.yml`

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| WindowsCpuHighWarning | Investigate | warning | CPU > 90% | 30m | **High** | Enabled | At 1,500 hosts, expect 5-15 fires/day during patching, AV scans, backups. The 30m `for` helps but patching windows will still trigger this. Consider raising to 92% or adding `unless` for known maintenance windows. |
| WindowsCpuHighCritical | Act Now | critical | CPU > 95% | 5m | Medium | Enabled | 5m at 95% is a legitimate emergency. Low false-positive rate. |
| WindowsMemoryHighWarning | Investigate | warning | Memory > 85% | 15m | **High** | Enabled | Many Windows servers run 80-90% memory by design (SQL, Exchange, file cache). This will be the noisiest alert at fleet scale. Consider raising to 90% for servers with >16GB RAM, or adding role-based exceptions for SQL/Exchange. |
| WindowsMemoryHighCritical | Act Now | critical | Memory > 95% | 5m | Medium | Enabled | Genuine OOM risk. Keep tight. |
| WindowsDiskSpaceLowWarning | Investigate | warning | Disk free < 20% | 30m | Medium | Enabled | 20% on a 2TB drive is 400GB -- not urgent. On a 40GB C: drive, 20% is 8GB -- urgent. Consider percentage + absolute minimum (e.g., < 20% AND < 50GB). |
| WindowsDiskSpaceLowCritical | Act Now | critical | Disk free < 10% | 5m | Low | Enabled | Imminent data loss. Keep tight. |
| WindowsServiceDown | Investigate | warning | Service not running | 10m | **High** | Enabled | Depends entirely on which services are monitored. Default Alloy config monitors critical services per role. If monitoring non-essential services, this will be very noisy. Review service list per role before enabling at scale. |
| WindowsServerReboot | Awareness | info | Uptime < 10min | 1m | Medium | Enabled | Fires after every reboot including planned patching. Expected volume: 20-50/month during patch cycles. Useful for audit trail but not actionable. |
| WindowsServerDown | Act Now | critical | No metrics for 5m | 5m | Low | Enabled | Fundamental liveness check. Low false-positive rate unless network issues between agent and Prometheus. |
| WindowsTimeDriftWarning | Investigate | warning | Clock offset > 1s | 15m | Low | Enabled | Rare in AD-joined environments with NTP. If it fires, something is wrong. |

**Fleet-scale estimate (1,500 hosts)**: Expect 10-30 warning alerts/day from CPU and memory during normal operations. This is the primary tuning target after pilot deployment.

---

## Linux OS Alerts

Source: `alerts/prometheus/linux_alerts.yml`

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| LinuxCpuHighWarning | Investigate | warning | CPU > 90% | 30m | Medium | Enabled | Linux servers tend to run leaner than Windows. Lower noise risk than Windows equivalent. |
| LinuxCpuHighCritical | Act Now | critical | CPU > 95% | 5m | Low | Enabled | Legitimate emergency. |
| LinuxMemoryHighWarning | Investigate | warning | Memory > 85% | 15m | **High** | Enabled | Linux page cache makes memory usage appear higher than actual pressure. Consider using `node_memory_MemAvailable_bytes` instead of raw utilization if not already. |
| LinuxMemoryHighCritical | Act Now | critical | Memory > 95% | 5m | Medium | Enabled | Genuine OOM risk. |
| LinuxDiskSpaceLowWarning | Investigate | warning | Disk free < 20% | 30m | Medium | Enabled | Same percentage caveat as Windows. Large volumes may not need attention at 20%. |
| LinuxDiskSpaceLowCritical | Act Now | critical | Disk free < 10% | 5m | Low | Enabled | Imminent data loss. |
| LinuxDiskIoHigh | Investigate | warning | IO busy > 90% | 30m | Medium | Enabled | Can fire during legitimate heavy workloads (database imports, backups). 30m `for` helps filter transients. |
| LinuxLoadHigh | Investigate | warning | Load/CPU > 2.0 | 30m | Medium | Enabled | Normalized by CPU count. Threshold of 2.0 is reasonable. May fire on build servers or batch processing hosts. |
| LinuxSystemdUnitFailed | Investigate | warning | Unit in failed state | 15m | Medium | Enabled | Depends on which units are monitored. Failed oneshot units can persist and cause noise. |
| LinuxServerDown | Act Now | critical | No metrics for 5m | 5m | Low | Enabled | Fundamental liveness check. |
| LinuxServerReboot | Awareness | info | Uptime < 10min | 1m | Low | Enabled | Linux reboots less frequently than Windows. Low volume. |
| LinuxTimeDriftWarning | Investigate | warning | Clock offset > 0.5s | 10m | Low | Enabled | Tighter than Windows (0.5s vs 1s). Appropriate for Linux environments. |
| LinuxSwapUsageHigh | Investigate | warning | Swap > 50% | 30m | Low | Enabled | Good early warning for memory pressure. Rare false positives. |

---

## Infrastructure Alerts

Source: `alerts/prometheus/infra_alerts.yml`

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| PrometheusTargetDown | Act Now | critical | Target unreachable | 5m | Low | Enabled | Monitors agent connectivity. Essential. |
| PrometheusRuleFailures | Investigate | warning | Rule eval failures > 0 | 10m | Low | Enabled | Indicates broken PromQL in rules. Should be zero in steady state. |
| PrometheusNotificationsFailing | Act Now | critical | Notification errors > 0 | 10m | Low | Enabled | Monitoring-of-monitoring. If this fires, alerts are not being delivered. |
| PrometheusStorageNearFull | Investigate | warning | TSDB > 80% of 50GB | 30m | Low | Enabled | Capacity planning. Fires well before data loss. |
| LokiRequestErrors | Investigate | warning | 5xx errors sustained | 10m | Low | Enabled | Log backend health. |
| LokiIngestionRateHigh | Investigate | warning | Ingestion > 10MB/s | 15m | Medium | Enabled | May fire during log storms (application errors, security events). Review rate limit if persistent. |
| AlertmanagerNotificationsFailing | Act Now | critical | Delivery failures > 0 | 10m | Low | Enabled | Monitoring-of-monitoring. Critical path. |
| FleetHighCpuServers | Investigate | warning | > 5 servers at CPU > 85% | 15m | Medium | Enabled | Fleet-level anomaly detection. Fires when multiple servers are stressed simultaneously -- may indicate a systemic issue (runaway deployment, DDoS, patch storm). |
| FleetLowDiskServers | Investigate | warning | > 3 servers at disk < 20% | 30m | Low | Enabled | Fleet-level disk trend. |
| FleetServersNotReporting | Act Now | critical | > 10% fleet silent for 1h | 10m | Low | Enabled | Mass connectivity failure. Very high signal. |
| GrafanaDown | Act Now | critical | Grafana health endpoint fails | 5m | Low | Enabled | Users lose dashboard access. |
| AlloyAgentUnhealthy | Investigate | warning | Alloy self-metrics indicate error state | 10m | Low | Enabled | Agent health monitoring. |

---

## Role-Specific Alerts

Source: `alerts/prometheus/role_alerts.yml`

### Active Directory / Domain Controller

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| AdReplicationFailure | Act Now | critical | Replication failures > 0 | 10m | Low | Enabled | AD replication failure is always actionable. |
| AdLdapSearchSlow | Investigate | warning | LDAP search rate = 0 on running DC | 10m | Low | Enabled | DC is up but not serving LDAP queries. |
| DnsQueryFailureRateHigh | Investigate | warning | DNS failure rate > 5% | 10m | Low | Enabled | DNS health on DCs. |
| AdCriticalServiceDown | Act Now | critical | NTDS/DNS/Netlogon/KDC/ADWS down | 3m | Low | Enabled | Core AD services. 3m `for` is appropriate. |

### SQL Server

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| SqlBufferCacheHitRatioLow | Investigate | warning | Buffer cache < 90% | 15m | Medium | Enabled | Can fire during large index rebuilds. 90% is industry standard threshold but some workloads run lower legitimately. |
| SqlPageLifeExpectancyLow | Investigate | warning | PLE < 300s | 10m | Medium | Enabled | Classic SQL memory pressure indicator. 300s is the traditional threshold but modern guidance suggests higher for large-memory servers. |
| SqlDeadlocksDetected | Investigate | warning | Deadlock rate > 0 | 5m | Medium | Enabled | Deadlocks happen in production. Persistent deadlocks are the concern. Consider raising to > 5/min or increasing `for` to 15m to avoid noise from occasional application deadlocks. |
| SqlCriticalServiceDown | Act Now | critical | MSSQLSERVER/SQLAGENT down | 3m | Low | Enabled | Core SQL services. |

### IIS Web Server

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| IisHighErrorRate | Investigate | warning | 5xx rate > 5% | 10m | Medium | Enabled | Depends on application quality. Poorly written apps may have chronic 5xx rates. Tune per-application if needed. |
| IisAppPoolDown | Act Now | critical | W3SVC/WAS down | 3m | Low | Enabled | IIS not serving requests. |
| IisHighConnectionCount | Investigate | warning | Active connections > 1000 | 10m | Low | Enabled | 1000 is conservative. Tune based on expected traffic per server. |

### File Server

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| FileServerDiskIoHigh | Investigate | warning | Disk idle < 10% | 30m | Medium | Enabled | File servers under heavy load can sustain high IO legitimately. 30m `for` is appropriate. |
| FileServerServiceDown | Act Now | critical | LanmanServer/DFSR down | 3m | Low | Enabled | SMB/DFS services. |

### Docker

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| DockerDaemonDown | Act Now | critical | Docker metrics endpoint gone | 3m | Low | Enabled | Container host unusable. |

---

## Hardware Alerts (Redfish/BMC)

Source: `alerts/prometheus/hardware_alerts.yml`

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| RedfishBMCUnreachable | Investigate | warning | BMC endpoint unreachable | 10m | Low | Enabled | BMC may be on a separate management VLAN. Network issues between Prometheus and BMC will trigger this. |
| RedfishHealthWarning | Investigate | warning | BMC reports degraded health | 5m | Low | Enabled | Non-critical hardware degradation (single fan failure, predictive disk failure). |
| RedfishHealthCritical | Act Now | critical | BMC reports critical fault | 2m | Low | Enabled | Hardware failure. Immediate investigation. |
| RedfishTemperatureHigh | Investigate | warning | Component > 75C | 10m | Low | Enabled | Environmental or cooling issue. |
| RedfishTemperatureCritical | Act Now | critical | Component > 85C | 5m | Low | Enabled | Thermal emergency. Server may auto-shutdown. |
| RedfishServerPoweredOff | Act Now | critical | Chassis powered off, BMC reachable | 5m | Low | Enabled | Server is off but not unreachable -- unexpected power-off. |
| RedfishDriveUnhealthy | Investigate | warning | Drive health non-OK | 5m | Low | Enabled | Predictive disk failure or RAID degradation. |
| RedfishMemoryUnhealthy | Investigate | warning | DIMM health non-healthy | 5m | Low | Enabled | Memory ECC errors or DIMM failure. |

**Fleet-scale note**: Hardware alerts are inherently low-noise. They fire when physical components fail. All should remain enabled.

---

## Certificate Alerts

Source: `alerts/prometheus/cert_alerts.yml`

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| TLSCertExpiring90Days | Awareness | info | Expires in 30-90 days | 1h | Low | Enabled | Planning window. Procurement/renewal lead time. |
| TLSCertExpiring30Days | Investigate | warning | Expires in 7-30 days | 30m | Low | Enabled | Renewal is overdue. Act within a week. |
| TLSCertExpiring7Days | Act Now | critical | Expires in 0-7 days | 10m | Low | Enabled | Imminent outage if not renewed. |
| TLSCertExpired | Act Now | critical | Certificate expired | 5m | Low | Enabled | Active outage. Users seeing browser warnings or TLS failures. |
| TLSCertProbeFailure | Investigate | warning | Probe to endpoint fails | 15m | Low | Enabled | Cannot check certificate -- endpoint may be down or network issue. |

**Fleet-scale note**: Certificate alerts scale with the number of monitored endpoints, not hosts. Typically 20-50 endpoints. Very low noise.

---

## Lansweeper / Asset Alerts

Source: `alerts/prometheus/lansweeper_alerts.yml`

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| AssetWarrantyExpiring90Days | Awareness | info | Warranty expires in 60-90 days | 6h | Low | Disabled | Only useful if procurement workflow exists. Enable when asset management process is defined. |
| AssetWarrantyExpiring60Days | Investigate | warning | Warranty expires in 30-60 days | 6h | Medium | Disabled | At fleet scale with staggered purchase dates, this could generate steady noise. Enable per-site as warranty tracking matures. |
| AssetWarrantyExpiring30Days | Investigate | warning | Warranty expires in 0-30 days | 1h | Low | Disabled | Urgent procurement action needed. |
| AssetWarrantyExpired | Act Now | critical | Warranty expired | 1h | Low | Disabled | Risk exposure on unwarranted hardware. May want to downgrade to warning -- expired warranty is not an operational emergency. |
| AssetNotSeenByLansweeper7Days | Investigate | warning | Asset invisible for > 7 days | 6h | Medium | Disabled | Depends on Lansweeper scan reliability. Can fire for decommissioned assets not yet removed from inventory. |

**Fleet-scale note**: All Lansweeper alerts are disabled by default because the Lansweeper integration (Phase 7D) is still in progress. Enable individually as the integration matures.

---

## SNMP Network Device Alerts

Source: `alerts/prometheus/snmp_alerts.yml`

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| SNMPDeviceUnreachable | Act Now | critical | No SNMP response | 5m | Low | Enabled | Network device down or SNMP misconfigured. |
| SNMPDeviceReboot | Investigate | warning | sysUpTime reset in 10m | 1m | Low | Enabled | Unexpected device reboot. |
| SNMPInterfaceDown | Investigate | warning | Interface oper-down, admin-up | 5m | Medium | Enabled | Can be noisy if monitoring unused but admin-enabled ports. Filter by interface description or exclude access ports. |
| SNMPInterfaceHighUtilization | Investigate | warning | Interface > 85% utilization | 30m | Medium | Enabled | Depends on link speed and expected traffic. 85% on a 1G uplink is different from 85% on a 10G backbone. |
| SNMPInterfaceSaturated | Act Now | critical | Interface > 95% utilization | 5m | Low | Enabled | Link is at capacity. Packet loss likely. |
| SNMPInterfaceErrors | Investigate | warning | Error rate > 1/sec | 15m | Low | Enabled | Physical layer problem (bad cable, failing optic). |

---

## Probe Alerts (HTTP/ICMP/TCP/DNS)

Source: `alerts/prometheus/probe_alerts.yml`

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| HTTPProbeFailed | Act Now | critical | HTTP endpoint unreachable | 3m | Low | Enabled | External service availability check. |
| HTTPProbeSlow | Investigate | warning | Response > 5s average | 15m | Medium | Enabled | 5s is generous. May need tuning per-endpoint for different SLA tiers. |
| ICMPProbeFailed | Act Now | critical | ICMP ping fails | 5m | Low | Enabled | Host or network path unreachable. |
| ICMPProbeHighLatency | Investigate | warning | Latency > 500ms | 15m | Low | Enabled | 500ms is high for LAN. Appropriate for WAN probes. Consider separate thresholds for LAN vs WAN targets. |
| TCPProbeFailed | Act Now | critical | TCP port connection fails | 3m | Low | Enabled | Service port unreachable. |
| DNSProbeFailed | Act Now | critical | DNS resolver unresponsive | 2m | Low | Enabled | DNS failure affects all services. 2m is appropriate. |
| ProbeTargetMissing | Investigate | warning | Probe target count decreased | 15m | Low | Enabled | Configuration drift -- a target was removed or became unreachable. |

---

## Endpoint Monitoring Alerts

Source: `alerts/prometheus/endpoint_alerts.yml`

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| FileSizeExceeded | Investigate | warning | File > 1GB | 5m | Medium | Enabled | Depends on which files are monitored. Log files that grow beyond 1GB indicate missing rotation. Tune threshold per use case. |
| DirectorySizeExceeded | Investigate | warning | Directory > 10GB | 10m | Medium | Enabled | Similar to file size -- depends on monitored directories. |
| FileStale | Investigate | warning | File not modified > 24h | 30m | Medium | Enabled | For monitoring batch job output files, log rotation, etc. Will false-positive on files that legitimately don't change daily. Requires careful target selection. |
| WindowsProcessNotRunning | Act Now | critical | Expected process missing | 10m | Low | Enabled | Specific process monitoring. Low noise if process list is curated. |
| LinuxProcessNotRunning | Act Now | critical | Expected process missing | 10m | Low | Enabled | Same as Windows variant. |

---

## Outage Detection Alerts

Source: `alerts/prometheus/outage_alerts.yml`

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| SitePartialOutage | Investigate | warning | < 70% hosts up at site (min 3 hosts) | 2m | Low | Enabled | Statistical anomaly detection. Fires when a significant portion of a site goes dark. Triggers inhibition rules to suppress per-host alerts. |
| SiteMajorOutage | Act Now | critical | < 30% hosts up at site (min 3 hosts) | 3m | Low | Enabled | Major site failure. Suppresses all per-host alerts at that site via inhibition. |
| RolePartialOutage | Investigate | warning | < 70% of role hosts up (min 2 hosts) | 5m | Low | Enabled | Role-level anomaly (all SQL servers down, all DCs down). Suppresses per-host warnings for that role. |
| SiteNetworkPartition | Investigate | warning | Hosts up but probes failing | 5m | Low | Enabled | Network path issue rather than host failure. |

**Fleet-scale note**: Outage alerts are the noise reduction mechanism. They fire rarely but when they do, they suppress dozens of per-host alerts. Essential for alert fatigue prevention.

---

## SNMP Trap Alerts (Grafana-Managed)

Source: `alerts/grafana/snmp_trap_alerts.yml`

| Alert | Tier | Severity | Threshold | For | Noise Risk | Default | Notes |
|-------|------|----------|-----------|-----|------------|---------|-------|
| SNMP Trap: Link Down | Investigate | warning | linkDown trap count > 0 in 5m | 0s | Medium | Enabled | Fires on every link-down trap received. Can be noisy if monitoring access ports that flap. Consider filtering by interface type in the Loki query. |
| SNMP Trap: Authentication Failure | Investigate | warning | authenticationFailure trap > 0 in 5m | 0s | **High** | Enabled | SNMP auth failures can be very noisy if misconfigured community strings exist. Review SNMP configuration before enabling at scale. |
| SNMP Trap: Device Cold Start | Act Now | critical | coldStart trap > 0 in 5m | 0s | Low | Enabled | Device rebooted. Important event. |
| SNMP Trap: High Volume from Device | Investigate | warning | > 50 traps from one device in 10m | 5m | Low | Enabled | Meta-alert: device is generating excessive traps. Indicates a flapping condition or misconfiguration. |

---

## Noise Risk Summary

### High Noise Risk (14 rules) -- Priority Tuning Targets

These rules are most likely to cause alert fatigue at fleet scale. Tune thresholds during pilot:

| Alert | Current Threshold | Recommendation |
|-------|-------------------|----------------|
| WindowsCpuHighWarning | > 90% for 30m | Consider 92% or add patching window exclusion |
| WindowsMemoryHighWarning | > 85% for 15m | Raise to 90% for servers with > 16GB RAM |
| WindowsServiceDown | Service not running for 10m | Audit monitored service list per role |
| LinuxMemoryHighWarning | > 85% for 15m | Verify using MemAvailable, not raw utilization |
| SNMPInterfaceDown | Oper-down/admin-up for 5m | Filter by interface description |
| SNMPInterfaceHighUtilization | > 85% for 30m | Differentiate by link speed |
| SNMP Trap: Auth Failure | Any trap in 5m | Review SNMP community string configuration first |
| SNMP Trap: Link Down | Any trap in 5m | Filter access port flaps |
| FileSizeExceeded | > 1GB for 5m | Tune per monitored file |
| DirectorySizeExceeded | > 10GB for 10m | Tune per monitored directory |
| FileStale | Not modified > 24h | Only monitor files expected to change daily |
| SqlDeadlocksDetected | Rate > 0 for 5m | Raise to > 5/min or increase `for` to 15m |
| AssetWarrantyExpiring60Days | 30-60 days | Disabled by default; enable when process exists |
| AssetNotSeenByLansweeper7Days | 7 days invisible | Disabled by default; clean inventory first |

### Recommended Disabled-by-Default Rules

These 5 rules (all Lansweeper) should remain disabled until the integration is production-ready:
- AssetWarrantyExpiring90Days
- AssetWarrantyExpiring60Days
- AssetWarrantyExpiring30Days
- AssetWarrantyExpired
- AssetNotSeenByLansweeper7Days

All other 95 rules should be enabled by default.

---

## SCOM Alert Mapping

**Status**: Pending human action.

The team needs to export the active SCOM alert rules from the SCOM console and identify:
1. Which SCOM alerts does the team actually act on today?
2. Which do they routinely ignore or acknowledge-and-close?
3. Are there SCOM alerts with no equivalent in this platform?

Once the SCOM export is available, this section will map each SCOM alert to its Prometheus equivalent (or document the gap).

**Known coverage**: The current 100 rules cover standard OS metrics (CPU, memory, disk, services), AD, SQL, IIS, file server, Docker, network devices, hardware health, and certificates. This exceeds typical SCOM Management Pack coverage for Windows Server, AD, SQL, and IIS MPs.
