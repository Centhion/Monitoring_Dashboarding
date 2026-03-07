# Alert Runbooks

Operational procedures for each alert rule. Find the alert name in the table of contents below, then follow the investigation and remediation steps.

---

## Table of Contents

### Windows Server Alerts
- [WindowsCpuHighWarning](#windowscpuhighwarning)
- [WindowsCpuHighCritical](#windowscpuhighcritical)
- [WindowsMemoryHighWarning](#windowsmemoryhighwarning)
- [WindowsMemoryHighCritical](#windowsmemoryhighcritical)
- [WindowsDiskSpaceLowWarning](#windowsdiskspacelowwarning)
- [WindowsDiskSpaceLowCritical](#windowsdiskspacelowcritical)
- [WindowsServiceDown](#windowsservicedown)
- [WindowsServerReboot](#windowsserverreboot)
- [WindowsServerDown](#windowsserverdown)
- [WindowsTimeDriftWarning](#windowstimedriftwarning)

### Linux Server Alerts
- [LinuxCpuHighWarning](#linuxcpuhighwarning)
- [LinuxCpuHighCritical](#linuxcpuhighcritical)
- [LinuxMemoryHighWarning](#linuxmemoryhighwarning)
- [LinuxMemoryHighCritical](#linuxmemoryhighcritical)
- [LinuxDiskSpaceLowWarning](#linuxdiskspacelowwarning)
- [LinuxDiskSpaceLowCritical](#linuxdiskspacelowcritical)
- [LinuxDiskIoHigh](#linuxdiskiohigh)
- [LinuxLoadHigh](#linuxloadhigh)
- [LinuxSystemdUnitFailed](#linuxsystemdunitfailed)
- [LinuxServerDown](#linuxserverdown)
- [LinuxServerReboot](#linuxserverreboot)
- [LinuxTimeDriftWarning](#linuxtimedriftwarning)
- [LinuxSwapUsageHigh](#linuxswapusagehigh)

### Infrastructure Alerts
- [PrometheusTargetDown](#prometheustargetdown)
- [PrometheusRuleFailures](#prometheusrulefailures)
- [PrometheusNotificationsFailing](#prometheusnotificationsfailing)
- [PrometheusStorageNearFull](#prometheusstoragnearfull)
- [LokiRequestErrors](#lokirequesterrors)
- [LokiIngestionRateHigh](#lokiingestionratehigh)
- [AlertmanagerNotificationsFailing](#alertmanagernotificationsfailing)
- [FleetHighCpuServers](#fleethighcpuservers)
- [FleetLowDiskServers](#fleetlowdiskservers)
- [FleetServersNotReporting](#fleetserversnotreporting)

### Alert Routing
- [Routing Hierarchy](#routing-hierarchy)
- [Adding a New Site](#adding-a-new-site)
- [Testing Route Matching](#testing-route-matching)
- [Teams Adaptive Card Template](#teams-adaptive-card-template)

### Role-Specific Alerts
- [AdReplicationFailure](#adreplicationfailure)
- [AdLdapSearchSlow](#adldapsearchslow)
- [DnsQueryFailureRateHigh](#dnsqueryfailureratehigh)
- [AdCriticalServiceDown](#adcriticalservicedown)
- [SqlBufferCacheHitRatioLow](#sqlbuffercachehitratiolow)
- [SqlPageLifeExpectancyLow](#sqlpagelifeexpectancylow)
- [SqlDeadlocksDetected](#sqldeadlocksdetected)
- [SqlCriticalServiceDown](#sqlcriticalservicedown)
- [IisHighErrorRate](#iishigherrorrate)
- [IisAppPoolDown](#iisapppooldown)
- [IisHighConnectionCount](#iishighconnectioncount)
- [FileServerDiskIoHigh](#fileserverdiskiohigh)
- [FileServerServiceDown](#fileserverservicedown)
- [DockerDaemonDown](#dockerdaemondown)

---

## Windows Server Alerts

### WindowsCpuHighWarning
**Severity**: Warning | **Threshold**: >85% for 10m

**Investigate**:
1. Check top processes: `Get-Process | Sort-Object CPU -Descending | Select -First 10`
2. Check for scheduled tasks running: Task Scheduler > Active Tasks
3. Check for Windows Update activity: `Get-WUHistory -Last 5`
4. Review CPU trend in Grafana Windows Server dashboard

**Remediate**:
- Kill or restart the offending process if non-critical
- Reschedule resource-intensive tasks to off-hours
- If persistent, consider scaling the server (add vCPUs)

### WindowsCpuHighCritical
**Severity**: Critical | **Threshold**: >95% for 5m

**Investigate**: Same as warning, plus:
1. Check if server is responsive via RDP
2. Check Event Log for application crashes or hangs

**Remediate**:
- Immediate: Kill the offending process
- If unresponsive, restart the server from hypervisor/cloud console

### WindowsMemoryHighWarning
**Severity**: Warning | **Threshold**: >85% for 10m

**Investigate**:
1. Check top memory consumers: `Get-Process | Sort-Object WorkingSet64 -Descending | Select -First 10`
2. Check for memory leaks: compare current vs baseline working set size
3. Check commit charge vs physical memory

**Remediate**:
- Restart the leaking application
- If persistent, add memory to the VM

### WindowsMemoryHighCritical
**Severity**: Critical | **Threshold**: >95% for 5m

**Investigate**: Same as warning, plus check page file usage.

**Remediate**: Restart the highest memory consumer or restart the server.

### WindowsDiskSpaceLowWarning
**Severity**: Warning | **Threshold**: <20% free for 15m

**Investigate**:
1. Check which files consume space: `TreeSize` or `WinDirStat`
2. Check for log file growth, temp files, Windows Update cache
3. Check for database transaction log growth (SQL servers)

**Remediate**:
- Clean temp files: `Disk Cleanup` or `cleanmgr.exe`
- Purge old logs: remove files in `C:\Windows\Temp`, application log directories
- Expand the volume if cleanup is insufficient

### WindowsDiskSpaceLowCritical
**Severity**: Critical | **Threshold**: <10% free for 5m

**Remediate**: Same as warning but with urgency. Services may crash if disk fills completely.

### WindowsServiceDown
**Severity**: Warning | **Threshold**: Not running for 5m

**Investigate**:
1. Check service status: `Get-Service -Name <service>`
2. Check Event Log for error events from the service
3. Check if the service was intentionally stopped (change window)

**Remediate**:
- Restart the service: `Start-Service -Name <service>`
- If it fails to start, check dependencies and error logs

### WindowsServerReboot
**Severity**: Info | **Threshold**: Uptime < 10 minutes

**Investigate**:
1. Was the reboot planned (maintenance window)?
2. Check Event Log for unexpected shutdown reason (Event ID 6008)

### WindowsServerDown
**Severity**: Critical | **Threshold**: No metrics for 3m

**Investigate**:
1. Ping the server
2. Check hypervisor/cloud console for VM state
3. Check network connectivity (VLAN, firewall rules)
4. Check Alloy agent service status if server is reachable

**Remediate**:
- If server is powered off, start it
- If Alloy agent is stopped, restart it
- If network issue, engage network team

### WindowsTimeDriftWarning
**Severity**: Warning | **Threshold**: >1s offset for 10m

**Investigate**:
1. Check W32Time service: `w32tm /query /status`
2. Check NTP source reachability: `w32tm /query /peers`

**Remediate**:
- Force time sync: `w32tm /resync`
- Fix NTP configuration if source is unreachable

---

## Linux Server Alerts

### LinuxCpuHighWarning
**Severity**: Warning | **Threshold**: >85% for 10m

**Investigate**:
1. Check top processes: `top -bn1 | head -20`
2. Check for cron jobs running
3. Review CPU trend in Grafana Linux Server dashboard

**Remediate**: Kill or nice the offending process. Reschedule batch jobs.

### LinuxCpuHighCritical
**Severity**: Critical | **Threshold**: >95% for 5m

**Remediate**: Kill the offending process. If unresponsive, restart from console.

### LinuxMemoryHighWarning
**Severity**: Warning | **Threshold**: >85% for 10m

**Investigate**:
1. `free -h` to check available vs used
2. `ps aux --sort=-%mem | head -10` for top memory consumers
3. Check for memory leaks in application processes

### LinuxMemoryHighCritical
**Severity**: Critical | **Threshold**: >95% for 5m

**Remediate**: OOM killer may activate. Restart the largest memory consumer.

### LinuxDiskSpaceLowWarning
**Severity**: Warning | **Threshold**: <20% free for 15m

**Investigate**: `df -h` and `du -sh /var/log/* | sort -rh | head -10`

**Remediate**: Clean logs, temp files, old kernels (`apt autoremove`).

### LinuxDiskSpaceLowCritical
**Severity**: Critical | **Threshold**: <10% free for 5m

**Remediate**: Immediate cleanup. Services will fail if filesystem hits 100%.

### LinuxDiskIoHigh
**Severity**: Warning | **Threshold**: >90% busy for 15m

**Investigate**: `iostat -xz 5` to identify the bottleneck device and process.

### LinuxLoadHigh
**Severity**: Warning | **Threshold**: Normalized load >2.0 for 15m

**Investigate**: `top`, `vmstat 1 5`, check for I/O wait or CPU saturation.

### LinuxSystemdUnitFailed
**Severity**: Warning | **Threshold**: Failed state for 5m

**Investigate**: `systemctl status <unit>` and `journalctl -u <unit> -n 50`

**Remediate**: `systemctl restart <unit>`. Fix underlying issue from logs.

### LinuxServerDown
**Severity**: Critical | **Threshold**: No metrics for 3m

**Investigate**: Same as Windows -- ping, console, network, agent status.

### LinuxServerReboot
**Severity**: Info | **Threshold**: Uptime < 10 minutes

**Investigate**: Check `last reboot` and `journalctl -b -1` for previous boot logs.

### LinuxTimeDriftWarning
**Severity**: Warning | **Threshold**: >0.5s offset for 10m

**Investigate**: `timedatectl status` and `chronyc tracking` (or `ntpq -p`).

### LinuxSwapUsageHigh
**Severity**: Warning | **Threshold**: >50% swap used for 15m

**Investigate**: `free -h`, `swapon --show`. System is memory-constrained.

---

## Infrastructure Alerts

### PrometheusTargetDown
**Severity**: Critical

**Investigate**: Check if the target service is running and network is reachable.

### PrometheusRuleFailures
**Severity**: Warning

**Investigate**: Check Prometheus logs for rule evaluation errors. May indicate bad PromQL syntax after a rule file update.

### PrometheusNotificationsFailing
**Severity**: Critical

**Investigate**: Check Alertmanager is running and reachable from Prometheus.

### PrometheusStorageNearFull
**Severity**: Warning

**Investigate**: Check TSDB size with `curl prometheus:9090/api/v1/status/tsdb`. Consider reducing retention or increasing volume.

### LokiRequestErrors
**Severity**: Warning

**Investigate**: Check Loki pod logs for errors. Common causes: storage full, out of memory.

### LokiIngestionRateHigh
**Severity**: Warning

**Investigate**: Identify which agent is sending excessive logs. Check for log spam (chatty application, debug logging left on).

### AlertmanagerNotificationsFailing
**Severity**: Critical

**Investigate**: Check Alertmanager logs. Verify Teams webhook URL is valid and network allows outbound HTTPS to Microsoft.

### FleetHighCpuServers
**Severity**: Warning

**Investigate**: Multiple servers with high CPU may indicate a deployment rollout, batch job storm, or external attack.

### FleetLowDiskServers
**Severity**: Warning

**Investigate**: Check for common cause (log rotation failure, Windows Update cache, database growth).

### FleetServersNotReporting
**Severity**: Critical

**Investigate**: Significant drop in reporting servers indicates a network partition, DNS failure, or widespread outage.

---

## Role-Specific Alerts

### AdReplicationFailure
**Severity**: Critical

**Investigate**: `repadmin /replsummary` and `repadmin /showrepl`. Check network between DCs.

### AdLdapSearchSlow
**Severity**: Warning

**Investigate**: Check NTDS service health, database integrity. Run `dcdiag /v`.

### DnsQueryFailureRateHigh
**Severity**: Warning

**Investigate**: `dnscmd /statistics` or DNS Server event log. Check forwarder reachability.

### AdCriticalServiceDown
**Severity**: Critical

**Investigate**: Check Event Log. Attempt service restart. Run `dcdiag`.

### SqlBufferCacheHitRatioLow
**Severity**: Warning

**Investigate**: Check memory allocation to SQL Server. Review query plans for table scans.

### SqlPageLifeExpectancyLow
**Severity**: Warning

**Investigate**: Memory pressure. Check for large queries consuming buffer pool.

### SqlDeadlocksDetected
**Severity**: Warning

**Investigate**: Enable deadlock trace flags (1204, 1222). Review application query patterns.

### SqlCriticalServiceDown
**Severity**: Critical

**Investigate**: SQL Server error log, Windows Event Log. Attempt service restart.

### IisHighErrorRate
**Severity**: Warning

**Investigate**: Check IIS logs for 5xx errors. Review application logs for exceptions.

### IisAppPoolDown
**Severity**: Critical

**Investigate**: Check Event Log for W3SVC errors. Restart IIS: `iisreset`.

### IisHighConnectionCount
**Severity**: Warning

**Investigate**: Check for connection leaks, slow responses, or traffic spike.

### FileServerDiskIoHigh
**Severity**: Warning

**Investigate**: `perfmon` disk counters. Identify which shares/files are causing I/O.

### FileServerServiceDown
**Severity**: Critical

**Investigate**: Check LanmanServer and DFSR service status. Restart services.

### DockerDaemonDown
**Severity**: Critical

**Investigate**: `systemctl status docker` and `journalctl -u docker`. Restart Docker daemon.

---

## Alert Routing Architecture

### Routing Hierarchy

Alertmanager routes alerts through a two-level hierarchy:

1. **Severity tier** (critical / warning / info) -- determines urgency and timing
2. **Datacenter tier** (site-a / site-b / site-c / ...) -- determines which ops team receives the alert

Each combination of severity and datacenter maps to a dedicated receiver that delivers notifications to both Teams (webhook) and the site-specific email distribution list.

### Routing Flow

```
Alert fires with labels: severity=critical, datacenter=site-a
  |
  v
Route tree evaluates severity=critical child
  |
  v
Datacenter child routes check datacenter label:
  - datacenter=site-a  -> site_a_critical receiver (Teams + site-a-ops@example.com)
  - datacenter=site-b  -> site_b_critical receiver (Teams + site-b-ops@example.com)
  - datacenter=site-c  -> site_c_critical receiver (Teams + site-c-ops@example.com)
  - (no match)          -> teams_and_email fallback (Teams + ops-team@example.com)
```

### Severity Behavior

| Severity | Channels | Group Wait | Repeat Interval | Site Routing |
|----------|----------|------------|-----------------|--------------|
| Critical | Teams + Email | 15s | 1h | Yes -- per-site email DL |
| Warning  | Teams + Email | 30s (default) | 4h | Yes -- per-site email DL |
| Info     | Teams only | 30s (default) | 12h | No -- informational only |

### Adding a New Site

To add a site to the routing tree:

1. **alertmanager.yml** -- Add two new routes (critical + warning) and two new receivers:
   - Route: `match: { datacenter: <site-name> }` under the critical and warning sections
   - Receiver: `site_<name>_critical` with Teams webhook + email to `<site>-ops@example.com`
   - Receiver: `site_<name>_warning` with Teams webhook + email to `<site>-ops@example.com`

2. **notifiers.yml** -- Add a new Grafana contact point and notification policy entries:
   - Contact point: `Site-<Name> Email` with the site email DL
   - Policy routes: `datacenter = <site-name>` under critical and warning tiers

3. **.env** -- Add `SITE_<NAME>_EMAIL=<site>-ops@yourcompany.com`

4. **Helm values.yaml** -- Add the site to `alertmanager.notifications.siteEmails`

### Fallback Behavior

Alerts from datacenters that are not explicitly mapped in the routing tree fall through to the default receiver:

- **Critical**: `teams_and_email` -- delivers to Teams and the catch-all `ops-team@example.com`
- **Warning**: `teams_default` -- delivers to Teams only
- **Info**: `teams_info` -- delivers to Teams only (no resolved notifications)

This ensures no alerts are dropped during incremental site onboarding.

### Inhibition Rules

Two inhibition rules suppress noise when higher-severity conditions exist:

1. **Server-down suppression**: If `WindowsServerDown` or `LinuxServerDown` fires for a host, all warning/info alerts for that same hostname are suppressed.
2. **Pipeline failure suppression**: If `PrometheusNotificationsFailing` fires, all `Fleet*` alerts are suppressed since the monitoring pipeline itself is unreliable.

### Testing Route Matching

Use `amtool` to verify which receiver an alert would route to:

```bash
# Test a critical alert from site-a
amtool config routes test --config.file=configs/alertmanager/alertmanager.yml \
  severity=critical datacenter=site-a alertname=WindowsCpuHighCritical hostname=web01

# Test a warning alert from an unmapped datacenter
amtool config routes test --config.file=configs/alertmanager/alertmanager.yml \
  severity=warning datacenter=site-z alertname=LinuxMemoryHighWarning hostname=db01

# Test an info alert (no site routing)
amtool config routes test --config.file=configs/alertmanager/alertmanager.yml \
  severity=info datacenter=site-a alertname=WindowsServerReboot hostname=app01
```

### Teams Adaptive Card Template

The Teams notification template (`configs/alertmanager/templates/teams.tmpl`) renders an Adaptive Card with:

- **Header**: Alert status (FIRING/RESOLVED) with color coding
- **Summary facts**: Severity, datacenter, environment, category, alert count
- **Per-alert blocks**: Each alert in the group renders its own section with hostname, summary, and description
- **Dashboard link**: If the alert has a `dashboard_url` annotation, an "Open in Grafana" action button appears

To add dashboard links to your alert rules, include the `dashboard_url` annotation:

```yaml
annotations:
  summary: "High CPU on {{ $labels.hostname }}"
  description: "CPU usage is above 90% for 5 minutes."
  dashboard_url: "https://grafana.example.com/d/windows-overview?var-hostname={{ $labels.hostname }}"
```
