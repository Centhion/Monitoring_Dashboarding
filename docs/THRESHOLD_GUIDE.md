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
