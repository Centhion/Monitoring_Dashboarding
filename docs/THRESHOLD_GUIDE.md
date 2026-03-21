# Alert and Dashboard Threshold Guide

Default thresholds applied across all dashboards and alert rules. Tuned to minimize alert fatigue while catching genuine issues.

**Design principles:**
- **Conservative thresholds**: Warning alerts fire at 90% (not 85%) to avoid noise during normal operations (patching, backups, AV scans)
- **Extended for durations**: Warning alerts require the condition to persist 15-30 minutes before firing. Brief spikes are normal and self-resolve.
- **Self-resolving**: All alerts automatically resolve when the condition clears. Resolved notifications are sent to Teams/email.
- **Mass-outage suppression**: When multiple servers fail at a site, one outage alert fires instead of dozens of individual alerts.
- **Severity contract**: Critical = act now. Warning = investigate within 4 hours. Info = awareness only, no email.

Review and adjust these values with your operations team based on your environment's baseline performance.

---

## How to Change Thresholds

**Dashboard panels** (visual color coding): Edit the dashboard JSON in `dashboards/` or use the Grafana UI (Edit panel > Field > Thresholds). Changes via UI require export to JSON to persist across deployments.

**Alert rules** (notification triggers): Edit the YAML files in `alerts/prometheus/`. Reload Prometheus after changes: `curl -X POST http://localhost:9090/-/reload`

---

## Server Health Thresholds

These apply to all server dashboards (Windows, Linux, and role-specific).

| Metric | Warning Alert | Critical Alert | For Duration | Notes |
|--------|--------------|----------------|-------------|-------|
| CPU Utilization | > 90% (was 85%) | > 95% | Warning: 30m, Critical: 5m | Raised from 85% to reduce noise during patching/backups |
| Memory Utilization | > 90% (was 80%) | > 95% | Warning: 15m, Critical: 5m | Raised from 80% -- SQL/IIS servers normally run 80%+ |
| Disk Free (worst volume) | > 20% | 10-20% | < 10% | percent | Red = immediate action needed |
| Disk I/O Utilization | < 80% | 80-95% | > 95% | percent | Sustained high I/O = storage bottleneck |
| Network Throughput | informational | -- | -- | Bps | No threshold (varies by server role) |
| Uptime | > 7d | 1-7d | < 1d | duration | Recent reboot may indicate issue |
| Services Down | 0 | -- | > 0 | count | Any stopped critical service is red |
| Load Average (Linux) | < 0.8 | 0.8-1.0 | > 1.0 | normalized | Per-CPU load; >1.0 means overloaded |

## SQL Server Thresholds

| Metric | Green | Yellow | Red | Unit | Notes |
|--------|-------|--------|-----|------|-------|
| Buffer Cache Hit Ratio | > 95% | 90-95% | < 90% | percent | Low = too little memory for data pages |
| Page Life Expectancy | > 300s | 60-300s | < 60s | seconds | Low = severe memory pressure |
| Blocked Processes | 0 | 1-5 | > 5 | count | Blocking chains impact application response |
| Deadlocks/sec | 0 | > 0 | > 1 | rate | Any deadlocks need investigation |
| Memory Grants Pending | 0 | > 0 | > 5 | count | Queries waiting for memory to execute |
| Batch Requests/sec | informational | -- | -- | rate | Baseline varies by workload |
| User Connections | informational | -- | -- | count | Baseline varies by application |

## Domain Controller Thresholds

| Metric | Green | Yellow | Red | Unit | Notes |
|--------|-------|--------|-----|------|-------|
| LDAP Searches/sec | informational | -- | -- | rate | Baseline varies by environment size |
| LDAP Binds/sec | informational | -- | -- | rate | Spike may indicate auth storm |
| Replication Objects | informational | -- | -- | count | Delta between inbound/outbound indicates lag |
| DNS Queries/sec | informational | -- | -- | rate | Baseline varies |
| DNS Recursive Queries | informational | -- | -- | rate | High recursive = possible misconfiguration |

## DHCP Server Thresholds

| Metric | Green | Yellow | Red | Unit | Notes |
|--------|-------|--------|-----|------|-------|
| NAK Rate | 0 | > 0 | > 5/sec | rate | NAKs indicate scope exhaustion or conflicts |
| Discover/Offer/Request/ACK | informational | -- | -- | rate | Normal DHCP traffic, no threshold needed |

## IIS Web Server Thresholds

| Metric | Green | Yellow | Red | Unit | Notes |
|--------|-------|--------|-----|------|-------|
| 5xx Error Rate | < 1% | 1-5% | > 5% | percent | Server errors indicate application issues |
| 4xx Error Rate | < 10% | 10-25% | > 25% | percent | Client errors may indicate broken links or attacks |
| Active Connections | informational | -- | -- | count | Baseline varies by application |
| Request Rate | informational | -- | -- | rate | Baseline varies |

## File Server Thresholds

| Metric | Green | Yellow | Red | Unit | Notes |
|--------|-------|--------|-----|------|-------|
| Disk Latency (read) | < 10ms | 10-20ms | > 20ms | milliseconds | High latency = storage bottleneck |
| Disk Latency (write) | < 10ms | 10-20ms | > 20ms | milliseconds | Write latency often higher than read |
| Disk Queue Depth | < 2 | 2-5 | > 5 | count | High queue = more I/O than disk can handle |
| FSRM Quota Usage | < 80% | 80-95% | > 95% | percent | Near-full quotas need expansion or cleanup |
| SMB Sessions | informational | -- | -- | count | Baseline varies |

## Certificate Thresholds

| Metric | Green | Yellow | Red | Unit | Notes |
|--------|-------|--------|-----|------|-------|
| Days Until Expiry | > 90d | 30-90d | < 30d | days | Red = urgent renewal needed |
| Critical Expiry | -- | -- | < 7d | days | Separate critical tier |
| Probe Success | 100% | < 100% | 0% | percent | Failed probe = endpoint unreachable |

## Network Device Thresholds

| Metric | Green | Yellow | Red | Unit | Notes |
|--------|-------|--------|-----|------|-------|
| Interface Utilization | < 70% | 70-90% | > 90% | percent | High utilization = congestion risk |
| Error Rate | 0 | > 0 | > 10/sec | rate | Any errors need investigation |
| Discard Rate | 0 | > 0 | > 10/sec | rate | Discards indicate buffer overflows |
| Devices Down | 0 | -- | > 0 | count | Any device down is critical |
| Interfaces Down | 0 | -- | > 0 | count | Unexpected down interfaces need review |

## Physical Server (BMC) Thresholds

| Metric | Green | Yellow | Red | Unit | Notes |
|--------|-------|--------|-----|------|-------|
| Inlet Temperature | < 30C | 30-40C | > 40C | celsius | Ambient temp affects all components |
| CPU Temperature | < 70C | 70-85C | > 85C | celsius | Thermal throttling starts ~85-95C |
| Health Status | OK (0) | Warning (1) | Critical (2) | status | BMC-reported overall health |
| Power Consumption | informational | -- | -- | watts | Baseline varies by server model |
| BMC Reachable | 1 (up) | -- | 0 (down) | boolean | Unreachable BMC = network or hardware issue |

## SLA Thresholds

| Metric | Green | Yellow | Red | Unit | Notes |
|--------|-------|--------|-----|------|-------|
| Host Availability (30d) | > 99.9% | 99.0-99.9% | < 99.0% | percent | Below 99% = significant downtime |
| Site Availability (30d) | > 99.5% | 99.0-99.5% | < 99.0% | percent | Site-level aggregation |
| Downtime Minutes (30d) | < 44min | 44-432min | > 432min | minutes | 44min = 99.9%, 432min = 99.0% |

---

## Updating Thresholds

To change a threshold:

1. Find the dashboard in `dashboards/enterprise/`, `dashboards/servers/`, or `dashboards/infrastructure/`
2. Search for the panel title in the JSON
3. Modify the `thresholds.steps` array:
   ```json
   "thresholds": {
     "mode": "absolute",
     "steps": [
       {"color": "green", "value": null},
       {"color": "yellow", "value": 75},
       {"color": "red", "value": 90}
     ]
   }
   ```
4. Restart Grafana or wait for the provisioning interval (30s)

For alert rule thresholds, edit the `expr` field in `alerts/prometheus/*.yml` and reload Prometheus.

---

## Complete Alert Rule Reference

Every alert rule in the platform with current parameters. Self-resolving: all alerts automatically clear when the condition is no longer true.

### Cert Alerts

**File**: `alerts/prometheus/cert_alerts.yml`

| Alert | Severity | For | Description |
|-------|----------|-----|-------------|
| TLSCertExpired | critical | 5m | EXPIRED: TLS certificate for {{ $labels.service }} ({{ $labels.instance }}) has  |
| TLSCertExpiring7Days | critical | 10m | URGENT: TLS certificate for {{ $labels.service }} ({{ $labels.instance }}) expir |
| TLSCertExpiring30Days | warning | 30m | TLS certificate for {{ $labels.service }} ({{ $labels.instance }}) expires in {{ |
| TLSCertProbeFailure | warning | 15m | Certificate probe failed for {{ $labels.service }} ({{ $labels.instance }}) |
| TLSCertExpiring90Days | info | 1h | TLS certificate for {{ $labels.service }} ({{ $labels.instance }}) expires in {{ |

### Endpoint Alerts

**File**: `alerts/prometheus/endpoint_alerts.yml`

| Alert | Severity | For | Description |
|-------|----------|-----|-------------|
| LinuxProcessNotRunning | critical | 10m | Process {{ $labels.name }} not running on {{ $labels.hostname }} |
| WindowsProcessNotRunning | critical | 10m | Process {{ $labels.process }} not running on {{ $labels.hostname }} |
| DirectorySizeExceeded | warning | 10m | Directory {{ $labels.name }} exceeds 10GB on {{ $labels.hostname }} |
| FileSizeExceeded | warning | 5m | File {{ $labels.name }} exceeds 1GB on {{ $labels.hostname }} |
| FileStale | warning | 30m | File {{ $labels.name }} is stale on {{ $labels.hostname }} |
| WindowsProcessHighMemory | warning | 15m | Process {{ $labels.process }} using {{ $value | humanize1024 }} on {{ $labels.ho |

### Hardware Alerts

**File**: `alerts/prometheus/hardware_alerts.yml`

| Alert | Severity | For | Description |
|-------|----------|-----|-------------|
| RedfishHealthCritical | critical | 2m | CRITICAL hardware fault on {{ $labels.device_name }} ({{ $labels.instance }}) |
| RedfishServerPoweredOff | critical | 5m | Server {{ $labels.device_name }} ({{ $labels.instance }}) is powered off |
| RedfishTemperatureCritical | critical | 5m | CRITICAL temperature on {{ $labels.device_name }} ({{ $labels.instance }}): {{ $ |
| RedfishBMCUnreachable | warning | 10m | BMC unreachable for {{ $labels.device_name }} ({{ $labels.instance }}) |
| RedfishDriveUnhealthy | warning | 5m | Drive health issue on {{ $labels.device_name }} ({{ $labels.instance }}) |
| RedfishHealthWarning | warning | 5m | Hardware warning on {{ $labels.device_name }} ({{ $labels.instance }}) |
| RedfishMemoryUnhealthy | warning | 5m | Memory health issue on {{ $labels.device_name }} ({{ $labels.instance }}) |
| RedfishTemperatureHigh | warning | 10m | High temperature on {{ $labels.device_name }} ({{ $labels.instance }}): {{ $valu |

### Infra Alerts

**File**: `alerts/prometheus/infra_alerts.yml`

| Alert | Severity | For | Description |
|-------|----------|-----|-------------|
| AlertmanagerNotificationsFailing | critical | 10m | Alertmanager failing to send notifications |
| FleetServersNotReporting | critical | 10m | Significant drop in reporting servers for {{ $labels.os }} in {{ $labels.environ |
| PrometheusNotificationsFailing | critical | 10m | Prometheus cannot send alerts to Alertmanager |
| PrometheusTargetDown | critical | 5m | Target {{ $labels.instance }} is down (job: {{ $labels.job }}) |
| FleetHighCpuServers | warning | 15m | {{ $value }} servers have high CPU in {{ $labels.environment }}/{{ $labels.datac |
| FleetLowDiskServers | warning | 30m | {{ $value }} servers have low disk space in {{ $labels.environment }}/{{ $labels |
| LokiIngestionRateHigh | warning | 15m | Loki ingestion rate exceeds 10MB/s |
| LokiRequestErrors | warning | 10m | Loki is returning 5xx errors |
| PrometheusRuleFailures | warning | 10m | Prometheus rule evaluation failures |
| PrometheusStorageNearFull | warning | 30m | Prometheus TSDB storage approaching limit |

### Lansweeper Alerts

**File**: `alerts/prometheus/lansweeper_alerts.yml`

| Alert | Severity | For | Description |
|-------|----------|-----|-------------|
| AssetWarrantyExpired | critical | 1h | Warranty EXPIRED: {{ $labels.hostname }} |
| AssetNotSeenByLansweeper7Days | warning | 6h | Asset not seen by Lansweeper in 7+ days: {{ $labels.hostname }} |
| AssetWarrantyExpiring30Days | warning | 1h | Warranty expiring within 30 days: {{ $labels.hostname }} |
| AssetWarrantyExpiring60Days | warning | 6h | Warranty expiring within 60 days: {{ $labels.hostname }} |
| AssetWarrantyExpiring90Days | info | 6h | Warranty expiring within 90 days: {{ $labels.hostname }} |

### Linux Alerts

**File**: `alerts/prometheus/linux_alerts.yml`

| Alert | Severity | For | Description |
|-------|----------|-----|-------------|
| LinuxCpuHighCritical | critical | 5m | Critical CPU usage on {{ $labels.hostname }} |
| LinuxDiskSpaceLowCritical | critical | 5m | Critical disk space on {{ $labels.hostname }} mount {{ $labels.mountpoint }} |
| LinuxMemoryHighCritical | critical | 5m | Critical memory usage on {{ $labels.hostname }} |
| LinuxServerDown | critical | 5m | Linux server {{ $labels.hostname }} is unreachable |
| LinuxCpuHighWarning | warning | 30m | High CPU usage on {{ $labels.hostname }} |
| LinuxDiskIoHigh | warning | 30m | High disk I/O on {{ $labels.hostname }} device {{ $labels.device }} |
| LinuxDiskSpaceLowWarning | warning | 30m | Low disk space on {{ $labels.hostname }} mount {{ $labels.mountpoint }} |
| LinuxLoadHigh | warning | 30m | High load average on {{ $labels.hostname }} |
| LinuxMemoryHighWarning | warning | 15m | High memory usage on {{ $labels.hostname }} |
| LinuxSwapUsageHigh | warning | 30m | High swap usage on {{ $labels.hostname }} |
| LinuxSystemdUnitFailed | warning | 15m | Systemd unit {{ $labels.name }} failed on {{ $labels.hostname }} |
| LinuxTimeDriftWarning | warning | 10m | Time drift detected on {{ $labels.hostname }} |
| LinuxServerReboot | info | 1m | Linux server {{ $labels.hostname }} was recently rebooted |

### Outage Alerts

**File**: `alerts/prometheus/outage_alerts.yml`

| Alert | Severity | For | Description |
|-------|----------|-----|-------------|
| SiteMajorOutage | critical | 3m | Major outage at {{ $labels.datacenter }}: {{ $value | printf "%.0f" }}% of hosts |
| RolePartialOutage | warning | 5m | Partial outage for {{ $labels.role }} at {{ $labels.datacenter }} |
| SitePartialOutage | warning | 2m | Partial outage at {{ $labels.datacenter }}: {{ $value | printf "%.0f" }}% of hos |

### Probe Alerts

**File**: `alerts/prometheus/probe_alerts.yml`

| Alert | Severity | For | Description |
|-------|----------|-----|-------------|
| DNSProbeFailed | critical | 2m | DNS probe failed for {{ $labels.service }} ({{ $labels.instance }}) |
| HTTPProbeFailed | critical | 3m | HTTP probe failed for {{ $labels.service }} ({{ $labels.instance }}) |
| ICMPProbeFailed | critical | 5m | ICMP probe failed for {{ $labels.service }} ({{ $labels.instance }}) |
| TCPProbeFailed | critical | 3m | TCP probe failed for {{ $labels.service }} ({{ $labels.instance }}) |
| HTTPProbeSlow | warning | 15m | HTTP probe slow for {{ $labels.service }} ({{ $labels.instance }}) |
| ICMPProbeHighLatency | warning | 15m | High ICMP latency to {{ $labels.service }} ({{ $labels.instance }}) |
| ProbeTargetMissing | warning | 15m | Probe target count dropped in {{ $labels.datacenter }} |

### Role Alerts

**File**: `alerts/prometheus/role_alerts.yml`

| Alert | Severity | For | Description |
|-------|----------|-----|-------------|
| AdCriticalServiceDown | critical | 3m | AD critical service {{ $labels.name }} down on {{ $labels.hostname }} |
| AdReplicationFailure | critical | 10m | AD replication failure on {{ $labels.hostname }} |
| DockerDaemonDown | critical | 3m | Docker daemon unreachable on {{ $labels.hostname }} |
| FileServerServiceDown | critical | 3m | File server service {{ $labels.name }} down on {{ $labels.hostname }} |
| IisAppPoolDown | critical | 3m | IIS service {{ $labels.name }} down on {{ $labels.hostname }} |
| SqlCriticalServiceDown | critical | 3m | SQL service {{ $labels.name }} down on {{ $labels.hostname }} |
| AdLdapSearchSlow | warning | 10m | LDAP searches stopped on {{ $labels.hostname }} |
| DnsQueryFailureRateHigh | warning | 10m | DNS query failure rate high on {{ $labels.hostname }} |
| FileServerDiskIoHigh | warning | 30m | High disk I/O on file server {{ $labels.hostname }} disk {{ $labels.volume }} |
| IisHighConnectionCount | warning | 10m | High connection count on IIS {{ $labels.hostname }} |
| IisHighErrorRate | warning | 10m | High 5xx error rate on IIS {{ $labels.hostname }} |
| SqlBufferCacheHitRatioLow | warning | 15m | SQL buffer cache hit ratio low on {{ $labels.hostname }} |
| SqlDeadlocksDetected | warning | 5m | SQL deadlocks detected on {{ $labels.hostname }} |
| SqlPageLifeExpectancyLow | warning | 10m | SQL page life expectancy low on {{ $labels.hostname }} |

### Snmp Alerts

**File**: `alerts/prometheus/snmp_alerts.yml`

| Alert | Severity | For | Description |
|-------|----------|-----|-------------|
| SNMPDeviceUnreachable | critical | 5m | SNMP device {{ $labels.device_name }} ({{ $labels.instance }}) is unreachable |
| SNMPInterfaceSaturated | critical | 5m | URGENT: Interface {{ $labels.ifDescr }} on {{ $labels.device_name }} ({{ $labels |
| SNMPDeviceReboot | warning | 1m | Network device {{ $labels.device_name }} ({{ $labels.instance }}) has rebooted |
| SNMPInterfaceDown | warning | 5m | Interface {{ $labels.ifDescr }} on {{ $labels.device_name }} ({{ $labels.instanc |
| SNMPInterfaceErrors | warning | 15m | Interface {{ $labels.ifDescr }} on {{ $labels.device_name }} ({{ $labels.instanc |
| SNMPInterfaceHighUtilization | warning | 30m | Interface {{ $labels.ifDescr }} on {{ $labels.device_name }} ({{ $labels.instanc |

### Windows Alerts

**File**: `alerts/prometheus/windows_alerts.yml`

| Alert | Severity | For | Description |
|-------|----------|-----|-------------|
| WindowsCpuHighCritical | critical | 5m | Critical CPU usage on {{ $labels.hostname }} |
| WindowsDiskSpaceLowCritical | critical | 5m | Critical disk space on {{ $labels.hostname }} volume {{ $labels.volume }} |
| WindowsMemoryHighCritical | critical | 5m | Critical memory usage on {{ $labels.hostname }} |
| WindowsServerDown | critical | 5m | Windows server {{ $labels.hostname }} is unreachable |
| WindowsCpuHighWarning | warning | 30m | High CPU usage on {{ $labels.hostname }} |
| WindowsDiskSpaceLowWarning | warning | 30m | Low disk space on {{ $labels.hostname }} volume {{ $labels.volume }} |
| WindowsMemoryHighWarning | warning | 15m | High memory usage on {{ $labels.hostname }} |
| WindowsServiceDown | warning | 10m | Windows service {{ $labels.name }} not running on {{ $labels.hostname }} |
| WindowsTimeDriftWarning | warning | 15m | Time drift detected on {{ $labels.hostname }} |
| WindowsServerReboot | info | 1m | Windows server {{ $labels.hostname }} was recently rebooted |
