# Dashboard Navigation Guide

How to find and use the monitoring dashboards. Written for sysadmins -- no PromQL or technical knowledge required.

---

## Navigation Flow

Dashboards follow a **drill-down pattern**: start broad, click to narrow.

```
Enterprise NOC (all sites at a glance)
    |
    v  click a site
Site Overview (one site, all servers)
    |
    v  click a server or role
Role Dashboard (one server, detailed metrics)
    |
    v  need logs?
Log Explorer (search logs by host, time, keyword)
```

You should rarely need to navigate more than 3 clicks deep.

---

## Dashboard Folders

Dashboards are organized into 4 folders in the left sidebar:

| Folder | What It Contains | Who Uses It |
|--------|-----------------|-------------|
| **Enterprise** | NOC overview, SLA availability, probing status, audit trail | NOC operators, management, anyone needing fleet-wide view |
| **Servers** | Per-server dashboards for Windows, Linux, and each role (DC, SQL, IIS, etc.) | Sysadmins investigating a specific server |
| **Infrastructure** | Site overview, infrastructure health, network, hardware, certificates | Sysadmins and engineers investigating site or infrastructure issues |
| **SCOM Monitoring** | Dashboards reading from the SCOM Data Warehouse (legacy data) | Anyone familiar with SquaredUp looking for SCOM-equivalent views |

---

## Enterprise Dashboards

### Enterprise NOC

**When to use**: First thing in the morning, or when you need a fleet-wide picture.

**What it shows**:
- Grid of all sites with health indicators (green/yellow/red)
- Total server count, alert count, and uptime summary
- Top problem servers across all sites

**How to use**:
- Each site tile shows the number of healthy/warning/critical servers
- Click a site tile to jump to the Site Overview for that site

### SLA Availability

**When to use**: Monthly reporting, management reviews, SLA compliance checks.

**What it shows**:
- Uptime percentage per site, per role, and per host
- Availability trends over time
- Fleet-wide availability summary

### Probing Overview

**When to use**: Checking external endpoint availability (HTTP, ICMP, TCP, DNS probes).

**What it shows**:
- Status of all probe targets (up/down)
- Response time trends
- Failed probes highlighted in red

### Audit Trail

**When to use**: Security reviews, change tracking, investigating who did what.

**What it shows**:
- Grafana login events
- Dashboard and alert rule changes
- API key usage

---

## Server Dashboards

### Windows Server Overview

**When to use**: Investigating a Windows server alert or checking server health.

**Filters**: Use the **hostname** dropdown at the top to select a server.

**Panels**:
| Panel | What It Shows | When to Worry |
|-------|--------------|---------------|
| CPU Utilization | Percentage of CPU in use | Above 90% sustained = investigate. Above 95% = act now. |
| Memory Utilization | Percentage of RAM in use | Above 90% sustained = investigate. SQL/Exchange servers may normally run higher. |
| Disk Free (%) | Free space per drive letter | Below 20% = plan cleanup. Below 10% = urgent. |
| Disk I/O | Read/write throughput and busy percentage | Above 90% busy sustained = storage bottleneck. |
| Network Throughput | Bytes in/out per second | Informational. Compare to baseline for anomalies. |
| Services | Count of stopped critical services | Any stopped service = investigate. |
| Uptime | Time since last reboot | Recent reboot (< 1 day) may indicate an issue. |

### Linux Server Overview

**When to use**: Same as Windows, but for Linux servers.

**Filters**: **hostname** dropdown.

**Additional panels** compared to Windows:
| Panel | What It Shows | When to Worry |
|-------|--------------|---------------|
| Load Average | Normalized system load per CPU | Above 1.0 = overloaded. Above 2.0 = severely overloaded. |
| Swap Usage | Swap space in use | Above 50% = memory pressure. Investigate what's consuming RAM. |
| Systemd Units | Failed systemd services | Any failed unit needs investigation. |

### Domain Controller Overview

**When to use**: AD replication alerts, LDAP performance issues, DC health checks.

**Filters**: **hostname** dropdown (filtered to DCs only).

**Key panels**:
- LDAP Searches/sec -- baseline varies, watch for drops to zero (DC not serving queries)
- Replication status -- any non-zero failure count is actionable
- DNS queries/sec -- watch for spikes (possible auth storm) or drops (DNS failure)
- Critical services: NTDS, DNS, Netlogon, KDC, ADWS -- all must be running

### SQL Server Overview

**When to use**: SQL performance alerts, database health checks.

**Filters**: **hostname** dropdown (filtered to SQL servers).

**Key panels**:
- Buffer Cache Hit Ratio -- below 90% means SQL needs more memory
- Page Life Expectancy -- below 300 seconds means severe memory pressure
- Batch Requests/sec -- baseline varies, sudden drops indicate an issue
- Deadlocks -- any sustained deadlocks need application investigation
- Database sizes and growth trends

### IIS Web Server Overview

**When to use**: Web application issues, 5xx error spikes, connection count alerts.

**Filters**: **hostname** dropdown (filtered to IIS servers).

**Key panels**:
- HTTP status code breakdown (2xx, 4xx, 5xx rates)
- Active connections
- Request rate (requests/sec)
- App pool status (running/stopped)

### File Server Overview

**When to use**: File server performance issues, SMB session monitoring, DFSR health.

**Key panels**:
- SMB sessions and open files
- Disk I/O per volume
- DFS replication status

### Docker Host Overview

**When to use**: Container health, Docker daemon issues.

**Key panels**:
- Container count by state (running, stopped, paused)
- Per-container CPU and memory usage
- Docker engine metrics

### DHCP Server Overview

**When to use**: DHCP scope exhaustion, NAK rate alerts.

### Certificate Authority Overview

**When to use**: AD CS health, certificate issuance trends.

### Log Explorer

**When to use**: Searching for specific log entries, correlating logs with metric anomalies.

**How to use**:
1. Select the **hostname** from the dropdown
2. Set the time range to the period you're investigating
3. Use the search box to filter by keyword (e.g., "error", "failed", "denied")
4. Windows logs show Event ID, source, and level
5. Linux logs show systemd unit, priority, and message

---

## Infrastructure Dashboards

### Infrastructure Overview

**When to use**: Fleet-wide health check, identifying problem servers across all sites.

**What it shows**:
- Server count by site and role
- Top servers by CPU, memory, and disk usage
- Alert summary grouped by severity

### Site Overview

**When to use**: Checking all servers at a specific site.

**Filters**: **datacenter** dropdown to select a site.

**What it shows**:
- All servers at the selected site with health status
- Per-server CPU, memory, disk summary in a table
- Click any row to drill down to the server's detailed dashboard

### Network Overview

**When to use**: Network device monitoring, interface utilization, SNMP alerts.

**What it shows**:
- Network device status (up/down)
- Interface utilization per device
- Error rates and packet loss

### Physical Server Health

**When to use**: Hardware alerts (Redfish/BMC), temperature, drive health.

**What it shows**:
- BMC health status per server
- Temperature readings
- Drive and memory health
- Power supply status

### Certificate Overview

**When to use**: TLS certificate expiry tracking, probe status.

**What it shows**:
- All monitored certificates with expiry dates
- Color-coded: green (> 90 days), yellow (30-90 days), red (< 30 days)
- Probe failures highlighted

---

## SCOM Monitoring Dashboards

These dashboards read directly from the SCOM Data Warehouse SQL Server. They show the same data that SquaredUp displays, replacing it with zero new agents. Use the **Site** dropdown to filter by datacenter and the **Server** dropdown to drill into a specific host.

**Navigation flow**: Fleet Overview (all sites) -> select a site -> select a server -> Server Overview or role-specific dashboard.

### SCOM Fleet Overview

**What it shows**: Fleet-wide summary with per-site breakdown table (server count, avg CPU, avg memory per site), top 10 problem servers by CPU, memory, and disk. Fleet CPU trend over time.

**When to use**: Starting point for fleet-wide health. Click a site name in the Per-Site Summary to filter, or click a server name in the Top 10 tables to drill into Server Overview.

### SCOM Server Overview

**What it shows**: Single-server detail view with CPU, memory, disk free space, processor queue, disk latency, disk throughput, and network throughput. All data from SCOM performance counters.

**When to use**: Investigating a specific server's performance. Typically reached by clicking a server name from Fleet Overview or other dashboards.

### SCOM Health State

**What it shows**: Count of healthy, warning, critical, and maintenance-mode servers. Server health table sorted by state. Health state changes over time chart.

**When to use**: Quick check on which servers are in a degraded state.

### SCOM Alerts

**What it shows**: Active alert counts by severity, active alerts table with server and timestamp, alert trend chart, recently resolved alerts with resolution duration.

**When to use**: Reviewing current and recent SCOM alerts. Filter by severity to focus on critical issues.

### SCOM AD/DC

**What it shows**: Active Directory Domain Controller metrics -- LDAP searches/sec, Kerberos and NTLM authentication rates, DRA replication traffic, DNS query volume.

**When to use**: Investigating AD authentication or replication issues at a specific site.

### SCOM IIS

**What it shows**: IIS web server metrics -- current connections, requests/sec, bandwidth, error rates.

**When to use**: Investigating web application performance issues.

### SCOM DHCP

**What it shows**: DHCP server metrics -- request rates, acknowledgment rates, queue depth, packet throughput.

**When to use**: Investigating DHCP lease issues at a specific site.

### SCOM DNS

**What it shows**: DNS server metrics -- total query volume, recursive queries, dynamic update rates.

**When to use**: Investigating DNS resolution performance. DNS runs on Domain Controllers.

### SCOM DFS Replication

**What it shows**: DFS staging space usage, conflict space, and bandwidth savings for replication-enabled servers (Domain Controllers and File Servers).

**When to use**: Investigating file replication backlog or conflict issues.

### SCOM Exchange

**What it shows**: Exchange Server mail flow (messages/sec), queue length, client connections, RPC latency, database I/O latency, and database size.

**When to use**: Investigating Exchange mail delivery or database performance issues. Note: this dashboard only shows data when connected to the production SCOM DW (Exchange counters are not in the simulator).

---

## Using Filters

Most dashboards have dropdown filters at the top:

| Filter | What It Does | Dashboards | How to Use |
|--------|-------------|------------|------------|
| **hostname** | Show data for a single server | Prometheus/Loki dashboards | Type the server name or scroll the list |
| **datacenter** | Filter to a single site | Prometheus/Loki dashboards | Select your site code |
| **role** | Filter to servers with a specific role | Prometheus/Loki dashboards | Select `dc`, `sql`, `iis`, etc. |
| **environment** | Filter to prod, staging, or dev | Prometheus/Loki dashboards | Usually left on `prod` |
| **Site** | Filter to a datacenter | SCOM dashboards | Select site code (DEN, SOL, etc.) or "All" |
| **Server** | Show data for a single server | SCOM dashboards | Cascades from Site selection. Lists only servers at the selected site. |
| **Severity** | Filter alerts by severity level | SCOM Alerts dashboard | Select "All", "Critical", or "Warning" |

Filters persist across panels on the same dashboard. Changing a filter updates all panels simultaneously.

---

## Understanding Colors

Consistent across all dashboards:

| Color | Meaning |
|-------|---------|
| **Green** | Healthy. Value is within normal range. |
| **Yellow** | Warning. Value is elevated but not critical. Investigate when convenient. |
| **Red** | Critical. Value is in a dangerous range. Act now. |
| **Gray/No Data** | No data received. The server may be down, the agent may not be installed, or the metric is not applicable. |

---

## Tips

- **Bookmark your site's overview**: Set `?var-datacenter=<your-site-code>` in the URL to pre-filter to your site
- **Use time range controls**: Click the time picker (top right) to zoom into a specific period. Use "Last 1 hour" for recent issues, "Last 7 days" for trends.
- **Click panel titles**: Many panels have drill-down links. Click the panel title to see options.
- **Full-screen a panel**: Hover over a panel and press `v` to view it in full screen. Press `Escape` to return.

---

## Glossary

| Term | Meaning |
|------|---------|
| **Alloy** | The agent software installed on each monitored server. Collects metrics and logs. |
| **Prometheus** | The metrics database. Stores time-series data (CPU, memory, etc.). |
| **Loki** | The log database. Stores Windows Event Logs and Linux journal entries. |
| **Alertmanager** | The notification engine. Routes alerts to Teams and email. |
| **Grafana** | The dashboard application you're looking at. Reads from Prometheus and Loki. |
| **PromQL** | Prometheus Query Language. Used internally by dashboards. You don't need to know it. |
| **Recording rule** | A pre-computed metric that makes dashboards faster. Runs in Prometheus. |
| **Datacenter** | The `datacenter` label. A site code like `dv`, `ent`, `sbt`. |
| **Role** | The `role` label. A server function like `dc`, `sql`, `iis`, `generic`. |
| **Mute timing** | A scheduled period when alerts are suppressed (maintenance window). |
| **Silence** | An ad-hoc suppression of alerts, usually for a specific server or alert type. |
| **SCOM** | System Center Operations Manager. The existing monitoring platform. SCOM agents collect data and store it in the Data Warehouse. |
| **SCOM DW** | SCOM Data Warehouse. A SQL Server database (`OperationsManagerDW`) containing historical performance, state, and alert data from SCOM agents. |
| **SquaredUp** | The previous dashboard tool ($26K/year) that read from the SCOM DW. Replaced by Grafana SCOM dashboards. |
| **Management Pack** | A SCOM plugin that defines what to monitor for a specific role (SQL Server MP, IIS MP, AD MP, etc.). Determines which performance counters are collected. |
