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

### Hardware Alerts (Redfish/BMC)
- [RedfishBMCUnreachable](#redfishbmcunreachable)
- [RedfishHealthWarning](#redfishhealthwarning)
- [RedfishHealthCritical](#redfishhealthcritical)
- [RedfishTemperatureHigh](#redfishtemperaturehigh)
- [RedfishTemperatureCritical](#redfishtemperaturecritical)
- [RedfishServerPoweredOff](#redfishserverpoweredoff)
- [RedfishDriveUnhealthy](#redfishdriveunhealthy)
- [RedfishMemoryUnhealthy](#redfishmemoryunhealthy)

### Certificate Alerts
- [TLSCertExpiring90Days](#tlscertexpiring90days)
- [TLSCertExpiring30Days](#tlscertexpiring30days)
- [TLSCertExpiring7Days](#tlscertexpiring7days)
- [TLSCertExpired](#tlscertexpired)
- [TLSCertProbeFailure](#tlscertprobefailure)

### Lansweeper / Asset Alerts
- [AssetWarrantyExpiring90Days](#assetwarrantyexpiring90days)
- [AssetWarrantyExpiring60Days](#assetwarrantyexpiring60days)
- [AssetWarrantyExpiring30Days](#assetwarrantyexpiring30days)
- [AssetWarrantyExpired](#assetwarrantyexpired)
- [AssetNotSeenByLansweeper7Days](#assetnotseenbylansweeper7days)

### SNMP Network Device Alerts
- [SNMPDeviceUnreachable](#snmpdeviceunreachable)
- [SNMPDeviceReboot](#snmpdevicereboot)
- [SNMPInterfaceDown](#snmpinterfacedown)
- [SNMPInterfaceHighUtilization](#snmpinterfacehighutilization)
- [SNMPInterfaceSaturated](#snmpinterfacesaturated)
- [SNMPInterfaceErrors](#snmpinterfaceerrors)

### Probe Alerts
- [HTTPProbeFailed](#httpprobefailed)
- [HTTPProbeSlow](#httpprobeslow)
- [ICMPProbeFailed](#icmpprobefailed)
- [ICMPProbeHighLatency](#icmpprobehighlatency)
- [TCPProbeFailed](#tcpprobefailed)
- [DNSProbeFailed](#dnsprobefailed)
- [ProbeTargetMissing](#probetargetmissing)

### Endpoint Monitoring Alerts
- [FileSizeExceeded](#filesizeexceeded)
- [DirectorySizeExceeded](#directorysizeexceeded)
- [FileStale](#filestale)
- [WindowsProcessNotRunning](#windowsprocessnotrunning)
- [LinuxProcessNotRunning](#linuxprocessnotrunning)

### Outage Detection Alerts
- [SitePartialOutage](#sitepartialoutage)
- [SiteMajorOutage](#sitemajoroutage)
- [RolePartialOutage](#rolepartialoutage)

### SNMP Trap Alerts
- [SNMP Trap: Link Down](#snmp-trap-link-down)
- [SNMP Trap: Authentication Failure](#snmp-trap-authentication-failure)
- [SNMP Trap: Device Cold Start](#snmp-trap-device-cold-start)
- [SNMP Trap: High Volume from Device](#snmp-trap-high-volume-from-device)

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

## Hardware Alerts (Redfish/BMC)

### RedfishBMCUnreachable
**Severity**: Warning | **Threshold**: BMC endpoint unreachable for 10m

**Investigate**:
1. Verify BMC/iLO/iDRAC network connectivity: ping the BMC IP from the monitoring server
2. Check if the BMC is on a separate management VLAN -- verify routing between Prometheus and the management network
3. Log into the BMC web interface directly to confirm it is responsive
4. Check if the BMC firmware was recently updated (may be rebooting)

**Remediate**:
- If BMC is reachable via browser but not from Prometheus, check firewall rules on the management VLAN
- If BMC is completely unresponsive, perform an AC power cycle on the server (physical or remote PDU) to reset the BMC
- If recurring, check BMC firmware version and update if outdated

### RedfishHealthWarning
**Severity**: Warning | **Threshold**: BMC reports degraded/non-critical health for 5m

**Investigate**:
1. Log into the BMC web interface and check the system event log
2. Identify which component is degraded (fan, PSU, RAID controller, NIC)
3. Check if the server is still operational (degraded does not mean down)

**Remediate**:
- Single fan failure: schedule replacement during next maintenance window
- PSU warning: check for redundant PSU. If redundant, schedule replacement. If not, escalate.
- RAID degradation: check for failed/rebuilding drive. See RedfishDriveUnhealthy.
- Open a hardware support ticket with the vendor if under warranty

### RedfishHealthCritical
**Severity**: Critical | **Threshold**: BMC reports critical hardware fault for 2m

**Investigate**:
1. Immediately check server availability -- can users access services?
2. Log into BMC and check the system event log for the specific failure
3. Check if automatic failover has occurred (cluster, load balancer)

**Remediate**:
- If server is down, initiate failover to backup/cluster member
- Open an urgent hardware support ticket with the vendor
- Do not attempt to restart the server until the hardware fault is diagnosed -- restarting with a critical fault may cause data loss

### RedfishTemperatureHigh
**Severity**: Warning | **Threshold**: Component > 75C for 10m

**Investigate**:
1. Check which component is hot (CPU, GPU, ambient, inlet)
2. Check datacenter environmental monitoring for HVAC issues
3. Check if other servers in the same rack are also reporting high temps
4. Check server fan speeds in BMC -- are fans running at full speed?

**Remediate**:
- If datacenter-wide: escalate to facilities team for HVAC investigation
- If single server: check for blocked airflow, failed fans, or improper rack placement
- If CPU-specific: check for sustained 100% CPU workload driving thermal output

### RedfishTemperatureCritical
**Severity**: Critical | **Threshold**: Component > 85C for 5m

**Investigate**: Same as warning, but urgent. Server may auto-shutdown to protect hardware.

**Remediate**:
- Reduce workload immediately (migrate VMs, stop non-essential services)
- If approaching shutdown threshold, perform a controlled shutdown before the server crashes
- Escalate to facilities for emergency HVAC response if datacenter-wide

### RedfishServerPoweredOff
**Severity**: Critical | **Threshold**: Chassis powered off but BMC reachable for 5m

**Investigate**:
1. Was this a planned shutdown? Check maintenance windows and change management
2. Check BMC event log for the reason (thermal shutdown, power failure, manual action)
3. Check PDU/UPS for power events

**Remediate**:
- If unplanned, power on the server via BMC remote console
- If thermal shutdown, do NOT power on until temperature issue is resolved
- If power event, verify UPS and PDU health before restarting

### RedfishDriveUnhealthy
**Severity**: Warning | **Threshold**: Storage drive health non-OK for 5m

**Investigate**:
1. Log into BMC and identify the failed/failing drive (slot number, serial)
2. Check RAID controller status -- is the array degraded or rebuilding?
3. Determine if the array is still redundant (can it survive another drive failure?)

**Remediate**:
- If RAID is redundant (degraded but functional): schedule drive replacement during next maintenance window
- If RAID has no remaining redundancy: escalate immediately -- another drive failure means data loss
- Order replacement drive and coordinate hot-swap if supported

### RedfishMemoryUnhealthy
**Severity**: Warning | **Threshold**: DIMM health non-healthy for 5m

**Investigate**:
1. Check BMC event log for the specific DIMM slot and error type (correctable ECC, uncorrectable, thermal)
2. Check OS event logs for machine check exceptions (MCE)
3. Determine if the system has automatically disabled the DIMM or reduced memory capacity

**Remediate**:
- Correctable ECC errors: monitor trend. If error rate is increasing, schedule DIMM replacement
- Uncorrectable errors: schedule replacement soon -- risk of OS crash or data corruption
- Open hardware support ticket with DIMM slot and error details

---

## Certificate Alerts

### TLSCertExpiring90Days
**Severity**: Info | **Threshold**: Certificate expires in 30-90 days

**Investigate**:
1. Identify the certificate and service (check the `target` label for the endpoint)
2. Determine the certificate authority (internal CA, Let's Encrypt, commercial CA)
3. Check if auto-renewal is configured

**Remediate**:
- If auto-renewal is configured: verify renewal mechanism is working. No action needed.
- If manual renewal: add to the renewal tracking queue. Coordinate with the certificate owner.
- This is a planning alert -- no immediate action required.

### TLSCertExpiring30Days
**Severity**: Warning | **Threshold**: Certificate expires in 7-30 days

**Investigate**: Same as 90-day alert, but renewal should already be in progress.

**Remediate**:
- If renewal is not started, escalate to the certificate owner immediately
- If using a commercial CA, verify the purchase order is submitted
- If using internal CA, submit the certificate signing request (CSR)

### TLSCertExpiring7Days
**Severity**: Critical | **Threshold**: Certificate expires in 0-7 days

**Investigate**:
1. Confirm the certificate is still expiring (check via browser or `openssl s_client -connect host:port`)
2. Determine if the service can tolerate a brief outage for certificate replacement

**Remediate**:
- Install the renewed certificate immediately
- If the renewed certificate is not available, generate an emergency self-signed or Let's Encrypt certificate as a temporary fix
- Test the service after certificate replacement to confirm TLS handshake works

### TLSCertExpired
**Severity**: Critical | **Threshold**: Certificate expiry timestamp has passed

**Investigate**:
1. Users are likely experiencing TLS errors or browser warnings
2. Confirm the service is affected: `curl -v https://endpoint` to see the TLS error

**Remediate**:
- Replace the certificate immediately
- If a renewed certificate is not available, consider temporarily disabling TLS enforcement if the service is internal-only (not recommended for external-facing services)
- Post-incident: review why the certificate was not renewed before expiry. Add auto-renewal if possible.

### TLSCertProbeFailure
**Severity**: Warning | **Threshold**: Blackbox probe to certificate endpoint fails for 15m

**Investigate**:
1. Is the endpoint down entirely, or just the TLS probe failing?
2. Try connecting manually: `openssl s_client -connect host:port -servername hostname`
3. Check DNS resolution for the endpoint
4. Check firewall rules between the probe server and the endpoint

**Remediate**:
- If endpoint is down: this is a service outage, not a certificate issue. Check the appropriate service runbook.
- If endpoint is up but TLS fails: check for misconfigured certificates, expired intermediates, or protocol version mismatches
- If network issue: work with the network team to restore connectivity

---

## Lansweeper / Asset Alerts

### AssetWarrantyExpiring90Days
**Severity**: Info | **Threshold**: Hardware warranty expires in 60-90 days

**Investigate**:
1. Identify the asset from the alert labels (hostname, serial number, model)
2. Check if the asset is critical infrastructure or a candidate for retirement

**Remediate**:
- Add to procurement queue for warranty renewal or hardware refresh planning
- No immediate action required. Review during weekly operations meeting.

### AssetWarrantyExpiring60Days
**Severity**: Warning | **Threshold**: Hardware warranty expires in 30-60 days

**Investigate**: Same as 90-day alert. Renewal should be in progress.

**Remediate**:
- If renewal PO is not submitted, escalate to procurement
- If the hardware is being replaced, confirm the replacement timeline fits within the warranty window

### AssetWarrantyExpiring30Days
**Severity**: Warning | **Threshold**: Hardware warranty expires in 0-30 days

**Investigate**: Renewal should be completed or imminent.

**Remediate**:
- If renewal is not complete, escalate urgently to procurement
- If the asset is low-risk (non-production, has redundancy), document the accepted risk

### AssetWarrantyExpired
**Severity**: Critical | **Threshold**: Hardware warranty has expired

**Investigate**:
1. Is this asset critical infrastructure?
2. Does a hardware failure on this asset have a business impact?
3. Is there redundancy or a spare available?

**Remediate**:
- For critical assets: pursue retroactive warranty renewal or plan immediate hardware refresh
- For non-critical assets: document the risk and plan replacement during the next budget cycle
- Consider downgrading this alert to warning if the team does not treat warranty expiry as an emergency

### AssetNotSeenByLansweeper7Days
**Severity**: Warning | **Threshold**: Asset not visible to Lansweeper for > 7 days

**Investigate**:
1. Is the asset still powered on and network-connected?
2. Has the asset been decommissioned but not removed from inventory?
3. Is Lansweeper scanning working correctly? Check Lansweeper scan logs.

**Remediate**:
- If the asset is decommissioned: remove it from Lansweeper inventory to stop the alert
- If the asset should be visible: check network connectivity, WMI/SSH access, and Lansweeper scanning credentials
- If Lansweeper scanning is broken: restart the Lansweeper scanning service

---

## SNMP Network Device Alerts

### SNMPDeviceUnreachable
**Severity**: Critical | **Threshold**: No SNMP response for 5m

**Investigate**:
1. Ping the device management IP to check basic connectivity
2. If ping fails, check upstream switch port status
3. If ping succeeds but SNMP fails, check SNMP community string and ACLs on the device
4. Check if the device was rebooted (see SNMPDeviceReboot)

**Remediate**:
- If device is down: check power, check upstream connectivity, attempt console access
- If SNMP is blocked: verify SNMP configuration on the device (community string, permitted hosts)
- If device is completely unresponsive: escalate to network team for physical access

### SNMPDeviceReboot
**Severity**: Warning | **Threshold**: sysUpTime reset detected in 10m window

**Investigate**:
1. Was this a planned reboot? Check change management records.
2. Log into the device and check for crash dumps or error logs
3. Check if the device came back up cleanly (all interfaces operational)

**Remediate**:
- If planned: no action needed. Close the alert.
- If unplanned: investigate root cause (power event, firmware crash, memory exhaustion)
- If recurring: open a support case with the device vendor

### SNMPInterfaceDown
**Severity**: Warning | **Threshold**: Interface operationally down but admin-enabled for 5m

**Investigate**:
1. Identify the interface from the alert labels (ifDescr, ifAlias)
2. Is this an uplink, access port, or trunk?
3. Check the remote end -- is the connected device/server powered on?
4. Check for physical layer issues (cable, optic, patch panel)

**Remediate**:
- If the connected device is intentionally powered off: silence the alert or admin-disable the interface
- If physical issue: check/replace the cable or optic
- If uplink: this may indicate a larger outage. Check for SitePartialOutage alerts.

### SNMPInterfaceHighUtilization
**Severity**: Warning | **Threshold**: Interface utilization > 85% for 30m

**Investigate**:
1. Identify the interface and its role (uplink, server port, WAN link)
2. Check traffic patterns in the network dashboard -- is this a spike or sustained?
3. Identify top talkers if your switch supports flow data (NetFlow/sFlow)

**Remediate**:
- If temporary spike (backups, data migration): no action needed, monitor
- If sustained: consider upgrading the link (1G -> 10G) or adding link aggregation
- If unexpected: investigate for network loops, broadcast storms, or misconfigured applications

### SNMPInterfaceSaturated
**Severity**: Critical | **Threshold**: Interface utilization > 95% for 5m

**Investigate**: Same as high utilization, but immediate. Packet loss is likely occurring.

**Remediate**:
- Identify and throttle the traffic source if possible
- If a critical uplink: reroute traffic or add capacity immediately
- This is causing user-visible degradation -- treat as an active incident

### SNMPInterfaceErrors
**Severity**: Warning | **Threshold**: Error rate > 1/sec for 15m

**Investigate**:
1. Check error type: CRC errors suggest physical layer issues, alignment errors suggest duplex mismatch
2. Check both ends of the connection
3. Look for environmental factors (EMI, cable routing near power cables)

**Remediate**:
- Replace the cable or optic
- If duplex mismatch: configure both ends to the same speed/duplex (preferably auto-negotiate)
- If persists after cable replacement: suspect a failing port on the switch or NIC

---

## Probe Alerts

### HTTPProbeFailed
**Severity**: Critical | **Threshold**: HTTP endpoint unreachable for 3m

**Investigate**:
1. Try accessing the endpoint from your browser or curl
2. Check if the server hosting the service is up (ping, RDP/SSH)
3. Check the application/service status on the server
4. Check load balancer health if the endpoint is behind one

**Remediate**:
- Restart the application/service
- If the server is down, see WindowsServerDown or LinuxServerDown runbooks
- If load balancer issue: check backend health and remove unhealthy backends

### HTTPProbeSlow
**Severity**: Warning | **Threshold**: Average response > 5s for 15m

**Investigate**:
1. Check application performance metrics (CPU, memory, database connections)
2. Check database query performance if the application is database-backed
3. Check network latency between the probe and the endpoint
4. Review recent deployments that may have introduced a performance regression

**Remediate**:
- If database-related: check for slow queries, missing indexes, or lock contention
- If resource-related: scale the application (more instances, more resources)
- If network-related: check for packet loss or routing changes

### ICMPProbeFailed
**Severity**: Critical | **Threshold**: ICMP ping fails for 5m

**Investigate**:
1. Is this a server or network device? Check for corresponding ServerDown or SNMPDeviceUnreachable alerts.
2. Check if ICMP is being blocked by a firewall change
3. Check the network path: traceroute to the target

**Remediate**:
- If the host is down: follow the appropriate server/device runbook
- If firewall change: revert or update the probe configuration
- If network path issue: escalate to the network team

### ICMPProbeHighLatency
**Severity**: Warning | **Threshold**: Latency > 500ms for 15m

**Investigate**:
1. Is this a LAN or WAN target? 500ms on LAN is severe; on WAN it may be normal.
2. Run a traceroute to identify where latency is introduced
3. Check for network congestion on intermediate links (see SNMPInterfaceHighUtilization)

**Remediate**:
- If WAN and expected: tune the threshold higher for WAN targets
- If LAN: investigate network congestion, duplex mismatches, or failing hardware
- If ISP-related: contact the ISP with traceroute evidence

### TCPProbeFailed
**Severity**: Critical | **Threshold**: TCP port connection fails for 3m

**Investigate**:
1. Check if the service is listening on the expected port: `netstat -an | findstr <port>` or `ss -tlnp | grep <port>`
2. Check if the service process is running
3. Check firewall rules for the port

**Remediate**:
- Restart the service if it has stopped
- If firewall change: revert or update the probe configuration
- If the service is running but not accepting connections: check service logs for binding errors or resource exhaustion

### DNSProbeFailed
**Severity**: Critical | **Threshold**: DNS resolver unresponsive for 2m

**Investigate**:
1. Test DNS resolution from another client: `nslookup example.com <dns-server-ip>`
2. Check if the DNS service is running on the target server
3. Check if this is affecting other services (DNS failure has cascading impact)

**Remediate**:
- Restart the DNS service (on Windows DCs: `Restart-Service DNS`)
- If the server is down, failover to secondary DNS
- DNS outages affect all services -- treat this as a high-priority incident

### ProbeTargetMissing
**Severity**: Warning | **Threshold**: Probe target count decreased vs 1 hour ago for 15m

**Investigate**:
1. Compare the current probe target list with the expected list
2. Check if a target was intentionally decommissioned
3. Check if the blackbox exporter configuration was modified

**Remediate**:
- If target was decommissioned: update the probe configuration to remove it
- If unintentional: restore the configuration from git
- If the target was removed from DNS: check why and restore if needed

---

## Endpoint Monitoring Alerts

### FileSizeExceeded
**Severity**: Warning | **Threshold**: File > 1GB for 5m

**Investigate**:
1. Identify the file from the alert labels (path, hostname)
2. Determine if the file is a log file, temp file, or data file
3. Check if log rotation is configured and working

**Remediate**:
- If log file: fix log rotation configuration. Truncate or archive the oversized log.
- If temp file: identify the process creating it and clean up
- If data file: determine if growth is expected. Adjust the threshold if the file legitimately grows beyond 1GB.

### DirectorySizeExceeded
**Severity**: Warning | **Threshold**: Directory > 10GB for 10m

**Investigate**:
1. Identify the directory and its purpose
2. List the largest files: `du -sh * | sort -rh | head -20` (Linux) or `Get-ChildItem -Recurse | Sort-Object Length -Descending | Select -First 20` (Windows)
3. Check if cleanup jobs are running (log rotation, temp cleanup)

**Remediate**:
- Remove old/unnecessary files from the directory
- Fix the cleanup job if it has stopped running
- Adjust the threshold if the directory legitimately exceeds 10GB

### FileStale
**Severity**: Warning | **Threshold**: File not modified > 24h for 30m

**Investigate**:
1. Identify the file -- this alert monitors files expected to be updated regularly (batch job output, heartbeat files, log files)
2. Check if the process that writes to this file is running
3. Check if the batch job or scheduled task completed successfully

**Remediate**:
- If the process is stopped: restart it
- If the batch job failed: check job logs and re-run
- If the file is no longer relevant: remove it from monitoring

### WindowsProcessNotRunning
**Severity**: Critical | **Threshold**: Expected process not running for 10m

**Investigate**:
1. Identify the process from the alert labels
2. Check if the process crashed: look in Windows Event Log (Application and System)
3. Check if the service that manages this process is in a stopped state

**Remediate**:
- Restart the process or its parent service
- If it crashes immediately after restart: check application logs for the root cause
- If a dependency is missing (database, network share), resolve the dependency first

### LinuxProcessNotRunning
**Severity**: Critical | **Threshold**: Expected process not running for 10m

**Investigate**:
1. Check if the process is running: `systemctl status <service>` or `ps aux | grep <process>`
2. Check system logs: `journalctl -u <service> --since "1 hour ago"`
3. Check for OOM kills: `dmesg | grep -i oom`

**Remediate**:
- Restart the service: `systemctl restart <service>`
- If OOM killed: increase memory limits or investigate the memory leak
- If dependency issue: check database connectivity, disk space, or network access

---

## Outage Detection Alerts

### SitePartialOutage
**Severity**: Warning | **Threshold**: < 70% hosts reporting at site (min 3 hosts) for 2m

**Investigate**:
1. Check which hosts at the site are down vs up in the NOC dashboard
2. Determine if this is a network issue (switch failure, WAN outage) or a power issue
3. Check for corresponding SNMPDeviceUnreachable alerts on site network equipment
4. Contact the site team for physical confirmation

**Remediate**:
- If network: work with the network team to restore connectivity
- If power: check UPS status and contact facilities
- This alert automatically suppresses per-host warning alerts at the affected site via inhibition rules

**Note**: This alert will NOT fire if the site has fewer than 3 monitored hosts. This prevents false outage detection at small sites.

### SiteMajorOutage
**Severity**: Critical | **Threshold**: < 30% hosts reporting at site (min 3 hosts) for 3m

**Investigate**: Same as partial outage, but the site is severely impacted.

**Remediate**:
- Treat as a major incident. Engage the site team and management immediately.
- This alert suppresses ALL per-host critical and warning alerts at the affected site. The team should focus on restoring site connectivity, not individual server alerts.
- When connectivity is restored, suppressed alerts will begin firing for any servers that have genuine issues.

### RolePartialOutage
**Severity**: Warning | **Threshold**: < 70% of role hosts reporting (min 2 hosts) for 5m

**Investigate**:
1. Check which role is affected (SQL, DC, IIS, etc.) from the alert labels
2. Determine if this is coincidental (multiple servers down for different reasons) or correlated (shared dependency failure)
3. Check for common dependencies: shared storage, network segment, load balancer

**Remediate**:
- If correlated: identify and fix the shared dependency
- If coincidental: investigate each down server individually
- This alert suppresses per-host warnings for the affected role at the affected site

---

## SNMP Trap Alerts

These alerts are Grafana-managed (not Prometheus) and fire based on Loki log queries against SNMP trap data collected by snmptrapd.

### SNMP Trap: Link Down
**Severity**: Warning | **Threshold**: linkDown trap received in 5m window

**Investigate**:
1. Identify the device and interface from the trap data in the Grafana alert details
2. Check if the interface is an uplink, access port, or management port
3. Cross-reference with SNMPInterfaceDown alerts for the same device

**Remediate**:
- If access port: the connected device was disconnected or powered off. Check with the user.
- If uplink/trunk: this is a network connectivity event. Check both ends of the link.
- If flapping (repeated link down/up): suspect a physical layer issue (bad cable, failing optic)

### SNMP Trap: Authentication Failure
**Severity**: Warning | **Threshold**: authenticationFailure trap received in 5m window

**Investigate**:
1. Identify the source IP of the failed authentication attempt from the trap data
2. Is this a known monitoring system or management tool using an incorrect community string?
3. Could this be a security event (unauthorized SNMP polling)?

**Remediate**:
- If misconfigured monitoring tool: update the community string on the tool to match the device
- If unknown source: investigate as a potential security event. Block the source IP if unauthorized.
- If this alert is very noisy due to known misconfiguration, silence it until the configuration is fixed

### SNMP Trap: Device Cold Start
**Severity**: Critical | **Threshold**: coldStart trap received in 5m window

**Investigate**:
1. The device has fully rebooted (cold start = power cycle, not just software reload)
2. Was this planned? Check change management records.
3. Cross-reference with SNMPDeviceReboot alerts

**Remediate**:
- If planned: no action needed
- If unplanned: investigate power issues (UPS, PDU, power supply failure)
- Check the device event log after it comes back up for crash information
- Verify all interfaces and routing are restored after the reboot

### SNMP Trap: High Volume from Device
**Severity**: Warning | **Threshold**: > 50 traps from one device in 10m window

**Investigate**:
1. What type of traps is the device sending? Check the Loki log explorer for trap details.
2. Is the device experiencing a flapping condition (interface up/down repeatedly)?
3. Is the device under attack or experiencing a failure condition that generates continuous traps?

**Remediate**:
- If interface flapping: fix the physical layer issue (cable, optic, port)
- If authentication storms: fix the SNMP configuration on the polling source
- If the device is in a failure loop: stabilize the device first, then investigate root cause
- Consider temporarily filtering traps from this device if the volume is overwhelming the log pipeline

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
