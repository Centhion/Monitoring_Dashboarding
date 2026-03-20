# Alloy Agent Deployment Guide

This guide covers deploying Grafana Alloy to Windows and Linux servers using the configuration files from this repository.

## Architecture

Alloy configs in this repository follow a modular, directory-based architecture. Alloy loads all `.alloy` files in a directory via `alloy run <dir>`, merging them into a single configuration scope.

### Config Layout

```
configs/alloy/
+-- common/                    # Shared components (deploy to EVERY server)
|   +-- labels.alloy           # Standard label taxonomy
|   +-- remote_write.alloy     # Prometheus remote_write endpoint
|   +-- loki_push.alloy        # Loki write endpoint
+-- windows/
|   +-- base.alloy             # OS metrics (deploy to EVERY Windows server)
|   +-- logs_eventlog.alloy    # Event log collection (deploy to EVERY Windows server)
|   +-- role_dc.alloy          # Domain Controller role (deploy only to DCs)
|   +-- role_sql.alloy         # SQL Server role (deploy only to SQL servers)
|   +-- role_iis.alloy         # IIS Web Server role (deploy only to IIS servers)
|   +-- role_fileserver.alloy  # File Server role (deploy only to file servers)
+-- linux/
    +-- base.alloy             # OS metrics (deploy to EVERY Linux server)
    +-- logs_journal.alloy     # Journal log collection (deploy to EVERY Linux server)
    +-- role_docker.alloy      # Docker host role (deploy only to Docker hosts)
```

### Deployment Pattern

For each server, combine:

1. ALL files from `common/` (always required)
2. `base.alloy` from the matching OS directory (always required)
3. The OS-specific log collector (always required)
4. One or more `role_*.alloy` files matching the server's role

**Example: Windows Domain Controller**
```
common/labels.alloy
common/remote_write.alloy
common/loki_push.alloy
windows/base.alloy
windows/logs_eventlog.alloy
windows/role_dc.alloy
```

**Example: Linux Docker host**
```
common/labels.alloy
common/remote_write.alloy
common/loki_push.alloy
linux/base.alloy
linux/logs_journal.alloy
linux/role_docker.alloy
```

---

## Environment Variables

Every server running Alloy must have these environment variables set. Configs reference them via `sys.env()`.

### Required (All Servers)

| Variable | Description | Example |
|----------|-------------|---------|
| `ALLOY_ENV` | Deployment environment | `prod`, `staging`, `dev` |
| `ALLOY_DATACENTER` | Physical or logical datacenter | `us-east-1`, `site-a` |
| `ALLOY_ROLE` | Server role identifier | `dc`, `sql`, `iis`, `fileserver`, `docker`, `generic` |
| `PROMETHEUS_REMOTE_WRITE_URL` | Prometheus remote write endpoint | `http://prometheus:9090/api/v1/write` |
| `LOKI_WRITE_URL` | Loki push API endpoint | `http://loki:3100/loki/api/v1/push` |

### Role-Specific (Only Where Applicable)

| Variable | Role | Description | Default |
|----------|------|-------------|---------|
| `SQL_ERROR_LOG_PATH` | SQL Server | Path to SQL error log directory | `C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\Log` |
| `IIS_LOG_PATH` | IIS | Path to IIS W3C log files | `C:\inetpub\logs\LogFiles` |
| `DOCKER_METRICS_HOST` | Docker | Docker metrics endpoint | `127.0.0.1:9323` |
| `DOCKER_SOCKET_PATH` | Docker | Docker socket path | `unix:///var/run/docker.sock` |

---

## Windows Deployment

### 1. Install Alloy

Download and install Grafana Alloy for Windows from the Grafana releases page or use the MSI installer.

Default install path: `C:\Program Files\GrafanaLabs\Alloy\`

### 2. Deploy Config Files

Copy the appropriate config files to the Alloy config directory:

```powershell
$alloyConfigDir = "C:\Program Files\GrafanaLabs\Alloy\config"

# Always deploy common + base + logs
Copy-Item configs\alloy\common\*.alloy $alloyConfigDir
Copy-Item configs\alloy\windows\base.alloy $alloyConfigDir
Copy-Item configs\alloy\windows\logs_eventlog.alloy $alloyConfigDir

# Deploy role-specific config (example: Domain Controller)
Copy-Item configs\alloy\windows\role_dc.alloy $alloyConfigDir
```

### 3. Set Environment Variables

Set environment variables via the Windows registry (persistent across reboots). Alloy on Windows reads environment variables from:

`HKEY_LOCAL_MACHINE\SOFTWARE\GrafanaLabs\Alloy`

Or set system environment variables via PowerShell:

```powershell
[System.Environment]::SetEnvironmentVariable("ALLOY_ENV", "prod", "Machine")
[System.Environment]::SetEnvironmentVariable("ALLOY_DATACENTER", "site-a", "Machine")
[System.Environment]::SetEnvironmentVariable("ALLOY_ROLE", "dc", "Machine")
[System.Environment]::SetEnvironmentVariable("PROMETHEUS_REMOTE_WRITE_URL", "http://prometheus:9090/api/v1/write", "Machine")
[System.Environment]::SetEnvironmentVariable("LOKI_WRITE_URL", "http://loki:3100/loki/api/v1/push", "Machine")
```

### 4. Configure and Start the Service

Point Alloy at the config directory:

```powershell
# Modify the Alloy service to use the config directory
sc.exe config "Alloy" binPath= "\"C:\Program Files\GrafanaLabs\Alloy\alloy-windows-amd64.exe\" run \"C:\Program Files\GrafanaLabs\Alloy\config\""

# Restart the service
Restart-Service -Name "Alloy"
```

### 5. Verify

```powershell
# Check service status
Get-Service -Name "Alloy"

# Alloy exposes a UI at http://localhost:12345 by default
# Open in browser to see component health and data flow
Start-Process "http://localhost:12345"
```

---

## Linux Deployment

### 1. Install Alloy

Install via the Grafana APT/YUM repository:

```bash
# Debian/Ubuntu
sudo apt-get install alloy

# RHEL/CentOS
sudo yum install alloy
```

Or download the binary directly from the Grafana releases page.

### 2. Prerequisites

```bash
# Grant Alloy access to systemd journal
sudo usermod -aG systemd-journal alloy
sudo usermod -aG adm alloy

# For Docker hosts: grant Docker socket access
sudo usermod -aG docker alloy

# For Docker hosts: enable Docker metrics endpoint
# Add to /etc/docker/daemon.json:
#   { "metrics-addr": "127.0.0.1:9323" }
sudo systemctl restart docker
```

### 3. Deploy Config Files

```bash
ALLOY_CONFIG_DIR="/etc/alloy"

# Always deploy common + base + logs
sudo cp configs/alloy/common/*.alloy $ALLOY_CONFIG_DIR/
sudo cp configs/alloy/linux/base.alloy $ALLOY_CONFIG_DIR/
sudo cp configs/alloy/linux/logs_journal.alloy $ALLOY_CONFIG_DIR/

# Deploy role-specific config (example: Docker host)
sudo cp configs/alloy/linux/role_docker.alloy $ALLOY_CONFIG_DIR/
```

### 4. Set Environment Variables

Create or edit `/etc/default/alloy`:

```bash
ALLOY_ENV=prod
ALLOY_DATACENTER=site-a
ALLOY_ROLE=docker
PROMETHEUS_REMOTE_WRITE_URL=http://prometheus:9090/api/v1/write
LOKI_WRITE_URL=http://loki:3100/loki/api/v1/push
```

### 5. Configure the Systemd Service

Edit the Alloy systemd unit to point at the config directory:

```bash
sudo systemctl edit alloy
```

Add the override:

```ini
[Service]
ExecStart=
ExecStart=/usr/bin/alloy run /etc/alloy/
EnvironmentFile=/etc/default/alloy
```

### 6. Start and Verify

```bash
sudo systemctl daemon-reload
sudo systemctl enable alloy
sudo systemctl start alloy

# Check status
sudo systemctl status alloy

# View logs
sudo journalctl -u alloy -f

# Alloy UI at http://localhost:12345
```

---

## Validation

Before deploying configs to production, use `alloy fmt` to check syntax:

```bash
# Format check (does not modify, exits non-zero on bad syntax)
alloy fmt --test configs/alloy/common/
alloy fmt --test configs/alloy/windows/
alloy fmt --test configs/alloy/linux/
```

The Alloy UI at `http://localhost:12345` shows:
- Component health (green = running, red = error)
- Data flow graph (which components feed into which)
- Recent errors and warnings

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Alloy fails to start | Syntax error in .alloy file | Run `alloy fmt --test <dir>` to find errors |
| Metrics not appearing in Prometheus | Wrong `PROMETHEUS_REMOTE_WRITE_URL` | Verify URL is reachable from the server |
| Logs not appearing in Loki | Wrong `LOKI_WRITE_URL` or missing journal permissions | Verify URL; check `alloy` user is in `systemd-journal` group |
| Component label conflict | Two role configs define same component label | Only deploy one role config per role, or check for label conflicts |
| High cardinality metrics | Service filter too broad | Tighten the `where_clause` in the exporter's `service` block |
| Windows Event Log missing events | Alloy service account lacks permissions | Run Alloy as Local System or grant Event Log Readers group |
| Docker container logs not appearing | Alloy not in docker group | Run `sudo usermod -aG docker alloy` and restart Alloy |
| Server not appearing in dashboards | Labels mismatch | Check `ALLOY_DATACENTER` matches dashboard variable values; verify `remote_write` URL |
| Duplicate hostnames | Two servers report same hostname | Hostnames must be unique within a datacenter; use FQDN or add a disambiguating label |

---

## Fleet Onboarding

### Label Taxonomy

The platform uses five standard labels across all metrics and logs:

| Label | Source | Purpose | Example |
|-------|--------|---------|---------|
| environment | ALLOY_ENV | Deployment tier | prod, staging, dev |
| datacenter | ALLOY_DATACENTER | Physical/logical site | us-east-1, site-alpha |
| role | ALLOY_ROLE | Server function | dc, sql, iis, fileserver, docker, generic |
| os | Static in config | Operating system | windows, linux |
| hostname | Auto-detected | Server name | srv-web-01 |

Dashboard template variables filter on these labels. Alert routing uses `datacenter` for per-site notification. The Enterprise NOC auto-discovers sites from unique `datacenter` values. No backend config changes are needed when adding new servers or sites.

### Adding a New Site (Datacenter)

1. **Choose a site code**: Use a consistent, short identifier (`site-alpha`, `us-east-dc1`). This becomes `ALLOY_DATACENTER` for all servers at that site. Once chosen, do NOT change it (breaks historical metric continuity).
2. **Deploy backend** (if dedicated): For hub-and-spoke, a single central Prometheus/Loki/Grafana serves all sites. For per-site, deploy a separate stack (see `docs/BACKEND_DEPLOYMENT.md`).
3. **Deploy site gateway** (optional): Required for SNMP, Redfish, or certificate monitoring at the site. See `configs/alloy/gateway/site_gateway.alloy`.
4. **Configure alert routing**: Add site-specific email routing in `configs/alertmanager/alertmanager.yml`, matching on the `datacenter` label.
5. **Verify**: Deploy one test agent, check the Enterprise NOC dashboard for the new site.

### Adding Multiple Servers (Bulk Onboarding)

For deploying to many servers, create a CSV inventory:

```csv
hostname,site,role,os,ip_address
srv-web-01,site-alpha,iis,windows,10.0.1.10
srv-sql-01,site-alpha,sql,windows,10.0.1.20
srv-docker-01,site-alpha,docker,linux,10.0.2.10
```

Automation options: Ansible (recommended for large fleets), PowerShell remoting (Windows-only), SSH + shell scripts (Linux-only), SCCM/Intune (enterprises with existing device management).

### Decommissioning

**Removing a server**: Stop and uninstall Alloy. Metrics age out based on Prometheus retention (default 15 days). No backend config changes needed. An alert will fire for host unreachable -- silence or acknowledge it.

**Removing a site**: Decommission all servers, remove the site gateway, remove site-specific alert routing from `alertmanager.yml`, remove the site email from Helm values. Historical data ages out. The site disappears from the Enterprise NOC once metrics expire.

**Removing a network device / BMC / certificate endpoint**: Remove the target from `site_gateway.alloy` or `role_cert_monitor.alloy`, reload Alloy config (`kill -HUP <pid>` or restart).

### Post-Deployment Checklist

- [ ] Alloy UI accessible on port 12345
- [ ] Metrics visible in Prometheus (`up{hostname="<server>"}`)
- [ ] Logs visible in Loki (`{hostname="<server>"}`)
- [ ] Server appears in appropriate dashboard
- [ ] Alerts would fire if thresholds breached

### Firewall Rules

Outbound from every monitored server:

- TCP to Prometheus `remote_write` endpoint (default 9090)
- TCP to Loki push endpoint (default 3100)

No inbound ports are needed on monitored servers (push model).
