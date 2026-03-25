# Troubleshooting Guide

Common problems and how to diagnose them. Start with the symptom, follow the steps.

---

## No Data on a Dashboard

**Symptom**: Dashboard panels show "No data" or are empty.

### Check 1: Is the server selected?

Most dashboards require selecting a hostname from the dropdown. If no hostname is selected, panels show no data.

### Check 2: Is the time range correct?

Click the time picker (top right). If the time range is set to a period before the server was added to monitoring, there will be no data. Try "Last 1 hour" or "Last 6 hours".

### Check 3: Is the Alloy agent running?

Connect to the server and check:
- Windows: `Get-Service "Grafana Alloy"` -- should show "Running"
- Linux: `systemctl status alloy` -- should show "active (running)"

If stopped, start it and wait 2-3 minutes.

### Check 4: Can the agent reach Prometheus/Loki?

From the server, test connectivity:
```bash
curl http://prometheus.example.com:9090/-/healthy
curl http://loki.example.com:3100/ready
```

If these fail, check firewall rules. The server needs outbound access to ports 9090 and 3100 on the monitoring host.

### Check 5: Is Prometheus receiving data?

Open `http://<prometheus-host>:9090/targets` in your browser. Look for the server's hostname in the target list. If it shows "UP", data is flowing. If "DOWN", the agent is not pushing successfully.

### Check 6: Are the environment variables set?

The agent needs `ALLOY_DATACENTER`, `ALLOY_ROLE`, `PROMETHEUS_REMOTE_WRITE_URL`, and `LOKI_WRITE_URL` set. Missing variables cause silent failures.

- Windows: `[System.Environment]::GetEnvironmentVariable("ALLOY_DATACENTER", "Machine")`
- Linux: `cat /etc/alloy/environment`

---

## Alert Not Firing

**Symptom**: A condition exists (e.g., disk is 95% full) but no alert notification was received.

### Check 1: Is the alert rule enabled?

Open `http://<prometheus-host>:9090/rules`. Find the alert rule. Check:
- Is the rule "active" (condition met)?
- Is the rule in "pending" state? (The `for` duration hasn't elapsed yet. Wait.)
- Is the rule "inactive"? (The condition is not met -- double-check the metric value.)

### Check 2: Is the `for` duration too long?

Alert rules require the condition to persist for the configured duration. A 30-minute `for` duration means the condition must be continuously true for 30 minutes before the alert fires. Check if the condition is intermittent.

### Check 3: Is there an active silence?

Open Grafana > **Alerting** > **Silences**. Check if someone created a silence that matches this alert. If so, the alert fires but notifications are suppressed.

### Check 4: Is Alertmanager delivering?

Open `http://<alertmanager-host>:9093/#/alerts`. The alert should appear here if Prometheus sent it. If it appears in Alertmanager but you didn't get a notification, check:
- Teams webhook URL is correct and working
- SMTP relay is accessible
- The routing tree is sending the alert to the correct receiver for the site

### Check 5: Is an inhibition rule suppressing it?

If a more severe alert is active (e.g., server is down), warning-level alerts on the same host are suppressed by inhibition rules. Check `http://<alertmanager-host>:9093/#/alerts` for related alerts.

---

## Alert Firing But Should Not Be

**Symptom**: Receiving alerts for conditions that are normal for the server.

### Option 1: Silence it temporarily

If this is a known condition during maintenance, create a silence (see `MAINTENANCE_WINDOWS.md`).

### Option 2: Adjust the threshold

If the threshold is wrong for this server's workload, request a threshold change (see `CHANGING_THRESHOLDS.md`).

### Option 3: Check if it's a role mismatch

If a SQL server is alerting on high memory, verify the alert threshold accounts for SQL's memory usage pattern. SQL servers with 128GB RAM legitimately use 90%+.

---

## Dashboard Shows Stale Data

**Symptom**: Data on the dashboard hasn't updated in a while. The last data point is 10+ minutes old.

### Check 1: Is the Alloy agent running?

See "No Data" Check 3 above.

### Check 2: Is Prometheus healthy?

Run `python3 scripts/stack_manage.py --status`. If Prometheus shows unhealthy, restart it:
```bash
docker compose restart prometheus
```

### Check 3: Is the Prometheus disk full?

```bash
docker exec mon-prometheus df -h /prometheus
```

If usage is above 95%, Prometheus may have stopped ingesting. Options:
- Reduce retention: edit `configs/prometheus/prometheus.yml`, lower `--storage.tsdb.retention.time`
- Expand the volume
- Delete old data: `docker exec mon-prometheus promtool tsdb clean` (removes out-of-retention blocks)

---

## Teams Notifications Not Arriving

**Symptom**: Alerts fire in Prometheus/Alertmanager but no Teams messages appear.

### Check 1: Is the webhook URL configured?

Check `.env` for `TEAMS_WEBHOOK_URL`. If it's a placeholder (`https://example.com/webhook/placeholder`), it hasn't been configured yet.

### Check 2: Is Alertmanager healthy?

Open `http://<alertmanager-host>:9093`. If unreachable, restart:
```bash
docker compose restart alertmanager
```

### Check 3: Check Alertmanager logs

```bash
docker compose logs --tail=100 alertmanager | grep -i "error\|fail"
```

Common errors:
- `connection refused` -- webhook URL is wrong or Teams connector is disabled
- `timeout` -- network issue between the Docker host and Teams/Office 365
- `400 Bad Request` -- the webhook message format is invalid

### Check 4: Test the webhook directly

```bash
curl -H "Content-Type: application/json" -d '{"text":"Test from monitoring stack"}' "$TEAMS_WEBHOOK_URL"
```

If this succeeds, the webhook is working and the issue is in Alertmanager's template rendering.

---

## Email Notifications Not Arriving

### Check 1: SMTP configuration

Verify in `configs/alertmanager/alertmanager.yml`:
- `smtp_smarthost` points to your SMTP relay
- `smtp_from` is a valid sender address
- `smtp_auth_username` and `smtp_auth_password` are correct

### Check 2: Network access

The Docker host must be able to reach the SMTP relay on port 587 (or 25). Test:
```bash
docker exec mon-alertmanager nc -zv smtp.example.com 587
```

### Check 3: Check Alertmanager logs for SMTP errors

```bash
docker compose logs --tail=100 alertmanager | grep -i "smtp\|email\|mail"
```

---

## Grafana Login Issues

**Symptom**: Cannot log in to Grafana.

### Local accounts

Default credentials (demo environments only): `admin` / `admin`. Change on first login.

If you forgot the admin password:
```bash
docker exec mon-grafana grafana-cli admin reset-admin-password <new-password>
```

### LDAP login

If LDAP is configured and login fails:
1. Check Grafana logs: `docker compose logs --tail=50 grafana | grep -i ldap`
2. Verify the LDAP bind account credentials in `configs/grafana/ldap.toml`
3. Verify network access from the Docker host to the domain controller on port 636 (LDAPS)
4. Verify the user is a member of an `SG-Monitoring-*` security group

---

## Container Won't Start

If a container fails to start or keeps restarting:

1. Check the container logs:
   ```bash
   docker compose logs --tail=100 <service-name>
   ```

2. Common causes:
   - **Port conflict**: Another process is using the port. Check with `lsof -i :<port>`
   - **Volume permission error**: Docker can't write to the data volume. Check directory ownership.
   - **Invalid configuration**: A YAML syntax error in a config file. The error message usually includes the file name and line number.
   - **Out of disk space**: `df -h` on the Docker host

3. After fixing the issue:
   ```bash
   docker compose up -d <service-name>
   ```
