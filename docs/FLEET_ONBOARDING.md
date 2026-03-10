# Fleet Onboarding Guide

Comprehensive guide for onboarding sites, servers, and devices into the monitoring platform.

---

## Overview

- How to add new sites (datacenters), servers, and network devices to the monitoring platform.
- Label-driven architecture: dashboards auto-populate when agents report with correct labels.
- No central registration needed -- deploy the agent with the correct environment variables and data flows automatically.

---

## Label Taxonomy

The platform uses five standard labels across all metrics and logs:

| Label | Source | Purpose | Example |
|-------|--------|---------|---------|
| environment | ALLOY_ENV | Deployment tier | prod, staging, dev |
| datacenter | ALLOY_DATACENTER | Physical/logical site | us-east-1, site-alpha |
| role | ALLOY_ROLE | Server function | dc, sql, iis, fileserver, docker, generic |
| os | Static in config | Operating system | windows, linux |
| hostname | Auto-detected | Server name | srv-web-01 |

### Why This Matters

- Dashboard template variables filter on these labels.
- Alert routing uses `datacenter` for per-site notification.
- The Enterprise NOC auto-discovers sites from unique `datacenter` values.
- No config changes are needed on the backend when adding new servers or sites.

---

## Adding a New Site (Datacenter)

### Step 1: Choose a Site Code

- Use a consistent, short identifier: `site-alpha`, `us-east-dc1`, `london-01`.
- This becomes the `ALLOY_DATACENTER` value for all servers at that site.
- Once chosen, do NOT change it (breaks historical metric continuity).

### Step 2: Deploy Backend (if Dedicated)

- For hub-and-spoke: a single central Prometheus/Loki/Grafana serves all sites.
- For per-site: deploy a Prometheus/Loki stack at the site (see `docs/BACKEND_DEPLOYMENT.md`).
- Most deployments use a centralized backend with `remote_write` from agents.

### Step 3: Deploy Site Gateway (Optional)

- Required if the site has network devices (SNMP), hardware BMCs (Redfish), or certificates to monitor.
- See `configs/alloy/gateway/site_gateway.alloy`.
- Configure `ALLOY_DATACENTER` to match the site code.
- Add SNMP targets, Redfish targets, and certificate endpoints as needed.

### Step 4: Configure Alert Routing

- Add site-specific email routing in `configs/alertmanager/alertmanager.yml`.
- Match on the `datacenter` label to route alerts to the correct site ops team.
- Add the site email in Helm `values.yaml` under `alertmanager.siteEmails`.

### Step 5: Verify

- Deploy one test agent at the site.
- Check the Enterprise NOC dashboard -- the new site should appear in the grid.
- Check the Site Overview dashboard with the `datacenter` filter set to the new site.

---

## Adding a New Server

### Windows Server

#### Prerequisites

- Windows Server 2016+ recommended.
- Administrative access for Alloy installation.
- Network access from the server to Prometheus (`remote_write`) and Loki (push) endpoints.
- Identify server role: `dc`, `sql`, `iis`, `fileserver`, or `generic`.

#### Step 1: Install Alloy

```powershell
# Download Alloy installer from Grafana releases
# Install to default path
msiexec /i alloy-installer-windows-amd64.msi /quiet
```

#### Step 2: Deploy Configuration Files

Copy these config files to `C:\Program Files\GrafanaLabs\Alloy\config\`:

- From `configs/alloy/common/`: `labels.alloy`, `remote_write.alloy`, `loki_push.alloy`
- From `configs/alloy/windows/`: `base.alloy`, `logs_eventlog.alloy`
- Role-specific: `role_dc.alloy`, `role_sql.alloy`, `role_iis.alloy`, or `role_fileserver.alloy`

#### Step 3: Set Environment Variables

```powershell
[System.Environment]::SetEnvironmentVariable("ALLOY_ENV", "prod", "Machine")
[System.Environment]::SetEnvironmentVariable("ALLOY_DATACENTER", "site-alpha", "Machine")
[System.Environment]::SetEnvironmentVariable("ALLOY_ROLE", "iis", "Machine")
[System.Environment]::SetEnvironmentVariable("PROMETHEUS_REMOTE_WRITE_URL", "http://prometheus.monitoring:9090/api/v1/write", "Machine")
[System.Environment]::SetEnvironmentVariable("LOKI_WRITE_URL", "http://loki.monitoring:3100/loki/api/v1/push", "Machine")
```

Role-specific variables:

```powershell
# SQL Server role
[System.Environment]::SetEnvironmentVariable("SQL_ERROR_LOG_PATH", "C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\Log", "Machine")

# IIS role
[System.Environment]::SetEnvironmentVariable("IIS_LOG_PATH", "C:\inetpub\logs\LogFiles", "Machine")
```

#### Step 4: Configure and Start Service

```powershell
# Update service to use config directory
sc.exe config "Alloy" binPath= "\"C:\Program Files\GrafanaLabs\Alloy\alloy-windows-amd64.exe\" run \"C:\Program Files\GrafanaLabs\Alloy\config\""

# Restart service
Restart-Service Alloy
```

#### Step 5: Verify

- Open `http://localhost:12345` for the Alloy UI.
- Check the Windows Server Overview dashboard with the hostname filter.
- Verify metrics: `up{job="windows_base", hostname="<server>"}`.

### Linux Server

#### Prerequisites

- Ubuntu 20.04+, RHEL/Rocky 8+, or Debian 11+.
- sudo/root access for installation.
- Network access to Prometheus and Loki endpoints.
- Identify server role: `docker` or `generic`.

#### Step 1: Install Alloy

```bash
# Ubuntu/Debian
sudo apt-get install -y grafana-alloy

# RHEL/Rocky
sudo yum install -y grafana-alloy
```

#### Step 2: Deploy Configuration Files

```bash
sudo cp configs/alloy/common/*.alloy /etc/alloy/
sudo cp configs/alloy/linux/base.alloy /etc/alloy/
sudo cp configs/alloy/linux/logs_journal.alloy /etc/alloy/
# Role-specific
sudo cp configs/alloy/linux/role_docker.alloy /etc/alloy/  # if Docker host
```

#### Step 3: Set Environment Variables

```bash
sudo tee /etc/default/alloy > /dev/null << 'EOF'
ALLOY_ENV=prod
ALLOY_DATACENTER=site-alpha
ALLOY_ROLE=docker
PROMETHEUS_REMOTE_WRITE_URL=http://prometheus.monitoring:9090/api/v1/write
LOKI_WRITE_URL=http://loki.monitoring:3100/loki/api/v1/push
EOF
```

#### Step 4: Configure and Start

```bash
# Add alloy user to required groups
sudo usermod -aG systemd-journal alloy
sudo usermod -aG adm alloy
sudo usermod -aG docker alloy  # if Docker host

# Create systemd override to load environment file
sudo systemctl edit alloy
# Add: EnvironmentFile=/etc/default/alloy

sudo systemctl enable --now alloy
```

#### Step 5: Verify

- Check: `systemctl status alloy`
- Open `http://localhost:12345` for the Alloy UI.
- Check the Linux Server Overview dashboard with the hostname filter.

---

## Adding Multiple Servers (Bulk Onboarding)

### CSV Inventory Approach

For deploying to many servers, create a CSV inventory:

```csv
hostname,site,role,os,ip_address
srv-web-01,site-alpha,iis,windows,10.0.1.10
srv-sql-01,site-alpha,sql,windows,10.0.1.20
srv-docker-01,site-alpha,docker,linux,10.0.2.10
```

### Automation Options

1. **Ansible** (recommended for large fleets): Use `deploy/ansible/` playbooks (planned Phase 5.7).
2. **PowerShell remoting**: For Windows-only environments.
3. **SSH + shell scripts**: For Linux-only environments.
4. **SCCM/Intune**: For enterprises with existing device management.

### Ansible Playbook Pattern (Planned)

```yaml
# ansible/deploy_alloy.yml (planned structure)
- hosts: monitoring_targets
  roles:
    - role: alloy_agent
      vars:
        alloy_env: "{{ alloy_env | default('prod') }}"
        alloy_datacenter: "{{ site_code }}"
        alloy_role: "{{ server_role }}"
```

---

## Adding Network Devices

See `docs/SNMP_MONITORING.md` for adding switches, firewalls, APs, and UPS units.

---

## Adding Hardware BMCs

See `docs/HARDWARE_MONITORING.md` for adding iLO/iDRAC endpoints.

---

## Adding Certificate Endpoints

See `docs/CERTIFICATE_MONITORING.md` for adding TLS/HTTPS endpoints.

---

## Decommissioning

### Removing a Server

1. Stop and uninstall Alloy on the server.
2. Metrics will naturally age out based on Prometheus retention (default 15 days).
3. No backend config changes needed -- the server simply stops reporting.
4. An alert will fire for host unreachable (expected) -- silence or acknowledge it.

### Removing a Site

1. Decommission all servers at the site (stop Alloy agents).
2. Remove the site gateway container.
3. Remove site-specific alert routing from `alertmanager.yml`.
4. Remove the site email from Helm values.
5. Historical data ages out based on retention.
6. The site disappears from the Enterprise NOC once all metrics expire.

### Removing a Network Device / BMC / Certificate Endpoint

1. Remove the target from `site_gateway.alloy` or `role_cert_monitor.alloy`.
2. Reload Alloy config: `kill -HUP <alloy_pid>` or restart the service.
3. Metrics age out based on retention.

---

## Validation

### Config Validation Before Deployment

```bash
# Validate Alloy syntax
alloy fmt --test configs/alloy/

# Validate all configs
python3 scripts/validate_all.py
```

### Post-Deployment Checklist

- [ ] Alloy UI accessible on port 12345
- [ ] Metrics visible in Prometheus (`up{hostname="<server>"}`)
- [ ] Logs visible in Loki (`{hostname="<server>"}`)
- [ ] Server appears in appropriate dashboard
- [ ] Alerts would fire if thresholds breached (verify with test data or PromQL)

---

## Common Issues

### Server Not Appearing in Dashboards

1. Check that `ALLOY_DATACENTER` matches dashboard variable values.
2. Verify the `remote_write` URL is correct and reachable.
3. Check Alloy logs for connection errors.
4. Ensure labels match dashboard query filters.

### Duplicate Hostnames

- Hostnames must be unique within a datacenter.
- If two servers report the same hostname, metrics will conflict.
- Use FQDN or add a disambiguating label.

### Firewall Rules

Outbound from every monitored server:

- TCP to Prometheus `remote_write` endpoint (default 9090).
- TCP to Loki push endpoint (default 3100).

No inbound ports are needed on monitored servers (push model).

---

## Related Documentation

- `docs/ALLOY_DEPLOYMENT.md` -- Detailed Alloy installation and configuration
- `docs/BACKEND_DEPLOYMENT.md` -- Prometheus, Loki, Grafana deployment
- `docs/SNMP_MONITORING.md` -- Network device onboarding
- `docs/HARDWARE_MONITORING.md` -- BMC onboarding
- `docs/CERTIFICATE_MONITORING.md` -- Certificate endpoint onboarding
- `QUICKSTART.md` -- Initial platform deployment
