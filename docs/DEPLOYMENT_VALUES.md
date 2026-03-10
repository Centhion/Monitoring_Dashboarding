# Deployment Configuration Guide

This document maps every placeholder value in the repository to what you need to replace it with for a production deployment.

**How to use this guide:**
1. Work through the [Quick-Start Checklist](#quick-start-checklist) in order
2. Use the [Configuration Reference](#configuration-reference) to find exact file locations and replacement values
3. See [ARCHITECTURE.md](../ARCHITECTURE.md) for component descriptions, data flow, label taxonomy, and design decisions

---

## Table of Contents

- [Quick-Start Checklist](#quick-start-checklist)
- [Configuration Reference](#configuration-reference)
  - [1. Notification Channels](#1-notification-channels)
  - [2. SMTP / Email Settings](#2-smtp--email-settings)
  - [3. Site / Datacenter Mapping](#3-site--datacenter-mapping)
  - [4. Grafana Admin Credentials](#4-grafana-admin-credentials)
  - [5. Alloy Agent Environment Variables](#5-alloy-agent-environment-variables)
  - [6. SNMP Network Monitoring](#6-snmp-network-monitoring)
  - [7. Hardware / Redfish Monitoring](#7-hardware--redfish-monitoring)
  - [8. Certificate Monitoring](#8-certificate-monitoring)
  - [9. Runbook URLs](#9-runbook-urls)
  - [10. Repository / Org URLs](#10-repository--org-urls)
  - [11. Ingress, Authentication, and RBAC (Future)](#11-ingress-authentication-and-rbac-future)
  - [12. Mimir Long-Term Storage (Future)](#12-mimir-long-term-storage-future)
- [Environment Variable Reference](#environment-variable-reference)
- [Adding a New Site](#adding-a-new-site)
- [Secrets Management](#secrets-management)

---

## Quick-Start Checklist

Complete these in order. Items marked with a lock are secrets that must never be committed to version control.

### Phase 1: Core Platform (get alerts flowing)

- [ ] **Teams Webhook URL** -- Create an Incoming Webhook in your Teams monitoring channel. Replace all `https://example.com/webhook/placeholder` entries in `configs/alertmanager/alertmanager.yml` (9 instances) and set `TEAMS_WEBHOOK_URL` in `.env`.
- [ ] **SMTP Relay** -- Get your mail relay hostname and port from your email team. Replace `smtp.example.com:587` in `configs/alertmanager/alertmanager.yml`.
- [ ] **SMTP Credentials** -- Replace `monitoring@example.com` and `changeme` with your SMTP auth credentials in `configs/alertmanager/alertmanager.yml`.
- [ ] **Grafana Admin Password** -- Replace `admin`/`admin` in your deployment method (Docker Compose `.env` or Helm `values.yaml`).
- [ ] **Prometheus + Loki URLs** -- Set `PROMETHEUS_REMOTE_WRITE_URL` and `LOKI_WRITE_URL` on every Alloy agent host to point at your Prometheus and Loki instances.

### Phase 2: Site Routing (per-datacenter alerting)

- [ ] **Site Names** -- Replace `site-a`, `site-b`, `site-c` with your actual datacenter names in `configs/alertmanager/alertmanager.yml` route matchers and receiver names, and in `configs/grafana/notifiers/notifiers.yml`.
- [ ] **Email Distribution Lists** -- Replace all `*-ops@example.com` addresses with your actual per-site ops team DLs.
- [ ] **Alloy Agent Labels** -- Set `ALLOY_ENV`, `ALLOY_DATACENTER`, and `ALLOY_ROLE` environment variables on every monitored server so alerts carry the correct labels.

### Phase 3: Device Monitoring (optional, per your fleet)

- [ ] **SNMP Targets** -- Populate `configs/alloy/gateway/snmp_targets.yml` with your network device IPs and SNMP credentials.
- [ ] **Redfish Targets** -- Populate `configs/alloy/gateway/redfish_targets.yml` with your server BMC/iLO/iDRAC IPs.
- [ ] **Certificate Endpoints** -- Populate `configs/alloy/certs/endpoints.yml` with HTTPS and TLS endpoints to monitor.

### Phase 4: Documentation (make it yours)

- [ ] **Runbook URLs** -- Replace `https://wiki.example.com/runbooks/*` in alert rule files with links to your internal wiki (19 instances across 3 files).
- [ ] **GitHub Org** -- Replace `<YOUR_ORG>` in `README.md`, `QUICKSTART.md`, and `deploy/helm/monitoring-stack/Chart.yaml`.

---

## Configuration Reference

### 1. Notification Channels

**What**: The Teams webhook URL that Alertmanager and Grafana use to send alert cards.

**How to get it**: In Microsoft Teams, go to the channel where you want alerts, click the `...` menu, select "Connectors" (or "Workflows"), and create an "Incoming Webhook". Copy the generated URL.

| File | Placeholder | Instances |
|------|-------------|-----------|
| `configs/alertmanager/alertmanager.yml` | `https://example.com/webhook/placeholder` | 9 (one per receiver) |
| `deploy/docker/docker-compose.yml` | `https://example.com/webhook/placeholder` | 2 |
| `deploy/helm/monitoring-stack/values.yaml` | `https://example.com/webhook/placeholder` | 1 |
| `.env.example` -> `.env` | `TEAMS_WEBHOOK_URL` | 1 |

**Tip**: All 9 instances in `alertmanager.yml` can use the same webhook URL (all alerts go to one channel), or you can create separate webhooks for different channels (e.g., one for critical, one for info).

---

### 2. SMTP / Email Settings

**What**: SMTP relay configuration for sending alert emails. All Alertmanager email receivers use these global settings.

**Who to ask**: Your email/messaging team for the SMTP relay hostname, port, and whether you need authentication credentials.

| Setting | Placeholder | Replace With |
|---------|-------------|--------------|
| SMTP Host | `smtp.example.com:587` | Your SMTP relay `host:port` |
| Sender Address | `monitoring@example.com` | The "from" address on alert emails |
| Auth Username | `monitoring@example.com` | SMTP login username (often same as sender) |
| Auth Password | `changeme` | SMTP login password |
| TLS Required | `true` | Usually `true` for port 587, `false` for port 25 on internal relays |

**Files to update:**

| File | Fields |
|------|--------|
| `configs/alertmanager/alertmanager.yml` | `global.smtp_smarthost`, `smtp_from`, `smtp_auth_username`, `smtp_auth_password`, `smtp_require_tls` |
| `.env.example` -> `.env` | `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_AUTH_USERNAME`, `SMTP_AUTH_PASSWORD` |
| `deploy/helm/monitoring-stack/values.yaml` | `alertmanager.notifications.smtp.*` |

**Common SMTP configurations:**

| Scenario | Host | Port | TLS | Auth |
|----------|------|------|-----|------|
| Office 365 SMTP relay | `smtp.office365.com` | 587 | Yes | Yes |
| Internal relay (no auth) | `smtp-relay.corp.local` | 25 | No | No |
| Google Workspace | `smtp.gmail.com` | 587 | Yes | Yes (app password) |
| Amazon SES | `email-smtp.us-east-1.amazonaws.com` | 587 | Yes | Yes (IAM credentials) |

---

### 3. Site / Datacenter Mapping

**What**: Maps each datacenter/site to an ops team email distribution list. When an alert fires, it routes to the email DL for the site where the alert originated.

**Template pattern**: The repo ships with 3 example sites. Replace, add, or remove to match your actual sites.

| Template Value | Replace With |
|----------------|--------------|
| `site-a` | Your first datacenter name (e.g., `dc-east`) |
| `site-b` | Your second datacenter name (e.g., `dc-west`) |
| `site-c` | Your third datacenter name (e.g., `cloud-us`) |
| `site-a-ops@example.com` | Email DL for site-a ops team |
| `site-b-ops@example.com` | Email DL for site-b ops team |
| `site-c-ops@example.com` | Email DL for site-c ops team |
| `ops-team@example.com` | Catch-all email DL for unmapped sites |

**Files to update:**

| File | What to Change |
|------|---------------|
| `configs/alertmanager/alertmanager.yml` | Route matchers (`match: datacenter: site-a`), receiver names (`site_a_critical`), email addresses (`to: site-a-ops@example.com`) |
| `configs/grafana/notifiers/notifiers.yml` | Contact point names, policy matchers, email addresses |
| `.env.example` -> `.env` | `SITE_A_EMAIL`, `SITE_B_EMAIL`, `SITE_C_EMAIL`, `ALERT_EMAIL_TO` |
| `deploy/helm/monitoring-stack/values.yaml` | `alertmanager.notifications.siteEmails` map, `defaultEmail` |

**The `datacenter` label on your servers must match the site names in the routing config.** Set via the `ALLOY_DATACENTER` environment variable on each Alloy agent.

See [Adding a New Site](#adding-a-new-site) for step-by-step instructions.

---

### 4. Grafana Admin Credentials

**What**: Initial admin login for the Grafana web UI. Change from the default `admin`/`admin` before any production deployment.

| File | Setting | Default |
|------|---------|---------|
| `deploy/docker/docker-compose.yml` | `GF_SECURITY_ADMIN_USER`, `GF_SECURITY_ADMIN_PASSWORD` | `admin` / `admin` |
| `deploy/helm/monitoring-stack/values.yaml` | `grafana.admin.user`, `grafana.admin.password` | `admin` / `admin` |

**For Helm deployments**: Use `grafana.admin.existingSecret` to reference a pre-created Kubernetes Secret instead of storing the password in `values.yaml`.

---

### 5. Alloy Agent Environment Variables

**What**: Every Alloy agent (installed on monitored servers) needs these environment variables to identify itself and connect to the backend.

| Variable | Purpose | Example | Required |
|----------|---------|---------|----------|
| `ALLOY_ENV` | Environment label | `production` | Yes |
| `ALLOY_DATACENTER` | Site/datacenter label | `dc-east` | Yes |
| `ALLOY_ROLE` | Server role | `sql`, `iis`, `dc`, `file`, `docker` | Yes |
| `PROMETHEUS_REMOTE_WRITE_URL` | Where to send metrics | `http://prometheus:9090/api/v1/write` | Yes |
| `LOKI_WRITE_URL` | Where to send logs | `http://loki:3100/loki/api/v1/push` | Yes |
| `SQL_ERROR_LOG_PATH` | SQL Server error log path | `C:\Program Files\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQL\Log\ERRORLOG` | SQL role only |
| `IIS_LOG_PATH` | IIS access log directory | `C:\inetpub\logs\LogFiles` | IIS role only |

**How to set on Windows**: System > Advanced System Settings > Environment Variables, or via Group Policy for fleet-wide deployment.

**How to set on Linux**: Add to `/etc/alloy/environment` or the systemd unit override.

**Referenced in:**
- `configs/alloy/common/labels.alloy` -- `ALLOY_ENV`, `ALLOY_DATACENTER`, `ALLOY_ROLE`
- `configs/alloy/common/remote_write.alloy` -- `PROMETHEUS_REMOTE_WRITE_URL`
- `configs/alloy/common/loki_push.alloy` -- `LOKI_WRITE_URL`
- `configs/alloy/gateway/site_gateway.alloy` -- all of the above

---

### 6. SNMP Network Monitoring

**What**: Network device monitoring via SNMP polling from the Alloy gateway.

**Files:**

| File | What to Configure |
|------|------------------|
| `configs/alloy/gateway/snmp_auths.yml` | SNMP authentication profiles (community strings, SNMPv3 credentials) |
| `configs/alloy/gateway/snmp_targets.yml` | Device inventory (IPs, hostnames, module assignments, labels) |

**Key values to replace:**

| Placeholder | Replace With |
|-------------|--------------|
| `community: public` | Your actual SNMP community string |
| `${SNMP_V3_USERNAME}` | SNMPv3 auth username (set as env var) |
| `${SNMP_V3_AUTH_PASSWORD}` | SNMPv3 auth password (set as env var) |
| `${SNMP_V3_PRIV_PASSWORD}` | SNMPv3 privacy password (set as env var) |
| `10.0.1.1`, `10.0.1.2`, etc. | Actual device management IP addresses |
| `site-alpha` | Actual datacenter/site name |

**Getting started**: Uncomment the example entries in `snmp_targets.yml` and replace with your devices. Start with one or two devices to validate connectivity before adding the full inventory.

---

### 7. Hardware / Redfish Monitoring

**What**: Server hardware health monitoring via Redfish API (iLO, iDRAC, BMC).

**File**: `configs/alloy/gateway/redfish_targets.yml`

| Placeholder | Replace With |
|-------------|--------------|
| `10.0.1.50`, `10.0.1.51`, etc. | Actual BMC/iLO/iDRAC management IP addresses |
| `site-alpha` | Actual datacenter/site name |
| `hpe-dl380`, `dell-r750` | Actual server model identifiers |

**Prerequisites**: Ensure Redfish API is enabled on your server BMCs and that the Alloy gateway has network access to the BMC management VLAN.

---

### 8. Certificate Monitoring

**What**: TLS certificate expiration monitoring for internal and external endpoints.

**File**: `configs/alloy/certs/endpoints.yml`

| Placeholder | Replace With |
|-------------|--------------|
| `https://portal.example.com` | Your actual HTTPS endpoints |
| `dc01.corp.example.com:636` | Your LDAPS endpoints |
| `smtp-relay.corp.example.com:465` | Your SMTPS endpoints |
| `sql01.corp.example.com:1433` | Your SQL Server TLS endpoints |

**Getting started**: Uncomment the examples and replace with your actual endpoints. Group by certificate provider (internal PKI, DigiCert, Let's Encrypt) using the `cert_source` label.

---

### 9. Runbook URLs

**What**: Links in alert annotations that point operators to investigation procedures in your internal wiki.

**Placeholder**: `https://wiki.example.com/runbooks/<alert-name>`

**Files:**

| File | Alert Count |
|------|-------------|
| `alerts/prometheus/snmp_alerts.yml` | 6 alerts |
| `alerts/prometheus/hardware_alerts.yml` | 8 alerts |
| `alerts/prometheus/cert_alerts.yml` | 5 alerts |

**Replace with**: Your internal wiki or knowledge base URLs. If you do not have a wiki, you can leave these as-is -- the `docs/ALERT_RUNBOOKS.md` file in this repo serves as the built-in runbook reference.

---

### 10. Repository / Org URLs

**What**: GitHub organization name in documentation and Helm chart metadata.

| File | Placeholder |
|------|-------------|
| `README.md` | `<YOUR_ORG>` |
| `QUICKSTART.md` | `<YOUR_ORG>` (2 instances) |
| `deploy/helm/monitoring-stack/Chart.yaml` | `<YOUR_ORG>` (2 instances) |

**Replace with**: Your GitHub organization or username (e.g., `mycompany`).

---

### 11. Ingress, Authentication, and RBAC (Future)

These values are commented out and only needed when you enable Phase B (Ingress), Phase C (LDAP authentication), or Phase 8 (RBAC folder/team provisioning). See [ARCHITECTURE.md](../ARCHITECTURE.md) for the RBAC access tier model and LDAP group sync design.

**Ingress (Phase B):**

| Setting | File | Placeholder |
|---------|------|-------------|
| Grafana Ingress hostname | `values.yaml` | `grafana.example.com` |
| TLS secret name | `values.yaml` | `monitoring-tls` |

**LDAP Authentication (Phase C):**

| Setting | File | Placeholder |
|---------|------|-------------|
| LDAP server | `values.yaml` | `ldap.example.com` |
| LDAP port | `values.yaml` | `636` (LDAPS) |
| LDAP bind DN | `values.yaml` | `cn=readonly,dc=example,dc=com` |
| LDAP bind password | `values.yaml` (via Secret) | LDAP service account password |
| LDAP search base | `values.yaml` | `ou=users,dc=example,dc=com` |
| LDAP search filter | `values.yaml` | `(sAMAccountName=%s)` for AD, `(uid=%s)` for standard LDAP |

**RBAC Group Sync (Phase 8):**

| Setting | File | Placeholder |
|---------|------|-------------|
| LDAP group search base | `grafana.ini` or `ldap.toml` | `ou=groups,dc=example,dc=com` |
| Group search filter | `grafana.ini` or `ldap.toml` | `(objectClass=group)` for AD |
| AD group -> Grafana Team mapping | `ldap.toml` | `SG-Monitoring-Admins` -> `Enterprise Ops`, etc. |
| Grafana org role for LDAP users | `grafana.ini` | `Viewer` (default for auto-provisioned users) |

No action needed until you are ready for these features.

---

### 12. Mimir Long-Term Storage (Future)

**What**: Grafana Mimir replaces Prometheus as the long-term metrics query backend. See [ARCHITECTURE.md](../ARCHITECTURE.md) for the migration architecture and decision criteria.

**Values to configure (Phase 6):**

| Setting | Placeholder | Replace With |
|---------|-------------|--------------|
| Mimir URL | `MIMIR_URL` in `.env.example` | Mimir distributor endpoint (e.g., `http://mimir:9009`) |
| Object storage bucket | `MIMIR_OBJECT_STORAGE_BUCKET` | S3-compatible bucket name for metric chunks (Nutanix Objects or cloud S3/GCS) |
| Object storage endpoint | `MIMIR_OBJECT_STORAGE_ENDPOINT` | S3-compatible endpoint URL (Nutanix Objects endpoint or cloud S3/GCS) |
| Grafana datasource | Prometheus URL in `datasources.yml` | Change to Mimir query-frontend URL |
| Prometheus remote_write | `remote_write` section in `prometheus.yml` | Add Mimir endpoint as a remote_write target |

No action needed until you are ready for Phase 6.

---

## Environment Variable Reference

Complete list of environment variables used across the platform, grouped by where they are consumed.

### Alloy Agent (set on every monitored server)

| Variable | Required | Description |
|----------|----------|-------------|
| `ALLOY_ENV` | Yes | Environment name: `production`, `staging`, `development` |
| `ALLOY_DATACENTER` | Yes | Site/datacenter name: must match routing config |
| `ALLOY_ROLE` | Yes | Server role: `dc`, `sql`, `iis`, `file`, `docker`, `general` |
| `PROMETHEUS_REMOTE_WRITE_URL` | Yes | Prometheus remote write endpoint |
| `LOKI_WRITE_URL` | Yes | Loki push API endpoint |
| `SQL_ERROR_LOG_PATH` | SQL only | Path to SQL Server ERRORLOG file |
| `IIS_LOG_PATH` | IIS only | Path to IIS W3SVC log directory |

### Alloy Gateway (set on the SNMP/Redfish/cert polling server)

| Variable | Required | Description |
|----------|----------|-------------|
| `PROMETHEUS_REMOTE_WRITE_URL` | Yes | Prometheus remote write endpoint |
| `LOKI_WRITE_URL` | Yes | Loki push API endpoint |
| `ALLOY_ENV` | Yes | Environment name |
| `ALLOY_DATACENTER` | Yes | Gateway site location |
| `SNMP_COMMUNITY_STRING` | SNMP only | SNMPv2c community string |
| `SNMP_V3_USERNAME` | SNMPv3 only | SNMPv3 authentication username |
| `SNMP_V3_AUTH_PASSWORD` | SNMPv3 only | SNMPv3 authentication password |
| `SNMP_V3_PRIV_PASSWORD` | SNMPv3 only | SNMPv3 privacy (encryption) password |

### Docker Compose / Kubernetes (set on the monitoring backend)

| Variable | Required | Description |
|----------|----------|-------------|
| `TEAMS_WEBHOOK_URL` | Yes | Microsoft Teams incoming webhook URL |
| `SMTP_HOST` | Yes | SMTP relay hostname |
| `SMTP_PORT` | Yes | SMTP relay port (typically 587 or 25) |
| `SMTP_FROM` | Yes | Sender email address |
| `SMTP_AUTH_USERNAME` | If auth required | SMTP login username |
| `SMTP_AUTH_PASSWORD` | If auth required | SMTP login password |
| `ALERT_EMAIL_TO` | Yes | Default/catch-all ops email DL |
| `SITE_A_EMAIL` | Per site | Site-A ops email distribution list |
| `SITE_B_EMAIL` | Per site | Site-B ops email distribution list |
| `SITE_C_EMAIL` | Per site | Site-C ops email distribution list |

---

## Adding a New Site

When your organization adds a new datacenter or site to the monitoring fleet:

### 1. Alertmanager Routing (`configs/alertmanager/alertmanager.yml`)

Add a route entry under both the **critical** and **warning** severity sections:

```yaml
# Under the critical routes section:
- match:
    datacenter: new-site
  receiver: new_site_critical
  continue: false

# Under the warning routes section:
- match:
    datacenter: new-site
  receiver: new_site_warning
  continue: false
```

Add receiver definitions:

```yaml
- name: new_site_critical
  webhook_configs:
    - url: "https://your-teams-webhook-url"
      send_resolved: true
  email_configs:
    - to: "new-site-ops@yourcompany.com"
      send_resolved: true
      headers:
        Subject: "[CRITICAL] [new-site] {{ .GroupLabels.alertname }} on {{ .GroupLabels.hostname }}"

- name: new_site_warning
  webhook_configs:
    - url: "https://your-teams-webhook-url"
      send_resolved: true
  email_configs:
    - to: "new-site-ops@yourcompany.com"
      send_resolved: true
      headers:
        Subject: "[WARNING] [new-site] {{ .GroupLabels.alertname }} on {{ .GroupLabels.hostname }}"
```

### 2. Grafana Contact Points (`configs/grafana/notifiers/notifiers.yml`)

Add a contact point:

```yaml
- orgId: 1
  name: "New-Site Email"
  receivers:
    - uid: email-new-site
      type: email
      settings:
        addresses: "${NEW_SITE_EMAIL:-new-site-ops@yourcompany.com}"
        singleEmail: true
      disableResolveMessage: false
```

Add policy routes under both critical and warning tiers:

```yaml
- receiver: "New-Site Email"
  matchers:
    - datacenter = new-site
  continue: true
```

### 3. Environment Variables (`.env`)

```bash
NEW_SITE_EMAIL=new-site-ops@yourcompany.com
```

### 4. Helm Values (`deploy/helm/monitoring-stack/values.yaml`)

```yaml
siteEmails:
  new-site: "new-site-ops@yourcompany.com"
```

### 5. Agent Deployment

Set `ALLOY_DATACENTER=new-site` on every server at the new site.

---

## Secrets Management

### What Counts as a Secret

These values must never be committed to Git in plain text:

| Secret | Where Used |
|--------|-----------|
| Teams Webhook URL | `alertmanager.yml`, `.env` |
| SMTP Password | `alertmanager.yml`, `.env` |
| Grafana Admin Password | Docker Compose `.env`, Helm values |
| SNMP Community Strings | `snmp_auths.yml` |
| SNMPv3 Credentials | `snmp_auths.yml` (via env vars) |
| Prometheus/Loki Auth | `remote_write.alloy`, `loki_push.alloy` (via env vars) |

### How Secrets Are Handled

| Deployment Method | Mechanism |
|-------------------|-----------|
| **Docker Compose** | `.env` file (gitignored). Copy `.env.example` to `.env` and fill in real values. |
| **Helm / Kubernetes** | Kubernetes Secrets. Override `values.yaml` with `--set` flags or an external secret manager (Vault, Sealed Secrets). Never commit real values to `values.yaml`. |
| **Alloy Agents** | System environment variables. Set via Group Policy (Windows) or systemd environment files (Linux). |

### Pre-Commit Protection

The repository includes:
- `.gitignore` rules blocking `.env`, `*.key`, `*.pem`, and credential files
- `.claude/settings.json` deny rules preventing agent access to secret files
- Pre-commit scan that flags potential hardcoded secrets before every commit
- Validator warning for the `changeme` placeholder (reminds you to replace it)
