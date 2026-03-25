# Adding a New Server to Monitoring

Step-by-step guide for adding a Windows or Linux server to the monitoring platform. No code knowledge required -- just follow the steps.

**Time required**: 15-20 minutes per server.

---

## Before You Start

You need:
- Administrator access to the server being added
- The monitoring platform URLs:
  - Prometheus: `http://<prometheus-host>:9090`
  - Loki: `http://<loki-host>:3100`
  - Grafana: `http://<grafana-host>:3000`
- The server's **site code** (e.g., `dv`, `ent`, `sbt`) and **role** (e.g., `dc`, `sql`, `iis`, `fileserver`, `generic`)

If you don't know the site code or role, ask your site lead or check the NOC dashboard in Grafana for the list of existing sites.

---

## Step 1: Determine the Server's Role

The role controls which metrics are collected. Pick the role that matches the server's primary function:

| Role | ALLOY_ROLE Value | When to Use |
|------|------------------|-------------|
| Domain Controller | `dc` | Server runs AD DS (includes DNS and DHCP if co-located) |
| SQL Server | `sql` | Server runs Microsoft SQL Server |
| IIS Web Server | `iis` | Server runs IIS for web hosting |
| File Server | `fileserver` | Server is a dedicated file/DFS server |
| DHCP Server | `dhcp` | Dedicated DHCP server (not co-located on a DC) |
| Certificate Authority | `ca` | Server runs AD Certificate Services |
| Docker Host | `docker` | Linux server running Docker containers |
| Generic | `generic` | Any server without a specific role above |

**Important**: If a server has multiple roles (e.g., DC + DHCP), use the primary role. The DC role already includes DHCP metrics. Do not deploy both `role_dc.alloy` and `role_dhcp.alloy` on the same server.

---

## Step 2: Install Grafana Alloy

### Windows

1. Download the Grafana Alloy MSI installer from the [Grafana releases page](https://grafana.com/docs/alloy/latest/install/windows/)
2. Run the installer with default settings
3. Alloy installs to `C:\Program Files\GrafanaLabs\Alloy\`
4. The Alloy service is created but not started yet

### Linux

**Debian/Ubuntu:**
```bash
sudo apt-get install -y grafana-alloy
```

**RHEL/CentOS/Rocky:**
```bash
sudo yum install -y grafana-alloy
```

Or download the binary from the Grafana releases page and install manually.

---

## Step 3: Deploy Configuration Files

Copy the appropriate config files from the repository to the Alloy config directory on the server.

### Windows

Open an elevated PowerShell prompt:

```powershell
$alloyConfigDir = "C:\Program Files\GrafanaLabs\Alloy\config"

# Create config directory if it doesn't exist
New-Item -ItemType Directory -Force -Path $alloyConfigDir

# Copy common configs (required for ALL servers)
Copy-Item configs\alloy\common\*.alloy $alloyConfigDir

# Copy Windows base and log collection (required for ALL Windows servers)
Copy-Item configs\alloy\windows\base.alloy $alloyConfigDir
Copy-Item configs\alloy\windows\logs_eventlog.alloy $alloyConfigDir

# Copy the role-specific config (pick ONE based on Step 1)
# Example for a Domain Controller:
Copy-Item configs\alloy\windows\role_dc.alloy $alloyConfigDir
```

### Linux

```bash
ALLOY_CONFIG_DIR="/etc/alloy"

# Copy common configs (required for ALL servers)
sudo cp configs/alloy/common/*.alloy $ALLOY_CONFIG_DIR/

# Copy Linux base and log collection (required for ALL Linux servers)
sudo cp configs/alloy/linux/base.alloy $ALLOY_CONFIG_DIR/
sudo cp configs/alloy/linux/logs_journal.alloy $ALLOY_CONFIG_DIR/

# Copy the role-specific config (if applicable)
# Example for a Docker host:
sudo cp configs/alloy/linux/role_docker.alloy $ALLOY_CONFIG_DIR/
```

---

## Step 4: Set Environment Variables

Alloy configs read environment variables to know where to send data and how to label the server.

### Windows (PowerShell, elevated)

Replace the placeholder values with your actual site code, role, and monitoring URLs:

```powershell
[System.Environment]::SetEnvironmentVariable("ALLOY_ENV", "prod", "Machine")
[System.Environment]::SetEnvironmentVariable("ALLOY_DATACENTER", "dv", "Machine")
[System.Environment]::SetEnvironmentVariable("ALLOY_ROLE", "dc", "Machine")
[System.Environment]::SetEnvironmentVariable("PROMETHEUS_REMOTE_WRITE_URL", "http://prometheus.example.com:9090/api/v1/write", "Machine")
[System.Environment]::SetEnvironmentVariable("LOKI_WRITE_URL", "http://loki.example.com:3100/loki/api/v1/push", "Machine")
```

**Role-specific variables** (only if needed):

```powershell
# SQL Server only:
[System.Environment]::SetEnvironmentVariable("SQL_ERROR_LOG_PATH", "C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\Log", "Machine")

# IIS only:
[System.Environment]::SetEnvironmentVariable("IIS_LOG_PATH", "C:\inetpub\logs\LogFiles", "Machine")
```

### Linux

Edit `/etc/alloy/environment` (create if it doesn't exist):

```bash
ALLOY_ENV=prod
ALLOY_DATACENTER=dv
ALLOY_ROLE=docker
PROMETHEUS_REMOTE_WRITE_URL=http://prometheus.example.com:9090/api/v1/write
LOKI_WRITE_URL=http://loki.example.com:3100/loki/api/v1/push
```

For Docker hosts, also set:
```bash
DOCKER_METRICS_HOST=127.0.0.1:9323
DOCKER_SOCKET_PATH=unix:///var/run/docker.sock
```

---

## Step 5: Start the Alloy Service

### Windows

```powershell
Start-Service "Grafana Alloy"

# Verify it's running
Get-Service "Grafana Alloy"
```

### Linux

```bash
sudo systemctl enable alloy
sudo systemctl start alloy

# Verify it's running
sudo systemctl status alloy
```

---

## Step 6: Verify in Grafana

Wait 2-3 minutes for the first metrics to arrive, then verify:

1. Open Grafana in your browser
2. Go to the appropriate dashboard:
   - Windows server: **Servers > Windows Server Overview**
   - Linux server: **Servers > Linux Server Overview**
   - Role-specific: **Servers > [Role] Overview** (e.g., SQL Server Overview)
3. Use the **hostname** dropdown at the top to select your new server
4. Verify that panels show data (CPU, memory, disk, network)

If the server does not appear in the dropdown after 5 minutes, see the Troubleshooting section below.

---

## Troubleshooting

**Server not appearing in Grafana dropdown:**
1. Check that the Alloy service is running on the server
2. Check Alloy logs for errors:
   - Windows: Event Viewer > Application log, source "Alloy"
   - Linux: `journalctl -u alloy --since "10 minutes ago"`
3. Verify the `PROMETHEUS_REMOTE_WRITE_URL` is correct and reachable from the server:
   - `curl http://prometheus.example.com:9090/-/healthy` (should return "Prometheus Server is Healthy")
4. Check firewall rules: the server must be able to reach Prometheus on port 9090 and Loki on port 3100

**Metrics appear but no logs:**
1. Verify `LOKI_WRITE_URL` is set correctly
2. Check that the log collection config is deployed (`logs_eventlog.alloy` for Windows, `logs_journal.alloy` for Linux)
3. Check Alloy logs for Loki connection errors

**Wrong role or site label:**
1. Fix the environment variable (`ALLOY_ROLE` or `ALLOY_DATACENTER`)
2. Restart the Alloy service
3. The corrected labels will appear within 2-3 minutes

---

## Summary of Files Per Server

| Server Type | Config Files to Deploy |
|-------------|----------------------|
| Windows (any role) | `common/*.alloy` + `windows/base.alloy` + `windows/logs_eventlog.alloy` + `windows/role_<role>.alloy` |
| Linux (generic) | `common/*.alloy` + `linux/base.alloy` + `linux/logs_journal.alloy` |
| Linux (Docker) | `common/*.alloy` + `linux/base.alloy` + `linux/logs_journal.alloy` + `linux/role_docker.alloy` |

| Environment Variable | Required | Example |
|---------------------|----------|---------|
| `ALLOY_ENV` | Yes | `prod` |
| `ALLOY_DATACENTER` | Yes | `dv` |
| `ALLOY_ROLE` | Yes | `dc`, `sql`, `iis`, `generic` |
| `PROMETHEUS_REMOTE_WRITE_URL` | Yes | `http://prometheus:9090/api/v1/write` |
| `LOKI_WRITE_URL` | Yes | `http://loki:3100/loki/api/v1/push` |
