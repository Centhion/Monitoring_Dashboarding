# Audit Logging Architecture

## Overview

The monitoring platform provides Tier 1 and partial Tier 2 audit logging for Grafana using the OSS edition. Grafana server logs are captured, enriched, and forwarded to Loki for long-term storage, querying, and dashboard visibility.

## Audit Tiers

| Tier | Capability | This Platform | Requires |
|------|-----------|---------------|----------|
| Tier 1 | Login/logout events, session tracking | Covered | Grafana OSS |
| Tier 2 | Dashboard CRUD, alert changes, API activity | Partial | Grafana OSS (log parsing) |
| Tier 2+ | Detailed change diffs, before/after state | Not covered | Grafana Enterprise |
| Tier 3 | Compliance-grade audit with tamper-proof storage | Not covered | Grafana Enterprise + external SIEM |

## Data Flow

```
Grafana Server
  |-- Writes structured JSON logs to /var/log/grafana/grafana.log
  |
Alloy (role_grafana_audit.alloy)
  |-- Tails the log file via loki.source.file
  |-- Extracts labels: level, logger, method, status
  |-- Adds static labels: datacenter, environment, source=grafana, log_type=audit
  |
Loki
  |-- Stores audit log entries with labels
  |-- Retention follows Loki's configured retention period
  |
Grafana Dashboard (audit_trail.json)
  |-- Queries Loki via LogQL
  |-- Shows login events, dashboard changes, alert modifications
```

## Configuration

### Grafana Logging (Environment Variables)

Set these environment variables on the Grafana instance to enable structured JSON logging:

```bash
GF_LOG_MODE=file
GF_LOG_LEVEL=info
GF_LOG_CONSOLE_FORMAT=json
GF_LOG_FILTERS=context:info
```

For Docker Compose, add to the `grafana` service environment in `deploy/docker/docker-compose.yml`.

For Kubernetes, add to the Grafana deployment env section or ConfigMap.

### Alloy Configuration

The `configs/alloy/roles/role_grafana_audit.alloy` config must run on the same host/pod as Grafana. It:

1. Tails `GRAFANA_LOG_PATH` (default: `/var/log/grafana/grafana.log`)
2. Parses JSON log entries for `lvl`, `logger`, `method`, `status` fields
3. Applies `level` and `logger` as Loki labels (low cardinality)
4. Forwards to a dedicated `loki.write` endpoint

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_LOG_PATH` | `/var/log/grafana/grafana.log` | Path to Grafana server log file |
| `LOKI_WRITE_URL` | (required) | Loki push API endpoint |
| `ALLOY_DATACENTER` | (required) | Site/datacenter label |
| `ALLOY_ENV` | (required) | Environment label |

## What Gets Captured

### Tier 1: Authentication Events
- User login (successful and failed)
- Session creation and expiration
- API key usage
- OAuth/LDAP authentication events

### Tier 2 (Partial): User Actions
- Dashboard create, update, delete (via API logger)
- Alert rule modifications
- Notification policy changes
- Folder and permission changes
- Data source modifications
- User and team management

### Not Captured (Requires Enterprise)
- Exact field-level changes (before/after diffs)
- Dashboard version comparison
- Compliance-grade immutable audit log
- SCIM provisioning events

## Querying Audit Logs

### LogQL Examples

```logql
# All login events
{job="grafana_audit"} |~ "(?i)login|session"

# Failed logins only
{job="grafana_audit", level="warn"} |~ "login"

# Dashboard modifications
{job="grafana_audit", logger="api"} | json | method=~"POST|PUT|DELETE" | line_format "{{.path}}" |~ "dashboard"

# All actions by a specific user
{job="grafana_audit"} | json | uname="admin"

# API activity in the last hour
{job="grafana_audit", logger="api"} | json
```

## Dashboard

The Audit Trail dashboard (`dashboards/overview/audit_trail.json`) provides:
- Login activity summary (total events, failed logins)
- Dashboard modification log
- Alert configuration change log
- API request volume and status distribution
- Full audit log with search

## Limitations

1. **Log format dependency**: The label extraction pipeline assumes Grafana's JSON log format. Changes in Grafana versions may require pipeline updates.
2. **No change diffs**: OSS Grafana logs the action (POST /api/dashboards/db) but not what specifically changed in the dashboard JSON.
3. **Log volume**: At `info` level, Grafana generates significant log volume. Loki retention should be sized accordingly.
4. **Delayed visibility**: Log tailing introduces a few seconds of delay between the action and its appearance in the audit dashboard.

## Configuration Files

| File | Purpose |
|------|---------|
| `configs/alloy/roles/role_grafana_audit.alloy` | Alloy log tailing and forwarding |
| `dashboards/overview/audit_trail.json` | Audit Trail Grafana dashboard |
| `deploy/docker/docker-compose.yml` | Grafana logging env vars (GF_LOG_*) |
